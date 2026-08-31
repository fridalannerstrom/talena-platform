from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai import personality_questions
from apps.core.ai.candidate_question_grounding_policy import (
    _cognitive_grounding_instruction,
    _fallback_personality_questions,
    _motivation_grounding_instruction,
    _personality_grounding_instruction,
)
from apps.processes.interview_config import get_interview_section_config


class CandidateQuestionGroundingPolicyTests(SimpleTestCase):
    def test_personality_grounding_uses_selected_trait_score_direction(self):
        owner = SimpleNamespace(
            selected_personality_traits=["Cooperative"],
        )
        prompt = _personality_grounding_instruction(
            owner,
            [
                {"name": "Cooperative", "sten": 9},
                {"name": "Analytical", "sten": 2},
            ],
        )

        self.assertIn("Cooperative: STEN 9 of 10 (high)", prompt)
        self.assertNotIn("Analytical: STEN 2", prompt)
        self.assertIn("opposite result pattern", prompt)

    def test_motivation_grounding_preserves_profile_shape(self):
        prompt = _motivation_grounding_instruction(
            [
                {"name": "Learning", "score": 5},
                {"name": "Recognition", "score": 1},
                {"name": "Autonomy", "score": 3},
            ]
        )

        self.assertIn("Learning: STIVE 5 of 5 (prominent)", prompt)
        self.assertIn("Recognition: STIVE 1 of 5 (less central)", prompt)
        self.assertIn("Autonomy: STIVE 3 of 5 (mid-range)", prompt)
        self.assertIn("factor pattern were reversed", prompt)

    def test_cognitive_grounding_uses_percentile_pattern(self):
        prompt = _cognitive_grounding_instruction(
            [
                {"label": "Logical reasoning", "percentile": 92},
                {"label": "Numerical reasoning", "percentile": 18},
                {"label": "Verbal reasoning", "percentile": 55},
            ]
        )

        self.assertIn(
            "Logical reasoning: percentile 92 (very high relative to the reference group)",
            prompt,
        )
        self.assertIn(
            "Numerical reasoning: percentile 18 (low relative to the reference group)",
            prompt,
        )
        self.assertIn(
            "Verbal reasoning: percentile 55 (within the typical range)",
            prompt,
        )
        self.assertIn("Do not infer personality, motivation or work ethic", prompt)

    def test_same_personality_selection_gets_different_fallback_angle_by_score(self):
        language_token = personality_questions._personality_questions_language.set("en")
        try:
            low = _fallback_personality_questions(
                selected_traits=["Cooperative"],
                personality_results=[{"name": "Cooperative", "sten": 2}],
            )
            high = _fallback_personality_questions(
                selected_traits=["Cooperative"],
                personality_results=[{"name": "Cooperative", "sten": 9}],
            )
        finally:
            personality_questions._personality_questions_language.reset(language_token)

        expected_count = int(
            get_interview_section_config("personality")["question_count"]
        )

        self.assertEqual(len(low["items"]), expected_count)
        self.assertEqual(len(high["items"]), expected_count)
        self.assertNotEqual(
            low["items"][0]["question"],
            high["items"][0]["question"],
        )
        self.assertIn("low-side indication", low["items"][0]["why"])
        self.assertIn("high-side indication", high["items"][0]["why"])

    def test_personality_fallback_respects_swedish_language(self):
        language_token = personality_questions._personality_questions_language.set("sv")
        try:
            result = _fallback_personality_questions(
                selected_traits=["Cooperative"],
                personality_results=[{"name": "Cooperative", "sten": 9}],
            )
        finally:
            personality_questions._personality_questions_language.reset(language_token)

        self.assertTrue(result["items"][0]["question"].startswith("Berätta"))
        self.assertIn("hög indikation", result["items"][0]["why"])

    def test_competency_fallback_keeps_token_technical_and_uses_profile_evidence(self):
        owner = SimpleNamespace(
            sova_activities=[
                {
                    "activity": "Personality Assessment",
                    "competencies": [
                        {
                            "competency": "Cooperative",
                            "sten_rounded": 9,
                        }
                    ],
                }
            ],
        )
        selected_token = "competency::Teamwork"

        language_token = personality_questions._personality_questions_language.set("en")
        try:
            result = _fallback_personality_questions(
                owner=owner,
                selected_traits=[selected_token],
                personality_results=[{"name": "Cooperative", "sten": 9}],
            )
        finally:
            personality_questions._personality_questions_language.reset(language_token)

        first = result["items"][0]

        self.assertEqual(first["traits"], [selected_token])
        self.assertNotIn("competency::", first["question"])
        self.assertIn("Teamwork", first["question"])
        self.assertIn("Cooperative", first["why"])
        self.assertIn("supporting personality signal", first["why"])
