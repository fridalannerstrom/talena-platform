from datetime import timezone as dt_timezone
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import EmailDeliveryUpdate, EmailLog


DELIVERY_STATUS_MAP = {
    "Delivered": "delivered",
    "Bounced": "failed",
    "Suppressed": "failed",
    "Quarantined": "failed",
    "FilteredSpam": "failed",
    "Failed": "failed",
    "Dropped": "failed",
    "Queued": "pending",
    "OutForDelivery": "pending",
    "Expanded": "pending",
}


def map_delivery_status(provider_status):
    status = str(provider_status or "").strip()
    return next(
        (mapped for provider_value, mapped in DELIVERY_STATUS_MAP.items()
         if provider_value.casefold() == status.casefold()),
        "unknown",
    )


def _event_time(value):
    if not value:
        return None
    parsed = parse_datetime(str(value))
    if parsed and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone=dt_timezone.utc)
    return parsed


def process_delivery_event(event):
    """Apply one ACS delivery event once, matching both message and recipient."""
    if not isinstance(event, dict):
        return "ignored"
    event_id = str(event.get("id") or "").strip()
    data = event.get("data") or {}
    if not isinstance(data, dict):
        return "ignored"
    internet_message_id = str(data.get("internetMessageId") or "").strip()
    recipient = str(data.get("recipient") or "").strip()
    provider_status = str(data.get("deliveryStatus") or "").strip()
    delivery_status = map_delivery_status(provider_status)

    if not event_id or not internet_message_id or not recipient or delivery_status == "unknown":
        return "ignored"

    occurred_at = _event_time(event.get("eventTime"))
    with transaction.atomic():
        email_log = (
            EmailLog.objects.select_for_update()
            .filter(internet_message_id__iexact=internet_message_id)
            .first()
        )
        if not email_log or email_log.to_email.casefold() != recipient.casefold():
            return "unmatched"

        update, created = EmailDeliveryUpdate.objects.get_or_create(
            provider_event_id=event_id,
            defaults={
                "email_log": email_log,
                "provider_status": provider_status[:40],
                "delivery_status": delivery_status,
                "provider_occurred_at": occurred_at,
            },
        )
        if not created:
            return "duplicate"

        latest_timestamp = email_log.delivery_status_updated_at
        if latest_timestamp and occurred_at and occurred_at < latest_timestamp:
            return "stored"

        email_log.delivery_status = delivery_status
        email_log.delivery_status_updated_at = occurred_at or timezone.now()
        email_log.delivery_error_code = (
            provider_status.lower() if delivery_status == "failed" else ""
        )
        email_log.save(update_fields=[
            "delivery_status",
            "delivery_status_updated_at",
            "delivery_error_code",
        ])

        if delivery_status == "failed":
            invitation = email_log.invitation
            latest_log = invitation.email_logs.filter(template_type="invitation").order_by("-created_at", "-pk").first()
            if (
                latest_log and latest_log.pk == email_log.pk
                and invitation.status == "sent"
            ):
                invitation.status = "failed"
                invitation.save(update_fields=["status"])

    return "updated"
