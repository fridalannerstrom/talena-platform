from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.decision_support import (
    build_post_interview_decision_support_prompt,
)


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

        self.assertIn("GLOBAL ADMINISTRATOR AI GUIDANCE", prompt)
        self.assertIn(
            "OVERALL_PICTURE GUIDANCE\nPROMPT::post_interview_overall_picture",
            prompt,
        )
        self.assertIn(
            "LEGACY DECISION-SUPPORT GUIDANCE",
            prompt,
        )
        self.assertIn(
            "PROMPT::post_interview_decision_support",
            prompt,
        )
        self.assertIn(
            "Never substitute the",
            prompt,
        )
