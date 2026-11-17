"""Ticket #512: polished Chefsrapport comments use only matching interview evidence."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai import manager_report_interview_comments as comments


NOTES = (
    "### Intervjuunderlag: Personlighet\n"
    "PERSONALITY_ONLY: Kandidaten prioriterar noggrant.\n\n"
    "### Intervjuunderlag: Motivation\n"
    "MOTIVATION_ONLY: Variation i arbetet ger energi.\n\n"
    "### Intervjuunderlag: Färdighet\n"
    "SKILLS_ONLY: Kandidaten dubbelkollar siffror.\n"
)
ITEMS = [
    {"source": "personality", "question": "PERSONALITY_QUESTION", "saved_answer_or_note": "PERSONALITY_ANSWER"},
    {"source": "motivation", "question": "MOTIVATION_QUESTION", "saved_answer_or_note": "MOTIVATION_ANSWER"},
    {"source": "cognitive", "question": "SKILLS_QUESTION", "saved_answer_or_note": "SKILLS_ANSWER"},
]


class ManagerReportCommentTests(SimpleTestCase):
    def setUp(self):
        self.owner = SimpleNamespace(
            interview_notes=NOTES,
            candidate=SimpleNamespace(first_name="Example", last_name="Person"),
            ai_manager_report_interview_comments={},
        )

    def test_each_area_receives_only_matching_notes_and_saved_answers(self):
        with patch(
            "apps.processes.interview_question_evidence.build_interview_question_evidence",
            return_value={"items": ITEMS},
        ):
            for category, included, excluded in (
                ("motivation", "MOTIVATION_ONLY", ["PERSONALITY_ONLY", "SKILLS_ONLY"]),
                ("skills", "SKILLS_ONLY", ["PERSONALITY_ONLY", "MOTIVATION_ONLY"]),
            ):
                with self.subTest(category=category):
                    evidence = comments.manager_report_comment_evidence(self.owner, category)
                    self.assertIn(included, str(evidence))
                    for token in excluded:
                        self.assertNotIn(token, str(evidence))
                    self.assertEqual(len(evidence["answers"]), 1)
                    self.assertIn(category.upper(), evidence["answers"][0]["question"])
                    self.assertNotIn("PERSONALITY_ANSWER", str(evidence))

    def test_prompt_polishes_prose_and_does_not_include_other_area_material(self):
        with (
            patch(
                "apps.processes.interview_question_evidence.build_interview_question_evidence",
                return_value={"items": ITEMS},
            ),
            patch.object(comments, "get_global_ai_guidance", return_value="Keep it balanced."),
        ):
            for category in ("motivation", "skills"):
                evidence = comments.manager_report_comment_evidence(self.owner, category)
                prompt = comments.build_manager_report_comment_prompt(evidence, category, "sv")
                self.assertIn("Kandidatens kommentarer", prompt)
                self.assertIn("Never copy/paste", prompt)
                self.assertIn("not interpret test results", prompt)
                self.assertNotIn("PERSONALITY_ONLY", prompt)
                self.assertNotIn("PERSONALITY_ANSWER", prompt)
                self.assertNotIn(
                    "SKILLS_ONLY" if category == "motivation" else "MOTIVATION_ONLY",
                    prompt,
                )

    def test_plain_legacy_notes_are_never_sent_to_motivation_or_skills(self):
        self.owner.interview_notes = "Unclassified notes from the old editor."
        with patch(
            "apps.processes.interview_question_evidence.build_interview_question_evidence",
            return_value={"items": []},
        ):
            for category in comments.CATEGORIES:
                with self.subTest(category=category):
                    evidence = comments.manager_report_comment_evidence(self.owner, category)
                    self.assertEqual(evidence, {"notes": "", "answers": []})

    def test_missing_area_evidence_makes_no_openai_call(self):
        self.owner.interview_notes = ""
        with (
            patch(
                "apps.processes.interview_question_evidence.build_interview_question_evidence",
                return_value={"items": []},
            ),
            patch.object(comments, "get_openai_client",
                         side_effect=AssertionError("No AI call for missing interview notes")),
        ):
            text, fingerprint = comments.generate_manager_report_comment(self.owner, "skills", "sv")
        self.assertEqual(text, "")
        self.assertEqual(len(fingerprint), 64)

    def test_generated_result_is_validated_and_candidate_name_is_redacted(self):
        model = SimpleNamespace(
            choices=[SimpleNamespace(
                finish_reason="stop",
                message=SimpleNamespace(content=json.dumps({"text": "Kandidaten beskriver att variation ger energi."})),
            )]
        )
        create = lambda **kwargs: model
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with (
            patch(
                "apps.processes.interview_question_evidence.build_interview_question_evidence",
                return_value={"items": ITEMS},
            ),
            patch.object(comments, "get_openai_client", return_value=client),
            patch.object(comments, "get_chat_model", return_value="mock-model"),
            patch.object(comments, "get_global_ai_guidance", return_value="Respect the source."),
            patch.object(comments, "redact_candidate_name",
                         side_effect=lambda text, candidate: text.replace("Example", "CANDIDATE_A")) as redact,
        ):
            text, fingerprint = comments.generate_manager_report_comment(self.owner, "motivation", "sv")
        self.assertIn("variation ger energi", text)
        self.assertEqual(len(fingerprint), 64)
        redact.assert_called_once()
        self.assertNotIn("SKILLS_ONLY", redact.call_args.args[0])

    def test_persisted_comments_are_only_visible_with_matching_source_and_language(self):
        with patch(
            "apps.processes.interview_question_evidence.build_interview_question_evidence",
            return_value={"items": ITEMS},
        ):
            motivation = comments.manager_report_comment_evidence(self.owner, "motivation")
            skills = comments.manager_report_comment_evidence(self.owner, "skills")
            self.owner.ai_manager_report_interview_comments = {
                "motivation": {
                    "text": "Bearbetad kommentar.",
                    "fingerprint": comments.comment_fingerprint(motivation, "sv"),
                    "language": "sv",
                },
                "skills": {
                    "text": "Färdighetskommentar.",
                    "fingerprint": comments.comment_fingerprint(skills, "sv"),
                    "language": "sv",
                },
            }
            self.assertEqual(
                comments.visible_manager_report_comments(self.owner, "sv"),
                {"motivation": "Bearbetad kommentar.", "skills": "Färdighetskommentar."},
            )
            self.assertEqual(
                comments.visible_manager_report_comments(self.owner, "en"),
                {"motivation": "", "skills": ""},
            )
            self.owner.interview_notes = self.owner.interview_notes.replace(
                "Variation i arbetet ger energi", "Kandidaten trivs med variation"
            )
            self.assertEqual(
                comments.visible_manager_report_comments(self.owner, "sv"),
                {"motivation": "", "skills": "Färdighetskommentar."},
            )

    def test_invalid_category_and_raw_source_dump_are_rejected(self):
        with self.assertRaises(ValueError):
            comments.manager_report_comment_evidence(self.owner, "personality")
        with patch(
            "apps.processes.interview_question_evidence.build_interview_question_evidence",
            return_value={"items": ITEMS},
        ):
            evidence = comments.manager_report_comment_evidence(self.owner, "skills")
            self.assertEqual(evidence["answers"][0]["question"], "SKILLS_QUESTION")
