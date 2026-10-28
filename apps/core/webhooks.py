from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
import json
from apps.processes.models import TestInvitation
from apps.core.integrations.sova import SovaClient
from apps.core.integrations.integrity_guard import extract_integrity_guard
import logging
from apps.activity.models import ActivityEvent
from apps.activity.services import log_event

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("-", " ")
    s = " ".join(s.split())
    return s


@csrf_exempt
def sova_webhook(request):
    # Only operational metadata belongs in standard logs. No raw payloads,
    # auth headers, query strings or identifiers.
    logger.info(
        "SOVA webhook received: method=%s body_bytes=%s",
        request.method,
        len(request.body or b""),
    )

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("SOVA webhook rejected malformed JSON")
        return JsonResponse({"error": "invalid json"}, status=400)
    
    # Legacy file-based webhook debugging intentionally disabled: it stored
    # complete callback bodies and authorization headers on the app server.

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

    overall_raw = payload.get("overall_status") or payload.get("overallStatus") or ""
    overall = _norm(overall_raw)

    current_phase_code = (payload.get("current_phase_code") or payload.get("currentPhaseCode") or "").strip()
    current_phase_idx = payload.get("current_phase_idx")
    if current_phase_idx is None:
        current_phase_idx = payload.get("currentPhaseIdx")

    has_phase_hint = bool(current_phase_code) or (current_phase_idx is not None)

    status_raw = payload.get("status") or payload.get("current_phase_status") or payload.get("currentPhaseStatus") or ""
    status = _norm(status_raw)

    invitation = None
    if request_id:
        invitation = TestInvitation.objects.filter(request_id=request_id).first()
    if not invitation and sova_inv_id:
        invitation = TestInvitation.objects.filter(sova_invitation_id=str(sova_inv_id)).first()
    if not invitation and talena_process_id and talena_candidate_id:
        invitation = TestInvitation.objects.filter(
            process_id=talena_process_id,
            candidate_id=talena_candidate_id
        ).first()

    if not invitation:
        return JsonResponse({"status": "ignored", "reason": "invitation not found"})
    
    old_status = invitation.status
    old_activities = invitation.sova_activities or []
    new_activities = payload.get("activities", []) or []

    old_status_by_name = {
        (item.get("activity") or "").strip(): _norm(item.get("status") or "")
        for item in old_activities
    }

    new_status_by_name = {
        (item.get("activity") or "").strip(): _norm(item.get("status") or "")
        for item in new_activities
    }

    completed_statuses = {"completed", "complete", "finished", "done", "result available", "result_available"}
    started_statuses = {"started", "in progress"}

    for activity_name, new_activity_status in new_status_by_name.items():
        old_activity_status = old_status_by_name.get(activity_name)

        if old_activity_status == new_activity_status:
            continue

        if new_activity_status in started_statuses:
            log_event(
                company=invitation.process.company,
                verb=ActivityEvent.Verb.STATUS_CHANGED,
                actor=None,
                actor_name="SOVA",
                process=invitation.process,
                candidate=invitation.candidate,
                invitation=invitation,
                meta={
                    "old_status": old_activity_status,
                    "new_status": "started",
                    "activity_name": activity_name,
                    "level": "activity",
                },
            )

        elif new_activity_status in completed_statuses:
            log_event(
                company=invitation.process.company,
                verb=ActivityEvent.Verb.STATUS_CHANGED,
                actor=None,
                actor_name="SOVA",
                process=invitation.process,
                candidate=invitation.candidate,
                invitation=invitation,
                meta={
                    "old_status": old_activity_status,
                    "new_status": "completed",
                    "activity_name": activity_name,
                    "level": "activity",
                },
            )

    parsed_integrity_guard = extract_integrity_guard(payload)
    if parsed_integrity_guard is not None:
        invitation.integrity_guard = parsed_integrity_guard

    invitation.sova_payload = payload

    if overall_raw:
        invitation.sova_overall_status = overall_raw.strip()

    invitation.sova_current_phase_code = current_phase_code
    invitation.sova_current_phase_idx = current_phase_idx
    invitation.sova_activities = new_activities
    invitation.sova_phases = payload.get("phases", []) or []
    invitation.sova_reports = payload.get("reports", []) or []

    project_results = payload.get("project_results")
    if isinstance(project_results, dict):
        invitation.project_results = project_results
        invitation.overall_score = project_results.get("overall_score")

    invitation.save(update_fields=[
        "sova_payload",
        *(["integrity_guard"] if parsed_integrity_guard is not None else []),
        "sova_overall_status",
        "sova_current_phase_code",
        "sova_current_phase_idx",
        "sova_activities",
        "sova_phases",
        "sova_reports",
        "project_results",
        "overall_score",
    ])


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
        reason = f"no mapping hit (overall={overall}, status={status})"


    old_status = invitation.status

    if normalized == "started":
        if invitation.status not in {"started", "completed"}:
            invitation.status = "started"
            if hasattr(invitation, "started_at") and not invitation.started_at:
                invitation.started_at = timezone.now()
                invitation.save(update_fields=["status", "started_at"])
            else:
                invitation.save(update_fields=["status"])

            log_event(
                company=invitation.process.company,
                verb=ActivityEvent.Verb.STATUS_CHANGED,
                actor=None,
                actor_name="SOVA",
                process=invitation.process,
                candidate=invitation.candidate,
                invitation=invitation,
                meta={"old_status": old_status, "new_status": "started", "reason": reason},
            )


    elif normalized == "completed":
        if invitation.status != "completed":
            invitation.status = "completed"
            invitation.completed_at = timezone.now()
            invitation.save(update_fields=["status", "completed_at"])

            log_event(
                company=invitation.process.company,
                verb=ActivityEvent.Verb.STATUS_CHANGED,
                actor=None,
                actor_name="SOVA",
                process=invitation.process,
                candidate=invitation.candidate,
                invitation=invitation,
                meta={"old_status": old_status, "new_status": "completed", "reason": reason},
            )



    if normalized == "completed" and not invitation.overall_score and invitation.process.sova_project_id and invitation.request_id:
        try:
            client = SovaClient()
            data = client.get_project_candidates(invitation.process.sova_project_id)
            items = data.get("candidates") if isinstance(data, dict) else data
            items = items or []

            match = next((c for c in items if c.get("request_id") == invitation.request_id), None)
            if match:
                invitation.overall_score = match.get("overall_score")
                invitation.save(update_fields=["overall_score"])
        except Exception:
            logger.warning("SOVA candidate status lookup failed")

    return JsonResponse({"status": "ok"})