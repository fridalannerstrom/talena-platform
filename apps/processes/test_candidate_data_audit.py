"""Regression tests for the GDPR candidate inventory. Synthetic records only."""
import json
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import Company, User
from apps.activity.models import ActivityEvent
from apps.candidate_results.models import (
    CandidateResultAccess,
    CandidateResultFeedback,
    CandidateResultSnapshot,
)
from apps.emails.models import EmailLog
from apps.processes.models import (
    AssessmentUsage,
    Candidate,
    HistoricalAssessmentImport,
    HistoricalAssessmentResult,
    HistoricalAssessmentScore,
    HistoricalCandidateReport,
    HistoricalProcessCandidate,
    SelfRegistration,
    TestInvitation,
    TestProcess,
)
from apps.teams.models import Team, TeamAIInsight, TeamMembership


class CandidateDataAuditTests(TestCase):
    def setUp(self):
        self.a = Company.objects.create(name="Synthetic organisation A")
        self.b = Company.objects.create(name="Synthetic organisation B")
        self.user = User.objects.create_user(
            username="audit-test", password="synthetic-only"
        )
        self.candidate = Candidate.objects.create(
            first_name="Synthetic", last_name="Private",
            email="synthetic.private@example.test",
        )
        self.unrelated = Candidate.objects.create(
            first_name="Unrelated", last_name="Person",
            email="unrelated@example.test",
        )
        self.process_a = self._process(self.a, "A")
        self.process_b = self._process(self.b, "B")
        self.invitation_a = TestInvitation.objects.create(
            candidate=self.candidate, process=self.process_a,
        )
        self.invitation_b = TestInvitation.objects.create(
            candidate=self.candidate, process=self.process_b,
        )
        self.usage_a = AssessmentUsage.objects.create(
            company=self.a, process=self.process_a,
            candidate=self.candidate, invitation=self.invitation_a,
            assessment_type=AssessmentUsage.AssessmentType.PERSONALITY,
            candidate_name_snapshot="Synthetic Private",
            candidate_email_snapshot="synthetic.private@example.test",
        )
        self.snapshot_a = CandidateResultSnapshot.objects.create(
            invitation=self.invitation_a,
            process=self.process_a, candidate=self.candidate,
            content={"private_sample": "synthetic secret"},
            prompt_versions={"synthetic_prompt": "v1"},
        )
        CandidateResultAccess.objects.create(
            snapshot=self.snapshot_a,
            token_digest="0" * 64,
            verification_code_hash="1" * 64,
        )
        CandidateResultFeedback.objects.create(
            snapshot=self.snapshot_a, result_area="personality",
            response="recognises", comment="confidential synthetic answer",
        )
        EmailLog.objects.create(
            invitation=self.invitation_a, template_type="invitation",
            to_email=self.candidate.email, subject="Synthetic confidential",
            body_snapshot="Email body with private details",
        )
        ActivityEvent.objects.create(
            company=self.a, process=self.process_a, candidate=self.candidate,
            invitation=self.invitation_a,
            verb=ActivityEvent.Verb.CANDIDATE_ADDED,
            actor_name="synthetic person",
            meta={"private": "confidential"},
        )
        SelfRegistration.objects.create(
            process=self.process_a, name="Synthetic Private",
            email=self.candidate.email,
        )
        self.team = Team.objects.create(
            company=self.a, name="Team A", created_by=self.user,
        )
        TeamMembership.objects.create(
            team=self.team, candidate=self.candidate,
        )
        TeamAIInsight.objects.create(
            team=self.team, insight_type="collaboration", language="sv",
            content="Aggregate synthetic insight",
            source_signature="a" * 64, prompt_key="test",
            prompt_digest="b" * 64,
        )
        self.historical_process = self._process(self.a, "HIST", is_historical=True)
        hist = HistoricalProcessCandidate.objects.create(
            process=self.historical_process, candidate=self.candidate,
            notes="Synthetic interview notes",
        )
        imported = HistoricalAssessmentImport.objects.create(
            process=self.historical_process,
            file="historical_assessment_imports/synthetic.xlsx",
            original_filename="synthetic.xlsx",
        )
        historical_result = HistoricalAssessmentResult.objects.create(
            process=self.historical_process, candidate=self.candidate,
            historical_candidate=hist, import_file=imported,
            assessment_type="personality", raw_data={"synthetic": 123},
        )
        HistoricalAssessmentScore.objects.create(
            result=historical_result, name="Test scale", score=7,
        )
        HistoricalCandidateReport.objects.create(
            historical_candidate=hist,
            title="Retired legacy document",
            file="historical_sova_reports/synthetic.pdf",
        )

    def _process(self, company, label, is_historical=False):
        return TestProcess.objects.create(
            name="Synthetic " + label,
            company=company,
            account_code="synthetic-account",
            project_code="synthetic-" + label,
            created_by=self.user,
            is_historical=is_historical,
        )

    def _run(self, company, candidate=None):
        output = StringIO()
        with CaptureQueriesContext(connection) as queries:
            call_command(
                "audit_candidate_data",
                company_id=company.pk,
                candidate_id=(candidate or self.candidate).pk,
                stdout=output,
            )
        # No write SQL (including hidden writes) may occur in the command.
        for query in queries:
            statement = query["sql"].lstrip().upper()
            self.assertTrue(statement.startswith("SELECT"), statement)
        return json.loads(output.getvalue()), output.getvalue()

    def test_company_a_is_scoped_and_never_prints_private_values(self):
        result, raw = self._run(self.a)
        counts = result["counts"]
        self.assertEqual(result["mode"], "read_only_dry_run")
        self.assertTrue(result["candidate_record_shared_outside_scope"])
        self.assertEqual(counts["test_invitations"], 1)
        self.assertEqual(counts["assessment_usages"], 1)
        self.assertEqual(counts["candidate_result_snapshots"], 1)
        self.assertEqual(counts["candidate_result_access_credentials"], 1)
        self.assertEqual(counts["candidate_result_feedback"], 1)
        self.assertEqual(counts["email_logs"], 1)
        self.assertEqual(counts["activity_events"], 1)
        self.assertEqual(counts["self_registrations_email_match_unverified"], 1)
        self.assertEqual(counts["historical_process_candidates"], 1)
        self.assertEqual(counts["historical_assessment_results"], 1)
        self.assertEqual(counts["historical_assessment_scores"], 1)
        self.assertEqual(counts["shared_historical_import_files_referenced"], 1)
        self.assertEqual(counts["legacy_historical_pdf_records"], 1)
        self.assertEqual(counts["team_memberships"], 1)
        self.assertEqual(counts["shared_team_ai_insights_to_review"], 1)
        self.assertTrue(result["blockers"]["invitation_deletion_may_be_blocked"])
        self.assertTrue(result["blockers"]["candidate_global_delete_not_authorized"])
        for private in (
            "Synthetic", "Private", "synthetic.private@example.test",
            "confidential", "synthetic.xlsx", "synthetic.pdf",
            "synthetic secret",
        ):
            self.assertNotIn(private, raw)
        self.assertEqual(TestInvitation.objects.count(), 2)
        self.assertEqual(AssessmentUsage.objects.count(), 1)

    def test_company_b_cannot_see_company_a_counts(self):
        result, raw = self._run(self.b)
        counts = result["counts"]
        self.assertEqual(counts["test_invitations"], 1)
        self.assertEqual(counts["assessment_usages"], 0)
        self.assertEqual(counts["candidate_result_snapshots"], 0)
        self.assertEqual(counts["historical_assessment_results"], 0)
        self.assertEqual(counts["team_memberships"], 0)
        self.assertTrue(result["candidate_record_shared_outside_scope"])
        self.assertFalse(result["blockers"]["invitation_deletion_may_be_blocked"])
        self.assertNotIn("Synthetic organisation A", raw)

    def test_unrelated_candidate_fails_closed(self):
        with self.assertRaisesMessage(
            CommandError, "No candidate-related records in this company."
        ):
            call_command(
                "audit_candidate_data",
                company_id=self.b.pk,
                candidate_id=self.unrelated.pk,
                stdout=StringIO(),
            )

    def test_missing_and_invalid_scope_rejected(self):
        with self.assertRaisesMessage(CommandError, "Company does not exist."):
            call_command(
                "audit_candidate_data", company_id=9999999,
                candidate_id=self.candidate.pk, stdout=StringIO(),
            )
        with self.assertRaisesMessage(CommandError, "Candidate does not exist."):
            call_command(
                "audit_candidate_data", company_id=self.a.pk,
                candidate_id=9999999, stdout=StringIO(),
            )
        with self.assertRaisesMessage(CommandError, "IDs must be positive"):
            call_command(
                "audit_candidate_data", company_id=self.a.pk,
                candidate_id=0, stdout=StringIO(),
            )
