from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.shared_personality_grounding_policy import (
    augment_assessment_text_with_personality_grounding,
    augment_general_insights_prompt_with_personality_grounding,
    augment_owner_prompt_with_personality_grounding,
)


class SharedPersonalityGroundingPolicyTests(SimpleTestCase):
    def _owner(self):
        return SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=[
                {
                    "activity": "Personality Profile",
                    "competencies": [
                        {"competency": "Cooperative", "sten": 6},
                        {"competency": "Sensitivity", "sten": 5},
                        {"competency": "Teamwork", "sten": 8},
                        {"competency": "Agreeableness", "sten": 3},
                    ],
                }
            ],
        )

    def test_ai_overview_and_pre_interview_raw_evidence_share_result_summary(self):
        result = augment_assessment_text_with_personality_grounding(
            "Personality:\n- Cooperative: sten 6",
            self._owner(),
            language_code="sv",
        )

        self.assertIn("Personality:\n- Cooperative: sten 6", result)
        self.assertIn(
            "TALENA CANDIDATE-SPECIFIC PERSONALITY RESULT EVIDENCE",
            result,
        )
        self.assertIn("Cooperative / Samverkande", result)
        self.assertIn("KANDIDATENS RESULTATSAMMANFATTNING", result)
        self.assertNotIn("GODKÄND LÅG-POL", result)

    def test_personality_interpretation_can_receive_indicator_details(self):
        prompt = (
            "PERSONALITY ASSESSMENT DATA\n- Cooperative: STEN 6 of 10"
            "\n\nADMINISTRATOR AI GUIDANCE\nAdmin text"
        )

        result = augment_owner_prompt_with_personality_grounding(
            prompt,
            self._owner(),
            language_code="en",
            marker="\n\nADMINISTRATOR AI GUIDANCE",
            include_indicator_details=True,
        )

        evidence_index = result.index(
            "TALENA CANDIDATE-SPECIFIC PERSONALITY RESULT EVIDENCE"
        )
        admin_index = result.index("ADMINISTRATOR AI GUIDANCE")

        self.assertLess(evidence_index, admin_index)
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", result)
        self.assertIn("UNDERLYING INDICATOR NUANCE", result)
        self.assertIn("Sensitivity", result)

    def test_candidate_summary_uses_same_owner_result_summary(self):
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
            "TALENA CANDIDATE-SPECIFIC PERSONALITY RESULT EVIDENCE",
            result,
        )
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", result)
        self.assertLess(
            result.index("CANDIDATE-SPECIFIC RESULT SUMMARY"),
            result.index("INTERPRETATION INSTRUCTION"),
        )

    def test_general_insights_uses_localized_result_summary(self):
        prompt = (
            "Assessment evidence:\n{}"
            "\n\nReturn valid JSON only.\n{}"
        )
        insight_input = {
            "personality": {
                "all_scores": [
                    {"name": "Cooperative", "score": 6},
                    {"name": "Sensitivity", "score": 5},
                    {"name": "Teamwork", "score": 8},
                    {"name": "Agreeableness", "score": 3},
                ]
            }
        }

        result = augment_general_insights_prompt_with_personality_grounding(
            prompt,
            insight_input,
            language_code="sv",
        )

        self.assertIn("Cooperative / Samverkande", result)
        self.assertIn("KANDIDATENS RESULTATSAMMANFATTNING", result)
        self.assertNotIn("TRAIT: Sensitivity", result)
        self.assertLess(
            result.index(
                "TALENA CANDIDATE-SPECIFIC PERSONALITY RESULT EVIDENCE"
            ),
            result.index("Return valid JSON only."),
        )

    def test_no_parent_results_leaves_prompt_unchanged(self):
        prompt = "Input\n\nINTERPRETATION INSTRUCTION\nAdmin"
        owner = SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=[
                {
                    "activity": "Personality Profile",
                    "competencies": [
                        {"competency": "Sensitivity", "sten": 9},
                    ],
                }
            ],
        )

        result = augment_owner_prompt_with_personality_grounding(
            prompt,
            owner,
            language_code="en",
            marker="\n\nINTERPRETATION INSTRUCTION",
        )

        self.assertEqual(result, prompt)
