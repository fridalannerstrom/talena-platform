"""Candidate directory: one independent, authorised row per project membership."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Company, CompanyMember, OrgUnit, UserOrgUnitAccess
from apps.processes.models import (
    Candidate, HistoricalAssessmentResult, HistoricalProcessCandidate,
    TestInvitation, TestProcess,
)
from apps.teams.models import Team, TeamMembership


User = get_user_model()


class CandidateDirectoryProjectMembershipTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Company A")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Main", unit_code="MAIN",
        )
        self.user = User.objects.create_user(
            username="directory-editor", password="test-password",
        )
        CompanyMember.objects.create(
            company=self.company, user=self.user,
            primary_org_unit=self.unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.user, org_unit=self.unit, permission="editor",
        )
        self.client.force_login(self.user)

        # The same email is intentionally ONE Candidate row in the database.
        self.candidate = Candidate.objects.create(
            first_name="Test", last_name="Visar", email="demo@test.se",
        )
        self.old_project = self.make_project(
            "Old demo with results", "OLD",
            ["personality", "motivation", "logical", "verbal", "numerical"],
        )
        self.new_project = self.make_project(
            "New demo without results", "NEW",
            ["personality", "motivation", "logical", "verbal", "numerical"],
        )
        self.old_invitation = TestInvitation.objects.create(
            process=self.old_project,
            candidate=self.candidate,
            status="completed",
            sova_activities=[
                {"activity": "Personality Questionnaire", "status": "completed"},
                {"activity": "Motivation Questionnaire", "status": "completed"},
                {"activity": "Logical reasoning", "status": "completed"},
                {"activity": "Verbal reasoning", "status": "completed"},
                {"activity": "Numerical reasoning", "status": "completed"},
            ],
        )
        self.new_invitation = TestInvitation.objects.create(
            process=self.new_project,
            candidate=self.candidate,
            status="sent",
            sova_activities=[
                {"activity": "Personality Questionnaire", "status": "started"},
                {"activity": "Motivation Questionnaire", "status": "sent"},
            ],
        )
        self.url = reverse("candidates:candidate_list")

    def make_project(self, name, code, selected_tests, *, company=None,
                     unit=None, created_by=None, is_historical=False):
        return TestProcess.objects.create(
            name=name, company=company or self.company,
            org_unit=unit or self.unit, created_by=created_by or self.user,
            account_code="DEMO", project_code=code,
            selected_tests=selected_tests, is_historical=is_historical,
        )

    def entries(self, response):
        return {
            entry.project.pk: entry
            for entry in response.context["candidates"]
        }

    def statuses(self, entry):
        return {
            test["key"]: test["status"]
            for test in entry.test_overview
        }

    def test_same_email_has_two_visible_project_entries_with_distinct_links(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["unique_candidate_count"], 1)
        self.assertEqual(len(response.context["candidates"]), 2)
        self.assertContains(response, "Test Visar", count=2)
        self.assertContains(response, "demo@test.se", count=2)
        self.assertContains(response, "Old demo with results")
        self.assertContains(response, "New demo without results")
        for project in (self.old_project, self.new_project):
            target = (
                reverse("processes:process_detail", args=[project.pk])
                + f"?open_candidate={self.candidate.pk}"
            )
            self.assertContains(response, target, count=1)
        self.assertEqual(Candidate.objects.filter(email="demo@test.se").count(), 1)

    def test_prior_results_do_not_make_new_project_appear_completed(self):
        response = self.client.get(self.url)
        rows = self.entries(response)
        old_status = self.statuses(rows[self.old_project.pk])
        new_status = self.statuses(rows[self.new_project.pk])
        self.assertTrue(all(status == "completed" for status in old_status.values()))
        self.assertEqual(new_status["personality"], "pending")
        self.assertEqual(new_status["motivation"], "pending")
        self.assertEqual(new_status["logical"], "pending")
        self.assertEqual(new_status["verbal"], "pending")
        self.assertEqual(new_status["numerical"], "pending")

    def test_unordered_activity_status_overrides_overall_completed_for_own_test(self):
        self.new_invitation.status = "completed"
        self.new_invitation.sova_activities = [
            {"activity": "Personality Questionnaire", "status": "completed"},
            {"activity": "Motivation Questionnaire", "status": "started"},
        ]
        self.new_invitation.save(update_fields=["status", "sova_activities"])
        response = self.client.get(self.url)
        new_status = self.statuses(self.entries(response)[self.new_project.pk])
        self.assertEqual(new_status["personality"], "completed")
        self.assertEqual(new_status["motivation"], "pending")

    def test_historical_results_are_visible_in_their_own_project_row(self):
        hist_project = self.make_project(
            "Historical Sova results", "HIST",
            ["personality"], is_historical=True,
        )
        history = HistoricalProcessCandidate.objects.create(
            process=hist_project, candidate=self.candidate,
        )
        HistoricalAssessmentResult.objects.create(
            process=hist_project, historical_candidate=history,
            candidate=self.candidate, assessment_type="personality",
        )
        response = self.client.get(self.url)
        rows = self.entries(response)
        self.assertEqual(len(rows), 3)
        self.assertEqual(self.statuses(rows[hist_project.pk])["personality"], "completed")
        self.assertEqual(self.statuses(rows[hist_project.pk])["motivation"], "not_sent")
        self.assertContains(
            response,
            reverse("processes:process_detail", args=[hist_project.pk])
            + f"?open_candidate={self.candidate.pk}",
        )

    def test_removed_membership_does_not_appear_or_leak_results(self):
        from django.utils import timezone
        self.old_invitation.removed_from_process_at = timezone.now()
        self.old_invitation.save(update_fields=["removed_from_process_at"])
        response = self.client.get(self.url)
        rows = self.entries(response)
        self.assertEqual(set(rows), {self.new_project.pk})
        self.assertNotContains(response, "Old demo with results")
        self.assertNotContains(response, reverse(
            "processes:process_detail", args=[self.old_project.pk],
        ))

    def test_inaccessible_other_company_process_does_not_appear(self):
        other_company = Company.objects.create(name="Company B")
        other_unit = OrgUnit.objects.create(
            company=other_company, name="Private", unit_code="PRIVATE",
        )
        other_user = User.objects.create_user(
            username="other-company-user", password="test-password",
        )
        foreign_project = self.make_project(
            "Secret project", "SECRET", ["personality"],
            company=other_company, unit=other_unit, created_by=other_user,
        )
        TestInvitation.objects.create(
            process=foreign_project, candidate=self.candidate,
            status="completed",
        )
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["candidates"]), 2)
        self.assertNotContains(response, "Secret project")
        self.assertEqual(
            self.statuses(self.entries(response)[self.new_project.pk])["personality"],
            "pending",
        )

    def test_own_only_user_sees_only_their_project_membership(self):
        UserOrgUnitAccess.objects.filter(user=self.user).update(permission="own")
        other_user = User.objects.create_user(
            username="different-creator", password="test-password",
        )
        self.new_project.created_by = other_user
        self.new_project.save(update_fields=["created_by"])
        response = self.client.get(self.url)
        rows = self.entries(response)
        self.assertEqual(set(rows), {self.old_project.pk})
        self.assertNotContains(response, "New demo without results")

    def test_team_filter_preserves_separate_project_rows(self):
        team = Team.objects.create(
            company=self.company, org_unit=self.unit,
            name="Demo team", created_by=self.user,
        )
        TeamMembership.objects.create(team=team, candidate=self.candidate)
        response = self.client.get(self.url + f"?team={team.pk}")
        self.assertEqual(len(response.context["candidates"]), 2)
        response = self.client.get(self.url + "?team=none")
        self.assertEqual(len(response.context["candidates"]), 0)

    def test_multiple_projects_do_not_change_database_results(self):
        self.client.get(self.url)
        self.assertTrue(TestInvitation.objects.filter(pk=self.old_invitation.pk).exists())
        self.assertTrue(TestInvitation.objects.filter(pk=self.new_invitation.pk).exists())
        self.assertEqual(Candidate.objects.filter(email="demo@test.se").count(), 1)
