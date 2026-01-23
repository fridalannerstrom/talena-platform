from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

from django.utils import timezone
from apps.processes.models import TestInvitation

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

    return JsonResponse({"status": "ok"})
