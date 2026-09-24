from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Company, OrgUnit, User
from apps.core.ai import decision_support
from apps.core.ai.post_interview_question_evidence_policy import (
    get_post_interview_note_evidence,
)
from apps.core.ai.prompt_templates import AI_PROMPT_REGISTRY
from apps.processes.interview_question_models import InterviewQuestionNote
from apps.processes.interview_question_evidence import (
    build_interview_question_evidence,
)
from apps.processes.models import Candidate, TestInvitation, TestProcess


class PostInterviewQuestionEvidenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="post-question-evidence-admin",
            email="post-question-evidence@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)

        self.company = Company.objects.create(
            name="Post interview question evidence company",
        )
        self.unit = OrgUnit.objects.create(
            company=self.company,
            name="Post interview question evidence unit",
            unit_code="POST-QUESTION-EVIDENCE",
        )
        self.process = TestProcess.objects.create(
            name="Post interview question evidence process",
            provider="sova",
            company=self.company,
            project_code="POST-QUESTION-EVIDENCE-PROJECT",
            account_code="POST-QUESTION-EVIDENCE-ACCOUNT",
            org_unit=self.unit,
            created_by=self.user,
            purpose="hiring",
        )
        self.candidate = Candidate.objects.create(
            first_name="Taylor",
            last_name="Candidate",
            email="taylor-post-question-evidence@example.com",
        )
        self.owner = TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            status="completed",
            interview_notes="",
            ai_purpose_fit={
                "summary": "Assessment evidence is available.",
            },
            ai_purpose_fit_status="completed",
            ai_pre_interview_decision_support={
                "overall_synthesis": "Pre-interview synthesis.",
            },
            sova_activities=[
                {
                    "activity": "Personality Questionnaire",
                    "competencies": [
                        {
                            "competency": "Adaptability",
                            "sten_rounded": 3,
                        }
                    ],
                }
            ],
        )

        self.question = (
            "Tell me about a time when you had to adapt your usual "
            "working style."
        )
        self.answer = (
            "Taylor described changing the customer meeting structure after "
            "receiving new stakeholder feedback."
        )

        InterviewQuestionNote.objects.create(
            process=self.process,
            candidate=self.candidate,
            source="personality",
            question_key="stable-question-key",
            question_text=self.question,
            note=self.answer,
            updated_by=self.user,
        )

    def _post_stream_url(self):
        return reverse(
            "processes:process_candidate_post_interview_decision_support_stream",
            kwargs={
                "process_id": self.process.id,
                "candidate_id": self.candidate.id,
            },
        )

    def _post_regenerate_url(self):
        return reverse(
            "processes:process_candidate_post_interview_decision_support_regenerate",
            kwargs={
                "process_id": self.process.id,
                "candidate_id": self.candidate.id,
            },
        )

    def test_structured_evidence_keeps_exact_question_with_saved_answer(self):
        evidence = build_interview_question_evidence(self.owner)

        self.assertTrue(evidence["has_evidence"])
        self.assertEqual(evidence["count"], 1)
        self.assertEqual(evidence["items"][0]["question"], self.question)
        self.assertEqual(
            evidence["items"][0]["saved_answer_or_note"],
            self.answer,
        )
        self.assertIn(self.question, evidence["text"])
        self.assertIn(self.answer, evidence["text"])

    def test_question_note_counts_as_interview_evidence_without_general_notes(self):
        evidence = get_post_interview_note_evidence(self.owner)

        self.assertEqual(evidence["general_notes"], "")
        self.assertFalse(evidence["has_general_notes"])
        self.assertTrue(evidence["question_evidence"]["has_evidence"])
        self.assertTrue(evidence["has_question_evidence"])
        self.assertTrue(evidence["has_evidence"])

    def test_post_interview_prompt_contains_exact_question_and_answer(self):
        prompt = decision_support.build_post_interview_decision_support_prompt(
            self.owner,
            language_code="en",
        )

        self.assertIn("QUESTION-SPECIFIC INTERVIEW EVIDENCE", prompt)
        self.assertIn(self.question, prompt)
        self.assertIn(self.answer, prompt)
        self.assertIn(
            "Always interpret a saved answer/note in the context of its exact question",
            prompt,
        )
        self.assertIn(
            "No additional general interview notes were added.",
            prompt,
        )

    def test_prompt_marks_question_notes_as_available_interview_evidence(self):
        prompt = decision_support.build_post_interview_decision_support_prompt(
            self.owner,
            language_code="en",
        )

        normalised = " ".join(prompt.split())

        self.assertIn(
            "General interview notes: NOT PROVIDED",
            normalised,
        )
        self.assertIn(
            "Question-specific interview evidence: AVAILABLE (1 saved answer/note record(s))",
            normalised,
        )
        self.assertIn(
            "Overall interview evidence: AVAILABLE",
            normalised,
        )
        self.assertIn(
            "never say that interview evidence, interview material, candidate examples or interview input is entirely missing",
            normalised,
        )
        self.assertIn(
            "context_note must accurately name question-specific interview evidence as a source",
            normalised,
        )

    def test_prompt_prioritises_relevant_concrete_question_evidence(self):
        prompt = decision_support.build_post_interview_decision_support_prompt(
            self.owner,
            language_code="en",
        )

        normalised = " ".join(prompt.split())

        self.assertIn(
            "Question-specific evidence must not become background noise",
            normalised,
        )
        self.assertIn(
            "prefer the concrete behavioural detail over a vague or generic statement",
            normalised,
        )
        self.assertIn(
            "MUST surface at least one distinguishing concrete detail",
            normalised,
        )
        self.assertIn(
            "A generic restatement of the assessment profile is not sufficient",
            normalised,
        )

    def test_default_admin_prompt_mentions_question_specific_evidence(self):
        defaults = AI_PROMPT_REGISTRY[
            "post_interview_decision_support"
        ]["defaults"]

        self.assertIn(
            "FRÅGESPECIFIKT INTERVJUUNDERLAG I EFTER INTERVJU",
            defaults["sv"],
        )
        self.assertIn(
            "QUESTION-SPECIFIC INTERVIEW EVIDENCE IN AFTER INTERVIEW",
            defaults["en"],
        )
        self.assertIn(
            "skriv inte att intervjuunderlag saknas",
            defaults["sv"],
        )

    def test_stream_accepts_question_notes_without_general_interview_notes(self):
        with patch(
            "apps.core.ai.decision_support.get_openai_client"
        ) as get_client:
            get_client.return_value.chat.completions.create.return_value = []

            events = list(
                decision_support.stream_post_interview_decision_support(
                    owner=self.owner,
                    language_code="en",
                )
            )

        self.assertEqual(events, [])
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.interview_notes, "")

    def test_general_and_question_specific_notes_are_kept_separate(self):
        self.owner.interview_notes = (
            "General interviewer note about the overall conversation."
        )
        self.owner.save(update_fields=["interview_notes"])

        prompt = decision_support.build_post_interview_decision_support_prompt(
            self.owner,
            language_code="en",
        )

        self.assertIn(
            "GENERAL INTERVIEW NOTES AND CANDIDATE EXAMPLES",
            prompt,
        )
        self.assertIn(
            "General interviewer note about the overall conversation.",
            prompt,
        )
        self.assertIn("QUESTION-SPECIFIC INTERVIEW EVIDENCE", prompt)
        self.assertIn(self.question, prompt)
        self.assertIn(self.answer, prompt)
        self.assertIn(
            "General interview notes: AVAILABLE",
            prompt,
        )
        self.assertIn(
            "Question-specific interview evidence: AVAILABLE",
            prompt,
        )
        self.assertIn(
            "must be actively considered before describing",
            prompt,
        )
        self.assertIn(
            "Remaining uncertainties may only describe what is still unanswered",
            prompt,
        )

    def test_regenerate_endpoint_accepts_question_notes_without_general_notes(self):
        response = self.client.post(
            self._post_regenerate_url(),
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("stream_url"))

    def test_stream_endpoint_accepts_question_notes_without_general_notes(self):
        response = self.client.get(
            self._post_stream_url(),
            HTTP_ACCEPT="application/x-ndjson",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)

    def test_stream_saves_complete_content_blocks_without_legacy_fields(self):
        content_blocks = {
            key: f"Generated {key} content."
            for key in (
                "overall_picture",
                "interview_summary",
                "explore_further",
                "wellbeing_tips",
            )
        }
        events = [
            {
                "type": "content_blocks",
                "blocks": {
                    **content_blocks,
                    "test_results_candidate": "Legacy block should be ignored.",
                },
            },
            {
                "type": "done",
            },
        ]

        with patch(
            "apps.core.ai.decision_support.stream_post_interview_decision_support",
            return_value=events,
        ):
            response = self.client.get(
                self._post_stream_url() + "?force=1",
                HTTP_ACCEPT="application/x-ndjson",
            )
            body = b"".join(response.streaming_content).decode("utf-8")

        self.assertNotIn('"type": "error"', body)
        self.owner.refresh_from_db()
        self.assertEqual(
            self.owner.ai_post_interview_decision_support_status,
            "completed",
        )
        self.assertEqual(
            self.owner.ai_post_interview_decision_support[
                "overall_synthesis"
            ],
            content_blocks["overall_picture"],
        )
        self.assertEqual(
            self.owner.ai_post_interview_decision_support[
                "content_blocks"
            ],
            content_blocks,
        )

    def test_regenerate_endpoint_rejects_when_all_interview_evidence_is_empty(self):
        InterviewQuestionNote.objects.filter(
            process=self.process,
            candidate=self.candidate,
        ).delete()

        self.owner.interview_notes = ""
        self.owner.save(update_fields=["interview_notes"])

        response = self.client.post(
            self._post_regenerate_url(),
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "interview evidence",
            response.json().get("error", "").lower(),
        )

    def test_regenerate_endpoint_accepts_general_notes_without_question_notes(self):
        InterviewQuestionNote.objects.filter(
            process=self.process,
            candidate=self.candidate,
        ).delete()

        self.owner.interview_notes = (
            "Saved general interview evidence."
        )
        self.owner.save(update_fields=["interview_notes"])

        response = self.client.post(
            self._post_regenerate_url(),
            data={},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("stream_url"))
