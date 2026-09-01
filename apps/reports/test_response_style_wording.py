from django.test import SimpleTestCase

from apps.reports.libraries.personality.response_styles import (
    build_response_style_results,
)


class ResponseStyleWordingTests(SimpleTestCase):
    def setUp(self):
        self.results = [
            {"competency": "Social Desirability", "sten_rounded": 5},
            {"competency": "Fillers", "sten_rounded": 5},
            {"competency": "Reliability", "sten_rounded": 5},
        ]

    def test_approved_swedish_titles_and_poles(self):
        styles = build_response_style_results(self.results, language="sv")
        by_key = {style["key"]: style for style in styles}

        self.assertEqual(
            by_key["social_desirability"]["title"],
            "Social önskvärdhet",
        )
        self.assertEqual(
            by_key["social_desirability"]["low_pole"],
            "Tenderar att svara på ett självkritiskt sätt. Kan ha tydligare preferenser än vad resultaten antyder",
        )
        self.assertEqual(
            by_key["social_desirability"]["high_pole"],
            "Framställde sig själv på ett positivt sätt. Kan ha preferenser som inte är lika tydliga som resultaten antyder.",
        )

        self.assertEqual(by_key["profile_spread"]["title"], "Konsekvensskala")
        self.assertEqual(
            by_key["profile_spread"]["low_pole"],
            "Svaren visar mindre differentiering mellan egenskaperna vilket kan bero på mindre konsekvens eller brist på självinsikt",
        )
        self.assertEqual(
            by_key["profile_spread"]["high_pole"],
            "Svaren visar tydliga styrkor och utvecklingsbehov, profilen visar ett brett utbud av poäng över egenskaperna",
        )

        self.assertEqual(by_key["ratings_spread"]["title"], "Värderingsspridning")
        self.assertEqual(
            by_key["ratings_spread"]["low_pole"],
            "Svaren på frågeformuläret visar mindre användning av extrema alternativ, tendens att välja ett smalt urval av betyg",
        )
        self.assertEqual(
            by_key["ratings_spread"]["high_pole"],
            "Svaren på enkäten visar tydlig differentiering i svaren; mer användning av extrema alternativ",
        )

    def test_approved_english_titles_and_poles(self):
        styles = build_response_style_results(self.results, language="en")
        by_key = {style["key"]: style for style in styles}

        self.assertEqual(by_key["social_desirability"]["title"], "Social Desirability")
        self.assertEqual(
            by_key["social_desirability"]["low_pole"],
            "Tended to respond self-critically; preferences may be more accentuated than the results suggest",
        )
        self.assertEqual(
            by_key["social_desirability"]["high_pole"],
            "Presented themselves positively; preferences may be less accentuated than the results suggest",
        )

        self.assertEqual(by_key["profile_spread"]["title"], "Profile Spread")
        self.assertEqual(
            by_key["profile_spread"]["low_pole"],
            "Responses show less differentiation across the traits which may be due to less consistency or lack of self-insight",
        )
        self.assertEqual(
            by_key["profile_spread"]["high_pole"],
            "Responses show clear strengths and development needs, profile demonstrates a wide range of scores across the traits",
        )

        self.assertEqual(by_key["ratings_spread"]["title"], "Ratings Spread")
        self.assertEqual(
            by_key["ratings_spread"]["low_pole"],
            "Responses to the questionnaire show less use of extreme options, tendency to select narrow range of ratings",
        )
        self.assertEqual(
            by_key["ratings_spread"]["high_pole"],
            "Responses to the questionnaire show clear differentiation in responses; more use of extreme options",
        )
