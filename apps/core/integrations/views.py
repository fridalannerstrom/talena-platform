import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

from apps.processes.models import TestInvitation
from apps.core.integrations.sova import SovaClient

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
    print("="*80)
    print("🚨 sova_ingest CALLED!")
    print("="*80)
    
    logger.warning("WEBHOOK headers: %s", dict(request.headers))
    logger.warning("Expected secret set? %s", bool(getattr(settings, "SOVA_WEBHOOK_SHARED_SECRET", "")))
    logger.info("✅ sova_ingest HIT")
    
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    # ✅ Enkel auth: shared secret i header
    secret = request.headers.get("X-Talena-Webhook-Secret")
    expected_secret = getattr(settings, "SOVA_WEBHOOK_SHARED_SECRET", "")
    
    print(f"🔐 Received secret: {secret}")
    print(f"🔐 Expected secret: {expected_secret}")
    
    if not secret or secret != expected_secret:
        print("❌ SECRET MISMATCH!")
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
        invitation = TestInvitation.objects.filter(request_id=request_id).first()
    if not invitation and sova_inv_id:
        invitation = TestInvitation.objects.filter(sova_invitation_id=str(sova_inv_id)).first()
    if not invitation and talena_process_id and talena_candidate_id:
        invitation = TestInvitation.objects.filter(
            process_id=talena_process_id,
            candidate_id=talena_candidate_id
        ).first()

    if not invitation:
        print("⚠️ No matching invitation found")
        return JsonResponse({"status": "ignored", "reason": "invitation not found"}, status=200)

    print(f"✅ Found invitation: {invitation.id}")

    # ✅ Spara payload
    invitation.sova_payload = payload
    invitation.save(update_fields=["sova_payload"])

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

    # ✅ Uppdatera status
    if normalized == "started":
        if invitation.status not in {"started", "completed"}:
            invitation.status = "started"
            invitation.save(update_fields=["status"])
            print(f"✅ Updated invitation to STARTED: {invitation.id}")
        else:
            print(f"ℹ️ Skip STARTED update (already {invitation.status})")

    elif normalized == "completed":
        if invitation.status != "completed":
            invitation.status = "completed"
            invitation.completed_at = timezone.now()
            invitation.save(update_fields=["status", "completed_at"])
            print(f"✅ Updated invitation to COMPLETED: {invitation.id}")
        else:
            print("ℹ️ Skip COMPLETED update (already completed)")
    else:
        print("ℹ️ Nothing to update for status.")

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