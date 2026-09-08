from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.candidate_summary import _get_score_parts
from apps.core.ai.motivation_interpretation import (
    build_motivation_evidence_text,
    extract_motivation_results,
)
from apps.core.ai.personality_interpretation import (
    build_motivation_results_for_personality_owner,
)
from apps.reports.services.candidate_insights import (
    build_general_insight_input,
)


class MotivationDataPrecisionTests(SimpleTestCase):
    def test_motivation_extraction_isolated_from_personality_and_keeps_stive(self):
        owner = SimpleNamespace(
            sova_activities=[
                {
                    "activity": "Personality Questionnaire",
                    "competencies": [
                        {
                            "competency": "Creativity",
                            "sten": 8,
                            "sten_rounded": 8,
                            "stive": 4.8,
                            "stive_rounded": 5,
                        },
                    ],
                },
                {
                    "activity": "Motivation Questionnaire",
                    "competencies": [
                        {
                            "competency": "Creativity",
                            "stive": 2.37,
                            "stive_rounded": 2,
                        },
                        {
                            "competency": "Curiosity",
                            "stive": 2.49,
                            "stive_rounded": 2,
                        },
                        {
                            "competency": "Variety",
                            "stive": 2.51,
                            "stive_rounded": 3,
                        },
                    ],
                },
            ],
        )

        results = extract_motivation_results(owner)
        by_name = {
            item["name"]: item
            for item in results
        }

        self.assertEqual(
            set(by_name),
            {"Creativity", "Curiosity", "Variety"},
        )
        self.assertEqual(
            by_name["Creativity"]["score"],
            2.37,
        )

        evidence = build_motivation_evidence_text(results)

        self.assertIn(
            "Creativity: STIVE 2.37 of 5",
            evidence,
        )
        self.assertNotIn(
            "STIVE 4.8",
            evidence,
        )
        self.assertLess(
            evidence.index("Variety: STIVE 2.51"),
            evidence.index("Creativity: STIVE 2.37"),
        )

    def test_general_insight_input_ranks_unrounded_motivation_values(self):
        insight_input = build_general_insight_input(
            personality_competencies=[
                {
                    "competency": "Creativity",
                    "sten": 8,
                    "sten_rounded": 8,
                },
            ],
            motivation_competencies=[
                {
                    "competency": "Creativity",
                    "score": 2.49,
                    "stive": 2.49,
                    "stive_rounded": 2,
                },
                {
                    "competency": "Curiosity",
                    "score": 2.51,
                    "stive": 2.51,
                    "stive_rounded": 3,
                },
            ],
            verbal_percentile=None,
            logical_percentile=None,
            numerical_percentile=None,
        )

        motivation = insight_input["motivation"]

        self.assertEqual(
            motivation["all_scores"][0]["score"],
            2.49,
        )
        self.assertEqual(
            motivation["highest_scores"][0]["name"],
            "Curiosity",
        )
        self.assertEqual(
            motivation["lowest_scores"][0]["name"],
            "Creativity",
        )

    def test_ai_overview_score_parts_prefer_precise_stive(self):
        score_parts = _get_score_parts(
            {
                "sten": 8,
                "sten_rounded": 8,
                "stive": 2.37,
                "stive_rounded": 2,
            }
        )

        self.assertIn("stive 2.37", score_parts)
        self.assertNotIn("stive 2", score_parts)

    def test_personality_motivation_interaction_uses_precise_historical_stive(self):
        owner = SimpleNamespace(
            process=SimpleNamespace(is_historical=True),
        )

        with patch(
            "apps.processes.services.candidate_profile.build_historical_candidate_profile",
            return_value={
                "motivation_competencies": [
                    {
                        "name": "Creativity",
                        "stive": 2.37,
                        "stive_rounded": 2,
                    },
                ],
            },
        ):
            results = build_motivation_results_for_personality_owner(
                owner
            )

        self.assertEqual(
            results[0]["score"],
            2.37,
        )
