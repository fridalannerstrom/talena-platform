from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.personality_ai_evidence import (
    build_owner_personality_ai_evidence,
    build_personality_ai_evidence,
    build_personality_ai_evidence_text,
    canonical_parent_trait_name,
)
from apps.reports.libraries.personality.builder import (
    get_localized_text,
    get_score_band,
)
from apps.reports.libraries.personality.content import (
    INDICATOR_PROFILE_CONTENT,
    TRAIT_PROFILE_CONTENT,
)


class PersonalityAIEvidenceTests(SimpleTestCase):
    def _cooperative_rows(self):
        return [
            {"name": "Cooperative", "sten": 6},
            {"name": "Sensitivity", "sten": 5},
            {"name": "Teamwork", "sten": 8},
            {"name": "Agreeableness", "sten": 3},
        ]

    def test_evidence_builds_same_indicator_band_text_as_result_summary(self):
        evidence = build_personality_ai_evidence(
            self._cooperative_rows(),
            language_code="en",
        )

        self.assertEqual(len(evidence), 1)
        item = evidence[0]

        self.assertEqual(item["name"], "Cooperative")
        self.assertEqual(
            item["label"],
            TRAIT_PROFILE_CONTENT["Cooperative"]["label_en"],
        )
        self.assertEqual(item["sten"], 6)
        self.assertEqual(len(item["indicators"]), 3)

        expected_sentences = []
        for name, sten in (
            ("Sensitivity", 5),
            ("Teamwork", 8),
            ("Agreeableness", 3),
        ):
            expected = get_localized_text(
                INDICATOR_PROFILE_CONTENT[name]["score_texts"][
                    get_score_band(sten)
                ],
                "en",
            ).strip()
            expected_sentences.append(
                expected if expected.endswith((".", "!", "?")) else expected + "."
            )

        self.assertEqual(
            item["summary"],
            " ".join(expected_sentences),
        )

    def test_swedish_evidence_uses_swedish_result_texts(self):
        evidence = build_personality_ai_evidence(
            self._cooperative_rows(),
            language_code="sv-SE",
        )

        item = evidence[0]
        sensitivity = item["indicators"][0]

        self.assertEqual(
            item["label"],
            TRAIT_PROFILE_CONTENT["Cooperative"]["label_sv"],
        )
        self.assertEqual(
            sensitivity["label"],
            INDICATOR_PROFILE_CONTENT["Sensitivity"]["label_sv"],
        )
        self.assertEqual(
            sensitivity["text"],
            get_localized_text(
                INDICATOR_PROFILE_CONTENT["Sensitivity"]["score_texts"]["4_7"],
                "sv",
            ),
        )

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

    def test_unknown_indicator_and_response_style_do_not_become_parent_traits(self):
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

    def test_include_traits_limits_payload(self):
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

    def test_active_owner_extraction_includes_indicator_nuance(self):
        owner = SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=[
                {
                    "activity": "Personality Profile",
                    "competencies": [
                        {"competency": "Cooperative", "sten": 6},
                        {"competency": "Sensitivity", "sten": 5},
                        {"competency": "Teamwork", "sten": 8},
                        {"competency": "Agreeableness", "sten": 3},
                    ],
                }
            ],
        )

        evidence = build_owner_personality_ai_evidence(
            owner,
            language_code="en",
        )

        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["name"], "Cooperative")
        self.assertEqual(len(evidence[0]["indicators"]), 3)
        self.assertTrue(evidence[0]["summary"])

    def test_rendered_contract_uses_result_summary_not_generic_poles(self):
        text = build_personality_ai_evidence_text(
            self._cooperative_rows(),
            language_code="en",
            include_indicator_details=True,
        )

        self.assertIn(
            "TALENA CANDIDATE-SPECIFIC PERSONALITY RESULT EVIDENCE",
            text,
        )
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", text)
        self.assertIn("UNDERLYING INDICATOR NUANCE", text)
        self.assertIn("Sensitivity", text)
        self.assertIn("STEN 4–7", text)
        self.assertIn("situational", text)
        self.assertNotIn("APPROVED LOW POLE", text)
        self.assertNotIn("APPROVED HIGH POLE", text)
        self.assertIn("not proof of fixed behaviour", text)
