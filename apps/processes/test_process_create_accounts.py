from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Company, CompanyMember, OrgUnit, UserOrgUnitAccess
from apps.processes.models import TestProcess


class ProcessCreateAccountTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="account-selector@example.com",
            email="account-selector@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.company = Company.objects.create(name="First company")
        CompanyMember.objects.create(company=self.company, user=self.user)
        self.first = OrgUnit.objects.create(
            company=self.company, name="First account", unit_code="FIRST"
        )
        UserOrgUnitAccess.objects.create(user=self.user, org_unit=self.first)
        self.url = reverse("processes:process_create")
        sova = patch("apps.processes.views.SovaClient")
        self.addCleanup(sova.stop)
        sova.start().return_value.get_template_accounts_with_projects.return_value = [{
            "name": "Talena Modern Projects",
            "code": "SOVA",
            "projects": [{"code": "PERSONALITY", "name": "Personality", "id": 12}],
        }]

    def _post(self, **overrides):
        data = {
            "purpose": "hiring",
            "selected_tests": ["personality"],
            "candidate_language": "sv",
            "name": "Account selection test",
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_single_account_is_selected_without_a_form_choice(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="org_unit"')

        response = self._post()
        self.assertEqual(response.status_code, 302)
        process = TestProcess.objects.get(name="Account selection test")
        self.assertEqual(process.org_unit, self.first)
        self.assertEqual(process.company, self.company)

    def test_multiple_accounts_require_a_choice_and_save_selected_company(self):
        company_two = Company.objects.create(name="Second company")
        CompanyMember.objects.create(company=company_two, user=self.user)
        second = OrgUnit.objects.create(
            company=company_two, name="Second account", unit_code="SECOND"
        )
        UserOrgUnitAccess.objects.create(user=self.user, org_unit=second)

        response = self.client.get(self.url)
        self.assertContains(response, 'name="org_unit"')
        self.assertContains(response, "First company · First account")
        self.assertContains(response, "Second company · Second account")

        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertIn("org_unit", response.context["form"].errors)
        self.assertFalse(TestProcess.objects.exists())

        response = self._post(org_unit=str(second.pk))
        self.assertEqual(response.status_code, 302)
        process = TestProcess.objects.get(name="Account selection test")
        self.assertEqual(process.org_unit, second)
        self.assertEqual(process.company, company_two)

    def test_account_from_another_company_cannot_be_selected(self):
        other_company = Company.objects.create(name="Other company")
        other = OrgUnit.objects.create(
            company=other_company, name="Private account", unit_code="PRIVATE"
        )
        second = OrgUnit.objects.create(
            company=self.company, name="Second account", unit_code="SECOND"
        )
        UserOrgUnitAccess.objects.create(user=self.user, org_unit=second)

        response = self._post(org_unit=str(other.pk))
        self.assertEqual(response.status_code, 200)
        self.assertIn("org_unit", response.context["form"].errors)
        self.assertFalse(TestProcess.objects.exists())
