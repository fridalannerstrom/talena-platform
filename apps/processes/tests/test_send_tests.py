from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.processes.services.send_tests import send_assessments_and_emails


class FakeInvitation:
    def __init__(self):
        self.id = 101
        self.status = "created"
        self.assessment_url = None
        self.request_id = None
        self.sova_request_id = None
        self.sova_payload = None
        self.sova_project_id = None
        self.invited_at = None
        self.invited_by = None
        self.candidate = SimpleNamespace(
            id=202,
            first_name="Frida",
            last_name="Candidate",
            email="candidate@example.com",
        )
        self.saved_update_fields = []

    def save(self, *, update_fields=None, **kwargs):
        self.saved_update_fields.append(tuple(update_fields or ()))


class SendAssessmentsRetrySafetyTests(SimpleTestCase):
    def setUp(self):
        self.process = SimpleNamespace(
            id=303,
            account_code="ACCOUNT",
            project_code="PROJECT",
            candidate_language="en",
            job_title="Software Developer",
            job_location="Stockholm",
            name="Developer hiring",
            selected_tests=["personality"],
            company=SimpleNamespace(id=1, name="Talent Qode"),
        )

        self.actor = SimpleNamespace(
            id=404,
            first_name="Frida",
            last_name="Admin",
            email="frida@example.com",
            get_full_name=lambda: "Frida Admin",
        )

    def _email_log(self):
        log = MagicMock()
        log.id = 505
        return log

    @patch("apps.processes.services.send_tests.log_event")
    @patch("apps.processes.services.send_tests.register_sent_assessments")
    @patch("apps.processes.services.send_tests.EmailMultiAlternatives")
    @patch("apps.processes.services.send_tests.EmailLog.objects.create")
    @patch("apps.processes.services.send_tests.EmailTemplate.objects.filter")
    @patch("apps.core.integrations.sova.SovaClient")
    def test_retry_after_email_failure_reuses_existing_sova_order(
        self,
        sova_client_cls,
        template_filter,
        email_log_create,
        email_cls,
        register_usage,
        log_event,
    ):
        invitation = FakeInvitation()

        client = sova_client_cls.return_value
        client.get_accounts_with_projects.return_value = []
        client.order_assessment.return_value = {
            "url": "https://assessment.example.com/abc123",
        }

        template_filter.return_value.first.return_value = None
        email_log_create.side_effect = [
            self._email_log(),
            self._email_log(),
        ]

        email = email_cls.return_value
        email.send.side_effect = [
            RuntimeError("SMTP unavailable"),
            1,
        ]

        first_result = send_assessments_and_emails(
            process=self.process,
            invitations=[invitation],
            actor_user=self.actor,
            context="customer",
        )

        self.assertEqual(first_result["sent_count"], 0)
        self.assertEqual(len(first_result["errors"]), 1)
        self.assertEqual(invitation.status, "failed")
        self.assertEqual(
            invitation.assessment_url,
            "https://assessment.example.com/abc123",
        )
        self.assertTrue(invitation.request_id)
        self.assertEqual(client.order_assessment.call_count, 1)
        self.assertEqual(register_usage.call_count, 1)

        second_result = send_assessments_and_emails(
            process=self.process,
            invitations=[invitation],
            actor_user=self.actor,
            context="customer",
        )

        self.assertEqual(second_result["sent_count"], 1)
        self.assertEqual(second_result["errors"], [])
        self.assertEqual(invitation.status, "sent")

        # The critical regression assertion: retrying email delivery must not
        # create a second SOVA assessment order.
        self.assertEqual(client.order_assessment.call_count, 1)

        # Usage registration is intentionally idempotent and is refreshed on
        # retry without creating duplicate billing rows.
        self.assertEqual(register_usage.call_count, 2)
        log_event.assert_called_once()

    @patch("apps.processes.services.send_tests.log_event")
    @patch("apps.processes.services.send_tests.register_sent_assessments")
    @patch("apps.processes.services.send_tests.EmailMultiAlternatives")
    @patch("apps.processes.services.send_tests.EmailLog.objects.create")
    @patch("apps.processes.services.send_tests.EmailTemplate.objects.filter")
    @patch("apps.core.integrations.sova.SovaClient")
    def test_existing_assessment_url_never_orders_again(
        self,
        sova_client_cls,
        template_filter,
        email_log_create,
        email_cls,
        register_usage,
        log_event,
    ):
        invitation = FakeInvitation()
        invitation.status = "failed"
        invitation.assessment_url = "https://assessment.example.com/existing"
        invitation.request_id = "existing-request-id"
        invitation.sova_payload = {
            "url": invitation.assessment_url,
        }

        client = sova_client_cls.return_value
        client.get_accounts_with_projects.return_value = []

        template_filter.return_value.first.return_value = None
        email_log_create.return_value = self._email_log()
        email_cls.return_value.send.return_value = 1

        result = send_assessments_and_emails(
            process=self.process,
            invitations=[invitation],
            actor_user=self.actor,
            context="customer",
        )

        self.assertEqual(result["sent_count"], 1)
        self.assertEqual(result["errors"], [])
        self.assertEqual(invitation.status, "sent")
        client.order_assessment.assert_not_called()
        register_usage.assert_called_once()
        log_event.assert_called_once()
