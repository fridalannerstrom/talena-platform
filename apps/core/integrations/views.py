import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

from apps.processes.models import TestInvitation
from apps.core.integrations.sova import SovaClient


@csrf_exempt
def sova_ingest(request):
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    # ✅ Enkel auth: shared secret i header
    secret = request.headers.get("X-Talena-Webhook-Secret")
    if not secret or secret != getattr(settings, "SOVA_WEBHOOK_SHARED_SECRET", ""):
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "invalid json"}, status=400)

    meta = payload.get("meta_data") or {}
    status = (payload.get("status") or "").lower()

    process_id = meta.get("talena_process_id")
    candidate_id = meta.get("talena_candidate_id")
    request_id = meta.get("talena_request_id") or payload.get("request_id")

    # ✅ Hitta invitation: request_id är bäst (unika)
    invitation = None
    if request_id:
        invitation = TestInvitation.objects.filter(request_id=request_id).first()
    if not invitation and process_id and candidate_id:
        invitation = TestInvitation.objects.filter(process_id=process_id, candidate_id=candidate_id).first()

    if not invitation:
        return JsonResponse({"status": "ignored", "reason": "invitation not found"}, status=200)

    # ✅ Spara rå webhook payload (om du har ett fält för det)
    # invitation.webhook_payload = payload

    if status in ("started", "in_progress"):
        if invitation.status not in ("completed",):
            invitation.status = "started"
            invitation.save(update_fields=["status"])

    if status == "completed":
        invitation.status = "completed"
        invitation.completed_at = timezone.now()

        # 1) om SOVA skickar score i webhooken: plocka här (exempel)
        # invitation.overall_score = payload.get("overall_score")

        # 2) annars: hämta score via API (som du redan gjort)
        if invitation.sova_project_id and invitation.request_id:
            client = SovaClient()
            data = client.get_project_candidates(invitation.sova_project_id)
            items = data.get("candidates") if isinstance(data, dict) else data
            items = items or []
            match = next((c for c in items if c.get("request_id") == invitation.request_id), None)
            if match:
                invitation.overall_score = match.get("overall_score")
                invitation.project_results = match.get("project_results")

        invitation.save(update_fields=["status", "completed_at", "overall_score", "project_results"])

    return JsonResponse({"status": "ok"})