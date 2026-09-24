from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.personality_ai_input_contract_policy import (
    _install_personality_interpretation_contract,
    _install_response_style_contract,
    _personality_interpretation_admin_guidance,
    _render_personality_result_summaries,
    _response_style_admin_guidance,
    _shared_personality_input,
)
from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
)


class PersonalityAIInputContractPolicyTests(SimpleTestCase):
    def _owner(self):
        owner = SimpleNamespace(
            candidate=SimpleNamespace(
                first_name="Alex",
                last_name="Andersson",
                email="alex@example.com",
            ),
            selected_personality_traits=["Analytical"],
            sova_activities=[
                {
                    "activity": "Personality Assessment",
                    "competencies": [
                        {"competency": "Analytical", "sten_rounded": 5},
                        {"competency": "Data Focus", "sten_rounded": 2},
                        {"competency": "Evaluating", "sten_rounded": 8},
                        {"competency": "Analysing Problems", "sten_rounded": 4},
                    ],
                }
            ],
        )
        owner.process = SimpleNamespace(
            purpose="recruitment",
            is_historical=False,
            role_context=SimpleNamespace(
                purpose_data={},
                get_context_for_purpose=lambda purpose: {
                    "context_text": (
                        "Role: Project Controller. The role requires evaluating "
                        "limited numerical information and explaining trade-offs "
                        "to project stakeholders."
                    )
                },
            ),
        )
        return owner

    def test_result_summary_is_primary_personality_payload_without_raw_scores(self):
        text = _render_personality_result_summaries(
            self._owner(),
            language_code="sv",
        )

        self.assertIn("PERSONALITY TRAIT: Analytical / Analytisk", text)
        self.assertIn("KANDIDATENS RESULTATSAMMANFATTNING", text)
        self.assertIn(
            INDICATOR_PROFILE_CONTENT["Data Focus"]["score_texts"]["1_2"]["sv"],
            text,
        )
        self.assertIn(
            INDICATOR_PROFILE_CONTENT["Evaluating"]["score_texts"]["8"]["sv"],
            text,
        )
        self.assertIn(
            INDICATOR_PROFILE_CONTENT["Analysing Problems"]["score_texts"]["4_7"]["sv"],
            text,
        )
        self.assertNotIn("STEN", text)
        self.assertNotIn("Data Focus:", text)
        self.assertNotIn("Evaluating:", text)
        self.assertNotIn("Analysing Problems:", text)

    def test_interpretation_input_contains_result_summary_without_process_context(self):
        text = _shared_personality_input(
            self._owner(),
            language_code="en",
            include_process_context=False,
        )

        self.assertIn("TALENA SHARED PERSONALITY AI INPUT", text)
        self.assertIn("PERSONALITY TRAIT: Analytical", text)
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", text)
        self.assertNotIn("PROCESS CONTEXT", text)
        self.assertNotIn("PROCESS PURPOSE", text)
        self.assertNotIn("Role: Project Controller", text)
        self.assertNotIn("APPROVED LOW POLE", text)
        self.assertNotIn("APPROVED HIGH POLE", text)

    @patch(
        "apps.core.ai.prompt_templates.get_global_ai_guidance",
        return_value="GLOBAL GUIDANCE",
    )
    @patch("apps.core.ai.prompt_templates.get_ai_feature_prompt_instructions")
    def test_personality_interpretation_uses_global_plus_each_box_prompt(
        self,
        feature_prompt,
        global_prompt,
    ):
        feature_values = {
            "personality_interpretation": "OVERALL BOX GUIDANCE",
            "personality_trait_interplay": "DYNAMICS BOX GUIDANCE",
            "personality_motivation_interaction": "MOTIVATION BOX GUIDANCE",
            "personality_supportive_patterns": "STRENGTHS BOX GUIDANCE",
            "personality_areas_to_explore": "DEVELOPMENT BOX GUIDANCE",
        }
        feature_prompt.side_effect = lambda **kwargs: feature_values[kwargs["key"]]

        text = _personality_interpretation_admin_guidance(language_code="en")

        self.assertEqual(text.count("GLOBAL GUIDANCE"), 1)
        self.assertIn("OVERALL BOX GUIDANCE", text)
        self.assertIn("DYNAMICS BOX GUIDANCE", text)
        self.assertIn("MOTIVATION BOX GUIDANCE", text)
        self.assertIn("STRENGTHS BOX GUIDANCE", text)
        self.assertIn("DEVELOPMENT BOX GUIDANCE", text)
        self.assertIn("Every box uses exactly two administrator layers", text)

    @patch(
        "apps.core.ai.prompt_templates.get_global_ai_guidance",
        return_value="GLOBAL GUIDANCE",
    )
    @patch("apps.core.ai.prompt_templates.get_ai_feature_prompt_instructions")
    def test_response_style_uses_global_plus_exact_section_prompt(
        self,
        feature_prompt,
        global_prompt,
    ):
        values = {
            "response_style_interpretation": "RESPONSE INTERPRETATION GUIDANCE",
            "response_style_interview_approach": "RESPONSE INTERVIEW GUIDANCE",
        }
        feature_prompt.side_effect = lambda **kwargs: values[kwargs["key"]]

        text = _response_style_admin_guidance(language_code="en")

        self.assertEqual(text.count("GLOBAL GUIDANCE"), 1)
        self.assertIn("RESPONSE INTERPRETATION GUIDANCE", text)
        self.assertIn("RESPONSE INTERVIEW GUIDANCE", text)

    @patch(
        "apps.core.ai.personality_ai_input_contract_policy._personality_interpretation_admin_guidance",
        return_value="ADMINISTRATOR AI GUIDANCE\n\nCLEAN ADMIN GUIDANCE",
    )
    def test_runtime_interpretation_contract_replaces_raw_personality_payload(
        self,
        admin_guidance,
    ):
        base_prompt = """
TALENA INPUT DATA

PERSONALITY ASSESSMENT DATA
- Analytical: STEN 5 of 10

MOTIVATION ASSESSMENT DATA
No motivation data.

ADMINISTRATOR AI GUIDANCE
OLD ADMIN BLOCK

TALENA TECHNICAL OUTPUT CONTRACT
OUTPUT RULES
""".strip()

        module = SimpleNamespace(
            build_personality_interpretation_prompt=(
                lambda owner, personality_results, motivation_results=None, language_code="en": base_prompt
            )
        )
        _install_personality_interpretation_contract(module)

        prompt = module.build_personality_interpretation_prompt(
            self._owner(),
            [{"name": "Analytical", "sten": 5}],
            language_code="en",
        )

        self.assertNotIn("- Analytical: STEN 5 of 10", prompt)
        self.assertIn("TALENA SHARED PERSONALITY AI INPUT", prompt)
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", prompt)
        self.assertNotIn("Role: Project Controller", prompt)
        self.assertNotIn("PROCESS CONTEXT", prompt)
        self.assertIn("CLEAN ADMIN GUIDANCE", prompt)
        self.assertNotIn("OLD ADMIN BLOCK", prompt)
        self.assertLess(
            prompt.index("TALENA SHARED PERSONALITY AI INPUT"),
            prompt.index("CLEAN ADMIN GUIDANCE"),
        )
        self.assertLess(
            prompt.index("CLEAN ADMIN GUIDANCE"),
            prompt.index("TALENA TECHNICAL OUTPUT CONTRACT"),
        )

    @patch(
        "apps.core.ai.personality_ai_input_contract_policy._response_style_admin_guidance",
        return_value="ADMINISTRATOR AI GUIDANCE\n\nCLEAN RESPONSE ADMIN",
    )
    def test_runtime_response_style_contract_adds_personality_summary_and_context(
        self,
        admin_guidance,
    ):
        base_prompt = """
TALENA INPUT DATA

PROCESS CONTEXT
Role context.

RESPONSE-STYLE ASSESSMENT DATA
Profile spread: 6

ADMINISTRATOR AI GUIDANCE
OLD RESPONSE ADMIN

TALENA TECHNICAL OUTPUT CONTRACT
OUTPUT RULES
""".strip()

        module = SimpleNamespace(
            build_response_style_guidance_prompt=(
                lambda guidance_owner, response_styles, language_code="en": base_prompt
            )
        )
        _install_response_style_contract(module)

        prompt = module.build_response_style_guidance_prompt(
            guidance_owner=self._owner(),
            response_styles=[{"key": "profile_spread", "available": True}],
            language_code="en",
        )

        self.assertIn("TALENA SHARED PERSONALITY AI INPUT", prompt)
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", prompt)
        self.assertIn("Role: Project Controller", prompt)
        self.assertIn("RESPONSE-STYLE EVIDENCE BOUNDARY", prompt)
        self.assertIn("CLEAN RESPONSE ADMIN", prompt)
        self.assertNotIn("OLD RESPONSE ADMIN", prompt)
        self.assertLess(
            prompt.index("TALENA SHARED PERSONALITY AI INPUT"),
            prompt.index("CLEAN RESPONSE ADMIN"),
        )
        self.assertLess(
            prompt.index("CLEAN RESPONSE ADMIN"),
            prompt.index("TALENA TECHNICAL OUTPUT CONTRACT"),
        )
