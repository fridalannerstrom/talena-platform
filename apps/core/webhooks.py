from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
import json
from apps.processes.models import TestInvitation
from apps.core.integrations.sova import SovaClient
import logging
from apps.activity.models import ActivityEvent
from apps.activity.services import log_event
import os
from django.conf import settings

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("-", " ")
    s = " ".join(s.split())
    return s


@csrf_exempt
def sova_webhook(request):
    print("🔥🔥🔥 CORE WEBHOOK HIT 🔥🔥🔥", request.path)
    raw = request.body.decode("utf-8", errors="ignore")
    print("🔎 RAW BODY:", raw)

    logger.warning("WEBHOOK headers(relevant): %s", {
        "Content-Type": request.headers.get("Content-Type"),
        "User-Agent": request.headers.get("User-Agent"),
        "X-Talena-Webhook-Secret": (request.headers.get("X-Talena-Webhook-Secret") or "")[:6] + "...",
        "X-Request-Id": request.headers.get("X-Request-Id"),
        "X-Event-Type": request.headers.get("X-Event-Type"),
    })

    logger.warning(
        "WEBHOOK method=%s path=%s content_type=%s len=%s",
        request.method,
        request.path,
        request.headers.get("Content-Type"),
        len(request.body or b""),
    )

    logger.warning("WEBHOOK RAW FULL (first 2000): %s", raw[:2000])
    logger.warning("WEBHOOK RAW REPR (first 2000): %r", raw[:2000])

    try:
        _debug_payload = json.loads(raw)
        _pretty = json.dumps(_debug_payload, ensure_ascii=False, indent=2)
        logger.warning("WEBHOOK JSON PRETTY (first 4000): %s", _pretty[:4000])
        logger.warning("WEBHOOK JSON KEYS: %s", list(_debug_payload.keys()))
    except Exception as _e:
        logger.warning("WEBHOOK JSON PRETTY failed: %s", str(_e))

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        payload = json.loads(raw)
    except Exception as e:
        print("❌ WEBHOOK invalid JSON:", str(e))
        return JsonResponse({"error": "invalid json"}, status=400)
    
    debug_dir = os.path.join(settings.BASE_DIR, "debug_webhooks")
    os.makedirs(debug_dir, exist_ok=True)

    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S_%f")
    request_id_for_file = (
        payload.get("request_id")
        or payload.get("requestId")
        or "no_request_id"
    )

    safe_request_id = str(request_id_for_file).replace("/", "_").replace("\\", "_").replace(":", "_")

    raw_filepath = os.path.join(debug_dir, f"sova_raw_{timestamp}_{safe_request_id}.txt")
    json_filepath = os.path.join(debug_dir, f"sova_{timestamp}_{safe_request_id}.json")
    headers_filepath = os.path.join(debug_dir, f"sova_headers_{timestamp}_{safe_request_id}.json")

    with open(raw_filepath, "w", encoding="utf-8") as f:
        f.write(raw)

    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(headers_filepath, "w", encoding="utf-8") as f:
        json.dump(dict(request.headers), f, ensure_ascii=False, indent=2)

    print(f"✅ Saved raw webhook body to: {raw_filepath}")
    print(f"✅ Saved parsed webhook JSON to: {json_filepath}")
    print(f"✅ Saved webhook headers to: {headers_filepath}")

    print("🔔 SOVA WEBHOOK RECEIVED (parsed):", payload)

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

    print("🧠 Incoming status fields:", {
        "overall_status_raw": overall_raw,
        "overall_status_norm": overall,
        "status_raw": status_raw,
        "status_norm": status,
        "current_phase_code": current_phase_code,
        "current_phase_idx": current_phase_idx,
    })

    print("🧩 Parsed identifiers:", {
        "request_id": request_id,
        "sova_invitation_id": sova_inv_id,
        "talena_process_id": talena_process_id,
        "talena_candidate_id": talena_candidate_id,
    })

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
        print("⚠️ No matching invitation found.")
        return JsonResponse({"status": "ignored", "reason": "invitation not found"})

    invitation.sova_payload = payload

    if overall_raw:
        invitation.sova_overall_status = overall_raw.strip()
        print(f"✅ Saving overall_status: '{overall_raw}' to invitation {invitation.id}")

    invitation.sova_current_phase_code = current_phase_code
    invitation.sova_current_phase_idx = current_phase_idx
    invitation.sova_activities = payload.get("activities", []) or []
    invitation.sova_phases = payload.get("phases", []) or []
    invitation.sova_reports = payload.get("reports", []) or []

    project_results = payload.get("project_results")
    if isinstance(project_results, dict):
        invitation.project_results = project_results
        invitation.overall_score = project_results.get("overall_score")

    invitation.save(update_fields=[
        "sova_payload",
        "sova_overall_status",
        "sova_current_phase_code",
        "sova_current_phase_idx",
        "sova_activities",
        "sova_phases",
        "sova_reports",
        "project_results",
        "overall_score",
    ])

    print("✅ Saved SOVA fields:", {
        "sova_overall_status": invitation.sova_overall_status,
        "sova_current_phase_code": invitation.sova_current_phase_code,
        "sova_current_phase_idx": invitation.sova_current_phase_idx,
        "activities_count": len(invitation.sova_activities or []),
        "phases_count": len(invitation.sova_phases or []),
        "reports_count": len(invitation.sova_reports or []),
    })

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

    print("🧠 Normalized status:", normalized, "| reason:", reason)

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

            print("✅ Updated invitation to STARTED:", invitation.id)

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

            print("✅ Updated invitation to COMPLETED:", invitation.id)

    else:
        print("ℹ️ Nothing to update for status.")

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
                print("✅ Saved overall_score from API:", invitation.overall_score)
            else:
                print("⚠️ No matching request_id in project-candidates:", invitation.request_id)
        except Exception as e:
            print("❌ Error fetching project candidates:", str(e))

    return JsonResponse({"status": "ok"})