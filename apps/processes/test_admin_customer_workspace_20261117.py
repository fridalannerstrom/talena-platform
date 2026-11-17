"""Regression tests for staff working in a real customer candidate workspace.

All fixtures are synthetic. No Sova/OpenAI calls are needed.
"""
import json

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.models import Candidate, TestInvitation, TestProcess


class AdminCustomerWorkspaceTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Workspace Customer")
        self.other_company = Company.objects.create(name="Other Customer")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Recruitment", unit_code="WS-117"
        )
        self.other_unit = OrgUnit.objects.create(
            company=self.other_company, name="Other", unit_code="WS-OTHER"
        )
        self.admin = User.objects.create_superuser(
            username="workspace-admin", email="workspace-admin@example.test",
            password="not-used",
        )
        self.customer = User.objects.create_user(
            username="workspace-customer", email="workspace-customer@example.test",
            password="not-used",
        )
        CompanyMember.objects.create(
            company=self.company, user=self.customer, primary_org_unit=self.unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.customer, org_unit=self.unit, permission="editor",
        )
        self.other_user = User.objects.create_user(
            username="workspace-outsider", email="workspace-outsider@example.test",
            password="not-used",
        )
        CompanyMember.objects.create(
            company=self.other_company, user=self.other_user,
            primary_org_unit=self.other_unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.other_user, org_unit=self.other_unit, permission="editor",
        )
        self.process = TestProcess.objects.create(
            company=self.company, org_unit=self.unit, created_by=self.customer,
            name="Customer recruitment", purpose="hiring",
            account_code="MODERN", project_code="PQ-MQ",
            selected_tests=["personality", "motivation"], candidate_language="sv",
        )
        self.candidate = Candidate.objects.create(
            first_name="Synthetic", last_name="Candidate",
            email="synthetic-workspace@example.test",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process, candidate=self.candidate,
            status="created", source="invited",
        )
        self.detail_url = reverse(
            "processes:process_detail", args=[self.process.pk],
        )
        self.candidate_admin_url = reverse(
            "accounts:company_process_candidate_detail",
            args=[self.company.pk, self.process.pk, self.candidate.pk],
        )
        self.notes_url = reverse(
            "processes:process_candidate_interview_notes_update",
            args=[self.process.pk, self.candidate.pk],
        )

    def test_admin_without_company_membership_gets_real_customer_workspace(self):
        self.assertFalse(CompanyMember.objects.filter(user=self.admin).exists())
        self.client.force_login(self.admin)
        response = self.client.get(
            self.detail_url + "?focus_candidate=" + str(self.candidate.pk)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["process_base_layout"],
            "admin/core/layouts/admin_base.html",
        )
        self.assertTrue(response.context["can_edit"])
        markup = response.content.decode("utf-8")
        self.assertIn("talena-admin", markup)
        self.assertIn("focus_candidate", markup)
        self.assertIn('data-candidate-id="%s"' % self.candidate.pk, markup)

    def test_role_context_is_accessible_in_admin_work_mode(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("processes:process_role_context", args=[self.process.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["process_base_layout"],
            "admin/core/layouts/admin_base.html",
        )
        self.assertTrue(response.context["can_edit"])

    def test_admin_candidate_preview_links_to_edit_without_enabling_preview_writes(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            self.candidate_admin_url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        markup = response.content.decode("utf-8")
        self.assertIn("Arbeta med kandidaten", markup)
        self.assertIn("Rollkontext och personlighetsdrag", markup)
        self.assertIn(
            "?focus_candidate=%s" % self.candidate.pk, markup,
        )
        self.assertIn('data-read-only="true"', markup)

    def test_admin_work_mode_uses_write_enabled_candidate_endpoints(self):
        self.client.force_login(self.admin)
        candidate_url = reverse(
            "processes:process_candidate_detail",
            args=[self.process.pk, self.candidate.pk],
        )
        response = self.client.get(
            candidate_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["can_manage_candidate_results"])
        markup = response.content.decode("utf-8")
        self.assertIn('data-admin-read-only="false"', markup)
        self.assertIn('data-interview-notes-update-url="', markup)
        self.assertIn('data-personality-questions-root', markup)
        self.invitation.refresh_from_db()
        self.assertFalse(self.invitation.interview_notes)

    def test_admin_interview_notes_update_real_candidate_owner(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.notes_url,
            data=json.dumps({"interview_notes": "Synthetic interview notes"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.interview_notes, "Synthetic interview notes")

    def test_other_company_member_cannot_view_or_edit(self):
        self.client.force_login(self.other_user)
        response = self.client.get(self.detail_url)
        self.assertIn(response.status_code, (403, 404))
        response = self.client.post(
            self.notes_url,
            data=json.dumps({"interview_notes": "Must not save"}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, (403, 404))
        self.invitation.refresh_from_db()
        self.assertFalse(self.invitation.interview_notes)

    def test_customer_keeps_original_shell_and_editor_permissions(self):
        self.client.force_login(self.customer)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["process_base_layout"], "")
        self.assertTrue(response.context["can_edit"])
        self.assertNotIn("Administrator workspace:", response.content.decode("utf-8"))
