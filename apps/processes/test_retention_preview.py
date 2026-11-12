"""Synthetic tests: proposed retention dates never authorize deletion."""
import json
from datetime import date, timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import Company, User
from apps.processes.models import AssessmentUsage, Candidate, TestInvitation, TestProcess
from apps.processes.management.commands.preview_candidate_retention import (
    preview_retention,
)


class RetentionPreviewTests(TestCase):
    def setUp(self):
        self.a = Company.objects.create(name="Private test company A")
        self.b = Company.objects.create(name="Private test company B")
        self.user = User.objects.create_user(
            username="retention-test", password="test-only"
        )
        self.candidate = Candidate.objects.create(
            first_name="Private", last_name="Synthetic",
            email="retention.synthetic@example.test",
        )
        self.process_a = self._new_process(self.a, "a")
        self.process_b = self._new_process(self.b, "b")
        self.invitation_a = TestInvitation.objects.create(
            candidate=self.candidate, process=self.process_a
        )
        TestInvitation.objects.create(
            candidate=self.candidate, process=self.process_b
        )
        AssessmentUsage.objects.create(
            company=self.a,
            process=self.process_a,
            candidate=self.candidate,
            invitation=self.invitation_a,
            assessment_type=AssessmentUsage.AssessmentType.PERSONALITY,
            candidate_name_snapshot="Sensitive Private Synthetic",
            candidate_email_snapshot="retention.synthetic@example.test",
        )

    def _new_process(self, company, suffix):
        return TestProcess.objects.create(
            name="Synthetic process " + suffix,
            company=company,
            account_code="synthetic_account",
            project_code="synthetic_project_" + suffix,
            created_by=self.user,
            purpose="hiring",
        )

    def _command(self, company, **extra):
        output = StringIO()
        kwargs = {
            "company_id": company.pk,
            "candidate_id": self.candidate.pk,
            "purpose": "hiring",
            "closed_on": "2026-01-01",
            "as_of": "2026-04-01",
        }
        kwargs.update(extra)
        with CaptureQueriesContext(connection) as queries:
            call_command("preview_candidate_retention", stdout=output, **kwargs)
        for item in queries:
            self.assertTrue(item["sql"].lstrip().upper().startswith("SELECT"))
        return json.loads(output.getvalue()), output.getvalue()

    def test_review_due_is_only_a_review_not_deletion_permission(self):
        result, raw = self._command(self.a)
        self.assertEqual(result["mode"], "READ_ONLY_RETENTION_SIMULATION")
        self.assertEqual(result["scenario"]["review_on"], "2026-04-01")
        self.assertTrue(result["scenario"]["review_due_by_date"])
        self.assertEqual(
            result["scenario"]["status"], "review_due_NOT_delete_authorized"
        )
        self.assertFalse(result["policy_approved"])
        self.assertFalse(result["automatic_deletion_enabled"])
        self.assertFalse(result["candidate_global_delete_permitted"])
        self.assertTrue(result["input_is_hypothetical"])
        self.assertEqual(
            result["scoped_data_inventory"]["counts"]["assessment_usages"], 1
        )
        self.assertTrue(
            result["scoped_data_inventory"]["candidate_record_shared_outside_scope"]
        )
        self.assertEqual(AssessmentUsage.objects.count(), 1)
        self.assertEqual(TestInvitation.objects.count(), 2)
        for secret in (
            "Private Synthetic", "retention.synthetic@example.test",
            "Sensitive Private Synthetic", "Private test company A",
            "Private test company B",
        ):
            self.assertNotIn(secret, raw)

    def test_previous_day_is_not_due(self):
        result, _ = self._command(self.a, as_of="2026-03-31")
        self.assertFalse(result["scenario"]["review_due_by_date"])
        self.assertEqual(result["scenario"]["status"], "before_review_date")

    def test_legal_hold_scenario_stays_non_destructive(self):
        result, _ = self._command(self.a, legal_hold_scenario=True)
        self.assertEqual(
            result["scenario"]["status"], "hold_requires_human_review"
        )
        self.assertTrue(result["scenario"]["legal_hold_assumed"])
        self.assertFalse(result["automatic_deletion_enabled"])

    def test_other_company_does_not_receive_first_company_counts(self):
        result, raw = self._command(self.b)
        self.assertEqual(
            result["scoped_data_inventory"]["counts"]["test_invitations"], 1
        )
        self.assertEqual(
            result["scoped_data_inventory"]["counts"]["assessment_usages"], 0
        )
        self.assertNotIn("Private test company A", raw)

    def test_custom_days_are_hypothetical_not_approved(self):
        result = preview_retention(
            company_id=self.a.pk, candidate_id=self.candidate.pk,
            hypothetical_closed_on=date(2026, 1, 1),
            as_of=date(2026, 1, 31),
            grace_days=30,
        )
        self.assertTrue(result["scenario"]["review_due_by_date"])
        self.assertEqual(result["scenario"]["review_on"], "2026-01-31")
        self.assertFalse(result["policy_approved"])

    def test_invalid_purpose_date_or_days_fail_closed(self):
        for options, fragment in (
            ({"purpose": "development"}, "Only --purpose hiring"),
            ({"closed_on": "not-a-date"}, "valid ISO date"),
            ({"as_of": "2026-02-31"}, "valid ISO date"),
            ({"grace_days": 0}, "between 1 and 365"),
            ({"grace_days": 366}, "between 1 and 365"),
        ):
            with self.subTest(options=options):
                with self.assertRaisesMessage(CommandError, fragment):
                    self._command(self.a, **options)
