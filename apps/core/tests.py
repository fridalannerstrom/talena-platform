from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.motivation_interpretation import (
    build_motivation_evidence_text,
    extract_motivation_results,
)


class MotivationAIEvidenceTests(SimpleTestCase):
    def setUp(self):
        # Samma profil som kandidaten vi jämförde med SOVA-rapporten.
        self.expected_scores = {
            "Affiliation": 4,
            "Customer Service": 4,
            "Work-life Balance": 1,
            "People Development": 4,
            "Stability": 1,
            "Authority": 3,
            "Acquisition": 3,
            "Autonomy": 1,
            "Recognition": 1,
            "Making a Difference": 3,
            "Achievement": 4,
            "Quality": 2,
            "Learning": 2,
            "Ethics": 2,
            "Commercial Value": 4,
            "Curiosity": 1,
            "Creativity": 2,
            "Enjoyment": 4,
            "Variety": 5,
            "Risk": 3,
        }

        self.invitation = SimpleNamespace(
            sova_activities=[
                {
                    "activity": "Motivation Questionnaire",
                    "competencies": [
                        {
                            "competency": name,
                            "stive_rounded": score,
                        }
                        for name, score in self.expected_scores.items()
                    ],
                }
            ]
        )

    def test_extracts_correct_motivation_scores_for_ai(self):
        results = extract_motivation_results(
            self.invitation
        )

        actual_scores = {
            item["name"]: item["score"]
            for item in results
        }

        self.assertEqual(
            actual_scores,
            self.expected_scores,
        )

    def test_ai_evidence_contains_correct_scores(self):
        results = extract_motivation_results(
            self.invitation
        )

        evidence = build_motivation_evidence_text(
            results
        )

        for name, score in self.expected_scores.items():
            self.assertIn(
                f"{name}: STIVE {score} of 5",
                evidence,
            )

    def test_ai_receives_correct_scale_interpretation(self):
        results = extract_motivation_results(
            self.invitation
        )

        evidence = build_motivation_evidence_text(
            results
        )

        self.assertIn(
            "A higher score means that the factor is more likely to be "
            "a prominent source of motivation",
            evidence,
        )

        self.assertIn(
            "A lower score means that the factor is less central",
            evidence,
        )

        self.assertIn(
            "A low score does NOT mean poor performance.",
            evidence,
        )

        self.assertIn(
            "A low score does NOT mean low ability or competence.",
            evidence,
        )

    def test_ai_receives_factor_definitions(self):
        results = extract_motivation_results(
            self.invitation
        )

        evidence = build_motivation_evidence_text(
            results
        )

        self.assertIn(
            "Affiliation: STIVE 4 of 5",
            evidence,
        )
        self.assertIn(
            "Meaning: Social interaction, support and a sense of belonging at work.",
            evidence,
        )

        self.assertIn(
            "Work-life Balance: STIVE 1 of 5",
            evidence,
        )
        self.assertIn(
            "Score meaning: Less central motivational driver.",
            evidence,
        )

        self.assertIn(
            "Variety: STIVE 5 of 5",
            evidence,
        )
        self.assertIn(
            "Score meaning: More prominent motivational driver.",
            evidence,
        )