from django.test import SimpleTestCase

from apps.core.ai.personality_question_situational_language_policy import (
    _normalise_legacy_prompt_language,
    _normalise_visible_why_language,
    _situational_sten_band,
    _situational_sten_direction,
)


class PersonalityQuestionSituationalLanguagePolicyTests(SimpleTestCase):
    def test_sten_4_to_7_is_situational(self):
        for score in (4, 5, 6, 7):
            with self.subTest(score=score):
                self.assertEqual(
                    _situational_sten_band(score),
                    "situational",
                )
                self.assertEqual(
                    _situational_sten_direction(score),
                    "situational behavioural pattern",
                )

    def test_directional_bands_are_unchanged(self):
        self.assertEqual(_situational_sten_band(3), "low")
        self.assertEqual(_situational_sten_band(8), "high")
        self.assertEqual(
            _situational_sten_direction(3),
            "clearer low-side indication",
        )
        self.assertEqual(
            _situational_sten_direction(8),
            "clearer high-side indication",
        )

    def test_english_legacy_prompt_wording_is_replaced(self):
        prompt = (
            "STEN 4 to 7\n"
            "- may indicate a more mid-range or situational preference\n\n"
            "Mid-range results may sometimes indicate moderation, flexibility\n"
            "or greater context dependence.\n\n"
            "Selected evidence: Networking: more mid-range indication\n"
            "Skriv aldrig: mid-range"
        )

        result = _normalise_legacy_prompt_language(prompt)

        self.assertIn(
            "STEN 4 to 7\n- should be interpreted as a situational behavioural pattern",
            result,
        )
        self.assertIn(
            "Networking: situational behavioural pattern",
            result,
        )
        # Administrator prohibitions must remain intact rather than being
        # rewritten into the opposite instruction.
        self.assertIn("Skriv aldrig: mid-range", result)

    def test_swedish_legacy_prompt_wording_is_replaced(self):
        prompt = (
            "STEN 4 till 7\n"
            "- kan indikera en mer mellanhög eller situationsberoende preferens\n\n"
            "Mellanhöga resultat kan ibland indikera moderation, flexibilitet\n"
            "eller större situationsberoende."
        )

        result = _normalise_legacy_prompt_language(prompt)

        self.assertIn(
            "STEN 4 till 7\n- ska tolkas som ett situationsbaserat beteendemönster",
            result,
        )
        self.assertNotIn("mellanhög", result.casefold())

    def test_visible_why_removes_middle_language_in_swedish(self):
        why = (
            "Nätverkande ligger närmare mitten av kandidatens profil. "
            "Det gör området relevant att utforska."
        )

        result = _normalise_visible_why_language(why)

        self.assertIn("situationsbaserat", result.casefold())
        self.assertNotIn("mitten", result.casefold())
        self.assertNotIn("medelnivå", result.casefold())

    def test_visible_why_removes_mid_range_language_in_english(self):
        why = (
            "Networking sits closer to the middle of the candidate's profile. "
            "This mid-range indication is useful to explore."
        )

        result = _normalise_visible_why_language(why)

        self.assertIn("situational", result.casefold())
        self.assertNotIn("mid-range", result.casefold())
        self.assertNotIn("middle", result.casefold())
