from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.personality_question_definition_grounding_policy import (
    _build_personality_definition_grounding,
    _score_band_key,
)
from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
    TRAIT_PROFILE_CONTENT,
)


class PersonalityQuestionDefinitionGroundingPolicyTests(SimpleTestCase):
    def _owner(
        self,
        *,
        selected_traits=None,
    ):
        return SimpleNamespace(
            selected_personality_traits=(
                selected_traits
                if selected_traits is not None
                else ["Cooperative"]
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
                    ],
                }
            ],
        )

    def test_indicator_sten_values_map_to_approved_score_bands(self):
        expected = {
            1: "1_2",
            2: "1_2",
            3: "3",
            4: "4_7",
            7: "4_7",
            8: "8",
            9: "9_10",
            10: "9_10",
        }

        for sten, band in expected.items():
            with self.subTest(sten=sten):
                self.assertEqual(
                    _score_band_key(sten),
                    band,
                )

    def test_english_grounding_contains_parent_definitions_and_indicator_bands(self):
        prompt = _build_personality_definition_grounding(
            owner=self._owner(),
            personality_results=[
                {"name": "Cooperative", "sten": 7},
                {"name": "Analytical", "sten": 2},
            ],
            language_code="en",
        )

        cooperative = TRAIT_PROFILE_CONTENT[
            "Cooperative"
        ]
        sensitivity = INDICATOR_PROFILE_CONTENT[
            "Sensitivity"
        ]
        teamwork = INDICATOR_PROFILE_CONTENT[
            "Teamwork"
        ]
        agreeableness = INDICATOR_PROFILE_CONTENT[
            "Agreeableness"
        ]

        self.assertIn(
            cooperative["low_pole"]["en"],
            prompt,
        )
        self.assertIn(
            cooperative["high_pole"]["en"],
            prompt,
        )
        self.assertIn(
            sensitivity["score_texts"]["9_10"]["en"],
            prompt,
        )
        self.assertIn(
            teamwork["score_texts"]["4_7"]["en"],
            prompt,
        )
        self.assertIn(
            agreeableness["score_texts"]["8"]["en"],
            prompt,
        )

        self.assertIn(
            "Sensitivity / Sensitivity: STEN 9 of 10",
            prompt,
        )
        self.assertIn(
            "APPROVED SCORE-BAND INTERPRETATION (9–10)",
            prompt,
        )
        self.assertIn(
            "APPROVED SCORE-BAND INTERPRETATION (4–7)",
            prompt,
        )
        self.assertIn(
            "APPROVED SCORE-BAND INTERPRETATION (8)",
            prompt,
        )

    def test_selected_trait_limits_grounding_to_that_parent_trait(self):
        prompt = _build_personality_definition_grounding(
            owner=self._owner(
                selected_traits=["Cooperative"]
            ),
            personality_results=[
                {"name": "Cooperative", "sten": 7},
                {"name": "Analytical", "sten": 2},
            ],
            language_code="en",
        )

        self.assertIn(
            "TECHNICAL TRAIT NAME: Cooperative",
            prompt,
        )
        self.assertNotIn(
            "TECHNICAL TRAIT NAME: Analytical",
            prompt,
        )

    def test_ai_selection_receives_all_available_parent_trait_definitions(self):
        prompt = _build_personality_definition_grounding(
            owner=self._owner(selected_traits=[]),
            personality_results=[
                {"name": "Cooperative", "sten": 7},
                {"name": "Analytical", "sten": 2},
            ],
            language_code="en",
        )

        self.assertIn(
            "TECHNICAL TRAIT NAME: Cooperative",
            prompt,
        )
        self.assertIn(
            "TECHNICAL TRAIT NAME: Analytical",
            prompt,
        )

    def test_swedish_grounding_uses_swedish_approved_content(self):
        prompt = _build_personality_definition_grounding(
            owner=self._owner(),
            personality_results=[
                {"name": "Cooperative", "sten": 7},
            ],
            language_code="sv",
        )

        self.assertIn(
            TRAIT_PROFILE_CONTENT[
                "Cooperative"
            ]["low_pole"]["sv"],
            prompt,
        )
        self.assertIn(
            TRAIT_PROFILE_CONTENT[
                "Cooperative"
            ]["high_pole"]["sv"],
            prompt,
        )
        self.assertIn(
            INDICATOR_PROFILE_CONTENT[
                "Sensitivity"
            ]["score_texts"]["9_10"]["sv"],
            prompt,
        )
        self.assertIn(
            "Sensitivity / Känslighet: STEN 9 of 10",
            prompt,
        )

    def test_indicator_evidence_stays_supporting_and_not_selectable(self):
        prompt = _build_personality_definition_grounding(
            owner=self._owner(),
            personality_results=[
                {"name": "Cooperative", "sten": 7},
            ],
            language_code="en",
        )

        self.assertIn(
            "NOT additional user-selected traits",
            prompt,
        )
        self.assertIn(
            "must not appear as new technical trait names",
            prompt,
        )
        self.assertIn(
            "Normally cover each selected trait before reusing a trait",
            prompt,
        )
        self.assertIn(
            "Avoid near-duplicate wording",
            prompt,
        )

    def test_goal_focused_alias_uses_approved_goal_focused_definition(self):
        owner = SimpleNamespace(
            selected_personality_traits=[
                "Achievement Striving"
            ],
            sova_activities=[
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
                    ],
                }
            ],
        )

        prompt = _build_personality_definition_grounding(
            owner=owner,
            personality_results=[
                {
                    "name": "Achievement Striving",
                    "sten": 8,
                },
            ],
            language_code="en",
        )

        self.assertIn(
            "APPROVED TRAIT: Goal-focused",
            prompt,
        )
        self.assertIn(
            TRAIT_PROFILE_CONTENT[
                "Goal-focused"
            ]["high_pole"]["en"],
            prompt,
        )
        self.assertIn(
            INDICATOR_PROFILE_CONTENT[
                "Competitive"
            ]["score_texts"]["3"]["en"],
            prompt,
        )

    def test_competency_selection_does_not_mix_in_parent_trait_grounding(self):
        owner = self._owner(
            selected_traits=["competency::Teamwork"]
        )

        prompt = _build_personality_definition_grounding(
            owner=owner,
            personality_results=[
                {"name": "Cooperative", "sten": 7},
            ],
            language_code="en",
        )

        self.assertEqual(prompt, "")
