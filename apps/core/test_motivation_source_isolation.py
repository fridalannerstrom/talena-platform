from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.motivation_interpretation import (
    extract_motivation_results,
)


class MotivationSourceIsolationTests(SimpleTestCase):
    def test_personality_overlap_does_not_override_motivation_score(self):
        owner = SimpleNamespace(
            sova_activities=[
                {
                    "activity": "Personality Questionnaire",
                    "competencies": [
                        {
                            "competency": "Variation",
                            "stive": 4.8,
                            "stive_rounded": 5,
                        },
                    ],
                },
                {
                    "activity": "Motivation Questionnaire",
                    "competencies": [
                        {
                            "competency": "Variation",
                            "stive": 2.37,
                            "stive_rounded": 2,
                        },
                    ],
                },
            ],
        )

        results = extract_motivation_results(owner)

        self.assertEqual(
            results,
            [
                {
                    "name": "Variation",
                    "score": 2.37,
                    "definition": (
                        "Is motivated by a role that offers a lot of variety and the opportunity to work with many different things. Thrives in a diverse role with a mix of tasks and projects where they can focus their attention on different work demands and take advantage of their different skills."
                    ),
                }
            ],
        )
