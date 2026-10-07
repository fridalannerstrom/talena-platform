import csv
from datetime import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company, OrgUnit
from apps.processes.models import AssessmentUsage, Candidate, TestInvitation, TestProcess


class BillingCsvExportTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="billing-admin@example.com",
            email="billing-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)
        self.company = Company.objects.create(name="Invoice company")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Sales", unit_code="SALES"
        )
        self.process = TestProcess.objects.create(
            name="Sales hiring",
            company=self.company,
            org_unit=self.unit,
            account_code="SOVA",
            project_code="PROJECT",
            created_by=self.admin,
        )
        candidate = Candidate.objects.create(
            first_name="Example", email="billing-candidate@example.com"
        )
        invitation = TestInvitation.objects.create(
            process=self.process, candidate=candidate, status="completed"
        )
        self.sent_at = timezone.make_aware(datetime(2026, 9, 19, 12))
        self.completed_at = timezone.make_aware(datetime(2026, 9, 20, 12))
        AssessmentUsage.objects.create(
            company=self.company,
            org_unit=self.unit,
            process=self.process,
            candidate=candidate,
            invitation=invitation,
            assessment_type="personality",
            status="completed",
            sent_at=self.sent_at,
            completed_at=self.completed_at,
            sent_by=self.admin,
        )
        AssessmentUsage.objects.create(
            company=self.company,
            org_unit=self.unit,
            process=self.process,
            candidate=candidate,
            invitation=invitation,
            assessment_type="motivation",
            status="sent",
            sent_at=self.sent_at,
            sent_by=self.admin,
        )
        self.url = reverse("accounts:admin_usage_billing")

    def _csv(self, **params):
        response = self.client.get(self.url, {
            "date_from": "2026-09-19",
            "date_to": "2026-09-20",
            "export": "csv",
            **params,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        rows = list(csv.reader(
            StringIO(response.content.decode("utf-8-sig")), delimiter=";"
        ))
        return response, rows

    def test_export_matches_filtered_billing_table_without_empty_columns(self):
        page = self.client.get(self.url, {
            "date_from": "2026-09-19",
            "date_to": "2026-09-20",
            "company": str(self.company.pk),
        })
        response, csv_rows = self._csv(company=str(self.company.pk))

        self.assertContains(page, "Sales hiring")
        self.assertEqual(len(page.context["rows"]), len(csv_rows) - 1)
        self.assertIn("talena-billing-2026-09-19-2026-09-20.csv",
                      response["Content-Disposition"])
        self.assertEqual(csv_rows[0], [
            "Company / account", "Process", "Sent by",
            "Candidates", "Tests", "Test types", "Status",
        ])
        self.assertEqual(len(csv_rows), 2)
        self.assertTrue(all(value for value in csv_rows[1]))
        self.assertEqual(csv_rows[1][3:6], ["1", "1", "Personality 1"])

    def test_lifecycle_and_date_filters_match_the_visible_rows(self):
        _, sent_rows = self._csv(lifecycle="sent")
        self.assertEqual(len(sent_rows), 2)
        self.assertEqual(sent_rows[1][4:6], [
            "2", "Personality 1, Motivation 1"
        ])
        self.assertEqual(len(sent_rows[0]), 6)

        _, empty_rows = self._csv(
            lifecycle="sent", date_from="2026-09-20", date_to="2026-09-20"
        )
        self.assertEqual(len(empty_rows), 1)

    def test_company_filter_excludes_other_company_usage(self):
        other = Company.objects.create(name="Other company")
        _, rows = self._csv(company=str(other.pk))
        self.assertEqual(len(rows), 1)
