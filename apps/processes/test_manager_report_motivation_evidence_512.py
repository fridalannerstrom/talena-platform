"""Ticket #512: manager-report interview provenance and category routing."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.processes.services.manager_report_motivation_evidence import (
    _motivation_notes,
    build_manager_motivation_interview_evidence,
)


class ManagerMotivationEvidenceTests(SimpleTestCase):
    def test_extracts_only_explicitly_categorised_motivation_notes(self):
        notes = (
            "### Intervjuunderlag: Personlighet\n"
            "Worked with the team.\n\n"
            "### Intervjuunderlag: Motivation\n"
            "Enjoys variation and ownership.\n\n"
            "### Intervjuunderlag: Färdighet\n"
            "Explained a calculation.\n"
        )
        self.assertEqual(
            _motivation_notes(notes),
            "Enjoys variation and ownership.",
        )

    def test_preserves_multiple_motivation_sections_without_inventing_content(self):
        notes = (
            "### Intervjuunderlag: Motivation\nFirst actual answer\n"
            "### Intervjuunderlag: Personlighet\nNot a motivator\n"
            "### Intervjuunderlag: Motivation\nSecond actual answer\n"
        )
        self.assertEqual(
            _motivation_notes(notes), "First actual answer\n\nSecond actual answer"
        )

    def test_does_not_guess_topic_of_legacy_notes(self):
        self.assertEqual(_motivation_notes("Candidate enjoys interesting tasks."), "")
        self.assertEqual(
            _motivation_notes(
                "Older uncategorised note\n### Intervjuunderlag: Personlighet\nA"
            ), "",
        )

    def test_includes_only_saved_motivation_question_answers_with_questions(self):
        owner = SimpleNamespace(interview_notes=(
            "### Intervjuunderlag: Motivation\n"
            "Wants clear feedback."
        ))
        evidence = {
            "items": [
                {
                    "source": "personality",
                    "question": "How do you cooperate?",
                    "saved_answer_or_note": "Works in a group.",
                },
                {
                    "source": "motivation",
                    "question": "What creates engagement?",
                    "saved_answer_or_note": "Seeing progress.",
                },
                {
                    "source": "cognitive",
                    "question": "Explain this pattern.",
                    "saved_answer_or_note": "Counting.",
                },
                {
                    "source": "motivation",
                    "question": "What energises you?",
                    "saved_answer_or_note": "",
                },
            ],
        }
        with patch(
            "apps.processes.services.manager_report_motivation_evidence."
            "build_interview_question_evidence", return_value=evidence,
        ):
            result = build_manager_motivation_interview_evidence(owner)
        self.assertEqual(result, {
            "notes": "Wants clear feedback.",
            "answers": [{
                "question": "What creates engagement?",
                "answer": "Seeing progress.",
            }],
        })

    def test_no_saved_source_yields_neutral_empty_state(self):
        owner = SimpleNamespace(interview_notes="")
        with patch(
            "apps.processes.services.manager_report_motivation_evidence."
            "build_interview_question_evidence",
            return_value={"items": []},
        ):
            result = build_manager_motivation_interview_evidence(owner)
        self.assertEqual(result, {"notes": "", "answers": []})
