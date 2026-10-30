"""Issue #309: direct-URL authorization tests for candidate results and teams.

Synthetic data only. Verify tenant, org-unit and own-only scopes on the HTTP
endpoints, not just UI visibility or direct calls to helper functions.
"""

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    Company, CompanyBranding, CompanyMember, OrgUnit, User, UserOrgUnitAccess,
)
from apps.candidate_results.models import CandidateResultSnapshot
from apps.processes.models import Candidate, TestInvitation, TestProcess
from apps.teams.models import Team, TeamMembership


class ReportAndTeamTenantAccessTests(TestCase):
    def setUp(self):
        self.company_a = Company.objects.create(name="Report test company A")
        self.company_b = Company.objects.create(name="Report test company B")
        self.unit_a = OrgUnit.objects.create(
            company=self.company_a, name="Unit A", unit_code="SEC-309-A",
        )
        self.unit_hidden = OrgUnit.objects.create(
            company=self.company_a, name="Restricted unit A", unit_code="SEC-309-X",
        )
        self.unit_b = OrgUnit.objects.create(
            company=self.company_b, name="Unit B", unit_code="SEC-309-B",
        )

        def new_member(username, company, unit, permission):
            user = User.objects.create_user(
                username=username, password="synthetic-only",
            )
            CompanyMember.objects.create(
                user=user, company=company, primary_org_unit=unit,
            )
            UserOrgUnitAccess.objects.create(
                user=user, org_unit=unit, permission=permission,
            )
            return user

        self.owner = new_member("r309-owner", self.company_a, self.unit_a, "editor")
        self.editor = new_member("r309-editor", self.company_a, self.unit_a, "editor")
        self.viewer = new_member("r309-viewer", self.company_a, self.unit_a, "viewer")
        self.own_only = new_member("r309-own-only", self.company_a, self.unit_a, "own")
        self.hidden_unit = new_member("r309-hidden-unit", self.company_a, self.unit_hidden, "viewer")
        self.foreign = new_member("r309-foreign", self.company_b, self.unit_b, "editor")

        def create_process(company, unit, creator, name):
            return TestProcess.objects.create(
                name=name, company=company, org_unit=unit, created_by=creator,
                provider="sova", account_code=name, project_code=name,
            )

        self.process = create_process(self.company_a, self.unit_a, self.owner, "scope-a")
        self.owned_process = create_process(
            self.company_a, self.unit_a, self.own_only, "scope-own",
        )
        self.foreign_process = create_process(
            self.company_b, self.unit_b, self.foreign, "scope-b",
        )

        self.candidate_a = Candidate.objects.create(
            first_name="Shared", last_name="Candidate",
            email="shared-recruitment@example.org",
        )
        self.candidate_foreign = Candidate.objects.create(
            first_name="Private", last_name="Elsewhere",
            email="private-recruitment@example.org",
        )
        self.invitation_a = TestInvitation.objects.create(
            process=self.process, candidate=self.candidate_a, status="completed",
        )
        self.invitation_owned = TestInvitation.objects.create(
            process=self.owned_process, candidate=self.candidate_a, status="completed",
        )
        TestInvitation.objects.create(
            process=self.foreign_process, candidate=self.candidate_foreign, status="completed",
        )

        self.snapshot_a = CandidateResultSnapshot.objects.create(
            invitation=self.invitation_a, candidate=self.candidate_a,
            process=self.process, locale="sv",
            content={"introduction": "Synthetic candidate summary A"},
            prompt_versions={"candidate_summary": {"version": "test"}},
        )
        self.snapshot_owned = CandidateResultSnapshot.objects.create(
            invitation=self.invitation_owned, candidate=self.candidate_a,
            process=self.owned_process, locale="sv",
            content={"introduction": "Synthetic candidate summary owned"},
            prompt_versions={"candidate_summary": {"version": "test"}},
        )

        self.shared_team = Team.objects.create(
            company=self.company_a, org_unit=self.unit_a, created_by=self.owner,
            name="Scope Team A",
        )
        self.own_team = Team.objects.create(
            company=self.company_a, org_unit=self.unit_a, created_by=self.own_only,
            name="Scope Team Owned",
        )
        self.foreign_team = Team.objects.create(
            company=self.company_b, org_unit=self.unit_b, created_by=self.foreign,
            name="Scope Team B",
        )
        TeamMembership.objects.create(team=self.shared_team, candidate=self.candidate_a)
        # Even if a bad import links an out-of-scope candidate to an otherwise
        # visible team, the team view must not expose that profile.
        TeamMembership.objects.create(
            team=self.shared_team, candidate=self.candidate_foreign,
        )

    def preview_url(self, snapshot):
        return reverse("candidate_results:preview", kwargs={"snapshot_id": snapshot.pk})

    def team_url(self, team):
        return reverse("teams:team_detail", kwargs={"pk": team.pk})

    def generate_url(self, team):
        return reverse(
            "teams:team_insight_generate",
            kwargs={"pk": team.pk, "insight_type": "collaboration"},
        )

    def test_candidate_preview_denies_other_company_and_unassigned_units(self):
        url = self.preview_url(self.snapshot_a)
        for user in (self.foreign, self.hidden_unit, self.own_only):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(b"Synthetic candidate summary A", response.content)

    def test_authorized_users_can_preview_only_permitted_processes(self):
        for user in (self.viewer, self.editor, self.owner):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(
                    self.client.get(self.preview_url(self.snapshot_a)).status_code,
                    200,
                )

        self.client.force_login(self.own_only)
        self.assertEqual(
            self.client.get(self.preview_url(self.snapshot_owned)).status_code,
            200,
        )

    def test_manager_report_pdf_branding_is_scoped_to_candidate_company(self):
        """The refreshed manager report uses only its authorized tenant assets."""
        CompanyBranding.objects.create(
            company=self.company_a, primary_color="#285A78",
        )
        CompanyBranding.objects.create(
            company=self.company_b, primary_color="#B24466",
        )
        url = reverse(
            "processes:process_candidate_final_output",
            kwargs={
                "process_id": self.process.pk,
                "candidate_id": self.candidate_a.pk,
            },
        )
        self.client.force_login(self.viewer)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-manager-report-brand-primary="#285A78"')
        self.assertNotContains(response, 'data-manager-report-brand-primary="#B24466"')
        self.assertEqual(response.context["report_branding"]["company_name"], self.company_a.name)

        self.client.force_login(self.foreign)
        denied = self.client.get(url)
        self.assertNotEqual(denied.status_code, 200)
        self.assertNotIn(b'data-manager-report-brand-primary="#285A78"', denied.content)

    def test_team_detail_scopes_report_branding_to_authorized_company(self):
        CompanyBranding.objects.create(
            company=self.company_a, primary_color="#285A78",
        )
        CompanyBranding.objects.create(
            company=self.company_b, primary_color="#B24466",
        )
        self.client.force_login(self.viewer)
        response = self.client.get(self.team_url(self.shared_team))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["report_branding"]["palette"]["primary"], "#285A78")
        self.assertContains(response, 'data-team-report-brand-primary="#285A78"')
        self.assertNotContains(response, 'data-team-report-brand-primary="#B24466"')

        self.client.force_login(self.foreign)
        self.assertEqual(self.client.get(self.team_url(self.shared_team)).status_code, 404)

    def test_team_detail_denies_cross_company_and_wrong_org_or_own(self):
        for user in (self.foreign, self.hidden_unit, self.own_only):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(self.team_url(self.shared_team))
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(b"Scope Team A", response.content)

        self.client.force_login(self.own_only)
        self.assertEqual(self.client.get(self.team_url(self.own_team)).status_code, 200)

    def test_team_detail_filters_candidates_not_accessible_via_any_process(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.team_url(self.shared_team))
        self.assertEqual(response.status_code, 200)
        members = list(response.context["memberships"])
        self.assertEqual([m.candidate_id for m in members], [self.candidate_a.pk])
        self.assertNotContains(response, "private-recruitment@example.org")

    def test_unauthorized_team_generation_never_calls_ai(self):
        with patch("apps.teams.ai_insights.generate_team_insight") as generate:
            for user, team, expected in (
                (self.foreign, self.shared_team, 404),
                (self.hidden_unit, self.shared_team, 404),
                (self.own_only, self.shared_team, 404),
                (self.viewer, self.shared_team, 403),
            ):
                with self.subTest(user=user.username):
                    self.client.force_login(user)
                    response = self.client.post(
                        self.generate_url(team),
                        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
                    )
                    self.assertEqual(response.status_code, expected)
            generate.assert_not_called()

    def test_billing_csv_export_is_admin_only(self):
        self.client.force_login(self.editor)
        response = self.client.get(
            reverse("accounts:admin_usage_billing"), {"export": "csv"},
        )
        self.assertNotEqual(response.status_code, 200)
        self.assertNotIn("text/csv", response.get("Content-Type", ""))
