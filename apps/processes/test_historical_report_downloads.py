"""#309: historical PDF delivery must enforce permission on every request."""

from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import (
    Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess,
)
from apps.processes.models import (
    Candidate, HistoricalCandidateReport, HistoricalProcessCandidate,
    TestProcess,
)


class HistoricalReportDownloadAuthorizationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_tmp = TemporaryDirectory()
        cls._media_settings = override_settings(MEDIA_ROOT=cls._media_tmp.name)
        cls._media_settings.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_settings.disable()
        cls._media_tmp.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.company_a = Company.objects.create(name="Historical PDF company A")
        self.company_b = Company.objects.create(name="Historical PDF company B")
        self.unit_a = OrgUnit.objects.create(
            company=self.company_a, name="Allowed unit", unit_code="HIST-A",
        )
        self.unit_hidden = OrgUnit.objects.create(
            company=self.company_a, name="Hidden unit", unit_code="HIST-X",
        )
        self.unit_b = OrgUnit.objects.create(
            company=self.company_b, name="Foreign unit", unit_code="HIST-B",
        )

        def member(name, company, unit, perm):
            user = User.objects.create_user(username=name, password="not-real")
            CompanyMember.objects.create(
                company=company, user=user, primary_org_unit=unit,
            )
            UserOrgUnitAccess.objects.create(
                user=user, org_unit=unit, permission=perm,
            )
            return user

        self.creator = member(
            "historic-owner", self.company_a, self.unit_a, "editor"
        )
        self.viewer = member(
            "historic-viewer", self.company_a, self.unit_a, "viewer"
        )
        self.editor = member(
            "historic-editor", self.company_a, self.unit_a, "editor"
        )
        self.own_only = member(
            "historic-own", self.company_a, self.unit_a, "own"
        )
        self.hidden_unit_user = member(
            "historic-hidden", self.company_a, self.unit_hidden, "viewer"
        )
        self.foreign = member(
            "historic-foreign", self.company_b, self.unit_b, "editor"
        )
        self.admin = User.objects.create_superuser(
            username="historic-platform-admin",
            email="historic-platform-admin@example.org",
            password="not-real",
        )
        self.process = TestProcess.objects.create(
            name="Archived Sova A", provider="sova",
            company=self.company_a, org_unit=self.unit_a,
            created_by=self.creator, project_code="HIST-P-A",
            account_code="HIST-A", is_historical=True,
        )
        self.candidate = Candidate.objects.create(
            first_name="Fictional", last_name="Applicant",
            email="fictional-applicant@example.org",
        )
        self.owner = HistoricalProcessCandidate.objects.create(
            process=self.process, candidate=self.candidate, status="completed",
        )
        self.pdf = b"%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF\n"
        self.report = HistoricalCandidateReport.objects.create(
            historical_candidate=self.owner,
            title="Example assessment",
            original_filename="example-sova-report.pdf",
            file=SimpleUploadedFile(
                "example-sova-report.pdf", self.pdf,
                content_type="application/pdf",
            ),
            uploaded_by=self.creator,
        )
        self.url = reverse(
            "processes:historical_candidate_report_download",
            kwargs={
                "process_id": self.process.pk,
                "candidate_id": self.candidate.pk,
                "report_id": self.report.pk,
            },
        )

    def test_viewer_editor_and_global_admin_can_open_scoped_report(self):
        for user in (self.viewer, self.editor, self.admin):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "application/pdf")
                self.assertIn("inline", response["Content-Disposition"])
                self.assertEqual(response["Cache-Control"], "private, no-store")
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")
                self.assertEqual(b"".join(response.streaming_content), self.pdf)
                response.close()

    def test_cannot_download_from_other_company_hidden_unit_or_others_own_process(self):
        for user in (self.foreign, self.hidden_unit_user, self.own_only):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(self.pdf, response.content)

    def test_anonymous_user_must_sign_in(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response["Location"])

    def test_report_id_must_match_both_process_and_candidate(self):
        self.client.force_login(self.viewer)
        other_candidate = Candidate.objects.create(
            first_name="Different", last_name="Applicant",
            email="different-applicant@example.org",
        )
        other_owner = HistoricalProcessCandidate.objects.create(
            process=self.process, candidate=other_candidate,
        )
        other_report = HistoricalCandidateReport.objects.create(
            historical_candidate=other_owner,
            title="Different report",
            original_filename="different.pdf",
            file=SimpleUploadedFile(
                "different.pdf", self.pdf, content_type="application/pdf",
            ),
        )
        mismatches = [
            {"process_id": self.process.id, "candidate_id": other_candidate.id,
             "report_id": self.report.id},
            {"process_id": self.process.id, "candidate_id": self.candidate.id,
             "report_id": other_report.id},
        ]
        for kwargs in mismatches:
            with self.subTest(kwargs=kwargs):
                response = self.client.get(reverse(
                    "processes:historical_candidate_report_download",
                    kwargs=kwargs,
                ))
                self.assertEqual(response.status_code, 404)

    def test_raw_storage_urls_are_not_exposed_in_historical_report_links(self):
        root = Path(__file__).resolve().parents[2]
        for path in (
            "templates/customer/processes/partials/candidate_insights/_workspace.html",
            "templates/admin/accounts/companies/company_candidate_sheet.html",
        ):
            with self.subTest(path=path):
                html = (root / path).read_text(encoding="utf-8")
                self.assertNotIn("report.file.url", html)
                self.assertIn(
                    "processes:historical_candidate_report_download", html,
                )
