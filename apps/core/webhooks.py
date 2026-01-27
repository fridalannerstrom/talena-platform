from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
import json

from apps.processes.models import TestInvitation
from apps.core.integrations.sova import SovaClient

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

    print("🔔 SOVA WEBHOOK RECEIVED (raw):", payload)

    # --- plocka ut status robust ---
    status = (payload.get("status") or payload.get("event") or "").lower().strip()

    # --- plocka identifiers robust ---
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

    print("🧩 Parsed:", {
        "status": status,
        "request_id": request_id,
        "sova_invitation_id": sova_inv_id,
        "talena_process_id": talena_process_id,
        "talena_candidate_id": talena_candidate_id,
    })

    # --- hitta invitation (viktigaste fixen) ---
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

    # (valfritt men guld): spara senaste payload för debugging
    invitation.sova_payload = payload
    invitation.save(update_fields=["sova_payload"])

    # --- status mapping ---
    # Anpassa listan om SOVA skickar andra ord
    STARTED_STATUSES = {"started", "in_progress", "in-progress", "inprogress"}
    COMPLETED_STATUSES = {"completed", "complete", "done", "finished"}

    if status in STARTED_STATUSES:
        if invitation.status != "started":
            invitation.status = "started"
            invitation.save(update_fields=["status"])
            print("✅ Updated invitation to STARTED:", invitation.id)

    elif status in COMPLETED_STATUSES:
        if invitation.status != "completed":
            invitation.status = "completed"
            invitation.completed_at = timezone.now()
            invitation.save(update_fields=["status", "completed_at"])
            print("✅ Updated invitation to COMPLETED:", invitation.id)

        # Hämta score/resultat om du vill (samma som innan)
        if invitation.sova_project_id and invitation.request_id:
            try:
                client = SovaClient()
                data = client.get_project_candidates(invitation.sova_project_id)

                items = data.get("candidates") if isinstance(data, dict) else data
                items = items or []

                match = next((c for c in items if c.get("request_id") == invitation.request_id), None)

                if match:
                    invitation.overall_score = match.get("overall_score")
                    invitation.project_results = match.get("project_results")
                    invitation.save(update_fields=["overall_score", "project_results"])
                    print("✅ Saved overall_score:", invitation.overall_score)
                else:
                    print("⚠️ No matching request_id in project-candidates:", invitation.request_id)

            except Exception as e:
                print("❌ Error fetching project candidates:", str(e))

    else:
        print("ℹ️ Unhandled status value:", status)

    return JsonResponse({"status": "ok"})
