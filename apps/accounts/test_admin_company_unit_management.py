"""Admin-only company and organisation-unit rename/deletion safeguards."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    Company, CompanyMember, OrgUnit, UserOrgUnitAccess,
)
from apps.activity.models import ActivityEvent
from apps.processes.models import TestProcess
from apps.teams.models import Team


User = get_user_model()


class AdminCompanyAndUnitManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="rename-admin", email="admin@example.com",
            password="test-password",
        )
        self.customer = User.objects.create_user(
            username="rename-customer", email="customer@example.com",
            password="test-password",
        )
        self.company = Company.objects.create(
            name="Original company", org_number="556677-8899",
        )
        self.other_company = Company.objects.create(name="Other company")
        self.main = OrgUnit.objects.create(
            company=self.company, name="Main account", unit_code="MAIN",
        )
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Sales unit", unit_code="SALES",
        )
        self.other_unit = OrgUnit.objects.create(
            company=self.other_company, name="Other unit", unit_code="OTHER",
        )
        CompanyMember.objects.create(company=self.company, user=self.customer)
        self.client.force_login(self.admin)

    def company_url(self, company=None):
        return reverse(
            "accounts:company_rename", args=[(company or self.company).pk],
        )

    def rename_url(self, unit=None, company=None):
        return reverse(
            "accounts:orgunit_rename",
            args=[(company or self.company).pk, (unit or self.unit).pk],
        )

    def delete_url(self, unit=None, company=None):
        return reverse(
            "accounts:orgunit_delete",
            args=[(company or self.company).pk, (unit or self.unit).pk],
        )

    def test_company_rename_changes_only_name_and_logs_it(self):
        old_pk = self.company.pk
        response = self.client.post(self.company_url(), {"name": "  New company  "})
        self.assertRedirects(response, reverse(
            "accounts:company_detail", args=[self.company.pk],
        ))
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "New company")
        self.assertEqual(self.company.pk, old_pk)
        self.assertEqual(self.company.org_number, "556677-8899")
        self.assertTrue(OrgUnit.objects.filter(pk=self.unit.pk, company=self.company).exists())
        event = ActivityEvent.objects.get(
            company=self.company, verb=ActivityEvent.Verb.COMPANY_UPDATED,
        )
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.meta["old_name"], "Original company")
        self.assertEqual(event.meta["new_name"], "New company")

    def test_company_rename_rejects_blank_and_get(self):
        self.assertEqual(self.client.get(self.company_url()).status_code, 405)
        self.client.post(self.company_url(), {"name": "   "})
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Original company")
        self.assertFalse(ActivityEvent.objects.filter(
            company=self.company, verb=ActivityEvent.Verb.COMPANY_UPDATED,
        ).exists())

    def test_unit_rename_keeps_code_and_project_links(self):
        project = TestProcess.objects.create(
            company=self.company, org_unit=self.unit,
            created_by=self.customer, name="Sales recruitment",
            project_code="RECRUIT", account_code="SALES",
        )
        self.assertRedirects(
            self.client.post(self.rename_url(), {"name": "  Customer success  "}),
            reverse("accounts:company_account_structure", args=[self.company.pk]),
        )
        self.unit.refresh_from_db()
        project.refresh_from_db()
        self.assertEqual(self.unit.name, "Customer success")
        self.assertEqual(self.unit.unit_code, "SALES")
        self.assertEqual(project.org_unit, self.unit)
        self.assertEqual(project.account_code, "SALES")
        event = ActivityEvent.objects.get(verb=ActivityEvent.Verb.ORGUNIT_UPDATED)
        self.assertEqual(event.meta["old_name"], "Sales unit")
        self.assertEqual(event.meta["new_name"], "Customer success")

    def test_unit_rename_rejects_blank_and_does_not_reassign_code(self):
        self.assertEqual(self.client.get(self.rename_url()).status_code, 405)
        self.client.post(self.rename_url(), {
            "name": " ", "unit_code": "WRONG",
        })
        self.unit.refresh_from_db()
        self.assertEqual(self.unit.name, "Sales unit")
        self.assertEqual(self.unit.unit_code, "SALES")

    def test_can_delete_unused_leaf_without_affecting_other_units(self):
        self.assertRedirects(
            self.client.post(self.delete_url()),
            reverse("accounts:company_account_structure", args=[self.company.pk]),
        )
        self.assertFalse(OrgUnit.objects.filter(pk=self.unit.pk).exists())
        self.assertTrue(OrgUnit.objects.filter(pk=self.main.pk).exists())
        self.assertTrue(OrgUnit.objects.filter(pk=self.other_unit.pk).exists())
        event = ActivityEvent.objects.get(
            company=self.company, verb=ActivityEvent.Verb.ORGUNIT_DELETED,
        )
        self.assertEqual(event.meta["unit_code"], "SALES")

    def test_main_account_is_protected(self):
        self.assertEqual(self.client.post(self.delete_url(self.main)).status_code, 302)
        self.assertTrue(OrgUnit.objects.filter(pk=self.main.pk).exists())

    def test_parent_unit_is_protected_until_children_moved(self):
        child = OrgUnit.objects.create(
            company=self.company, name="Sub account", unit_code="SUB",
            parent=self.unit,
        )
        self.client.post(self.delete_url())
        self.assertTrue(OrgUnit.objects.filter(pk=self.unit.pk).exists())
        self.assertTrue(OrgUnit.objects.filter(pk=child.pk).exists())

    def test_unit_with_project_is_protected(self):
        project = TestProcess.objects.create(
            company=self.company, org_unit=self.unit,
            created_by=self.customer, name="Live project",
            project_code="LIVE", account_code="SALES",
        )
        self.client.post(self.delete_url())
        self.assertTrue(OrgUnit.objects.filter(pk=self.unit.pk).exists())
        self.assertTrue(TestProcess.objects.filter(pk=project.pk).exists())

    def test_unit_with_team_is_protected(self):
        team = Team.objects.create(
            company=self.company, org_unit=self.unit, name="Team A",
        )
        self.client.post(self.delete_url())
        self.assertTrue(OrgUnit.objects.filter(pk=self.unit.pk).exists())
        self.assertTrue(Team.objects.filter(pk=team.pk).exists())

    def test_unit_with_primary_member_or_user_access_is_protected(self):
        membership = CompanyMember.objects.get(company=self.company, user=self.customer)
        membership.primary_org_unit = self.unit
        membership.save(update_fields=["primary_org_unit"])
        self.client.post(self.delete_url())
        self.assertTrue(OrgUnit.objects.filter(pk=self.unit.pk).exists())
        membership.primary_org_unit = None
        membership.save(update_fields=["primary_org_unit"])
        access = UserOrgUnitAccess.objects.create(user=self.customer, org_unit=self.unit)
        self.client.post(self.delete_url())
        self.assertTrue(OrgUnit.objects.filter(pk=self.unit.pk).exists())
        self.assertTrue(UserOrgUnitAccess.objects.filter(pk=access.pk).exists())

    def test_cross_company_unit_routes_are_not_accessible(self):
        for url in (
            self.rename_url(self.other_unit, self.company),
            self.delete_url(self.other_unit, self.company),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, {"name": "Wrong"}).status_code, 404)
        self.other_unit.refresh_from_db()
        self.assertEqual(self.other_unit.name, "Other unit")

    def test_non_admin_cannot_rename_or_delete(self):
        self.client.force_login(self.customer)
        for url, body in (
            (self.company_url(), {"name": "Hacked"}),
            (self.rename_url(), {"name": "Hacked"}),
            (self.delete_url(), {}),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, body).status_code, 403)
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, "Original company")
        self.assertTrue(OrgUnit.objects.filter(pk=self.unit.pk).exists())

    def test_structure_displays_both_modal_actions_and_disabled_main(self):
        response = self.client.get(reverse(
            "accounts:company_account_structure", args=[self.company.pk],
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-unit-rename-url=')
        self.assertContains(response, 'data-unit-delete-url=')
        self.assertContains(response, 'id="renameOrgUnitModal"', count=1)
        self.assertContains(response, 'id="deleteOrgUnitModal"', count=1)
        self.assertContains(response, 'aria-label="Cannot delete Main account"')
        self.assertContains(response, 'id="companyRenameModal"', count=1)
        self.assertContains(response, reverse(
            "accounts:company_rename", args=[self.company.pk],
        ))

    def test_rename_company_works_from_overview_too(self):
        response = self.client.get(reverse(
            "accounts:company_detail", args=[self.company.pk],
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-bs-target="#companyRenameModal"')
