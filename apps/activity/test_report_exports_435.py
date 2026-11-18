"""#435 report receipt contract: no fabricated downloads, no payload content."""
import json
from uuid import uuid4

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import Company, User
from apps.activity.models import ActivityEvent
from apps.activity.usage_summary import platform_report_exports
from apps.processes.models import Candidate, TestInvitation, TestProcess
from apps.teams.models import Team


class ReportExportReceiptTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            "export-admin", "export-admin@example.test", "test-password",
        )
        self.stranger = User.objects.create_user(
            "export-stranger", "export-stranger@example.test", "test-password",
        )
        self.company = Company.objects.create(name="Fictional export tenant")
        self.other = Company.objects.create(name="Unrelated tenant")
        self.process = TestProcess.objects.create(
            company=self.company, created_by=self.admin,
            name="Synthetic process", purpose="hiring", account_code="MODERN",
            project_code="PQ", selected_tests=["personality"],
        )
        self.candidate = Candidate.objects.create(
            first_name="Synthetic", last_name="Person",
            email="synthetic@example.test",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process, candidate=self.candidate,
        )
        self.team = Team.objects.create(
            company=self.company, created_by=self.admin, name="Synthetic team",
        )
        self.candidate_url = reverse(
            "processes:process_candidate_report_export_receipt",
            args=[self.process.pk, self.candidate.pk],
        )
        self.team_url = reverse("teams:team_report_export_receipt", args=[self.team.pk])
        self.client.force_login(self.admin)

    def post_receipt(self, url, report_type, *, export_id=None, **extra):
        return self.client.post(
            url,
            data=json.dumps({
                "report_type": report_type,
                "export_id": export_id or str(uuid4()),
                **extra,
            }),
            content_type="application/json",
        )

    def test_candidate_pdf_receipt_is_attributed_with_server_side_context(self):
        token = str(uuid4())
        first = self.post_receipt(
            self.candidate_url, "motivation-results", export_id=token,
            company_id=self.other.pk, actor_id=self.stranger.pk,
            candidate_id=999999, candidate_name="PRIVATE_NAME",
            prompt="PRIVATE_PROMPT",
        )
        repeated = self.post_receipt(
            self.candidate_url, "motivation-results", export_id=token,
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(repeated.status_code, 200)
        events = ActivityEvent.objects.filter(
            verb=ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
        )
        self.assertEqual(events.count(), 1)
        event = events.get()
        self.assertEqual(event.company_id, self.company.pk)
        self.assertEqual(event.process_id, self.process.pk)
        self.assertEqual(event.candidate_id, self.candidate.pk)
        self.assertEqual(event.actor_id, self.admin.pk)
        self.assertEqual(event.invitation_id, self.invitation.pk)
        self.assertEqual(event.meta, {
            "schema": 1, "report_type": "motivation-results",
            "format": "pdf", "status": "client_reported_generated",
            "export_id": token,
        })
        self.assertNotIn("PRIVATE", repr(event.meta))

    def test_export_identifier_reuse_with_other_type_is_rejected(self):
        token = str(uuid4())
        self.assertEqual(
            self.post_receipt(self.candidate_url, "overview", export_id=token).status_code,
            200,
        )
        replay = self.post_receipt(
            self.candidate_url, "candidate-package-zip", export_id=token,
        )
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(ActivityEvent.objects.filter(
            verb=ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
        ).count(), 1)

    def test_team_receipt_has_company_not_subject_or_fake_process(self):
        response = self.post_receipt(
            self.team_url, "team-package-zip", candidate_id=42,
        )
        self.assertEqual(response.status_code, 200)
        event = ActivityEvent.objects.get(
            verb=ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
        )
        self.assertEqual(event.company_id, self.company.pk)
        self.assertIsNone(event.candidate_id)
        self.assertIsNone(event.process_id)
        self.assertEqual(event.actor_id, self.admin.pk)
        self.assertEqual(event.meta["format"], "zip")

    def test_invalid_formats_and_manager_receipt_cannot_be_forged(self):
        for url, kind in [
            (self.candidate_url, "manager-report"),
            (self.candidate_url, "team-overview"),
            (self.team_url, "candidate-package-pdf"),
            (self.candidate_url, "arbitrary-new-type"),
        ]:
            with self.subTest(kind=kind):
                self.assertEqual(self.post_receipt(url, kind).status_code, 400)
        self.assertEqual(self.post_receipt(
            self.candidate_url, "overview", export_id="no uuid",
        ).status_code, 400)
        self.assertEqual(self.client.get(self.candidate_url).status_code, 405)
        self.assertFalse(ActivityEvent.objects.filter(
            verb=ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
        ).exists())

    def test_access_is_server_authorized_and_csrf_protected(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.post_receipt(
            self.candidate_url, "overview",
        ).status_code, 403)
        self.assertEqual(self.post_receipt(
            self.team_url, "team-overview",
        ).status_code, 404)
        self.assertFalse(ActivityEvent.objects.filter(
            verb=ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
        ).exists())
        self.client.force_login(self.admin)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        denied = csrf_client.post(
            self.candidate_url, data=json.dumps({
                "report_type": "overview", "export_id": str(uuid4()),
            }), content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)

    def test_summary_counts_legacy_manager_pdf_and_packages_once(self):
        from django.utils import timezone
        date = timezone.localdate()
        ActivityEvent.objects.create(
            company=self.company, process=self.process,
            verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
        )
        ActivityEvent.objects.create(
            company=self.company, process=self.process,
            verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED,
            meta={"report": "manager_report", "status": "client_reported_generated"},
        )
        self.post_receipt(self.candidate_url, "personality-results")
        self.post_receipt(self.candidate_url, "candidate-package-zip")
        self.post_receipt(self.team_url, "team-package-pdf")
        ActivityEvent.objects.create(
            company=self.other,
            verb=ActivityEvent.Verb.REPORT_EXPORT_GENERATED,
            meta={"report_type": "team-profile"},
        )
        summary = platform_report_exports(start=date, end=date,
                                          company=self.company.pk)
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["pdf"], 3)
        self.assertEqual(summary["zip"], 1)
        codes = {row["code"]: row["count"] for row in summary["rows"]}
        self.assertEqual(codes["manager-report"], 1)
        self.assertEqual(codes["personality-results"], 1)
        self.assertEqual(codes["candidate-package-zip"], 1)
        self.assertEqual(codes["team-package-pdf"], 1)
        self.assertNotIn("team-profile", codes)
        stats_url = reverse("core:admin_ai_statistics")
        response = self.client.get(stats_url, {"company": self.company.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["report_exports"]["total"], 4)
        self.assertContains(response, 'class="talena-ai-stats__report-exports"')
        # The organisation filter legitimately lists other tenant names;
        # no other tenant's export must affect this filtered metric.
        self.assertEqual(sum(row["count"] for row in
                             response.context["report_exports"]["rows"]), 4)

    def test_empty_summary_does_not_count_pdf_preparations(self):
        from django.utils import timezone
        date = timezone.localdate()
        ActivityEvent.objects.create(
            company=self.company,
            verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
        )
        summary = platform_report_exports(
            start=date, end=date, company=self.company.pk,
        )
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["rows"], [])
