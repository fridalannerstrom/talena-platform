"""Customer project wizard: Integrity Guard visibility only affects Talena.

All fixtures are synthetic. No Sova/OpenAI network calls are made.
"""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.forms import TestProcessWizardCreateForm
from apps.processes.models import TestProcess


class CustomerProjectIntegrityGuardWizardTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Synthetic wizard company")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Recruitment", unit_code="WIG-001",
        )
        self.customer = User.objects.create_user(
            username="wizard-ig-customer", email="wizard-ig@example.test",
            password="test-password",
        )
        CompanyMember.objects.create(
            company=self.company, user=self.customer, primary_org_unit=self.unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.customer, org_unit=self.unit, permission="editor",
        )
        self.url = reverse("processes:process_create")
        self.client.force_login(self.customer)
        self.data = {
            "purpose": "hiring",
            "selected_tests": ["personality"],
            "candidate_language": "sv",
            "org_unit": str(self.unit.pk),
            "name": "Synthetic new recruitment",
            "integrity_guard_visibility": "default",
        }
        self.sova_template = {
            "account_code": "SYNTHETIC",
            "project_code": "PQ",
            "value": "SYNTHETIC|PQ",
            "sova_name": "Synthetic Sova PQ",
            "title": "Synthetic Sova PQ",
        }

    def _post(self, **values):
        data = {**self.data, **values}
        with (
            patch("apps.processes.views.SovaClient") as sova,
            patch("apps.processes.views.resolve_sova_template",
                  return_value=self.sova_template),
        ):
            sova.return_value.get_template_accounts_with_projects.return_value = []
            return self.client.post(self.url, data)

    def test_last_step_shows_all_three_visibility_choices(self):
        with patch("apps.processes.views.SovaClient") as sova:
            sova.return_value.get_template_accounts_with_projects.return_value = []
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        markup = response.content.decode("utf-8")
        self.assertIn('name="integrity_guard_visibility"', markup)
        for value in ("default", "on", "off"):
            self.assertIn('value="%s"' % value, markup)
        self.assertIn('id="wizardIgTitle"', markup)
        self.assertIn('data-step="3"', markup)
        # The setting belongs in Details, not the preceding Tests step.
        self.assertLess(
            markup.index('data-step="3"'),
            markup.index('id="wizardIgTitle"'),
        )
        self.assertLess(
            markup.index('id="wizardIgTitle"'),
            markup.index('type="submit"'),
        )

    def test_wizard_defaults_to_company_setting(self):
        field = TestProcessWizardCreateForm.base_fields["integrity_guard_visibility"]
        self.assertFalse(field.required)
        self.assertEqual(field.initial, "default")
        self.assertEqual(field.clean("default"), "default")

        # When no project choice is made, a company change remains effective.
        self.company.integrity_guard_visible = False
        self.company.save(update_fields=["integrity_guard_visible"])
        response = self._post(integrity_guard_visibility="default")
        self.assertEqual(response.status_code, 302)
        project = TestProcess.objects.get(name=self.data["name"])
        self.assertIsNone(project.integrity_guard_visible_override)
        self.assertFalse(project.integrity_guard_visible_in_talena)

        self.company.integrity_guard_visible = True
        self.company.save(update_fields=["integrity_guard_visible"])
        project.refresh_from_db()
        self.assertTrue(project.integrity_guard_visible_in_talena)

    def test_wizard_on_overrides_company_off(self):
        self.company.integrity_guard_visible = False
        self.company.save(update_fields=["integrity_guard_visible"])
        response = self._post(integrity_guard_visibility="on")
        self.assertEqual(response.status_code, 302)
        project = TestProcess.objects.get(name=self.data["name"])
        self.assertIs(project.integrity_guard_visible_override, True)
        self.assertTrue(project.integrity_guard_visible_in_talena)
        self.assertFalse(self.company.integrity_guard_visible)

    def test_wizard_off_overrides_company_on(self):
        response = self._post(integrity_guard_visibility="off")
        self.assertEqual(response.status_code, 302)
        project = TestProcess.objects.get(name=self.data["name"])
        self.assertIs(project.integrity_guard_visible_override, False)
        self.assertFalse(project.integrity_guard_visible_in_talena)
        self.assertTrue(self.company.integrity_guard_visible)

    def test_wizard_missing_choice_inherits_company_and_invalid_is_rejected(self):
        response = self._post(integrity_guard_visibility="")
        self.assertEqual(response.status_code, 302)
        project = TestProcess.objects.get(name=self.data["name"])
        self.assertIsNone(project.integrity_guard_visible_override)

        TestProcess.objects.all().delete()
        response = self._post(integrity_guard_visibility="not-a-real-option")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "integrity_guard_visibility")
        self.assertFalse(TestProcess.objects.exists())
