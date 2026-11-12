"""Verify obsolete historical PDF reports are no longer available in Talena.

Historical Excel results and live Sova reports remain untouched. Previously
stored PDF blobs require a separate reviewed retention/deletion procedure.
"""
from pathlib import Path

from django.contrib import admin
from django.test import SimpleTestCase
from django.urls import NoReverseMatch, reverse

from apps.processes.forms import HistoricalCandidateForm
from apps.processes.models import HistoricalCandidateReport

ROOT = Path(__file__).resolve().parents[2]


class HistoricalCandidatePDFRemovalTests(SimpleTestCase):
    def test_no_pdf_upload_field(self):
        self.assertNotIn("historical_reports", HistoricalCandidateForm().fields)

    def test_old_download_url_name_removed(self):
        with self.assertRaises(NoReverseMatch):
            reverse("processes:historical_candidate_report_download", kwargs={
                "process_id": 10,
                "candidate_id": 20,
                "report_id": 30,
            })

    def test_pdf_model_is_not_registered_in_django_admin(self):
        self.assertNotIn(HistoricalCandidateReport, admin.site._registry)

    def test_no_pdf_links_or_uploads_in_historical_candidate_views(self):
        for path in (
            "templates/admin/accounts/companies/company_historical_candidate_form.html",
            "templates/admin/accounts/companies/company_candidate_sheet.html",
            "templates/customer/processes/partials/candidate_insights/_workspace.html",
        ):
            with self.subTest(path=path):
                content = (ROOT / path).read_text(encoding="utf-8")
                self.assertNotIn("historical_reports", content)
                self.assertNotIn("historical_candidate_report_download", content)
                self.assertNotIn("form.historical_reports", content)

    def test_live_sova_report_links_are_preserved(self):
        template = (
            ROOT / "templates/customer/processes/partials/"
            "candidate_insights/_workspace.html"
        ).read_text(encoding="utf-8")
        self.assertIn("not is_historical and sova_reports_for_ui", template)
        self.assertIn("{% for report in sova_reports_for_ui %}", template)
        self.assertIn('href="{{ report.url }}"', template)
