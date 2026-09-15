from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai import personality_questions
from apps.core.ai.personality_question_definition_grounding_policy import (
    _build_personality_result_grounding,
)
from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
)


class PersonalityQuestionDefinitionGroundingPolicyTests(SimpleTestCase):
    def _owner(
        self,
        *,
        selected_traits=None,
        context_text=(
            "Role: Key Account Manager. The role involves changing customer "
            "needs, long-term customer relationships and commercial priorities."
        ),
    ):
        owner = SimpleNamespace(
            selected_personality_traits=(
                selected_traits
                if selected_traits is not None
                else ["Cooperative"]
            ),
            candidate=SimpleNamespace(
                first_name="Alex",
                last_name="Andersson",
                email="alex@example.com",
            ),
            sova_activities=[
                {
                    "activity": "Personality Assessment",
                    "competencies": [
                        {
                            "competency": "Cooperative",
                            "sten_rounded": 7,
                        },
                        {
                            "competency": "Sensitivity",
                            "sten_rounded": 9,
                        },
                        {
                            "competency": "Teamwork",
                            "sten_rounded": 4,
                        },
                        {
                            "competency": "Agreeableness",
                            "sten_rounded": 8,
                        },
                        {
                            "competency": "Analytical",
                            "sten_rounded": 2,
                        },
                        {
                            "competency": "Data Focus",
                            "sten_rounded": 2,
                        },
                        {
                            "competency": "Evaluating",
                            "sten_rounded": 3,
                        },
                        {
                            "competency": "Analysing Problems",
                            "sten_rounded": 4,
                        },
                    ],
                }
            ],
        )

        owner.process = SimpleNamespace(
            purpose="recruitment",
            is_historical=False,
            role_context=SimpleNamespace(
                get_context_for_purpose=lambda purpose: {
                    "context_text": context_text,
                }
            ),
        )

        return owner

    def test_selected_trait_uses_result_summary_and_indicator_nuance(self):
        prompt = _build_personality_result_grounding(
            owner=self._owner(),
            language_code="en",
        )

        self.assertIn(
            "TALENA CANDIDATE-SPECIFIC PERSONALITY RESULT EVIDENCE",
            prompt,
        )
        self.assertIn("TRAIT: Cooperative", prompt)
        self.assertNotIn("TRAIT: Analytical", prompt)
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", prompt)
        self.assertIn("UNDERLYING INDICATOR NUANCE", prompt)

        self.assertIn(
            INDICATOR_PROFILE_CONTENT[
                "Sensitivity"
            ]["score_texts"]["9_10"]["en"],
            prompt,
        )
        self.assertIn(
            INDICATOR_PROFILE_CONTENT[
                "Teamwork"
            ]["score_texts"]["4_7"]["en"],
            prompt,
        )
        self.assertIn(
            INDICATOR_PROFILE_CONTENT[
                "Agreeableness"
            ]["score_texts"]["8"]["en"],
            prompt,
        )

        self.assertNotIn("APPROVED LOW POLE", prompt)
        self.assertNotIn("APPROVED HIGH POLE", prompt)

    def test_ai_selection_receives_compact_summaries_for_available_traits(self):
        prompt = _build_personality_result_grounding(
            owner=self._owner(selected_traits=[]),
            language_code="en",
        )

        self.assertIn("TRAIT: Cooperative", prompt)
        self.assertIn("TRAIT: Analytical", prompt)
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", prompt)
        self.assertNotIn("UNDERLYING INDICATOR NUANCE", prompt)

    def test_swedish_grounding_uses_swedish_score_band_content(self):
        prompt = _build_personality_result_grounding(
            owner=self._owner(),
            language_code="sv",
        )

        self.assertIn("Cooperative / Samverkande", prompt)
        self.assertIn("KANDIDATENS RESULTATSAMMANFATTNING", prompt)
        self.assertIn(
            INDICATOR_PROFILE_CONTENT[
                "Sensitivity"
            ]["score_texts"]["9_10"]["sv"],
            prompt,
        )
        self.assertIn(
            INDICATOR_PROFILE_CONTENT[
                "Teamwork"
            ]["score_texts"]["4_7"]["sv"],
            prompt,
        )

    def test_process_context_is_explicitly_required_when_available(self):
        prompt = _build_personality_result_grounding(
            owner=self._owner(),
            language_code="en",
        )

        self.assertIn("PROCESS-CONTEXT REQUIREMENT", prompt)
        self.assertIn(
            "Every question should use a concrete situation",
            prompt,
        )
        self.assertIn(
            "The process context determines WHERE or WHEN to explore it",
            prompt,
        )

    def test_situational_is_a_language_rule_not_the_whole_interpretation(self):
        prompt = _build_personality_result_grounding(
            owner=self._owner(),
            language_code="en",
        )

        self.assertIn(
            '"situational" is only a level-language rule',
            prompt,
        )
        self.assertIn(
            "must never replace the richer candidate-specific result summary",
            prompt,
        )

    def test_competency_selection_does_not_mix_parent_trait_grounding(self):
        prompt = _build_personality_result_grounding(
            owner=self._owner(
                selected_traits=["competency::Teamwork"]
            ),
            language_code="en",
        )

        self.assertEqual(prompt, "")

    def test_goal_focused_alias_uses_result_summary_indicator_text(self):
        owner = self._owner(
            selected_traits=["Achievement Striving"]
        )
        owner.sova_activities = [
            {
                "activity": "Personality Assessment",
                "competencies": [
                    {
                        "competency": "Achievement Striving",
                        "sten_rounded": 8,
                    },
                    {
                        "competency": "Competitive",
                        "sten_rounded": 3,
                    },
                    {
                        "competency": "Challenge",
                        "sten_rounded": 8,
                    },
                    {
                        "competency": "Self-Discipline",
                        "sten_rounded": 9,
                    },
                ],
            }
        ]

        prompt = _build_personality_result_grounding(
            owner=owner,
            language_code="en",
        )

        self.assertIn("Goal-focused", prompt)
        self.assertIn(
            INDICATOR_PROFILE_CONTENT[
                "Competitive"
            ]["score_texts"]["3"]["en"],
            prompt,
        )

    def test_runtime_prompt_places_result_summary_grounding_last(self):
        owner = self._owner()

        with patch.object(
            personality_questions,
            "get_ai_prompt_instructions",
            return_value="Use nuanced candidate-specific questions.",
        ), patch.object(
            personality_questions,
            "get_ai_feature_prompt_instructions",
            return_value="",
        ):
            prompt = (
                personality_questions.build_personality_questions_prompt(
                    owner,
                    [{"name": "Cooperative", "sten": 7}],
                    language_code="en",
                )
            )

        final_index = prompt.rfind(
            "TALENA FINAL CANDIDATE-SPECIFIC PERSONALITY QUESTION GROUNDING"
        )
        precision_index = prompt.rfind(
            "TALENA PERSONALITY QUESTION PRECISION STANDARD"
        )

        self.assertGreater(final_index, precision_index)
        self.assertIn(
            INDICATOR_PROFILE_CONTENT[
                "Sensitivity"
            ]["score_texts"]["9_10"]["en"],
            prompt,
        )
        self.assertIn("PROCESS-CONTEXT REQUIREMENT", prompt)
