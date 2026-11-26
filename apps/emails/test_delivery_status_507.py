from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.emails.delivery import map_delivery_status, process_delivery_event


class EmailDeliveryStatusTests(SimpleTestCase):
    def _event(self, status="Delivered", recipient="candidate@example.test", event_id="evt-1"):
        return {
            "id": event_id,
            "eventType": "Microsoft.Communication.EmailDeliveryReportReceived",
            "eventTime": "2026-11-26T09:00:00Z",
            "data": {
                "internetMessageId": "<mail-1@example.test>",
                "recipient": recipient,
                "status": status,
                "deliveryAttemptTimestamp": "2026-11-26T09:00:00Z",
            },
        }

    def _apply(self, event, *, log=None, created=True):
        log = log or MagicMock()
        log.to_email = "candidate@example.test"
        log.delivery_status = "pending"
        log.delivery_status_updated_at = None
        log.invitation = SimpleNamespace(
            status="sent",
            save=MagicMock(),
            email_logs=MagicMock(),
        )
        log.invitation.email_logs.order_by.return_value.first.return_value = log

        lookup = MagicMock()
        lookup.filter.return_value.first.return_value = log
        update_manager = MagicMock()
        update_manager.get_or_create.return_value = (MagicMock(), created)
        with (
            patch("apps.emails.delivery.transaction.atomic", return_value=nullcontext()),
            patch("apps.emails.delivery.EmailLog.objects.select_for_update", return_value=lookup),
            patch("apps.emails.delivery.EmailDeliveryUpdate.objects", update_manager),
        ):
            result = process_delivery_event(event)
        return result, log, update_manager

    def test_maps_confirmed_delivery_and_provider_failures(self):
        self.assertEqual(map_delivery_status("Delivered"), "delivered")
        self.assertEqual(map_delivery_status("Bounced"), "failed")
        self.assertEqual(map_delivery_status("bounced"), "failed")
        self.assertEqual(map_delivery_status("Queued"), "pending")
        self.assertEqual(map_delivery_status("Unrecognized"), "unknown")

    def test_confirmed_delivery_updates_the_matching_log(self):
        result, log, _ = self._apply(self._event())
        self.assertEqual(result, "updated")
        self.assertEqual(log.delivery_status, "delivered")
        log.save.assert_called_once()

    def test_confirmed_bounce_marks_latest_invitation_retryable(self):
        result, log, _ = self._apply(self._event(status="Bounced"))
        self.assertEqual(result, "updated")
        self.assertEqual(log.delivery_status, "failed")
        self.assertEqual(log.invitation.status, "failed")
        log.invitation.save.assert_called_once_with(update_fields=["status"])

    def test_duplicate_event_is_idempotent(self):
        result, log, _ = self._apply(self._event(), created=False)
        self.assertEqual(result, "duplicate")
        log.save.assert_not_called()

    def test_recipient_mismatch_is_not_applied(self):
        result, log, update_manager = self._apply(
            self._event(recipient="someone-else@example.test")
        )
        self.assertEqual(result, "unmatched")
        update_manager.get_or_create.assert_not_called()
        log.save.assert_not_called()

    def test_unknown_provider_status_is_not_treated_as_delivery(self):
        result, log, update_manager = self._apply(self._event(status="NewProviderState"))
        self.assertEqual(result, "ignored")
        update_manager.get_or_create.assert_not_called()
        log.save.assert_not_called()
