from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.personality_ai_evidence import (
    build_owner_personality_ai_evidence,
    build_personality_ai_evidence,
    build_personality_ai_evidence_text,
    canonical_parent_trait_name,
)
from apps.reports.libraries.personality.content import TRAIT_PROFILE_CONTENT


class PersonalityAIEvidenceTests(SimpleTestCase):
    def test_english_evidence_uses_approved_trait_content(self):
        evidence = build_personality_ai_evidence(
            [{"name": "Analytical", "sten": 3}],
            language_code="en",
        )

        self.assertEqual(len(evidence), 1)
        item = evidence[0]
        approved = TRAIT_PROFILE_CONTENT["Analytical"]

        self.assertEqual(item["name"], "Analytical")
        self.assertEqual(item["label"], approved["label_en"])
        self.assertEqual(item["sten"], 3)
        self.assertEqual(item["low_pole"], approved["low_pole"]["en"])
        self.assertEqual(item["high_pole"], approved["high_pole"]["en"])

    def test_swedish_evidence_uses_swedish_label_and_poles(self):
        evidence = build_personality_ai_evidence(
            [{"competency": "Analytical", "sten_rounded": 8}],
            language_code="sv-SE",
        )

        item = evidence[0]
        approved = TRAIT_PROFILE_CONTENT["Analytical"]

        self.assertEqual(item["label"], approved["label_sv"])
        self.assertEqual(item["low_pole"], approved["low_pole"]["sv"])
        self.assertEqual(item["high_pole"], approved["high_pole"]["sv"])

    def test_achievement_striving_alias_maps_to_goal_focused(self):
        self.assertEqual(
            canonical_parent_trait_name("Achievement Striving"),
            "Goal-focused",
        )

        evidence = build_personality_ai_evidence(
            [{"name": "Achievement Striving", "sten": 9}],
            language_code="en",
        )

        self.assertEqual(evidence[0]["name"], "Goal-focused")
        self.assertEqual(
            evidence[0]["source_name"],
            "Achievement Striving",
        )

    def test_unknown_indicators_and_response_styles_get_no_parent_definition(self):
        evidence = build_personality_ai_evidence(
            [
                {"name": "Sensitivity", "sten": 9},
                {"name": "Social desirability", "sten": 6},
                {"name": "Analytical", "sten": 4},
            ],
            language_code="en",
        )

        self.assertEqual(
            [item["name"] for item in evidence],
            ["Analytical"],
        )

    def test_include_traits_limits_definition_payload(self):
        evidence = build_personality_ai_evidence(
            [
                {"name": "Analytical", "sten": 4},
                {"name": "Creativity", "sten": 8},
            ],
            language_code="en",
            include_traits=["Creativity"],
        )

        self.assertEqual(
            [item["name"] for item in evidence],
            ["Creativity"],
        )

    def test_active_owner_extraction_keeps_only_parent_traits(self):
        owner = SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=[
                {
                    "activity": "Personality Profile",
                    "competencies": [
                        {"competency": "Analytical", "sten": 3},
                        {"competency": "Sensitivity", "sten": 9},
                    ],
                }
            ],
        )

        evidence = build_owner_personality_ai_evidence(
            owner,
            language_code="en",
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["name"], "Analytical")
        self.assertEqual(evidence[0]["sten"], 3)

    def test_rendered_contract_preserves_evidence_boundaries(self):
        text = build_personality_ai_evidence_text(
            [{"name": "Structured", "sten": 7}],
            language_code="en",
        )

        self.assertIn(
            "TALENA APPROVED PERSONALITY DEFINITION EVIDENCE",
            text,
        )
        self.assertIn("CANDIDATE RESULT: STEN 7 of 10", text)
        self.assertIn("APPROVED LOW POLE", text)
        self.assertIn("APPROVED HIGH POLE", text)
        self.assertIn("not, by itself, evidence of competence", text)
        self.assertIn("must not rewrite the meaning of the trait", text)
