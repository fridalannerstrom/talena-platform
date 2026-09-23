from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.core.ai.decision_support import (
    _extract_json_events_from_buffer,
    _post_get_content_block_prompt_instructions,
    build_post_interview_decision_support_prompt,
)

from apps.processes.models import AIPromptTemplate


class PostInterviewPromptContractTests(SimpleTestCase):
    def test_content_block_prompts_are_isolated_from_legacy_guidance(self):
        owner = SimpleNamespace(
            interview_notes="Interview notes",
            ai_pre_interview_decision_support={},
        )

        shared_context = {
            "candidate": SimpleNamespace(
                first_name="Test",
                last_name="Candidate",
            ),
            "purpose_label": "Purpose",
            "context_text": "Role context",
        }
        evidence = {
            "evidence_text": "Assessment evidence",
            "has_evidence": True,
        }

        def feature_prompt(*, key, language, default=None):
            return f"PROMPT::{key}"

        with (
            patch(
                "apps.core.ai.post_interview_question_evidence_policy.get_post_interview_note_evidence",
                return_value={
                    "general_notes": "Interview notes",
                    "has_general_notes": True,
                    "question_evidence": {
                        "text": "",
                        "count": 0,
                        "has_evidence": False,
                    },
                    "has_question_evidence": False,
                    "has_evidence": True,
                },
            ),
            patch(
                "apps.core.ai.decision_support.get_global_ai_guidance",
                return_value="GLOBAL GUIDANCE",
            ),
            patch(
                "apps.core.ai.decision_support.get_ai_feature_prompt_instructions",
                side_effect=feature_prompt,
            ),
            patch(
                "apps.core.ai.decision_support.build_shared_ai_context",
                return_value=shared_context,
            ),
            patch(
                "apps.core.ai.decision_support.build_pre_interview_evidence",
                return_value=evidence,
            ),
        ):
            prompt = build_post_interview_decision_support_prompt(
                owner,
                language_code="sv",
            )

        self.assertIn("GLOBAL AI GUIDANCE — PROTECTED BOUNDARIES ONLY", prompt)
        self.assertIn(
            "OVERALL_PICTURE GUIDANCE\nPROMPT::post_interview_overall_picture",
            prompt,
        )
        self.assertIn(
            "OPTIONAL LEGACY COMPATIBILITY EVENTS",
            prompt,
        )
        self.assertIn(
            "FINAL ADMINISTRATOR CONTENT AUTHORITY",
            prompt,
        )
        self.assertIn(
            "PROMPT::post_interview_overall_picture",
            prompt,
        )
        self.assertNotIn(
            "PROMPT::post_interview_decision_support",
            prompt,
        )
        self.assertIn(
            "sole authority for that value",
            prompt,
        )
        self.assertNotIn(
            "default word count",
            prompt,
        )
        self.assertNotIn(
            '"blocks": {"overall_picture"',
            prompt,
        )

        self.assertIn("Inside each user-facing content_blocks string, use simple Markdown", prompt)
        self.assertIn("Never include HTML", prompt)


    def test_stream_parser_accepts_literal_multiline_content_block_text(self):
        events, remainder = _extract_json_events_from_buffer(
            '{"type":"content_blocks","blocks":{"overall_picture":"Första stycket.\n\nAndra stycket."}}'
        )

        self.assertEqual(remainder, "")
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0]["blocks"]["overall_picture"],
            "Första stycket.\n\nAndra stycket.",
        )



class PostInterviewPromptOverrideCompatibilityTests(TestCase):
    def test_legacy_overall_picture_override_is_used_when_canonical_is_missing(self):
        AIPromptTemplate.objects.create(
            key="overall_picture",
            name="Legacy overall picture",
            language="sv",
            prompt_text="LEGACY HELHETSBILD PROMPT",
            is_active=True,
        )

        prompt = _post_get_content_block_prompt_instructions(
            key="overall_picture",
            language="sv",
        )

        self.assertEqual(prompt, "LEGACY HELHETSBILD PROMPT")

    def test_canonical_override_has_priority_over_legacy_override(self):
        AIPromptTemplate.objects.create(
            key="overall_picture",
            name="Legacy overall picture",
            language="sv",
            prompt_text="LEGACY HELHETSBILD PROMPT",
            is_active=True,
        )
        AIPromptTemplate.objects.create(
            key="post_interview_overall_picture",
            name="Overall picture",
            language="sv",
            prompt_text="CANONICAL HELHETSBILD PROMPT",
            is_active=True,
        )

        prompt = _post_get_content_block_prompt_instructions(
            key="overall_picture",
            language="sv",
        )

        self.assertEqual(prompt, "CANONICAL HELHETSBILD PROMPT")
