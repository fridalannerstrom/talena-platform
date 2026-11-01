"""HTTP-level regression tests for project duplication (ticket #328)."""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess,
)
from apps.processes.models import (
    Candidate, ProcessLabel, ProcessRoleContext, TestInvitation, TestProcess,
)
from apps.processes.process_settings_models import ProcessAutomationSettings


class ProcessDuplicationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Example company")
        self.other_company = Company.objects.create(name="Other company")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Sweden", unit_code="SE",
        )
        self.other_unit = OrgUnit.objects.create(
            company=self.other_company, name="Elsewhere", unit_code="OTHER",
        )

        def create_user(username, company, unit, permission):
            user = User.objects.create_user(username=username, password="test")
            CompanyMember.objects.create(
                user=user, company=company, primary_org_unit=unit,
            )
            UserOrgUnitAccess.objects.create(
                user=user, org_unit=unit, permission=permission,
            )
            return user

        self.owner = create_user("owner", self.company, self.unit, "editor")
        self.editor = create_user("editor", self.company, self.unit, "editor")
        self.viewer = create_user("viewer", self.company, self.unit, "viewer")
        self.own_only = create_user("own", self.company, self.unit, "own")
        self.outsider = create_user(
            "outsider", self.other_company, self.other_unit, "editor",
        )
        self.source = TestProcess.objects.create(
            name="Leadership",
            company=self.company,
            org_unit=self.unit,
            created_by=self.owner,
            provider="sova",
            account_code="SOVA",
            project_code="PQ_MQ",
            project_name_snapshot="Personality and motivation",
            job_title="Team lead",
            job_location="Stockholm",
            notes="Shared project instructions",
            purpose="hiring",
            selected_tests=["personality", "motivation"],
            candidate_language="en",
            candidate_results_enabled=True,
        )
        self.label = ProcessLabel.objects.create(company=self.company, name="Priority")
        self.source.labels.add(self.label)
        self.context = ProcessRoleContext.objects.create(
            process=self.source,
            context_text="People leadership, coaching, team culture",
            role_title="Lead",
            requirements_profile="Experience in coaching",
            competency_profile="Organisational skills",
            interview_notes="Legacy sensitive interview notes",
            purpose_data={"hiring": {"context_text": "Specific job context"}},
        )
        ProcessAutomationSettings.objects.create(
            process=self.source, automatic_invitation_enabled=True,
        )
        candidate = Candidate.objects.create(
            first_name="Alex", last_name="Case", email="alex@example.org",
        )
        TestInvitation.objects.create(
            process=self.source, candidate=candidate, status="completed",
            sova_project_id=849,
            ai_summary="Private candidate insight",
        )

        # A live Sova connection must not be required for duplication.
        mock_sova = patch("apps.core.integrations.sova.SovaClient")
        self.addCleanup(mock_sova.stop)
        self.sova = mock_sova.start()
        self.sova.side_effect = RuntimeError("Sova offline")
        self.url = reverse("processes:process_duplicate", args=[self.source.pk])

    def test_editor_duplicates_config_but_not_candidates(self):
        self.client.force_login(self.editor)
        self.source.archive()
        confirmation = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "Leadership (kopia)")
        response = self.client.post(self.url, {"name": "New team lead"})
        self.assertEqual(response.status_code, 302)
        duplicate = TestProcess.objects.get(name="New team lead")
        self.assertEqual(
            response.url, reverse("processes:process_detail", args=[duplicate.pk]),
        )
        self.assertNotEqual(duplicate.pk, self.source.pk)
        self.assertNotEqual(
            duplicate.self_registration_token, self.source.self_registration_token,
        )
        self.assertEqual(duplicate.company, self.company)
        self.assertEqual(duplicate.org_unit, self.unit)
        self.assertEqual(duplicate.created_by, self.editor)
        self.assertEqual(duplicate.account_code, "SOVA")
        self.assertEqual(duplicate.project_code, "PQ_MQ")
        self.assertEqual(duplicate.project_name_snapshot, self.source.project_name_snapshot)
        self.assertEqual(duplicate.purpose, self.source.purpose)
        self.assertEqual(duplicate.selected_tests, ["personality", "motivation"])
        self.assertEqual(duplicate.candidate_language, "en")
        self.assertTrue(duplicate.candidate_results_enabled)
        self.assertEqual(duplicate.job_title, self.source.job_title)
        self.assertEqual(duplicate.job_location, self.source.job_location)
        self.assertEqual(duplicate.notes, self.source.notes)
        self.assertFalse(duplicate.is_archived)
        self.assertIsNone(duplicate.archived_at)
        self.assertEqual(list(duplicate.labels.all()), [self.label])
        self.assertEqual(duplicate.role_context.context_text, self.context.context_text)
        self.assertEqual(duplicate.role_context.purpose_data, self.context.purpose_data)
        self.assertEqual(duplicate.role_context.requirements_profile, self.context.requirements_profile)
        self.assertEqual(duplicate.role_context.interview_notes, "")
        self.assertTrue(duplicate.automation_settings.automatic_invitation_enabled)
        self.assertEqual(duplicate.invitations.count(), 0)
        self.assertEqual(duplicate.self_registrations.count(), 0)
        self.assertEqual(duplicate.historical_candidates.count(), 0)

    def test_own_permission_applies_to_own_process_only(self):
        self.client.force_login(self.own_only)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        owned = TestProcess.objects.create(
            name="Owned", company=self.company, org_unit=self.unit,
            created_by=self.own_only, account_code="SOVA", project_code="PQ_MQ",
        )
        owned_url = reverse("processes:process_duplicate", args=[owned.pk])
        self.assertEqual(self.client.get(owned_url).status_code, 200)
        self.assertEqual(
            self.client.post(owned_url, {"name": "Owned copy"}).status_code, 302,
        )
        self.assertTrue(TestProcess.objects.filter(name="Owned copy").exists())

    def test_viewer_and_other_tenant_cannot_use_direct_url(self):
        for user in (self.viewer, self.outsider):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(
                self.client.post(self.url, {"name": "Unauthorized"}).status_code,
                403,
            )
        self.assertFalse(TestProcess.objects.filter(name="Unauthorized").exists())
        self.sova.assert_not_called()

    def test_duplicate_icon_only_on_editable_process_cards(self):
        self.client.force_login(self.editor)
        self.assertContains(
            self.client.get(reverse("processes:process_list")), self.url,
        )
        self.client.force_login(self.viewer)
        self.assertNotContains(
            self.client.get(reverse("processes:process_list")), self.url,
        )

    def test_blank_name_does_not_create_process(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {"name": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TestProcess.objects.count(), 1)
        self.sova.assert_not_called()

    def test_missing_saved_template_leaves_no_copy(self):
        self.client.force_login(self.owner)
        self.source.project_code = ""
        self.source.save(update_fields=["project_code"])
        response = self.client.post(self.url, {"name": "Unused"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no saved Sova template")
        self.assertFalse(TestProcess.objects.filter(name="Unused").exists())
        self.sova.assert_not_called()

    def test_sova_outage_does_not_block_duplicate(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {"name": "Offline copy"})
        self.assertEqual(response.status_code, 302)
        copy = TestProcess.objects.get(name="Offline copy")
        self.assertEqual(copy.account_code, "SOVA")
        self.assertEqual(copy.project_code, "PQ_MQ")
        self.assertEqual(copy.invitations.count(), 0)
        self.sova.assert_not_called()

    def test_missing_saved_account_leaves_no_copy(self):
        self.client.force_login(self.owner)
        self.source.account_code = ""
        self.source.save(update_fields=["account_code"])
        response = self.client.post(self.url, {"name": "Unused"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no saved Sova template")
        self.assertFalse(TestProcess.objects.filter(name="Unused").exists())

    def test_historical_process_cannot_be_duplicated(self):
        self.client.force_login(self.owner)
        self.source.is_historical = True
        self.source.save(update_fields=["is_historical"])
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {"name": "No"}).status_code, 404)
