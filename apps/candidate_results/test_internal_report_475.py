"""#475: Internal candidate reports must not depend on candidate sharing."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company
from apps.candidate_results.models import CandidateResultAccess, CandidateResultSnapshot
from apps.emails.models import EmailLog
from apps.processes.models import Candidate, TestInvitation, TestProcess


class InternalCandidateReportWithoutSharingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="candidate-report-475",
            email="candidate-report-475@example.org",
            password="test-password",
        )
        self.company = Company.objects.create(name="Internal candidate report 475")
        self.process = TestProcess.objects.create(
            name="Process without candidate sharing",
            company=self.company,
            project_code="candidate-report-475",
            account_code="candidate-report-475",
            created_by=self.user,
            candidate_results_enabled=False,
            candidate_language="sv",
        )
        self.candidate = Candidate.objects.create(
            first_name="Internal", last_name="Candidate",
            email="candidate-475@example.org",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process, candidate=self.candidate,
            status="completed", completed_at=timezone.now(),
        )
        self.detail_url = reverse(
            "processes:process_candidate_detail",
            kwargs={
                "process_id": self.process.pk,
                "candidate_id": self.candidate.pk,
            },
        )
        self.client.force_login(self.user)

    def test_completed_report_is_created_and_downloadable_without_sharing(self):
        self.assertFalse(CandidateResultSnapshot.objects.filter(invitation=self.invitation).exists())

        result = self.client.get(
            self.detail_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(result.status_code, 200)
        snapshot = CandidateResultSnapshot.objects.get(invitation=self.invitation)
        self.assertIsNotNone(snapshot)
        self.assertContains(result, "Download PDF")
        self.assertContains(result, "data-candidate-result-download")
        self.assertContains(result, reverse("candidate_results:preview", kwargs={"snapshot_id": snapshot.pk}))
        self.assertContains(result, "Internal preview")
        self.assertFalse(self.process.candidate_results_enabled)
        self.assertFalse(CandidateResultAccess.objects.filter(snapshot=snapshot).exists())
        self.assertFalse(EmailLog.objects.filter(invitation=self.invitation, template_type="candidate_result").exists())

        again = self.client.get(
            self.detail_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(again.status_code, 200)
        self.assertEqual(CandidateResultSnapshot.objects.filter(invitation=self.invitation).count(), 1)
        self.assertEqual(CandidateResultAccess.objects.count(), 0)

    def test_internal_preview_is_available_but_candidate_portal_stays_private(self):
        self.client.get(self.detail_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        snapshot = CandidateResultSnapshot.objects.get(invitation=self.invitation)
        response = self.client.get(
            reverse("candidate_results:preview", kwargs={"snapshot_id": snapshot.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-candidate-result-pdf-button")
        self.assertContains(response, "candidate-result-internal-pdf.js")
        self.assertNotContains(response, 'class="feedback-choices"')
        self.assertEqual(CandidateResultAccess.objects.count(), 0)

    def test_talena_admin_mirror_can_open_and_download_without_sharing(self):
        # #513 extends #475: the full admin candidate mirror must expose the
        # same authorised preview as the customer's report tab.
        self.assertFalse(self.process.candidate_results_enabled)
        admin_url = reverse(
            "accounts:company_process_candidate_detail",
            args=[self.company.pk, self.process.pk, self.candidate.pk],
        )
        response = self.client.get(
            admin_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        snapshot = CandidateResultSnapshot.objects.get(invitation=self.invitation)
        preview_url = reverse(
            "candidate_results:preview", kwargs={"snapshot_id": snapshot.pk}
        )
        self.assertContains(response, preview_url)
        self.assertContains(response, "data-candidate-result-download")
        self.assertContains(response, "data-read-only=\"true\"")
        preview = self.client.get(preview_url)
        self.assertEqual(preview.status_code, 200)
        self.assertContains(preview, "data-candidate-result-pdf-button")
        self.assertContains(preview, "Den här interna förhandsvisningen")
        self.assertNotContains(preview, 'class="feedback-choices"')

        self.process.refresh_from_db()
        self.assertFalse(self.process.candidate_results_enabled)
        self.assertEqual(CandidateResultAccess.objects.count(), 0)
        self.assertFalse(
            EmailLog.objects.filter(
                invitation=self.invitation, template_type="candidate_result"
            ).exists()
        )

    def test_public_result_link_is_still_blocked_when_sharing_is_off(self):
        from apps.candidate_results.services import create_candidate_result_access

        self.client.get(self.detail_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        snapshot = CandidateResultSnapshot.objects.get(invitation=self.invitation)
        access, token, code = create_candidate_result_access(snapshot)
        self.client.logout()
        response = self.client.get(
            reverse("candidate_results:result", kwargs={"token": token})
        )
        self.assertEqual(response.status_code, 410)
        self.assertFalse(access.is_expired())
        self.assertIsNotNone(code)

    def test_incomplete_candidate_does_not_get_internal_report(self):
        self.invitation.status = "started"
        self.invitation.save(update_fields=["status"])
        response = self.client.get(
            self.detail_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CandidateResultSnapshot.objects.filter(invitation=self.invitation).exists())
        self.assertNotContains(response, "data-candidate-result-download")

    def test_unrelated_user_cannot_open_protected_preview(self):
        self.client.get(self.detail_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        snapshot = CandidateResultSnapshot.objects.get(invitation=self.invitation)
        User = get_user_model()
        outsider = User.objects.create_user(
            username="unrelated-report-475", password="test-password",
        )
        self.client.force_login(outsider)
        response = self.client.get(
            reverse("candidate_results:preview", kwargs={"snapshot_id": snapshot.pk})
        )
        self.assertEqual(response.status_code, 404)
