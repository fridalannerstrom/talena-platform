"""Issue #206: project terminology stays consistent in the customer UI.

Tests verify compiled Swedish gettext messages as well as rendered customer
templates, without touching Django model names, saved URLs or Sova identifiers.
"""
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import gettext, override

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.models import TestProcess


class ProjectTerminologyTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Customer")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Sweden", unit_code="SV"
        )
        self.user = User.objects.create_user(
            username="project-terminology-editor", password="not-used"
        )
        CompanyMember.objects.create(
            company=self.company, user=self.user, primary_org_unit=self.unit
        )
        UserOrgUnitAccess.objects.create(
            user=self.user, org_unit=self.unit, permission="editor"
        )
        self.project = TestProcess.objects.create(
            company=self.company,
            org_unit=self.unit,
            name="Sales",
            created_by=self.user,
            account_code="TALENA",
            project_code="PQ",
        )
        self.client.force_login(self.user)

    def test_compiled_swedish_project_translations(self):
        with override("sv"):
            self.assertEqual(gettext("Projects"), "Projekt")
            self.assertEqual(gettext("Create project"), "Skapa projekt")
            self.assertEqual(gettext("Project settings"), "Projektinställningar")
            self.assertEqual(gettext("Project context"), "Projektkontext")
            self.assertEqual(gettext("Back to projects"), "Tillbaka till projekt")
        with override("en"):
            self.assertEqual(gettext("Projects"), "Projects")
            self.assertEqual(gettext("Create project"), "Create project")

    def test_project_list_swedish_labels(self):
        response = self.client.get(
            reverse("processes:process_list"), HTTP_ACCEPT_LANGUAGE="sv"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skapa projekt")
        self.assertContains(response, "Projekt")
        self.assertNotContains(response, "Testprocesser")
        self.assertNotContains(response, "Skapa testprocess")

    def test_project_list_english_labels(self):
        response = self.client.get(
            reverse("processes:process_list"), HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create project")
        self.assertContains(response, "Projects")
        self.assertNotContains(response, "Test processes")
        self.assertNotContains(response, "Create test process")

    def test_project_detail_navigation_swedish(self):
        response = self.client.get(
            reverse("processes:process_detail", args=[self.project.pk]),
            HTTP_ACCEPT_LANGUAGE="sv",
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tillbaka till projekt")
        self.assertNotContains(response, "Tillbaka till processer")
