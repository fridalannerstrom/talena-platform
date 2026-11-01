"""Ticket #366: customer-facing response styles and deterministic nuance states."""
import json
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from apps.reports.libraries.personality import profile_contrasts


TEMPLATE = "customer/processes/partials/candidate_insights/personality/_results.html"


class ResponseStylesUiTests(SimpleTestCase):
    def render_personality(self, *, language="sv", has_results=True,
                           has_response_style=True, contrasts=None, available=5):
        styles = ([{
            "key": "social_desirability",
            "title": "Social önskvärdhet" if language == "sv" else "Social Desirability",
            "available": True,
            "value": 5,
            "low_pole": "Vänster",
            "high_pole": "Höger",
            "scale_side": "left",
            "scale_strength": 2,
        }] if has_response_style else [])
        with override(language):
            return render_to_string(TEMPLATE, {
                "LANGUAGE_CODE": language,
                "candidate": SimpleNamespace(first_name="Alex"),
                "personality_profile": {"sections": []},
                "has_personality_results": has_results,
                "response_styles": styles,
                "response_style_side_segments": range(1, 6),
                "profile_contrast_analysis": {
                    "available_dimension_count": available,
                    "activated_contrasts": contrasts or [],
                },
            })

    def test_no_patterns_shows_helpful_neutral_state_in_swedish_and_english(self):
        sv = self.render_personality(language="sv")
        en = self.render_personality(language="en")
        self.assertIn('data-contrast-empty-state="no-patterns"', sv)
        self.assertIn("Inga särskilda mönster just nu", sv)
        self.assertIn("Det betyder inte att information saknas.", sv)
        self.assertIn("No particular patterns to highlight right now", en)
        self.assertIn("This does not mean information is missing.", en)
        for markup in (sv, en):
            self.assertNotIn('data-contrast-empty-state="unavailable"', markup)

    def test_no_personality_results_shows_distinct_unavailable_state(self):
        sv = self.render_personality(has_results=False, has_response_style=False, available=0)
        en = self.render_personality(language="en", has_results=False,
                                     has_response_style=False, available=0)
        self.assertIn("Resultat ännu inte tillgängligt", sv)
        self.assertIn("Results not yet available", en)
        self.assertIn('data-contrast-empty-state="unavailable"', sv)
        self.assertNotIn('data-contrast-empty-state="no-patterns"', sv)
        self.assertIn("Det finns ännu inget personlighetsresultat", sv)

    def test_insufficient_mapped_results_are_not_called_no_patterns(self):
        markup = self.render_personality(available=1)
        self.assertIn('data-contrast-empty-state="unavailable"', markup)

    def test_activated_catalog_contrasts_remain_visible_without_ai(self):
        contrast = {
            "id": "synthetic-catalog-pattern",
            "dimensions": [
                {"label": "Egenskap 1", "sten": 8, "graph_segments": [
                    {"score": 8, "selected": True, "filled_toward_midpoint": True},
                ]},
                {"label": "Egenskap 2", "sten": 2, "graph_segments": [
                    {"score": 2, "selected": True, "filled_toward_midpoint": True},
                ]},
            ],
            "hypothesis": "En fördefinierad möjlig nyans.",
        }
        markup = self.render_personality(contrasts=[contrast])
        self.assertIn('data-profile-contrast-id="synthetic-catalog-pattern"', markup)
        self.assertIn("En fördefinierad möjlig nyans.", markup)
        self.assertNotIn("data-contrast-empty-state=", markup)

    def test_no_sten_labels_or_removed_ai_sections_in_rendered_html(self):
        markup = self.render_personality()
        self.assertNotIn("STEN", markup)
        self.assertNotIn("Vad innebär detta för", markup)
        self.assertNotIn("What does this mean for", markup)
        self.assertNotIn("Om konsekvensskala och värderingsspridning", markup)
        self.assertNotIn("About Consequence Scale and Ratings Spread", markup)
        self.assertNotIn('data-response-style-guidance-root', markup)
        self.assertNotIn('data-guidance-stream-url', markup)
        self.assertIn("5/10", markup)

    def test_obsolete_auto_streaming_is_removed_but_interview_tools_remain(self):
        source = (Path(settings.BASE_DIR) /
                  "templates/customer/processes/process_base.html").read_text(encoding="utf-8")
        self.assertNotIn('window.__talenaResponseStyleGuidanceLoaded', source)
        self.assertNotIn('[data-response-style-guidance-root]', source)
        interview = (Path(settings.BASE_DIR) /
                     "templates/customer/processes/partials/candidate_insights/tabs/_final_output.html"
                     ).read_text(encoding="utf-8")
        self.assertIn("data-pre-interview-generate", interview)
        self.assertIn("data-response-style-interview-guidance", interview)

    def test_report_labels_do_not_expose_sten_or_change_score_scale(self):
        content = json.loads((Path(settings.BASE_DIR) /
            "apps/reports/data/derailment_report.json").read_text(encoding="utf-8"))
        for language in ("sv", "en"):
            report = content[language]
            for key in ("score_label", "scale_label", "empty_body"):
                self.assertNotIn("STEN", report[key])
            self.assertIn("1–10", report["scale_label"])
        self.assertEqual(profile_contrasts.LOW_MAXIMUM, 3)
        self.assertEqual(profile_contrasts.HIGH_MINIMUM, 8)
