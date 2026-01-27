from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
import json

from apps.processes.models import TestInvitation
from apps.core.integrations.sova import SovaClient

@csrf_exempt
def sova_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        print("❌ WEBHOOK JSON PARSE ERROR:", str(e))
        return JsonResponse({"error": "invalid json"}, status=400)

    print("🔔 SOVA WEBHOOK RECEIVED:", payload)

    inv = TestInvitation.objects.order_by("-created_at").first()
    if inv:
        inv.sova_payload = payload
        inv.save(update_fields=["sova_payload"])

    meta = payload.get("meta_data") or payload.get("metaData") or {}
    process_id = meta.get("talena_process_id")
    candidate_id = meta.get("talena_candidate_id")
    status = (payload.get("status") or "").lower()

    if not (process_id and candidate_id and status):
        print("⚠️ Missing fields:", {"process_id": process_id, "candidate_id": candidate_id, "status": status})
        return JsonResponse({"status": "ok"})  # tyst ok så SOVA inte spammar retries

    invitation = (
        TestInvitation.objects
        .filter(process_id=process_id, candidate_id=candidate_id)
        .first()
    )

    if not invitation:
        print("⚠️ No invitation found for process/candidate:", process_id, candidate_id)
        return JsonResponse({"status": "ok"})

    # --- Status mapping ---
    if status in ["started", "in_progress", "in-progress"]:
        if invitation.status != "started":
            invitation.status = "started"
            invitation.save(update_fields=["status"])
            print("✅ Invitation marked started:", invitation.id)

    elif status == "completed":
        if invitation.status != "completed":
            invitation.status = "completed"
            invitation.completed_at = timezone.now()
            invitation.save(update_fields=["status", "completed_at"])
            print("✅ Invitation marked completed:", invitation.id)

        # Hämta score/resultat från SOVA (om vi har nycklar)
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
            print("⚠️ Missing sova_project_id/request_id on invitation")

    else:
        print("ℹ️ Unhandled webhook status:", status)

    return JsonResponse({"status": "ok"})
