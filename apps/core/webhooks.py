from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

from django.utils import timezone
from apps.processes.models import TestInvitation

from apps.core.integrations.sova import SovaClient

@csrf_exempt
def sova_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    payload = json.loads(request.body.decode("utf-8"))
    print("🔔 SOVA WEBHOOK RECEIVED:", payload)

    meta = payload.get("meta_data", {})
    process_id = meta.get("talena_process_id")
    candidate_id = meta.get("talena_candidate_id")
    status = payload.get("status")

    if status == "completed" and process_id and candidate_id:
        invitation = TestInvitation.objects.filter(
            process_id=process_id,
            candidate_id=candidate_id,
        ).first()

        if invitation:
            invitation.status = "completed"
            invitation.completed_at = timezone.now()
            invitation.save(update_fields=["status", "completed_at"])

            # Hämta score från SOVA (om vi har nycklar)
            if invitation.sova_project_id and invitation.request_id:
                client = SovaClient()
                data = client.get_project_candidates(invitation.sova_project_id)

                # SOVA kan returnera en lista eller en dict med "candidates" – vi stödjer båda:
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
            else:
                print("⚠️ Missing sova_project_id/request_id on invitation")

    return JsonResponse({"status": "ok"})
