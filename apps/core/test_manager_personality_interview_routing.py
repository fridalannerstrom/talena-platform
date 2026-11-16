"""Regression tests: weakly classified interview notes remain available to the manager report."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.manager_report_personality import (
    _enforce_manager_interview_availability,
    _get_manager_report_interview_material,
    build_manager_report_personality_prompt,
    stream_manager_report_personality,
)


class ManagerPersonalityInterviewEvidenceTests(SimpleTestCase):
    def test_uncategorised_english_question_and_answer_are_not_discarded(self):
        item = {
            "source": "personality",
            "source_label": "Personality",
            "question": "Tell me about a challenging project you worked on.",
            "saved_answer_or_note": (
                "The candidate described clarifying expectations with a client "
                "and presenting two options before proceeding."
            ),
        }
        owner = SimpleNamespace(interview_notes="")
        with patch(
            "apps.processes.interview_question_evidence.build_interview_question_evidence",
            return_value={"items": [item]},
        ):
            routed, notes, items = _get_manager_report_interview_material(owner)

        self.assertFalse(any(routed.values()))  # old keyword-only gate lost it
        self.assertEqual(notes, "")
        self.assertEqual(items, [item])

    def test_prompt_includes_original_unrouted_question_and_general_notes(self):
        item = {
            "source": "personality",
            "source_label": "Personality",
            "question": "Tell me about a difficult situation.",
            "saved_answer_or_note": "Candidate described giving clear options to a client.",
        }
        owner = SimpleNamespace(interview_notes="Intervjuaren noterade tydliga exempel.")
        with (
            patch(
                "apps.core.ai.manager_report_personality.build_shared_ai_context",
                return_value={"purpose_label": "Recruitment", "context_text": ""},
            ),
            patch(
                "apps.core.ai.manager_report_personality.build_personality_indicator_interpretations",
                return_value={},
            ),
            patch(
                "apps.core.ai.manager_report_personality.get_ai_feature_prompt_instructions",
                return_value="Summarise factual interview material.",
            ),
            patch(
                "apps.core.ai.manager_report_personality._get_manager_report_interview_material",
                return_value=({"leading_and_working_with_others": [], "organising_and_thinking_patterns": [], "interaction_and_emotion_management": []},
                              owner.interview_notes, [item]),
            ),
        ):
            prompt = build_manager_report_personality_prompt(owner, language_code="sv")
        self.assertIn("Intervjuaren noterade tydliga exempel.", prompt)
        self.assertIn(item["question"], prompt)
        self.assertIn(item["saved_answer_or_note"], prompt)
        self.assertIn("An empty\ntheme list does NOT prove", prompt)
        self.assertIn("Preserve provenance", prompt)
        self.assertIn("return an empty string", prompt)

    def test_missing_all_interview_evidence_still_blanks_candidate_describes(self):
        event = {
            "type": "manager_report_personality_text",
            "theme": "organising_and_thinking_patterns",
            "part": "candidate_describes",
            "text": "This is an unsupported invented account.",
        }
        self.assertEqual(
            _enforce_manager_interview_availability(event, has_interview_evidence=False)["text"],
            "",
        )
        self.assertEqual(
            _enforce_manager_interview_availability(event, has_interview_evidence=True)["text"],
            event["text"],
        )

    def test_assessment_part_is_never_cleared_by_interview_availability(self):
        event = {
            "type": "manager_report_personality_text",
            "theme": "interaction_and_emotion_management",
            "part": "testbild",
            "text": "This describes test result indications.",
        }
        self.assertEqual(
            _enforce_manager_interview_availability(event, has_interview_evidence=False),
            event,
        )

    def test_stream_keeps_grounded_text_even_when_keyword_router_has_no_theme(self):
        event = {
            "type": "manager_report_personality_text",
            "theme": "organising_and_thinking_patterns",
            "part": "candidate_describes",
            "text": "The candidate described setting out options for a client.",
        }
        data = json.dumps(event) + "\n"
        response = SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=data))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: iter([response]))
            )
        )
        owner = SimpleNamespace(candidate=SimpleNamespace(first_name="Test"))
        blank_routes = {
            "leading_and_working_with_others": [],
            "organising_and_thinking_patterns": [],
            "interaction_and_emotion_management": [],
        }

        with (
            patch("apps.core.ai.manager_report_personality._get_manager_report_interview_material",
                  return_value=(blank_routes, "", [
                      {"question": "Tell me about a situation", "saved_answer_or_note": "The candidate set out options."}
                  ])),
            patch("apps.core.ai.manager_report_personality.build_manager_report_personality_prompt",
                  return_value="Safe test prompt"),
            patch("apps.core.ai.manager_report_personality.redact_candidate_name",
                  side_effect=lambda prompt, candidate: prompt),
            patch("apps.core.ai.manager_report_personality.get_ai_system_language_instruction",
                  return_value="Use English."),
            patch("apps.core.ai.manager_report_personality.get_chat_model", return_value="test-model"),
            patch("apps.core.ai.manager_report_personality.get_openai_client",
                  return_value=client),
        ):
            events = list(stream_manager_report_personality(owner=owner, language_code="en"))

        matches = [
            item for item in events
            if item.get("type") == "manager_report_personality_text"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], event["text"])
