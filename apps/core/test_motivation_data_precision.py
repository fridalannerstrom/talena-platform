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
from apps.processes.views import build_motivation_insight_section


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

    def test_motivation_summary_ranks_precise_top_and_bottom_three(self):
        insights = build_motivation_insight_section(
            [
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
                {
                    "competency": "Ethics",
                    "stive": 3.33,
                    "stive_rounded": 3,
                },
                {
                    "competency": "Enjoyment",
                    "stive": 4.11,
                    "stive_rounded": 4,
                },
                {
                    "competency": "Risk",
                    "stive": 4.19,
                    "stive_rounded": 4,
                },
            ]
        )

        self.assertEqual(
            [item["name"] for item in insights["motivators"]],
            ["Risk", "Enjoyment", "Ethics"],
        )
        self.assertEqual(
            [item["name"] for item in insights["less_central_drivers"]],
            ["Creativity", "Curiosity", "Variety"],
        )
        self.assertTrue(insights["has_rose_highlights"])
        marked = {
            item["name"]: item.get("rose_highlight")
            for item in insights["chart_items"]
            if item.get("rose_highlight")
        }
        self.assertEqual(marked, {
            "Risk": "top", "Enjoyment": "top", "Ethics": "top",
            "Creativity": "bottom", "Curiosity": "bottom", "Variety": "bottom",
        })
        self.assertEqual(
            sorted(item["name"] for item in insights["motivators"]),
            sorted(name for name, rank in marked.items() if rank == "top"),
        )
        self.assertEqual(
            sorted(item["name"] for item in insights["less_central_drivers"]),
            sorted(name for name, rank in marked.items() if rank == "bottom"),
        )

    def test_even_or_incomplete_motivation_profile_has_no_highlighted_top_bottom(self):
        factors = ["Creativity", "Curiosity", "Variety", "Ethics",
                   "Enjoyment", "Risk"]
        even = build_motivation_insight_section([
            {"competency": name, "stive": 3.0}
            for name in factors
        ])
        self.assertFalse(even["has_profile_difference"])
        self.assertFalse(even["has_rose_highlights"])
        self.assertFalse(any(
            item.get("rose_highlight") for item in even["chart_items"]
        ))

        # Fewer than six scored factors cannot form disjoint sets of three.
        partial = build_motivation_insight_section([
            {"competency": name, "stive": 1.2 + index * 0.7}
            for index, name in enumerate(factors[:5])
        ])
        self.assertTrue(partial["has_profile_difference"])
        self.assertFalse(partial["has_rose_highlights"])
        self.assertFalse(any(
            item.get("rose_highlight") for item in partial["chart_items"]
        ))

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
        self.assertNotIn("stive 2\n", "\n".join(score_parts))

    def test_personality_only_does_not_create_motivation_results(self):
        owner = SimpleNamespace(
            sova_activities=[
                {
                    "activity": "Personality Questionnaire",
                    "competencies": [
                        {
                            "competency": "Creativity",
                            "sten": 8,
                            "sten_rounded": 8,
                        },
                    ],
                },
            ],
        )

        self.assertEqual(
            extract_motivation_results(owner),
            [],
        )

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
