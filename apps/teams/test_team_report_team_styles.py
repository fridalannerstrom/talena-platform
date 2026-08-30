from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Company, OrgUnit, User
from apps.processes.models import (
    Candidate,
    HistoricalAssessmentResult,
    HistoricalAssessmentScore,
    HistoricalProcessCandidate,
    TestInvitation,
    TestProcess,
)
from apps.teams.models import Team, TeamMembership
from apps.teams.team_report_views import build_team_style_statistics


class TeamReportTeamStyleDataTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Team style company")
        self.unit = OrgUnit.objects.create(
            company=self.company,
            name="Sweden",
            unit_code="SE-TEAM",
        )
        self.user = User.objects.create_user(
            username="team-style-owner",
            email="team-style-owner@example.com",
            password="test-password",
        )
        self.process = TestProcess.objects.create(
            name="Team style process",
            provider="sova",
            company=self.company,
            project_code="TEAM-STYLES",
            account_code="TEAM-ACCOUNT",
            org_unit=self.unit,
            created_by=self.user,
        )
        self.candidate = Candidate.objects.create(
            first_name="Live",
            last_name="Candidate",
            email="team-style-candidate@example.com",
        )
        self.team = Team.objects.create(
            company=self.company,
            org_unit=self.unit,
            created_by=self.user,
            name="Team style team",
        )
        TeamMembership.objects.create(
            team=self.team,
            candidate=self.candidate,
            source="manual",
        )

    def test_live_sova_team_styles_are_included_on_five_point_scale(self):
        TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            status="completed",
            sova_activities=[
                {
                    "activity": "Personality Assessment",
                    "competencies": [
                        {"competency": "Connector", "stive": 4.4, "stive_rounded": 4},
                        {"competency": "Catalyst", "stive": 3.2, "stive_rounded": 3},
                        {"competency": "Director", "stive": 2.4, "stive_rounded": 2},
                        {"competency": "Energiser", "stive": 4.8, "stive_rounded": 5},
                        {"competency": "Architect", "stive": 2.8, "stive_rounded": 3},
                        {"competency": "Harmoniser", "stive": 3.7, "stive_rounded": 4},
                        {"competency": "Analyst", "stive": 1.9, "stive_rounded": 2},
                        {"competency": "Auditor", "stive": 2.2, "stive_rounded": 2},
                    ],
                }
            ],
        )

        stats = build_team_style_statistics(
            self.team,
            candidate_ids={self.candidate.id},
            process_ids=[self.process.id],
        )

        self.assertEqual(stats["members_with_scores"], 1)

        member_scores = {
            row["style"]: row
            for row in stats["member_profiles"][0]["scores"]
        }
        self.assertEqual(member_scores["Connector"]["score"], 4.4)
        self.assertEqual(member_scores["Connector"]["score_rounded"], 4)
        self.assertEqual(member_scores["Energiser"]["score_rounded"], 5)

        connector_average = next(
            row
            for row in stats["average_rows"]
            if row["style"] == "Connector"
        )
        self.assertEqual(connector_average["average"], 4.4)
        self.assertEqual(connector_average["average_percent"], 88.0)

    def test_historical_sten_team_style_is_normalised_to_five_point_scale(self):
        now = timezone.now()
        historical_candidate = HistoricalProcessCandidate.objects.create(
            process=self.process,
            candidate=self.candidate,
            status="completed",
            completed_at=now,
            sova_candidate_id="historical-team-style-candidate",
        )
        result = HistoricalAssessmentResult.objects.create(
            process=self.process,
            candidate=self.candidate,
            historical_candidate=historical_candidate,
            assessment_type="personality",
            scale="sten",
            sova_result_id="historical-team-style-result",
            status="completed",
            time_completed=now,
        )
        HistoricalAssessmentScore.objects.create(
            result=result,
            name="Connector",
            category="team_style",
            scale="sten",
            score=10,
        )

        stats = build_team_style_statistics(
            self.team,
            candidate_ids={self.candidate.id},
            process_ids=[self.process.id],
        )

        connector_score = next(
            row
            for row in stats["member_profiles"][0]["scores"]
            if row["style"] == "Connector"
        )
        self.assertEqual(connector_score["score"], 5.0)
        self.assertEqual(connector_score["percent"], 100.0)

    def test_results_outside_process_scope_are_not_used(self):
        TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            status="completed",
            sova_activities=[
                {
                    "competencies": [
                        {"competency": "Connector", "stive": 5, "stive_rounded": 5}
                    ]
                }
            ],
        )

        stats = build_team_style_statistics(
            self.team,
            candidate_ids={self.candidate.id},
            process_ids=[],
        )

        self.assertEqual(stats["members_with_scores"], 0)
