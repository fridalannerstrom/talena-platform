"""Regression coverage for the Efter intervju evidence-changed warning."""
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Company, OrgUnit, User
from apps.core.ai.decision_support import save_post_interview_content_block
from apps.core.ai.manager_report_personality import save_manager_report_personality
from apps.processes.interview_question_models import InterviewQuestionNote, ManagerReportTextEdit
from apps.processes.models import Candidate, TestInvitation, TestProcess
from apps.processes.post_interview_evidence import (
    EVIDENCE_DIGESTS_KEY,
    post_interview_evidence_changed,
)


class PostInterviewEvidenceDigestTests(TestCase):
    def setUp(self):
        user = User.objects.create_superuser(
            username="report-evidence-test", email="report-evidence@example.org",
            password="test-password",
        )
        company = Company.objects.create(name="Report evidence test company")
        unit = OrgUnit.objects.create(
            company=company, name="Evidence test unit", unit_code="EVIDENCE",
        )
        self.process = TestProcess.objects.create(
            name="Report evidence process", provider="sova",
            company=company, org_unit=unit, created_by=user,
            project_code="EVIDENCE-PROJECT", account_code="EVIDENCE-ACCOUNT",
        )
        self.candidate = Candidate.objects.create(
            first_name="Test", last_name="Candidate",
            email="evidence-candidate@example.org",
        )
        self.owner = TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            status="completed",
            interview_notes="Original interview notes",
        )
        self.user = user

    def generate(self, *parts):
        for part in parts:
            if part == "manager_personality":
                save_manager_report_personality(
                    owner=self.owner,
                    result={
                        "leading_and_working_with_others": {
                            "testbild": "Manager AI report text",
                            "candidate_describes": "The candidate described a situation.",
                        },
                    },
                    language_code="sv",
                )
            else:
                save_post_interview_content_block(
                    owner=self.owner,
                    block_key=part,
                    text=f"Generated {part}",
                    language_code="sv",
                )
            self.owner.refresh_from_db()

    def changed(self):
        self.owner.refresh_from_db()
        return post_interview_evidence_changed(self.owner, self.process)

    def test_repeated_generation_without_input_changes_never_warns(self):
        self.generate("overall_picture", "wellbeing_tips", "manager_personality")
        self.assertFalse(self.changed())
        self.generate("overall_picture", "wellbeing_tips", "manager_personality")
        self.assertFalse(self.changed())
        result = self.owner.ai_post_interview_decision_support
        self.assertEqual(
            set(result[EVIDENCE_DIGESTS_KEY]),
            {"overall_picture", "wellbeing_tips", "manager_personality"},
        )

    def test_editing_then_restoring_interview_notes_clears_warning(self):
        self.generate("overall_picture", "wellbeing_tips")
        self.owner.interview_notes = "Changed interview notes"
        self.owner.interview_notes_updated_at = timezone.now()
        self.owner.save(update_fields=["interview_notes", "interview_notes_updated_at"])
        self.assertTrue(self.changed())
        self.owner.interview_notes = "Original interview notes"
        self.owner.interview_notes_updated_at = timezone.now()
        self.owner.save(update_fields=["interview_notes", "interview_notes_updated_at"])
        self.assertFalse(self.changed())

    def test_saved_question_answers_are_compared_by_content_including_deletion(self):
        self.generate("overall_picture")
        answer = InterviewQuestionNote.objects.create(
            process=self.process, candidate=self.candidate,
            source="personality", question_key="q1",
            question_text="How did you organise the task?",
            note="I created a shared plan.",
        )
        self.assertTrue(self.changed())
        self.generate("overall_picture")
        self.assertFalse(self.changed())
        answer.note = "I created a different plan."
        answer.save(update_fields=["note", "updated_at"])
        self.assertTrue(self.changed())
        answer.note = "I created a shared plan."
        answer.save(update_fields=["note", "updated_at"])
        self.assertFalse(self.changed())
        answer.delete()
        self.assertTrue(self.changed())

    def test_one_fresh_report_does_not_hide_warning_for_another_stale_report(self):
        self.generate("overall_picture", "wellbeing_tips", "manager_personality")
        self.owner.interview_notes = "An additional concrete example"
        self.owner.save(update_fields=["interview_notes"])
        self.assertTrue(self.changed())
        self.generate("overall_picture")
        self.assertTrue(self.changed())
        self.generate("manager_personality")
        self.assertTrue(self.changed())
        self.generate("wellbeing_tips")
        self.assertFalse(self.changed())

    def test_manual_report_edits_and_timestamps_do_not_trigger_warning(self):
        self.generate("overall_picture", "wellbeing_tips")
        ManagerReportTextEdit.objects.create(
            process=self.process, candidate=self.candidate, block_key="wellbeing_tips",
            language_code="sv", text="Human-edited advice", updated_by=self.user,
        )
        self.owner.interview_notes_updated_at = timezone.now()
        self.owner.save(update_fields=["interview_notes_updated_at"])
        self.assertFalse(self.changed())

    def test_legacy_reports_use_fallback_until_every_part_has_a_digest(self):
        self.owner.ai_post_interview_decision_support = {
            "overall_synthesis": "Legacy synthesis",
            "content_blocks": {
                "overall_picture": "Legacy overall picture",
                "wellbeing_tips": "Legacy advice",
            },
            "interview_evidence_changed_since_compilation": True,
        }
        self.owner.save(update_fields=["ai_post_interview_decision_support"])
        self.assertTrue(self.changed())
        self.generate("overall_picture")
        self.assertTrue(self.changed())
        self.generate("wellbeing_tips")
        self.assertFalse(self.changed())
