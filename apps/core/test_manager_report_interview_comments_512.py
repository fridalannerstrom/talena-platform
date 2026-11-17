"""Ticket #512: polished Chefsrapport comments use only matching interview evidence."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.core.ai import manager_report_interview_comments as comments
from apps.core.ai.prompt_templates import get_default_ai_prompt, list_ai_prompt_definitions
from apps.processes.models import AIPromptTemplate


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
            patch.object(comments, "get_ai_feature_prompt_instructions", return_value="Admin wants shorter prose."),
        ):
            for category in ("motivation", "skills"):
                evidence = comments.manager_report_comment_evidence(self.owner, category)
                prompt = comments.build_manager_report_comment_prompt(evidence, category, "sv")
                self.assertIn("TASK: Generate the manager report candidate", prompt)
                self.assertIn("Never copy/paste", prompt)
                self.assertIn("Admin wants shorter prose.", prompt)
                self.assertIn("Do not use material from other assessment areas", prompt)
                self.assertNotIn("PERSONALITY_ONLY", prompt)
                self.assertNotIn("PERSONALITY_ANSWER", prompt)
                self.assertNotIn(
                    "SKILLS_ONLY" if category == "motivation" else "MOTIVATION_ONLY",
                    prompt,
                )

    def test_registry_lists_two_distinct_editable_prompts_in_both_languages(self):
        definitions = {item["key"]: item for item in list_ai_prompt_definitions()}
        for category, key in comments.PROMPT_KEYS.items():
            with self.subTest(category=category):
                self.assertIn(key, definitions)
                self.assertEqual(definitions[key]["category"], "Chefsrapport")
                for language in ("sv", "en"):
                    self.assertGreater(len(get_default_ai_prompt(key=key, language=language)), 100)
        self.assertNotEqual(
            get_default_ai_prompt(key=comments.PROMPT_KEYS["motivation"], language="sv"),
            get_default_ai_prompt(key=comments.PROMPT_KEYS["skills"], language="sv"),
        )

    def test_admin_prompt_controls_length_tone_and_selection_not_hardcoded_style(self):
        calls = []
        def feature_prompt(*, key, language, **_kwargs):
            calls.append((key, language))
            return "CUSTOM ADMIN: Write exactly seven sentences. Use a warm, factual tone."

        with (
            patch.object(comments, "get_global_ai_guidance", return_value="Global prompt."),
            patch.object(comments, "get_ai_feature_prompt_instructions", side_effect=feature_prompt),
        ):
            for category, lang in (("motivation", "sv"), ("skills", "en")):
                with self.subTest(category=category, language=lang):
                    prompt = comments.build_manager_report_comment_prompt(
                        {"notes": "Relevant interview fact.", "answers": []},
                        category, lang,
                    )
                    self.assertIn("Write exactly seven sentences", prompt)
                    self.assertIn("Global prompt.", prompt)
                    self.assertNotIn("3–5 sentences", prompt)
                    self.assertNotIn("one coherent, concise", prompt)
                    self.assertIn("PROTECTED EVIDENCE RULES", prompt)
                    self.assertIn('"notes": "Relevant interview fact."', prompt)
        self.assertEqual(
            calls,
            [(comments.PROMPT_KEYS["motivation"], "sv"),
             (comments.PROMPT_KEYS["skills"], "en")],
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
            patch.object(comments, "get_ai_feature_prompt_instructions", return_value="Use concise prose."),
            patch.object(comments, "redact_candidate_name",
                         side_effect=lambda text, candidate: text.replace("Example", "CANDIDATE_A")) as redact,
        ):
            text, fingerprint = comments.generate_manager_report_comment(self.owner, "motivation", "sv")
        self.assertIn("variation ger energi", text)
        self.assertEqual(len(fingerprint), 64)
        redact.assert_called_once()
        self.assertNotIn("SKILLS_ONLY", redact.call_args.args[0])

    def test_verbatim_model_response_is_rewritten_before_it_can_be_saved(self):
        from unittest.mock import Mock

        raw = "MOTIVATION_ONLY: Variation i arbetet ger energi."
        generated = "Kandidaten beskriver att variation bidrar till energi i arbetet."
        responses = [
            SimpleNamespace(choices=[SimpleNamespace(
                finish_reason="stop", message=SimpleNamespace(content=json.dumps({"text": value}))
            )])
            for value in (raw, generated)
        ]
        create = Mock(side_effect=responses)
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with (
            patch(
                "apps.processes.interview_question_evidence.build_interview_question_evidence",
                return_value={"items": []},
            ),
            patch.object(comments, "get_openai_client", return_value=client),
            patch.object(comments, "get_chat_model", return_value="mock-model"),
            patch.object(comments, "get_global_ai_guidance", return_value="Source faithful."),
            patch.object(comments, "get_ai_feature_prompt_instructions", return_value="Use one paragraph."),
        ):
            text, _fingerprint = comments.generate_manager_report_comment(self.owner, "motivation", "sv")
        self.assertEqual(text, generated)
        self.assertEqual(create.call_count, 2)
        self.assertIn("REPAIR:", create.call_args.kwargs["messages"][1]["content"])

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



class ManagerReportCommentAdminOverrideTests(TestCase):
    """Real database overrides, with no live OpenAI request."""

    def test_active_admin_prompt_replaces_default_for_each_area_and_language(self):
        for area, key in comments.PROMPT_KEYS.items():
            for language in ("sv", "en"):
                instruction = f"ADMIN_OVERRIDE::{area}::{language}: Write eight sentences."
                AIPromptTemplate.objects.create(
                    key=key,
                    name=f"Chefsrapport {area}",
                    language=language,
                    prompt_text=instruction,
                    is_active=True,
                )
                with patch.object(comments, "get_global_ai_guidance", return_value="GLOBAL ONLY"):
                    prompt = comments.build_manager_report_comment_prompt(
                        {"notes": "Actual interview statement.", "answers": []},
                        area, language,
                    )
                self.assertIn(instruction, prompt)
                self.assertIn("GLOBAL ONLY", prompt)
                self.assertNotIn("3–5 sentences", prompt)
                self.assertNotIn("3–5 meningar", prompt)
                self.assertIn("PROTECTED EVIDENCE RULES", prompt)

    def test_inactive_override_falls_back_to_editable_registry_default(self):
        key = comments.PROMPT_KEYS["motivation"]
        AIPromptTemplate.objects.create(
            key=key, name="Motivation", language="sv",
            prompt_text="INACTIVE ADMIN OVERRIDE", is_active=False,
        )
        with patch.object(comments, "get_global_ai_guidance", return_value="GLOBAL ONLY"):
            prompt = comments.build_manager_report_comment_prompt(
                {"notes": "Sparad uppgift från intervjun.", "answers": []},
                "motivation", "sv",
            )
        self.assertIn(get_default_ai_prompt(key=key, language="sv"), prompt)
        self.assertNotIn("INACTIVE ADMIN OVERRIDE", prompt)
