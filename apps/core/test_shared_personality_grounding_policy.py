from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.shared_personality_grounding_policy import (
    augment_assessment_text_with_personality_grounding,
    augment_general_insights_prompt_with_personality_grounding,
    augment_owner_prompt_with_personality_grounding,
    augment_result_prompt_with_personality_grounding,
)


class SharedPersonalityGroundingPolicyTests(SimpleTestCase):
    def _owner(self):
        return SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=[
                {
                    "activity": "Personality Profile",
                    "competencies": [
                        {"competency": "Analytical", "sten": 3},
                        {"competency": "Creativity", "sten": 8},
                    ],
                }
            ],
        )

    def test_ai_overview_and_pre_interview_raw_evidence_can_share_grounding(self):
        result = augment_assessment_text_with_personality_grounding(
            "Personality:\n- Analytical: sten 3",
            self._owner(),
            language_code="sv",
        )

        self.assertIn("Personality:\n- Analytical: sten 3", result)
        self.assertIn(
            "TALENA APPROVED PERSONALITY DEFINITION EVIDENCE",
            result,
        )
        self.assertIn("Analytical / Analytisk", result)
        self.assertIn("GODKÄND LÅG-POL", result)

    def test_personality_interpretation_grounding_is_inserted_before_admin_guidance(self):
        prompt = (
            "PERSONALITY ASSESSMENT DATA\n- Analytical: STEN 3 of 10"
            "\n\nADMINISTRATOR AI GUIDANCE\nAdmin text"
        )

        result = augment_result_prompt_with_personality_grounding(
            prompt,
            [{"name": "Analytical", "sten": 3}],
            language_code="en",
            marker="\n\nADMINISTRATOR AI GUIDANCE",
        )

        evidence_index = result.index(
            "TALENA APPROVED PERSONALITY DEFINITION EVIDENCE"
        )
        admin_index = result.index("ADMINISTRATOR AI GUIDANCE")

        self.assertLess(evidence_index, admin_index)
        self.assertIn("CANDIDATE RESULT: STEN 3 of 10", result)

    def test_candidate_summary_uses_same_owner_grounding(self):
        prompt = (
            "ASSESSMENT RESULTS\nPersonality results"
            "\n\nINTERPRETATION INSTRUCTION\nInterpret carefully"
        )

        result = augment_owner_prompt_with_personality_grounding(
            prompt,
            self._owner(),
            language_code="en",
            marker="\n\nINTERPRETATION INSTRUCTION",
        )

        self.assertIn(
            "TALENA APPROVED PERSONALITY DEFINITION EVIDENCE",
            result,
        )
        self.assertLess(
            result.index("APPROVED LOW POLE"),
            result.index("INTERPRETATION INSTRUCTION"),
        )

    def test_general_insights_uses_localized_shared_grounding(self):
        prompt = (
            "Assessment evidence:\n{}"
            "\n\nReturn valid JSON only.\n{}"
        )
        insight_input = {
            "personality": {
                "all_scores": [
                    {"name": "Structured", "score": 8},
                    {"name": "Sensitivity", "score": 9},
                ]
            }
        }

        result = augment_general_insights_prompt_with_personality_grounding(
            prompt,
            insight_input,
            language_code="sv",
        )

        self.assertIn("Structured / Strukturerad & disciplinerad", result)
        self.assertIn("GODKÄND HÖG-POL", result)
        self.assertNotIn("TRAIT: Sensitivity", result)
        self.assertLess(
            result.index("TALENA APPROVED PERSONALITY DEFINITION EVIDENCE"),
            result.index("Return valid JSON only."),
        )

    def test_no_parent_results_leaves_prompt_unchanged(self):
        prompt = "Input\n\nADMINISTRATOR AI GUIDANCE\nAdmin"

        result = augment_result_prompt_with_personality_grounding(
            prompt,
            [{"name": "Sensitivity", "sten": 9}],
            language_code="en",
            marker="\n\nADMINISTRATOR AI GUIDANCE",
        )

        self.assertEqual(result, prompt)
