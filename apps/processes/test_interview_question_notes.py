import json

from django.apps import apps
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Company, OrgUnit, User
from apps.processes.interview_question_models import InterviewQuestionNote
from apps.processes.interview_question_notes import (
    _question_texts_from_result,
    get_current_question_texts,
    interview_question_key,
    normalize_question_text,
)
from apps.processes.models import Candidate, TestInvitation, TestProcess


class InterviewQuestionNoteHelperTests(TestCase):
    def test_question_normalisation_collapses_rendering_whitespace(self):
        self.assertEqual(
            normalize_question_text("  Tell me\n  about   a challenge.  "),
            "Tell me about a challenge.",
        )

    def test_question_key_is_stable_after_whitespace_normalisation(self):
        compact = interview_question_key(
            "personality",
            "Tell me about a challenge.",
        )
        rendered = interview_question_key(
            " personality ",
            " Tell me\n about   a challenge. ",
        )
        other_source = interview_question_key(
            "motivation",
            "Tell me about a challenge.",
        )

        self.assertEqual(compact, rendered)
        self.assertNotEqual(compact, other_source)

    def test_question_text_extraction_supports_string_and_object_items(self):
        result = {
            "questions": [
                " First question? ",
                {"question": "Second\n question?"},
                {"question": ""},
                None,
            ]
        }

        self.assertEqual(
            _question_texts_from_result(result),
            {
                "First question?",
                "Second question?",
            },
        )

    def test_motivation_and_cognitive_can_use_interpretation_question_fallback(self):
        owner = type(
            "Owner",
            (),
            {
                "ai_motivation_questions": {},
                "ai_motivation_interpretation": {
                    "questions": [
                        {"question": "What gives you energy?"},
                    ]
                },
                "ai_cognitive_questions": {},
                "ai_cognitive_interpretation": {
                    "questions": [
                        {"question": "How do you approach unfamiliar problems?"},
                    ]
                },
            },
        )()

        self.assertEqual(
            get_current_question_texts(owner, "motivation"),
            {"What gives you energy?"},
        )
        self.assertEqual(
            get_current_question_texts(owner, "cognitive"),
            {"How do you approach unfamiliar problems?"},
        )

    def test_model_is_registered_with_processes_app(self):
        self.assertIs(
            apps.get_model("processes", "InterviewQuestionNote"),
            InterviewQuestionNote,
        )


class InterviewQuestionNoteEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="question-notes-admin",
            email="question-notes-admin@example.com",
            password="test-password",
        )
        self.company = Company.objects.create(name="Question notes company")
        self.unit = OrgUnit.objects.create(
            company=self.company,
            name="Question notes unit",
            unit_code="QUESTION-NOTES",
        )
        self.process = TestProcess.objects.create(
            name="Question notes process",
            provider="sova",
            company=self.company,
            project_code="QUESTION-NOTES-PROJECT",
            account_code="QUESTION-NOTES-ACCOUNT",
            org_unit=self.unit,
            created_by=self.user,
        )
        self.candidate = Candidate.objects.create(
            first_name="Taylor",
            last_name="Candidate",
            email="taylor-question-notes@example.com",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process,
            candidate=self.candidate,
            status="completed",
            ai_personality_questions={
                "questions": [
                    {
                        "question": (
                            "Tell me about a time when you had to "
                            "adapt your usual working style."
                        )
                    }
                ]
            },
            ai_motivation_questions={
                "questions": [
                    {"question": "What gives you energy at work?"}
                ]
            },
            ai_post_interview_decision_support={
                "overall_synthesis": "Existing synthesis",
            },
            ai_post_interview_decision_support_status="completed",
        )
        self.client.force_login(self.user)

        self.list_url = reverse(
            "processes:process_candidate_interview_question_notes",
            kwargs={
                "process_id": self.process.id,
                "candidate_id": self.candidate.id,
            },
        )
        self.update_url = reverse(
            "processes:process_candidate_interview_question_note_update",
            kwargs={
                "process_id": self.process.id,
                "candidate_id": self.candidate.id,
            },
        )

    def post_note(self, **overrides):
        payload = {
            "source": "personality",
            "question": (
                "Tell me about a time when you had to "
                "adapt your usual working style."
            ),
            "note": "Used a concrete stakeholder example.",
        }
        payload.update(overrides)
        return self.client.post(
            self.update_url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_saves_note_against_exact_generated_question(self):
        response = self.post_note(
            question=(
                " Tell me about a time when you had to\n"
                "adapt your usual   working style. "
            ),
        )

        self.assertEqual(response.status_code, 200)
        note = InterviewQuestionNote.objects.get()
        self.assertEqual(note.source, "personality")
        self.assertEqual(
            note.question_text,
            (
                "Tell me about a time when you had to "
                "adapt your usual working style."
            ),
        )
        self.assertEqual(note.note, "Used a concrete stakeholder example.")
        self.assertEqual(note.updated_by, self.user)

    def test_saved_notes_are_available_from_candidate_endpoint(self):
        self.post_note()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["notes"]), 1)
        self.assertEqual(payload["notes"][0]["source"], "personality")
        self.assertEqual(
            payload["notes"][0]["note"],
            "Used a concrete stakeholder example.",
        )

    def test_rejects_note_for_question_not_in_current_generated_questions(self):
        response = self.post_note(
            question="Invented question that was never generated.",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(InterviewQuestionNote.objects.exists())

    def test_empty_note_removes_existing_saved_note(self):
        self.post_note()
        self.assertTrue(InterviewQuestionNote.objects.exists())

        response = self.post_note(note="   ")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(InterviewQuestionNote.objects.exists())

    def test_editing_question_note_marks_existing_post_interview_result_outdated(self):
        response = self.post_note()

        self.assertEqual(response.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(
            self.invitation.ai_post_interview_decision_support_status,
            "outdated",
        )
        self.assertEqual(response.json()["post_interview_status"], "outdated")
