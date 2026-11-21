"""Neutral visual cues for the shared Response styles / Communication strategy view."""
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.reports.libraries.personality.communication_guidance import (
    build_static_communication_guidance,
)
from apps.reports.libraries.personality.content import TRAIT_PROFILE_CONTENT

SHARED_TEMPLATE = (
    "customer/processes/partials/candidate_insights/"
    "_static_communication_guidance.html"
)


class ResponseStyleVisualCueTests(SimpleTestCase):
    def _render(self, guidance):
        return render_to_string(
            SHARED_TEMPLATE, {"static_communication_guidance": guidance}
        )

    def test_social_desirability_three_bands_match_the_existing_thresholds(self):
        cases = [
            (1, "low", "Mer självkritisk", "More self-critical"),
            (2, "low", "Mer självkritisk", "More self-critical"),
            (3, "low", "Mer självkritisk", "More self-critical"),
            (4, "middle", "Balanserad", "Balanced"),
            (7, "middle", "Balanserad", "Balanced"),
            (8, "high", "Mer positiv självpresentation", "More positive self-presentation"),
            (9, "high", "Mer positiv självpresentation", "More positive self-presentation"),
            (10, "high", "Mer positiv självpresentation", "More positive self-presentation"),
        ]
        for score, band, sv_label, en_label in cases:
            for lang, label in (("sv", sv_label), ("en", en_label)):
                with self.subTest(score=score, language=lang):
                    guidance = build_static_communication_guidance(
                        None,
                        [{"key": "social_desirability", "available": True, "value": score}],
                        selected_traits=[],
                        language=lang,
                    )
                    self.assertEqual(guidance["social_desirability_visual_band"], band)
                    self.assertEqual(guidance["social_desirability_visual_label"], label)
                    html = self._render(guidance)
                    self.assertIn('response-style-result-icon--social', html)
                    self.assertIn(f'data-social-desirability-band="{band}"', html)
                    self.assertIn(label, html)
                    self.assertNotIn('data-static-profile-status="clear"', html)
                    self.assertNotIn('data-static-profile-status="middle"', html)
                    self.assertNotIn("STEN", html)

    def test_profile_headings_have_distinct_icons_in_both_languages(self):
        selected = list(TRAIT_PROFILE_CONTENT)[:8]
        cases = [
            ("middle", [4, 5, 6, 7, 1, 2, 9, 10], "Situationsbaserad profil", "Situational profile"),
            ("clear", [1, 2, 3, 8, 9, 4, 5, 7], "Tydlig profil", "Clear profile"),
        ]
        for status, scores, sv_title, en_title in cases:
            profile = {"sections": [{"traits": [
                {"name": name, "sten": score}
                for name, score in zip(selected, scores)
            ]}]}
            for lang, title in (("sv", sv_title), ("en", en_title)):
                with self.subTest(status=status, language=lang):
                    guidance = build_static_communication_guidance(
                        profile, [], language=lang, selected_traits=selected
                    )
                    self.assertEqual(guidance["profile_status"], status)
                    html = self._render(guidance)
                    self.assertIn(f'data-static-profile-status="{status}"', html)
                    self.assertIn(f'response-style-result-icon--{status}', html)
                    self.assertIn(title, html)
                    self.assertIn('aria-hidden="true"', html)
                    self.assertNotIn('data-social-desirability-band=', html)

    def test_missing_or_invalid_social_result_has_no_misleading_status_badge(self):
        for styles in (
            [], [{"key": "social_desirability", "available": False, "value": 2}],
            [{"key": "social_desirability", "available": True, "value": None}],
            [{"key": "social_desirability", "available": True, "value": 11}],
        ):
            with self.subTest(styles=styles):
                guidance = build_static_communication_guidance(
                    None, styles, selected_traits=[], language="sv"
                )
                self.assertEqual(guidance["social_desirability_visual_label"], "")
                self.assertEqual(guidance["social_desirability_visual_band"], "")
                self.assertNotIn('data-social-desirability-band=', self._render(guidance))

    def test_shared_css_is_loaded_in_both_customer_and_admin_shells(self):
        from pathlib import Path
        from django.conf import settings
        paths = (
            "templates/customer/processes/_process_header.html",
            "templates/admin/accounts/partials/_candidate_customer_styles.html",
        )
        for path in paths:
            with self.subTest(path=path):
                source = (Path(settings.BASE_DIR) / path).read_text(encoding="utf-8")
                self.assertIn("css/talena/pages/response-styles-icons.css", source)
