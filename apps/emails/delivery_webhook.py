import json
import secrets

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .delivery import process_delivery_event


@csrf_exempt
@require_POST
def azure_email_delivery_webhook(request):
    expected_secret = getattr(settings, "ACS_EMAIL_EVENTGRID_SECRET", "")
    supplied_secret = request.GET.get("token", "")
    if not expected_secret:
        return HttpResponse(status=503)
    if not secrets.compare_digest(supplied_secret, expected_secret):
        return HttpResponse(status=403)

    try:
        events = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HttpResponse(status=400)

    if not isinstance(events, list):
        return HttpResponse(status=400)

    if events and isinstance(events[0], dict) and events[0].get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
        code = ((events[0].get("data") or {}).get("validationCode") or "")
        return JsonResponse({"validationResponse": code}) if code else HttpResponse(status=400)

    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("eventType") != "Microsoft.Communication.EmailDeliveryReportReceived":
            continue
        process_delivery_event(event)

    return HttpResponse(status=200)
