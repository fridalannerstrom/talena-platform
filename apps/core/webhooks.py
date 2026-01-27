from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
import json

from apps.processes.models import TestInvitation
from apps.core.integrations.sova import SovaClient


def _norm(s: str | None) -> str:
    s = (s or "").strip().lower()
    s = s.replace("-", " ")
    s = " ".join(s.split())  # kollapsa flera spaces
    return s  # ex: "in progress"


@csrf_exempt
def sova_webhook(request):
    raw = request.body.decode("utf-8", errors="ignore")
    print("🔎 RAW BODY:", raw)
    print("🔎 HEADERS:", dict(request.headers))

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        print("❌ WEBHOOK invalid JSON:", str(e))
        return JsonResponse({"error": "invalid json"}, status=400)

    print("🔔 SOVA WEBHOOK RECEIVED (parsed):", payload)

    # ── Identifiers ───────────────────────────
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

    current_phase_code = (payload.get("current_phase_code") or payload.get("currentPhaseCode") or "").strip()
    current_phase_idx = payload.get("current_phase_idx")
    if current_phase_idx is None:
        current_phase_idx = payload.get("currentPhaseIdx")

    has_phase_hint = bool(current_phase_code) or (current_phase_idx is not None)

    # ── Statusfält enligt docs ─────────────────
    overall_raw = payload.get("overall_status") or payload.get("overallStatus") or ""
    overall = _norm(overall_raw)  # ex: "pass", "in progress", "completed", "invited"

    # fallback (ifall de skickar current_phase_status)
    phase_status_raw = payload.get("current_phase_status") or payload.get("currentPhaseStatus") or ""
    phase_status = _norm(phase_status_raw)

    print("🧠 Incoming status fields:", {
        "overall_status_raw": overall_raw,
        "overall_status_norm": overall,
        "current_phase_status_raw": phase_status_raw,
        "current_phase_status_norm": phase_status,
        "current_phase_code": current_phase_code,
        "current_phase_idx": current_phase_idx,
        "has_phase_hint": has_phase_hint,
    })

    print("🧩 Parsed identifiers:", {
        "request_id": request_id,
        "sova_invitation_id": sova_inv_id,
        "talena_process_id": talena_process_id,
        "talena_candidate_id": talena_candidate_id,
    })

    # ── Hitta invitation ───────────────────────
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
        print("⚠️ No matching invitation found. (This is why status stays 'sent')")
        return JsonResponse({"status": "ok"})

    # ── Spara payload + SOVA-fält (för admin/UI) ──
    invitation.sova_payload = payload
    # OBS: dessa fält kräver att du lagt till dem i modellen
    # sova_overall_status, sova_current_phase_code, sova_current_phase_idx
    if hasattr(invitation, "sova_overall_status"):
        invitation.sova_overall_status = overall_raw.strip()
    if hasattr(invitation, "sova_current_phase_code"):
        invitation.sova_current_phase_code = current_phase_code
    if hasattr(invitation, "sova_current_phase_idx"):
        invitation.sova_current_phase_idx = current_phase_idx

    update_fields = ["sova_payload"]
    if hasattr(invitation, "sova_overall_status"):
        update_fields.append("sova_overall_status")
    if hasattr(invitation, "sova_current_phase_code"):
        update_fields.append("sova_current_phase_code")
    if hasattr(invitation, "sova_current_phase_idx"):
        update_fields.append("sova_current_phase_idx")

    invitation.save(update_fields=update_fields)

    print("✅ Saved debug/SOVA fields:", {
        "invitation_id": invitation.id,
        "talena_status": invitation.status,
        "sova_overall_status": getattr(invitation, "sova_overall_status", None),
        "sova_current_phase_code": getattr(invitation, "sova_current_phase_code", None),
        "sova_current_phase_idx": getattr(invitation, "sova_current_phase_idx", None),
    })

    # ── Mapping: SOVA overall_status -> Talena status ──
    OVERALL_COMPLETED = {"completed", "pass", "fail", "refer"}
    OVERALL_STARTED = {"in progress"}
    OVERALL_TERMINAL_NEG = {"cancelled", "declined data protection", "did not attend"}

    normalized = ""
    reason = ""

    if overall in OVERALL_COMPLETED:
        normalized = "completed"
        reason = f"overall={overall}"

    elif overall in OVERALL_STARTED or has_phase_hint or phase_status == "in progress":
        normalized = "started"
        reason = f"overall={overall} phase_hint={has_phase_hint} phase_status={phase_status}"

    elif overall in OVERALL_TERMINAL_NEG:
        normalized = "failed"
        reason = f"overall terminal negative={overall}"

    else:
        normalized = ""
        reason = f"no mapping hit: overall={overall}"

    print("🧠 Normalized status:", normalized, "| reason:", reason)

    # ── Applicera utan downgrade ────────────────
    if normalized == "started":
        if invitation.status not in {"started", "completed"}:
            invitation.status = "started"
            invitation.save(update_fields=["status"])
            print("✅ Updated invitation to STARTED:", invitation.id)

    elif normalized == "completed":
        if invitation.status != "completed":
            invitation.status = "completed"
            invitation.completed_at = timezone.now()
            invitation.save(update_fields=["status", "completed_at"])
            print("✅ Updated invitation to COMPLETED:", invitation.id)

    elif normalized == "failed":
        if invitation.status != "failed":
            invitation.status = "failed"
            invitation.save(update_fields=["status"])
            print("✅ Updated invitation to FAILED:", invitation.id)

    # ── Results payload: spara om det finns ─────
    if isinstance(payload.get("project_results"), dict):
        invitation.project_results = payload.get("project_results")
        invitation.save(update_fields=["project_results"])
        print("✅ Saved project_results (from webhook payload)")

    # ── Optional score fetch fallback ───────────
    if normalized == "completed" and invitation.sova_project_id and invitation.request_id:
        try:
            client = SovaClient()
            data = client.get_project_candidates(invitation.sova_project_id)

            items = data.get("candidates") if isinstance(data, dict) else data
            items = items or []

            match = next((c for c in items if c.get("request_id") == invitation.request_id), None)

            if match:
                invitation.overall_score = match.get("overall_score")
                if match.get("project_results") and not invitation.project_results:
                    invitation.project_results = match.get("project_results")
                    invitation.save(update_fields=["overall_score", "project_results"])
                    print("✅ Saved overall_score + project_results (from project-candidates)")
                else:
                    invitation.save(update_fields=["overall_score"])
                    print("✅ Saved overall_score:", invitation.overall_score)
            else:
                print("⚠️ No matching request_id in project-candidates:", invitation.request_id)

        except Exception as e:
            print("❌ Error fetching project candidates:", str(e))

    return JsonResponse({"status": "ok"})
