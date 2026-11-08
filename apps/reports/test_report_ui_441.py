"""#441: presentation-only changes for Leadership and Derailment reports."""
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.reports.services.derailment_report import (
    _display_interpretation,
    _load_data,
    build_derailment_report_content,
)


class ReportUi441Tests(SimpleTestCase):
    def source(self, path):
        return (Path(settings.BASE_DIR) / path).read_text(encoding="utf-8")

    def report(self, score, language="sv"):
        return build_derailment_report_content(
            language, [{"competency": "Dependent", "sten_rounded": score}]
        )

    def test_boundaries_select_one_approved_text_not_two(self):
        for score, expected_level in [
            (1, "low"), (2, "low"), (3, "mid"),
            (7, "mid"), (8, "high"), (10, "high"),
        ]:
            for language in ("sv", "en"):
                with self.subTest(score=score, language=language):
                    report = self.report(score, language)
                    self.assertTrue(report["has_results"])
                    factor = report["factors"][0]
                    self.assertEqual(factor["score"], score)
                    self.assertEqual(len(factor["interpretations"]), 1)
                    self.assertEqual(
                        factor["interpretations"][0]["key"], expected_level
                    )
                    self.assertEqual(factor["scale_segments"], list(range(1, 11)))
                    self.assertEqual(factor["score_display"], str(score))
                    self.assertIn(str(score), factor["score_accessible"])

    def test_center_filled_segments_and_marker_are_not_recalculated(self):
        expected = {
            1: [1, 2, 3, 4, 5],
            2: [2, 3, 4, 5],
            3: [3, 4, 5],
            5: [5],
            6: [6],
            7: [6, 7],
            8: [6, 7, 8],
            10: [6, 7, 8, 9, 10],
        }
        for score, fill in expected.items():
            with self.subTest(score=score):
                factor = self.report(score)["factors"][0]
                self.assertEqual(factor["scale_filled_segments"], fill)
                self.assertEqual(factor["score"], score)
                self.assertEqual(factor["score_percent"], score * 10)

    def test_only_existing_level_text_is_shown(self):
        for lang in ("sv", "en"):
            for factor in _load_data()[lang]["factors"]:
                for level, score in [("low", 2), ("mid", 3), ("high", 8)]:
                    with self.subTest(language=lang, factor=factor["key"], level=level):
                        original = factor["levels"][level]
                        displayed = _display_interpretation(original, lang)
                        self.assertTrue(displayed)
                        self.assertGreater(len(displayed), 25)
                        # Normalisation may replace only the jargon opening.
                        # Preserve the remaining approved sentences verbatim.
                        sentences = original.split(". ", 1)
                        if len(sentences) > 1:
                            self.assertTrue(displayed.endswith(sentences[1]))

    def test_no_approved_text_produces_neutral_empty_state(self):
        from copy import deepcopy

        data = deepcopy(_load_data())
        data["sv"]["factors"][0]["levels"]["mid"] = ""
        with patch(
            "apps.reports.services.derailment_report._load_data",
            return_value=data,
        ):
            result = self.report(3)["factors"][0]
        self.assertEqual(result["interpretations"], [])

    def test_derailment_template_has_intro_first_and_meter_accessibility(self):
        html = render_to_string(
            "customer/processes/partials/candidate_insights/tabs/_derailment_report.html",
            {"derailment_report_content": self.report(7)},
        )
        self.assertLess(
            html.index('class="derailment-report__page-header"'),
            html.index('class="derailment-report__intro"'),
        )
        self.assertLess(
            html.index('class="derailment-report__intro"'),
            html.index('class="derailment-report__overview"'),
        )
        self.assertNotIn("Same compact, grouped reading pattern", html)
        self.assertNotIn("{#", html)
        self.assertIn('aria-valuenow="7"', html)
        self.assertIn('aria-valuemin="1"', html)
        self.assertIn('aria-valuemax="10"', html)
        self.assertIn("Resultat 7 av 10", html)
        self.assertEqual(html.count("personality-indicator-scale__segment--selected"), 1)
        self.assertEqual(html.count('data-score="'), 10)
        self.assertIn("personality-indicator-scale__center-line", html)
        self.assertIn("personality-indicator-scale__side--left", html)
        self.assertIn("personality-indicator-scale__side--right", html)
        self.assertIn("personality-indicator-scale__labels", html)
        self.assertNotIn("14 / 14", html)
        self.assertNotIn("Lägre poäng", html)
        self.assertNotIn("Högre poäng", html)
        self.assertNotIn("STEN", html)
        # The precise assessment result remains available to assistive tech,
        # but no score digits are printed next to the scale or interpretation.
        self.assertNotIn('class="derailment-report__score-pill"', html)
        self.assertNotIn("<span>7</span>", html)

    def test_leadership_hides_only_visual_count_and_legend(self):
        source = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_leadership_report.html"
        )
        self.assertNotIn("leadership-report__score-count", source)
        self.assertNotIn("leadership-report__score-scale", source)
        self.assertIn("leadership_report_content.chart_svg|safe", source)
        self.assertIn('role="meter"', source)

    def test_derailment_reuses_exact_personality_scale_styles(self):
        template = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_derailment_report.html"
        )
        old_css = self.source("static/css/talena/pages/team-styles.css")
        shared_css = self.source(
            "static/css/talena/pages/personality-trait-scale-experiment.css"
        )
        self.assertIn("derailment-report__scale-segments personality-indicator-scale", template)
        self.assertNotIn(".derailment-report__scale-segments::after", old_css)
        self.assertIn(".personality-indicator-scale__segment--selected", shared_css)
        self.assertIn(".personality-indicator-scale__center-line", shared_css)
        self.assertIn(".personality-indicator-scale__segment--filled", shared_css)
        self.assertIn("rgba(255, 111, 97, 0.25)", shared_css)
        self.assertIn("background: #ff8a7d", shared_css)
        self.assertIn("background: #f25549", shared_css)

    def test_visual_segment_classes_follow_midpoint_for_all_scores(self):
        from html import unescape
        import re

        selected = re.compile(
            r'<span\s+class="([^"]*personality-indicator-scale__segment[^"]*)"'
            r'\s+data-score="(\d+)"',
        )
        for score in range(1, 11):
            with self.subTest(score=score):
                rendered = unescape(render_to_string(
                    "customer/processes/partials/candidate_insights/tabs/_derailment_report.html",
                    {"derailment_report_content": self.report(score)},
                ))
                segments = selected.findall(rendered)
                self.assertEqual(len(segments), 10)
                markers = [int(value) for classes, value in segments
                           if "personality-indicator-scale__segment--selected" in classes]
                fills = [int(value) for classes, value in segments
                         if "personality-indicator-scale__segment--filled" in classes]
                self.assertEqual(markers, [score])
                self.assertEqual(fills, self.report(score)["factors"][0]["scale_filled_segments"])

    def test_derailment_density_matches_personality_without_touching_shared_scale(self):
        css = self.source("static/css/talena/pages/team-styles.css")
        personality = self.source(
            "static/css/talena/pages/personality-trait-scale-experiment.css"
        )
        self.assertIn(
            "grid-template-columns:minmax(0,1fr) minmax(260px,1.7fr) minmax(0,1fr)",
            css,
        )
        self.assertIn(
            "color:#656f81;font-size:.58rem;line-height:1.45", css
        )
        self.assertIn("gap:16px;padding:13px 0", css)
        self.assertIn(
            "display:flex;justify-content:center;align-items:center", css
        )
        self.assertIn(
            "max-width:100%;color:#302e36;font-size:.69rem",
            css,
        )
        self.assertNotIn(
            ".derailment-report__profile-result-heading span{position:absolute",
            css,
        )
        self.assertIn("@media(max-width:900px)", css)
        self.assertIn("@media(max-width:600px)", css)
        self.assertIn(".process-page .personality-indicator-scale__segment", personality)
        self.assertNotIn(".derailment-report__scale-segment.is-filled", css)

    def test_report_padding_keeps_outer_body_flush_and_restores_inner_panels(self):
        css = self.source("static/css/talena/pages/candidate-insight-tabs.css")
        reports = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_reports.html"
        )
        workspace = self.source(
            "templates/customer/processes/partials/candidate_insights/_workspace.html"
        )

        # The page body includes both tabs and content: keep that wrapper
        # flush, but restore the normal inset around each report panel.
        self.assertIn(
            ".process-page .candidate-insight-page-body {\n  padding: 0;",
            css,
        )
        self.assertIn(
            "/* Keep the surrounding page wrapper flush on mobile too. */\n"
            "  .process-page .candidate-insight-page-body {\n    padding: 0;",
            css,
        )
        self.assertNotIn(
            "#candidate-insights-panel-reports .candidate-insights-subworkspace__panels {",
            css,
        )
        self.assertIn(
            ".process-page .candidate-insight-page "
            ".candidate-insights-subworkspace__panels {\n  padding: 1.25rem",
            css,
        )
        self.assertIn(
            "  .process-page .candidate-insight-page "
            ".candidate-insights-subworkspace__panels {\n    padding: 1rem;",
            css,
        )
        self.assertEqual(workspace.count('class="candidate-insight-page-body"'), 1)
        self.assertIn('class="candidate-insights-subnavigation"', reports)
        for subtab in ("team-report", "leadership-report", "derailment-report"):
            with self.subTest(tab=subtab):
                self.assertIn(f'data-insights-subpanel="{subtab}"', reports)

    def test_no_visible_derailment_sten_scores_but_accessible_result(self):
        template = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_derailment_report.html"
        )
        self.assertNotIn("{{ factor.score_display }}", template)
        self.assertIn('aria-valuenow="{{ factor.score }}"', template)
        self.assertIn("{{ factor.score_accessible }}", template)
        for score in (1, 7, 10):
            with self.subTest(score=score):
                rendered = render_to_string(
                    "customer/processes/partials/candidate_insights/tabs/_derailment_report.html",
                    {"derailment_report_content": self.report(score)},
                )
                self.assertIn(f'aria-valuenow="{score}"', rendered)
                self.assertIn(f"Resultat {score} av 10", rendered)
                self.assertNotIn('derailment-report__score-pill', rendered)

    def test_derailment_interpretations_match_personality_summary_layout(self):
        source = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_derailment_report.html"
        )
        css = self.source("static/css/talena/pages/team-styles.css")
        self.assertIn('class="derailment-report__interpretation-list"', source)
        self.assertIn('class="derailment-report__interpretation-list-header"', source)
        self.assertIn('class="derailment-report__interpretation-item"', source)
        self.assertIn('class="derailment-report__interpretation-text"', source)
        self.assertNotIn('class="derailment-report__factor-card"', source)
        self.assertNotIn("<details", source)
        self.assertNotIn("derailment_report_content.guidance_label", source)
        self.assertNotIn("derailment-report__factor-card", css)
        self.assertIn(".derailment-report__interpretation-item:last-child{border-bottom:0}", css)
        self.assertIn("background:var(--talena-surface-soft", css)

    def test_all_14_interpretations_visible_without_expanding(self):
        from html import unescape
        from apps.reports.services.derailment_report import _SOURCE_NAMES

        for language in ("sv", "en"):
            competencies = [
                {"competency": names[0], "sten_rounded": (index % 10) + 1}
                for index, names in enumerate(_SOURCE_NAMES.values())
            ]
            report = build_derailment_report_content(language, competencies)
            rendered = unescape(render_to_string(
                "customer/processes/partials/candidate_insights/tabs/_derailment_report.html",
                {"derailment_report_content": report},
            ))
            with self.subTest(language=language):
                self.assertEqual(len(report["factors"]), 14)
                self.assertEqual(
                    rendered.count('class="derailment-report__interpretation-item"'),
                    14,
                )
                self.assertNotIn("<details", rendered)
                self.assertNotIn("Resultatbeskrivning", rendered)
                self.assertNotIn('derailment-report__score-pill', rendered)
                for factor in report["factors"]:
                    self.assertIn(factor["title"], rendered)
                    for interpretation in factor["interpretations"]:
                        self.assertIn(interpretation["text"], rendered)

    def test_missing_approved_text_shown_without_inventing_copy(self):
        from copy import deepcopy

        data = deepcopy(_load_data())
        data["sv"]["factors"][0]["levels"]["mid"] = ""
        with patch(
            "apps.reports.services.derailment_report._load_data",
            return_value=data,
        ):
            report = self.report(3)
        rendered = render_to_string(
            "customer/processes/partials/candidate_insights/tabs/_derailment_report.html",
            {"derailment_report_content": report},
        )
        self.assertIn(report["missing_interpretation_label"], rendered)
        self.assertIn("derailment-report__interpretation-text--missing", rendered)
        self.assertNotIn("<details", rendered)

    def test_derailment_page_heading_and_pdf_action_share_same_row(self):
        template = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_derailment_report.html"
        )
        js = self.source("static/js/talena/candidate-report-export.js")
        css = self.source("static/css/talena/pages/team-styles.css")
        pdf_css = self.source("static/css/talena/pages/candidate-report-export.css")

        self.assertIn('class="derailment-report__page-header"', template)
        self.assertIn('class="insight-summary-kicker"', template)
        self.assertIn('id="derailment-report-title"', template)
        self.assertIn("Urspårningsrapport", template)
        self.assertIn("Derailment report", template)
        self.assertNotIn('derailment-report__overview-heading', template)
        self.assertNotIn('derailment-report__eyebrow', template)
        self.assertNotIn("derailment-profile-title", template)
        self.assertIn(".derailment-report__page-header, .candidate-insight-page-header", js)
        self.assertIn('header.append(toolbar);', js)
        self.assertIn("talena-candidate-pdf-toolbar--inline", js)
        self.assertIn(".derailment-report__page-title", css)
        self.assertIn(".derailment-report__profile-row:first-child{border-top:0", css)
        self.assertIn(
            '[data-candidate-pdf-report="derailment-report"] .derailment-report__page-header',
            pdf_css,
        )

    def test_derailment_new_header_localized_and_comment_not_rendered(self):
        from django.utils.translation import override

        for language, expected_title, expected_eyebrow in (
            ("sv", "Urspårningsrapport", "Urspårning"),
            ("en", "Derailment report", "Derailment"),
        ):
            with self.subTest(language=language), override(language):
                html = render_to_string(
                    "customer/processes/partials/candidate_insights/tabs/_derailment_report.html",
                    {"derailment_report_content": self.report(7, language)},
                )
                self.assertIn(expected_title, html)
                self.assertIn(expected_eyebrow, html)
                self.assertEqual(html.count('id="derailment-report-title"'), 1)
                self.assertEqual(html.count('class="derailment-report__page-header"'), 1)
                self.assertNotIn("Same compact, grouped reading pattern", html)
                self.assertNotIn("Every approved scale interpretation", html)
                self.assertNotIn("{#", html)
                self.assertLess(
                    html.index('class="derailment-report__page-header"'),
                    html.index('class="derailment-report__intro"'),
                )

    def test_missing_results_do_not_generate_an_interpretation(self):
        result = build_derailment_report_content("sv", [])
        self.assertFalse(result["has_results"])
        self.assertEqual(result["factors"], [])
