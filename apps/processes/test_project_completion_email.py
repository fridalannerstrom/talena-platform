"""Regression tests for project creator test-completion email (#466)."""
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Company
from apps.emails.models import EmailLog
from apps.processes.forms import TestProcessWizardCreateForm
from apps.processes.models import Candidate, TestInvitation, TestProcess


@override_settings(
    SOVA_WEBHOOK_TEST_SECRET="test-completion-secret",
    SOVA_WEBHOOK_PROD_SECRET="",
    SOVA_WEBHOOK_SHARED_SECRET="",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class ProjectCompletionEmailTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.creator = User.objects.create_user(
            username="creator@example.com",
            email="creator@example.com",
            password="test-password",
            first_name="Alex",
        )
        self.company = Company.objects.create(name="Completion email company")
        self.project = TestProcess.objects.create(
            name="Recruitment specialist",
            company=self.company,
            project_code="PQ_MQ",
            account_code="test-account",
            created_by=self.creator,
            selected_tests=["personality", "motivation"],
            candidate_language="sv",
        )
        self.candidate = Candidate.objects.create(
            first_name="Robin",
            last_name="Example",
            email="robin@example.com",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.project,
            candidate=self.candidate,
            request_id="completion-request",
            status="sent",
        )

    def _activities(self, *, motivation_status="completed"):
        return [
            {"activity": "Personality questionnaire", "status": "completed"},
            {"activity": "Motivation questionnaire", "status": motivation_status},
        ]

    def _post(self, overall_status="completed", *, activities=None):
        return self.client.post(
            "/integrations/sova/ingest/",
            data=json.dumps({
                "request_id": self.invitation.request_id,
                "overall_status": overall_status,
                "activities": (
                    self._activities()
                    if activities is None else activities
                ),
            }),
            content_type="application/json",
            HTTP_X_TALENA_WEBHOOK_SECRET="test-completion-secret",
        )

    def test_default_enabled_and_one_email_after_last_test(self):
        self.assertTrue(self.project.project_completion_notifications_enabled)
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["creator@example.com"])
        self.assertIn("Robin Example", mail.outbox[0].body)
        self.assertIn("Recruitment specialist", mail.outbox[0].body)
        expected_path = reverse(
            "processes:process_candidate_detail",
            args=[self.project.pk, self.candidate.pk],
        )
        self.assertIn(f"http://testserver{expected_path}", mail.outbox[0].body)
        self.assertIn("Kandidaten har slutfört sina tester", mail.outbox[0].subject)
        self.assertIn("Talena", mail.outbox[0].alternatives[0][0])
        log = EmailLog.objects.get(template_type="project_completion")
        self.assertEqual(log.status, "sent")
        self.assertEqual(log.to_email, self.creator.email)
        self.invitation.refresh_from_db()
        self.assertIsNotNone(self.invitation.project_completion_email_sent_at)

        # Repeated SOVA callbacks must not send again.
        self.assertEqual(self._post().status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(EmailLog.objects.filter(
            template_type="project_completion"
        ).count(), 1)

    def test_partial_and_in_progress_statuses_do_not_send(self):
        self.assertEqual(
            self._post("in progress", activities=self._activities(
                motivation_status="started"
            )).status_code,
            200,
        )
        self.assertEqual(len(mail.outbox), 0)
        # Even if SOVA sends a contradictory overall completed flag,
        # an explicitly unfinished individual test blocks notification.
        self.assertEqual(
            self._post("completed", activities=self._activities(
                motivation_status="started"
            )).status_code,
            200,
        )
        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(self._post("completed").status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

    def test_disabled_setting_blocks_notification(self):
        self.project.project_completion_notifications_enabled = False
        self.project.save(update_fields=[
            "project_completion_notifications_enabled"
        ])
        self.assertEqual(self._post().status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EmailLog.objects.filter(
            template_type="project_completion"
        ).exists())

    def test_english_project_sends_english_copy(self):
        self.project.candidate_language = "en"
        self.project.save(update_fields=["candidate_language"])
        self.assertEqual(self._post().status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            "Candidate has completed their tests",
        )
        self.assertIn("View candidate in Talena", mail.outbox[0].body)
        self.assertIn('lang="en"', mail.outbox[0].alternatives[0][0])

    def test_notification_is_independent_of_candidate_result_sharing(self):
        self.assertFalse(self.project.candidate_results_enabled)
        self.assertEqual(self._post().status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.creator.email])
        self.assertFalse(EmailLog.objects.filter(
            template_type="candidate_result"
        ).exists())

    def test_missing_creator_email_does_not_send(self):
        self.creator.email = ""
        self.creator.save(update_fields=["email"])
        self.assertEqual(self._post().status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_removed_candidate_does_not_send(self):
        from django.utils import timezone
        self.invitation.removed_from_process_at = timezone.now()
        self.invitation.save(update_fields=["removed_from_process_at"])
        self.assertEqual(self._post().status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_delivery_failure_is_logged_and_later_callback_retries(self):
        with patch(
            "apps.processes.project_completion_email.EmailMultiAlternatives.send",
            side_effect=RuntimeError("Synthetic email provider failure"),
        ):
            self.assertEqual(self._post().status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.invitation.refresh_from_db()
        self.assertIsNone(self.invitation.project_completion_email_sent_at)
        failed = EmailLog.objects.get(template_type="project_completion")
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.error, "RuntimeError")
        self.assertNotIn("Synthetic", failed.error)

        self.assertEqual(self._post().status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            EmailLog.objects.filter(
                template_type="project_completion", status="sent"
            ).count(),
            1,
        )

    def test_settings_form_checkbox_defaults_enabled_and_accepts_off(self):
        field = TestProcessWizardCreateForm.base_fields[
            "project_completion_notifications_enabled"
        ]
        self.assertTrue(field.initial)
        self.assertFalse(field.required)
        self.assertFalse(field.clean(False))
