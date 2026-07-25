import json
import secrets
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

from apps.processes.models import TestInvitation
from apps.core.integrations.sova import SovaClient
from apps.activity.models import ActivityEvent
from apps.activity.services import log_event

from apps.processes.services.assessment_usage import (
    sync_assessment_usage_from_activities,
)

import logging
logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    """Normaliserar SOVA-strängar"""
    s = (s or "").strip().lower()
    s = s.replace("-", " ")
    s = " ".join(s.split())
    return s


@csrf_exempt
def sova_ingest(request):
    print("🚨🚨🚨 INGEST HIT 🚨🚨🚨", request.path)
    print("=" * 80)
    print("🚨 sova_ingest CALLED!")
    print("=" * 80)

    logger.info(
        "SOVA webhook received: path=%s secret_present=%s",
        request.path,
        bool(request.headers.get("X-Talena-Webhook-Secret")),
    )

    if request.method != "POST":
        return JsonResponse(
            {"error": "method not allowed"},
            status=405,
        )

    secret = request.headers.get("X-Talena-Webhook-Secret", "")

    # Accept separate secrets for Sova test and production.
    # The old shared secret is kept temporarily for backwards compatibility.
    configured_secrets = [
        getattr(settings, "SOVA_WEBHOOK_TEST_SECRET", ""),
        getattr(settings, "SOVA_WEBHOOK_PROD_SECRET", ""),
        getattr(settings, "SOVA_WEBHOOK_SHARED_SECRET", ""),
    ]

    # Remove empty values and accidental duplicates.
    allowed_secrets = list({
        configured_secret
        for configured_secret in configured_secrets
        if configured_secret
    })

    logger.info(
        "SOVA webhook authentication: received=%s configured_secret_count=%s",
        bool(secret),
        len(allowed_secrets),
    )

    is_authorized = (
        bool(secret)
        and any(
            secrets.compare_digest(secret, allowed_secret)
            for allowed_secret in allowed_secrets
        )
    )

    if not is_authorized:
        logger.warning("SOVA webhook authentication failed")
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        print(f"❌ JSON parsing error: {e}")
        return JsonResponse({"error": "invalid json"}, status=400)

    print("🔔 Payload received:", payload)

    # ✅ Identifiers
    request_id = payload.get("request_id") or payload.get("requestId")
    sova_inv_id = (
        payload.get("invitation_id") 
        or payload.get("invitationId") 
        or payload.get("invitation") 
        or payload.get("invitation_code")
    )
    
    meta = payload.get("meta_data") or payload.get("metaData") or {}
    talena_process_id = meta.get("talena_process_id")
    talena_candidate_id = meta.get("talena_candidate_id")

    # ✅ VIKTIGT: Läs overall_status (inte bara status!)
    overall_raw = payload.get("overall_status") or payload.get("overallStatus") or ""
    overall = _norm(overall_raw)
    
    current_phase_code = (payload.get("current_phase_code") or payload.get("currentPhaseCode") or "").strip()
    current_phase_idx = payload.get("current_phase_idx")
    if current_phase_idx is None:
        current_phase_idx = payload.get("currentPhaseIdx")
    
    has_phase_hint = bool(current_phase_code) or (current_phase_idx is not None)

    print("🧠 Status fields:", {
        "overall_status_raw": overall_raw,
        "overall_status_norm": overall,
        "current_phase_code": current_phase_code,
        "current_phase_idx": current_phase_idx,
    })
    
    # ✅ Hitta invitation
    invitation = None

    if request_id:
        invitation = TestInvitation.objects.filter(
            request_id=request_id
        ).first()

    if not invitation and sova_inv_id:
        invitation = TestInvitation.objects.filter(
            sova_invitation_id=str(sova_inv_id)
        ).first()

    if not invitation and talena_process_id and talena_candidate_id:
        invitation = TestInvitation.objects.filter(
            process_id=talena_process_id,
            candidate_id=talena_candidate_id,
        ).first()

    if not invitation:
        print("⚠️ No matching invitation found")
        return JsonResponse(
            {
                "status": "ignored",
                "reason": "invitation not found",
            },
            status=200,
        )

    print(f"✅ Found invitation: {invitation.id}")

    old_status = invitation.status
    observed_at = timezone.now()

    # ✅ Extract activities from either top level or phases
    activities = list(payload.get("activities") or [])

    if not activities:
        for phase in payload.get("phases") or []:
            activities.extend(phase.get("activities") or [])

    reports = payload.get("reports") or []

    # ✅ Save the complete payload and UI-specific fields
    invitation.sova_payload = payload
    invitation.sova_activities = activities
    invitation.sova_reports = reports

    invitation.save(
        update_fields=[
            "sova_payload",
            "sova_activities",
            "sova_reports",
        ]
    )
    sync_assessment_usage_from_activities(
        invitation=invitation,
        activities=activities,
        observed_at=observed_at,
    )
    # ✅ Spara overall_status och andra SOVA-fält
    if overall_raw:
        invitation.sova_overall_status = overall_raw.strip()
        print(f"✅ Saving overall_status: '{overall_raw}' to invitation {invitation.id}")
    
    invitation.sova_current_phase_code = current_phase_code
    invitation.sova_current_phase_idx = current_phase_idx
    invitation.save(update_fields=[
        "sova_overall_status", 
        "sova_current_phase_code", 
        "sova_current_phase_idx"
    ])
    
    print("✅ Saved SOVA fields:", {
        "sova_overall_status": invitation.sova_overall_status,
        "sova_current_phase_code": invitation.sova_current_phase_code,
        "sova_current_phase_idx": invitation.sova_current_phase_idx,
    })

    # ✅ Talena status mapping
    OVERALL_COMPLETED = {"completed", "pass", "fail", "refer"}
    OVERALL_STARTED = {"in progress"}
    
    normalized = ""
    reason = ""
    
    if overall in OVERALL_COMPLETED:
        normalized = "completed"
        reason = f"overall={overall}"
    elif overall in OVERALL_STARTED or has_phase_hint:
        normalized = "started"
        reason = f"overall={overall} phase_hint={has_phase_hint}"
    else:
        normalized = ""
        reason = f"no mapping hit (overall={overall})"
    
    print("🧠 Normalized status:", normalized, "| reason:", reason)
    
    # ✅ Update invitation lifecycle status

    if normalized == "started":
        update_fields = []

        status_changed = (
            invitation.status
            not in {
                "started",
                "completed",
            }
        )

        if status_changed:
            invitation.status = "started"
            update_fields.append("status")

        if invitation.started_at is None:
            invitation.started_at = observed_at
            update_fields.append(
                "started_at"
            )

        if update_fields:
            invitation.save(
                update_fields=update_fields
            )

        if status_changed:
            print(
                "✅ Updated invitation to STARTED: "
                f"{invitation.id}"
            )

            log_event(
                company=invitation.process.company,
                verb=ActivityEvent.Verb.STATUS_CHANGED,
                actor=None,
                actor_name="SOVA",
                process=invitation.process,
                candidate=invitation.candidate,
                invitation=invitation,
                meta={
                    "old_status": old_status,
                    "new_status": "started",
                },
            )
        else:
            print(
                "ℹ️ Skip STARTED status update "
                f"(already {invitation.status})"
            )

    elif normalized == "completed":
        update_fields = []

        status_changed = (
            invitation.status != "completed"
        )

        if status_changed:
            invitation.status = "completed"
            update_fields.append("status")

        # A completed invitation must have been started,
        # even if Talena did not receive an earlier webhook.
        if invitation.started_at is None:
            invitation.started_at = observed_at
            update_fields.append(
                "started_at"
            )

        # Preserve the first observed completion time.
        if invitation.completed_at is None:
            invitation.completed_at = observed_at
            update_fields.append(
                "completed_at"
            )

        if update_fields:
            invitation.save(
                update_fields=update_fields
            )

        if status_changed:
            print(
                "✅ Updated invitation to COMPLETED: "
                f"{invitation.id}"
            )

            log_event(
                company=invitation.process.company,
                verb=ActivityEvent.Verb.STATUS_CHANGED,
                actor=None,
                actor_name="SOVA",
                process=invitation.process,
                candidate=invitation.candidate,
                invitation=invitation,
                meta={
                    "old_status": old_status,
                    "new_status": "completed",
                },
            )
        else:
            print(
                "ℹ️ Skip COMPLETED status update "
                "(already completed)"
            )

    else:
        print(
            "ℹ️ Nothing to update for "
            "invitation status."
        )

    # ✅ Results: spara om payload har project_results
    if isinstance(payload.get("project_results"), dict):
        invitation.project_results = payload.get("project_results")
        invitation.save(update_fields=["project_results"])
        print("✅ Saved project_results")

    # ✅ Hämta overall_score från API (bara om completed)
    if normalized == "completed" and invitation.sova_project_id and invitation.request_id:
        try:
            client = SovaClient()
            data = client.get_project_candidates(invitation.sova_project_id)
            items = data.get("candidates") if isinstance(data, dict) else data
            items = items or []
            
            match = next((c for c in items if c.get("request_id") == invitation.request_id), None)
            if match:
                invitation.overall_score = match.get("overall_score")
                invitation.save(update_fields=["overall_score"])
                print(f"✅ Saved overall_score from API: {invitation.overall_score}")
            else:
                print(f"⚠️ No matching request_id in project-candidates: {invitation.request_id}")
        except Exception as e:
            print(f"❌ Error fetching project candidates: {str(e)}")

    return JsonResponse({"status": "ok"})