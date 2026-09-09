from django.test import SimpleTestCase

from apps.core.ai.motivation_interpretation import (
    MOTIVATION_DEFINITIONS,
    _motivation_definition_key,
)


class MotivationFactorDefinitionTests(SimpleTestCase):
    def test_all_canonical_motivation_factors_have_definitions(self):
        expected_keys = {
            "attachment",
            "customer_service",
            "work_life_balance",
            "people_development",
            "stability",
            "authority",
            "acquisition",
            "independence",
            "recognition",
            "making_a_difference",
            "achievement",
            "quality",
            "learning",
            "ethics",
            "commercial_focus",
            "curiosity",
            "creativity",
            "enjoyment",
            "variety",
            "risk",
        }

        self.assertEqual(
            set(MOTIVATION_DEFINITIONS),
            expected_keys,
        )
        self.assertTrue(all(MOTIVATION_DEFINITIONS.values()))

    def test_legacy_and_swedish_names_resolve_to_canonical_factors(self):
        aliases = {
            "Variation": "variety",
            "variation": "variety",
            "Autonomy": "independence",
            "Självständighet": "independence",
            "Commercial Value": "commercial_focus",
            "Kommersiellt fokus": "commercial_focus",
            "Kundservice": "customer_service",
            "Människors utveckling": "people_development",
            "Work-life balance": "work_life_balance",
            "Anknytning": "attachment",
        }

        for name, expected in aliases.items():
            with self.subTest(name=name):
                self.assertEqual(
                    _motivation_definition_key(name),
                    expected,
                )
