from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.accounts.models import Company, OrgUnit, User
from apps.processes.models import (
    Candidate,
    HistoricalAssessmentResult,
    HistoricalAssessmentScore,
    HistoricalProcessCandidate,
    TestProcess,
)
from apps.teams.models import Team, TeamMembership
from apps.teams.views import build_team_style_statistics


class SeedTeamReportDemoTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Demo company")
        self.unit = OrgUnit.objects.create(
            company=self.company,
            name="Demo unit",
            unit_code="DEMO",
        )
        self.user = User.objects.create_user(
            username="demo-owner",
            email="demo-owner@example.com",
            password="test-password",
        )
        self.process = TestProcess.objects.create(
            name="Team report sandbox",
            provider="sova",
            company=self.company,
            project_code="DEMO-PROJECT",
            account_code="DEMO-ACCOUNT",
            org_unit=self.unit,
            created_by=self.user,
            sova_sync_enabled=False,
        )
        self.team = Team.objects.create(
            company=self.company,
            org_unit=self.unit,
            created_by=self.user,
            name="Demo team",
        )

    @override_settings(ENVIRONMENT="local", DEBUG=True)
    def test_command_creates_three_complete_demo_profiles_and_team_memberships(self):
        stdout = StringIO()
        call_command(
            "seed_team_report_demo",
            process_id=self.process.id,
            team_id=self.team.id,
            stdout=stdout,
        )

        demo_candidates = Candidate.objects.filter(
            email__startswith=f"talena.demo.team.{self.process.id}."
        )
        self.assertEqual(demo_candidates.count(), 3)
        self.assertEqual(
            HistoricalProcessCandidate.objects.filter(
                process=self.process,
                candidate__in=demo_candidates,
            ).count(),
            3,
        )
        self.assertEqual(
            HistoricalAssessmentResult.objects.filter(
                process=self.process,
                candidate__in=demo_candidates,
            ).count(),
            15,
        )
        self.assertEqual(
            HistoricalAssessmentScore.objects.filter(
                result__process=self.process,
                result__candidate__in=demo_candidates,
                category="team_style",
            ).count(),
            24,
        )
        self.assertEqual(
            TeamMembership.objects.filter(
                team=self.team,
                candidate__in=demo_candidates,
            ).count(),
            3,
        )

        stats = build_team_style_statistics(self.team)
        self.assertEqual(stats["members_total"], 3)
        self.assertEqual(stats["members_with_scores"], 3)
        self.assertTrue(all(row["count"] == 3 for row in stats["average_rows"]))

    @override_settings(ENVIRONMENT="local", DEBUG=True)
    def test_rerun_refreshes_seed_instead_of_creating_duplicates(self):
        call_command(
            "seed_team_report_demo",
            process_id=self.process.id,
            team_id=self.team.id,
            stdout=StringIO(),
        )
        call_command(
            "seed_team_report_demo",
            process_id=self.process.id,
            team_id=self.team.id,
            stdout=StringIO(),
        )

        demo_candidates = Candidate.objects.filter(
            email__startswith=f"talena.demo.team.{self.process.id}."
        )
        self.assertEqual(demo_candidates.count(), 3)
        self.assertEqual(
            HistoricalAssessmentResult.objects.filter(
                process=self.process,
                candidate__in=demo_candidates,
            ).count(),
            15,
        )
        self.assertEqual(
            TeamMembership.objects.filter(
                team=self.team,
                candidate__in=demo_candidates,
            ).count(),
            3,
        )

    @override_settings(ENVIRONMENT="production", DEBUG=True)
    def test_command_is_blocked_in_production(self):
        with self.assertRaises(CommandError):
            call_command(
                "seed_team_report_demo",
                process_id=self.process.id,
                stdout=StringIO(),
            )
