"""Ticket #436: one MQ library, top-three grounding, real PQ texts, no new AI flow."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.decision_support import _build_wellbeing_tips_reference_evidence
from apps.core.ai.motivation_practical_advice import get_motivation_practical_advice


class WellbeingAdviceReferenceTests(SimpleTestCase):
    def test_approved_library_has_twenty_factors_and_four_tips_in_both_languages(self):
        library = get_motivation_practical_advice()
        self.assertEqual(set(library), {"sv", "en"})
        self.assertEqual(len(library["sv"]), 20)
        self.assertEqual(set(library["sv"]), set(library["en"]))
        for language in ("sv", "en"):
            for advice in library[language].values():
                self.assertEqual(len(advice["do"]), 2)
                self.assertEqual(len(advice["avoid"]), 2)

    def test_approved_swedish_reference_samples_are_unchanged(self):
        library = get_motivation_practical_advice()["sv"]
        self.assertEqual(
            library["variety"]["do"][0],
            "Erbjud en blandning av arbetsuppgifter, projekt och utmaningar.",
        )
        self.assertEqual(
            library["customer_service"]["avoid"][1],
            "Enbart mäta effektivitet utan att uppmärksamma kundupplevelsen.",
        )
        self.assertEqual(
            library["people_development"]["do"][0],
            "Ge möjlighet att coacha, stötta eller introducera kollegor.",
        )

    @patch("apps.core.ai.personality_ai_evidence.build_owner_personality_ai_evidence")
    @patch("apps.core.ai.motivation_interpretation._owner_motivation_results")
    def test_only_top_three_mq_tips_and_scored_pq_indicators_reach_ai(
        self, motivation, personality
    ):
        owner = SimpleNamespace()
        motivation.return_value = [
            {"key": "variety", "name": "Variety", "score": 3.2},
            {"key": "attachment", "name": "Attachment", "score": 4.9},
            {"key": "risk", "name": "Risk", "score": 4.1},
            {"key": "learning", "name": "Learning", "score": 4.6},
        ]
        personality.return_value = [
            {
                "label": "Ordning",
                "name": "Orderliness",
                "indicators": [{
                    "name": "Planning",
                    "label": "Planering",
                    "sten": 8,
                    "text": "Godkänd text för kandidatens faktiska STEN-band.",
                }],
            },
        ]
        rendered = _build_wellbeing_tips_reference_evidence(
            owner, language_code="sv"
        )
        self.assertLess(rendered.index("Anknytning"), rendered.index("Lärande"))
        self.assertLess(rendered.index("Lärande"), rendered.index("Risk"))
        self.assertNotIn("Variety", rendered)
        self.assertNotIn("Erbjud en blandning", rendered)
        self.assertEqual(rendered.count("   DO:"), 6)
        self.assertEqual(rendered.count("   AVOID:"), 6)
        self.assertIn("Planering (STEN 8/10): Godkänd text", rendered)
        personality.assert_called_once_with(owner, language_code="sv")

    @patch("apps.core.ai.personality_ai_evidence.build_owner_personality_ai_evidence")
    @patch("apps.core.ai.motivation_interpretation._owner_motivation_results")
    def test_missing_assessments_do_not_create_fake_references(
        self, motivation, personality
    ):
        motivation.return_value = []
        personality.return_value = []
        rendered = _build_wellbeing_tips_reference_evidence(
            SimpleNamespace(), language_code="en"
        )
        self.assertIn("No authoritative MQ top-three results available", rendered)
        self.assertIn("No scored PQ indicator evidence available", rendered)
        self.assertEqual(rendered.count("   DO:"), 0)
        self.assertEqual(rendered.count("   AVOID:"), 0)
