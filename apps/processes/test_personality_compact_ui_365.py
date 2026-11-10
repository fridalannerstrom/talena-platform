"""Tickets #365/#424/#425: personality scales, contrast and trait graph shading."""
import re
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from apps.reports.libraries.personality.builder import build_graph_segments


class PersonalityCompactUiTests(SimpleTestCase):
    def _render(self, language="sv", score=4):
        trait = {
            "label": "Samarbete" if language == "sv" else "Cooperation",
            "low_pole": "Självständigt arbete",
            "high_pole": "Arbete med andra",
            "graph_segments": build_graph_segments(score),
            "summary": "Resultatsammanfattning.",
            "indicators": [],
        }
        with override(language):
            return render_to_string(
                "customer/processes/partials/candidate_insights/personality/_results.html",
                {
                    "LANGUAGE_CODE": language,
                    "candidate": SimpleNamespace(first_name="Alex"),
                    "personality_profile": {"sections": [
                        {"section_name": "Personality", "traits": [trait]},
                    ]},
                    "has_personality_results": True,
                    "response_styles": [{
                        "key": "social_desirability",
                        "title": "Social önskvärdhet",
                        "available": True,
                        "value": 1,
                        "low_pole": "Vänster",
                        "high_pole": "Höger",
                        "scale_side": "left",
                        "scale_strength": 5,
                    }],
                    "response_style_side_segments": range(1, 6),
                    "profile_contrast_analysis": {
                        "available_dimension_count": 2,
                        "activated_contrasts": [],
                    },
                },
            )

    def test_all_ten_source_values_fill_from_midpoint(self):
        for score in range(1, 11):
            with self.subTest(score=score):
                segments = build_graph_segments(score)
                self.assertEqual(len(segments), 10)
                expected = (list(range(score, 6)) if score <= 5
                            else list(range(6, score + 1)))
                filled = [s["score"] for s in segments if s["filled_toward_midpoint"]]
                selected = [s["score"] for s in segments if s["selected"]]
                self.assertEqual(filled, expected)
                self.assertEqual(selected, [score])
        self.assertEqual([s["score"] for s in build_graph_segments(4)
                          if s["filled_toward_midpoint"]], [4, 5])
        self.assertEqual([s["score"] for s in build_graph_segments(7)
                          if s["filled_toward_midpoint"]], [6, 7])

    def test_detailed_graph_has_center_axis_and_filled_css_classes(self):
        html = self._render(score=4)
        self.assertIn('class="personality-graph__center-line"', html)
        # The detailed graph renders before the quick overview.
        graph = html.split('class="personality-graph__bars"', 1)[1].split(
            'class="personality-graph__axis"', 1
        )[0]
        filled = re.findall(
            r'class="\s*personality-graph__segment\s+personality-graph__segment--filled[^"]*"\s+data-score="(\d+)"',
            graph,
        )
        self.assertEqual(filled, ["4", "5"])
        self.assertNotIn("STEN", graph)
        html7 = self._render(score=7)
        graph7 = html7.split('class="personality-graph__bars"', 1)[1].split(
            'class="personality-graph__axis"', 1
        )[0]
        filled7 = re.findall(
            r'class="\s*personality-graph__segment\s+personality-graph__segment--filled[^"]*"\s+data-score="(\d+)"',
            graph7,
        )
        self.assertEqual(filled7, ["6", "7"])

    def test_tabs_and_scores_in_both_languages(self):
        sv, en = self._render(language="sv"), self._render(language="en")
        self.assertIn("Karaktärsdrags- och indikatorprofilen", sv)
        self.assertIn("Karaktärsdragsprofilen", sv)
        self.assertIn("Trait and indicator profile", en)
        self.assertIn("Trait profile", en)
        for html in (sv, en):
            self.assertNotIn("Egenskapsprofilen", html)
            self.assertNotIn("Egenskaps- och indikatorprofilen", html)
            self.assertNotIn("response-style-item__result", html)
            self.assertIn("response-style-scale", html)
            self.assertIn("personality-graph__center-line", html)
            self.assertNotIn("STEN", html)

    def test_summary_intro_removed_and_ai_tab_explicit(self):
        root = Path(settings.BASE_DIR) / "templates/customer/processes/partials/candidate_insights"
        summary = (root / "personality/_trait_descriptions.html").read_text(encoding="utf8")
        self.assertNotIn("Personality descriptions summarise likely behavioural", summary)
        personality_tabs = (root / "tabs/_personality.html").read_text(encoding="utf8")
        self.assertIn("AI-tolkning", personality_tabs)
        self.assertIn("AI interpretation", personality_tabs)

    def test_css_uses_reduced_spacing_without_hiding_content(self):
        stylesheet = (Path(settings.BASE_DIR) /
            "static/css/talena/pages/personality-trait-scale-experiment.css"
        ).read_text(encoding="utf8")
        tokens = (Path(settings.BASE_DIR) /
            "static/css/talena/tokens.css"
        ).read_text(encoding="utf8")
        self.assertIn("--talena-text: #514a46;", tokens)
        chart_stylesheet = (Path(settings.BASE_DIR) /
            "static/css/talena/pages/candidate-charts.css"
        ).read_text(encoding="utf8")
        self.assertIn(
            ".personality-overview-chart--segmented .personality-overview-item__track::after",
            chart_stylesheet,
        )
        self.assertIn("width: 2px;", chart_stylesheet)
        self.assertIn("--talena-text-muted: #625b57;", tokens)
        self.assertIn("--talena-text-subtle: #766f6a;", tokens)
        self.assertNotIn("--talena-text: #000000;", tokens)
        self.assertIn(".personality-graph__segment--filled", stylesheet)
        self.assertIn(".personality-graph__center-line", stylesheet)
        self.assertIn("#personality-detailed-view .personality-trait-card", stylesheet)
        self.assertIn("height: 78px !important", stylesheet)
        self.assertIn("height: 45px !important", stylesheet)
        self.assertIn("height: 52px;", stylesheet)
        self.assertIn("background: var(--talena-chart-line);", stylesheet)
        shading = stylesheet.split(
            "/* Match the indicator scale: neutral centre, progressively stronger tones at both ends. */",
            1,
        )[1].split(".process-page .personality-graph__segment--filled", 1)[0]
        for score in range(1, 11):
            self.assertIn(f'.personality-graph__segment[data-score="{score}"]', shading)
        for tone in (
            "#eeeae7",
            "rgba(255, 111, 97, 0.10)",
            "rgba(255, 111, 97, 0.17)",
            "rgba(255, 111, 97, 0.25)",
        ):
            self.assertIn(tone, shading)
        self.assertIn("width: 2px;", stylesheet)
        self.assertIn("height: 26px !important", stylesheet)
        self.assertIn("@media (max-width: 720px)", stylesheet)
