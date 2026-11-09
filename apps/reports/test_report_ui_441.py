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
        self.assertIn(".derailment-report__page-header", js)
        self.assertIn(".candidate-insight-page-header", js)
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

    def test_team_and_leadership_reports_share_heading_and_pdf_mount(self):
        team = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_team_styles.html"
        )
        leadership = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_leadership_report.html"
        )
        derailment = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_derailment_report.html"
        )
        js = self.source("static/js/talena/candidate-report-export.js")
        css = self.source("static/css/talena/pages/team-styles.css")
        pdf_css = self.source("static/css/talena/pages/candidate-report-export.css")

        for report, source in (
            ("team-report", team),
            ("leadership-report", leadership),
            ("derailment-report", derailment),
        ):
            with self.subTest(report=report):
                self.assertIn(f'class="{report}__page-header"', source)
                self.assertIn('class="insight-summary-kicker"', source)
                self.assertIn(f'class="{report}__page-title"', source)
                self.assertIn(f".{report}__page-header", js)
                self.assertIn(f".{report}__page-header", css)
                self.assertIn(f".{report}__page-title", css)
                self.assertIn(
                    f'[data-candidate-pdf-report="{report}"] .{report}__page-header',
                    pdf_css,
                )

        self.assertIn('header.append(toolbar);', js)
        self.assertIn("talena-candidate-pdf-toolbar--inline", js)
        self.assertIn('source.querySelector("[data-candidate-pdf-toolbar]")', js)
        self.assertIn('create("h1", "talena-candidate-pdf-heading"', js)
        self.assertIn("get_current_language as LANGUAGE_CODE", team)
        self.assertIn("get_current_language as leadership_language", leadership)
        # In the customer report view, the shared team-style component
        # keeps its existing hidden header and isn't modified globally.
        self.assertIn(
            '{% include "customer/processes/partials/_team_styles.html" with team_style_hide_footer=True team_style_use_svg=True %}',
            team,
        )

    def test_team_leadership_headers_render_in_both_languages(self):
        from django.utils.translation import override

        team_profile = {
            "available": True,
            "styles": [],
            "chart_styles": [],
            "chart": {
                "labels": [], "values": [],
                "backgrounds": [], "border_colors": [],
            },
        }
        leadership_content = {
            "has_results": True,
            "aria_label": "Leadership report",
            "profile_eyebrow": "Leadership profile",
            "chart_intro": {"title": "Competency profile"},
            "chart_svg": "<svg></svg>",
            "introduction": {"title": "About leadership", "body": "Explanation"},
            "quadrants": [],
        }
        for language, team_title, leadership_title, eyebrow in (
            ("sv", "Teamrapport", "Ledarskapsrapport", "Ledarskap"),
            ("en", "Team report", "Leadership report", "Leadership"),
        ):
            with self.subTest(language=language), override(language):
                team_html = render_to_string(
                    "customer/processes/partials/candidate_insights/tabs/_team_styles.html",
                    {"team_style_profile": team_profile, "team_style_embedded": False},
                )
                leader_html = render_to_string(
                    "customer/processes/partials/candidate_insights/tabs/_leadership_report.html",
                    {"leadership_report_content": leadership_content},
                )
                self.assertIn(team_title, team_html)
                self.assertIn(leadership_title, leader_html)
                self.assertIn(eyebrow, leader_html)
                self.assertIn('class="team-report__page-header"', team_html)
                self.assertIn('class="leadership-report__page-header"', leader_html)
                self.assertLess(
                    leader_html.index('class="leadership-report__page-header"'),
                    leader_html.index('class="leadership-report__score-overview"'),
                )
                self.assertNotIn("{#", team_html)
                self.assertNotIn("{#", leader_html)

    def test_team_report_drops_only_redundant_frame_and_centers_canvas(self):
        css = self.source("static/css/talena/pages/team-styles.css")
        html = self.source("templates/customer/processes/partials/_team_styles.html")

        self.assertIn(
            "#reports-subpanel-team-report > .team-styles-section", css
        )
        self.assertIn("border: 0 !important;", css)
        self.assertIn("box-shadow: none !important;", css)
        self.assertIn(
            "#reports-subpanel-team-report .team-style-chart-card", css
        )
        self.assertIn("max-width: 780px;", css)
        self.assertIn("height: clamp(430px, 59vw, 650px);", css)
        self.assertIn("height: clamp(340px, 103vw, 460px);", css)
        self.assertIn(
            'class="team-style-chart-card mb-4"', html
        )
        self.assertIn("data-team-style-chart", html)
        self.assertIn("data-style-score", html)

    def test_team_polar_chart_uses_upright_axes_and_no_data_changes(self):
        base = self.source("templates/customer/processes/process_base.html")
        theme = self.source("static/js/talena/candidate-chart-theme.js")
        self.assertIn(
            'startAngle: canvas.closest("#reports-subpanel-team-report") ? 0 : -22.5,',
            base,
        )
        self.assertIn('type: "polarArea"', base)
        self.assertIn("data: numericValues", base)
        self.assertIn('max: 5,', base)
        self.assertIn("function drawTeamStyleTracks(chart)", theme)
        self.assertIn(
            'canvas?.closest("#reports-subpanel-team-report")', theme
        )
        self.assertIn(
            "plugin.beforeDatasetsDraw = function talenaTeamStyleBeforeDatasetsDraw",
            theme,
        )
        self.assertIn('ctx.fillStyle = `rgba(', theme)
        self.assertIn("if (candidateReport) radial.startAngle = 0", theme)
        self.assertIn("if (candidateReport) radial.ticks.display = false;", theme)
        self.assertIn("drawTeamStyleOverlay(currentChart);", theme)
        self.assertNotIn("dataset.data =", theme)

    def test_team_report_hides_footer_without_changing_reused_component(self):
        from django.utils.translation import override

        wrapper = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_team_styles.html"
        )
        shared = self.source(
            "templates/customer/processes/partials/_team_styles.html"
        )
        self.assertIn("with team_style_hide_footer=True", wrapper)
        self.assertIn("{% if not team_style_hide_footer %}", shared)
        self.assertIn('class="team-styles-footer"', shared)

        profile = {
            "available": True,
            "styles": [],
            "chart_styles": [],
            "chart_svg": '<svg class="leadership-report__wheel team-style-flower__wheel"></svg>',
            "chart": {
                "labels": [], "values": [],
                "backgrounds": [], "border_colors": [],
            },
        }
        with override("sv"):
            report = render_to_string(
                "customer/processes/partials/candidate_insights/tabs/_team_styles.html",
                {"team_style_profile": profile, "team_style_embedded": False},
            )
            reused = render_to_string(
                "customer/processes/partials/_team_styles.html",
                {"team_style_profile": profile, "team_style_embedded": True},
            )
        self.assertNotIn('class="team-styles-footer"', report)
        self.assertIn('class="team-styles-footer"', reused)
        self.assertIn("team-style-flower__wheel", report)
        self.assertNotIn("<canvas", report)
        self.assertIn("data-team-style-chart", reused)

    def test_team_chart_petals_and_larger_quadrant_titles_are_candidate_only(self):
        base = self.source("templates/customer/processes/process_base.html")
        theme = self.source("static/js/talena/candidate-chart-theme.js")

        # The Chart.js dataset and canvas theme use the same rounded ends
        # for the candidate report. Embedded team charts remain unchanged.
        for source in (base, theme):
            self.assertIn(
                "candidateReport ? (compact ? 26 : 40) : (compact ? 7 : 12)",
                source,
            )
            self.assertIn(
                "candidateReport ? (compact ? 5 : 8) : (compact ? 1 : 2)",
                source,
            )
        self.assertIn(
            '"800 16px Inter, system-ui, sans-serif"', theme
        )
        self.assertIn(
            '"800 13px Inter, system-ui, sans-serif"', theme
        )
        self.assertIn('canvas.closest("#reports-subpanel-team-report")', base)
        self.assertIn('canvas.closest("#reports-subpanel-team-report")', theme)
        self.assertIn("data: numericValues", base)
        self.assertNotIn("dataset.data =", theme)

    def test_team_flower_uses_white_center_and_smaller_labels(self):
        theme = self.source("static/js/talena/candidate-chart-theme.js")
        base = self.source("templates/customer/processes/process_base.html")
        start = theme.index("  function drawTeamStyleOverlay(chart) {")
        end = theme.index("  function findLocalLabelsPlugin(", start)
        overlay = theme[start:end]

        self.assertIn('if (candidateReport) {', overlay)
        self.assertIn(
            'ctx.arc(centerX, centerY, compact ? 11 : 19, 0, Math.PI * 2);',
            overlay,
        )
        self.assertIn('ctx.fillStyle = "#ffffff";', overlay)
        self.assertLess(
            overlay.index('ctx.arc(centerX, centerY, compact ? 11 : 19'),
            overlay.index('ctx.fillText(String(item.score), scoreX, scoreY);'),
        )
        # Candidate-only font reductions; shared team chart numbers unchanged.
        self.assertIn('"600 11px Inter, system-ui, sans-serif"', overlay)
        self.assertIn('"700 10px Inter, system-ui, sans-serif"', overlay)
        self.assertIn('"700 8px Inter, system-ui, sans-serif"', overlay)
        self.assertIn('"800 16px Inter, system-ui, sans-serif"', overlay)
        self.assertIn('"800 13px Inter, system-ui, sans-serif"', overlay)
        self.assertIn(
            'ctx.fillStyle = `rgba(${palette.rgb.join(", ")}, 0.035)`;',
            theme,
        )
        self.assertIn('data: numericValues', base)
        self.assertNotIn("dataset.data =", theme)

    def test_leadership_graph_removes_duplicate_heading_but_keeps_accessibility(self):
        from apps.reports.services.leadership_report import build_leadership_report_content

        template = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_leadership_report.html"
        )
        css = self.source("static/css/talena/pages/team-styles.css")
        self.assertNotIn('id="leadership-score-heading"', template)
        self.assertNotIn("leadership-report__score-overview-heading", template)
        self.assertNotIn("{{ leadership_report_content.profile_eyebrow }}", template.split(
            '<div class="leadership-report__wheel-wrap">'
        )[0])
        self.assertIn('aria-label="{{ leadership_report_content.chart_intro.title }}"', template)
        self.assertIn('class="leadership-report__page-header"', template)
        self.assertIn("max-width:780px", css)
        self.assertIn(".leadership-wheel__quadrant{font:800 16px", css)
        self.assertIn(".leadership-wheel__trait{font:600 12px", css)

        report = build_leadership_report_content(
            "sv", [{"competency": "Creates the Vision", "stive": 2}]
        )
        rendered = render_to_string(
            "customer/processes/partials/candidate_insights/tabs/_leadership_report.html",
            {"leadership_report_content": report},
        )
        self.assertIn('class="leadership-report__wheel"', rendered)
        self.assertIn('id="leadership-wheel-title"', rendered)
        self.assertNotIn('id="leadership-score-heading"', rendered)

    def test_leadership_svg_is_valid_flower_with_eight_original_scores(self):
        from xml.etree import ElementTree
        from apps.reports.services.leadership_report import (
            _SOURCE_NAMES,
            build_leadership_report_content,
        )

        scores = [1, 2, 3, 4, 5, 2, 3, 4]
        names = list(_SOURCE_NAMES.values())
        assessments = [
            {"competency": name[0], "stive": score, "stive_rounded": score}
            for name, score in zip(names, scores)
        ]
        namespace = "{http://www.w3.org/2000/svg}"

        for language in ("sv", "en"):
            with self.subTest(language=language):
                report = build_leadership_report_content(language, assessments)
                self.assertTrue(report["has_results"])
                self.assertEqual(report["scores_count"], 8)
                self.assertEqual(
                    [competency["score_rounded"]
                     for quadrant in report["quadrants"]
                     for competency in quadrant["competencies"]],
                    scores,
                )
                self.assertEqual(
                    [competency["score_percent"]
                     for quadrant in report["quadrants"]
                     for competency in quadrant["competencies"]],
                    [score * 20 for score in scores],
                )
                svg = ElementTree.fromstring(report["chart_svg"])
                self.assertEqual(svg.tag, f"{namespace}svg")
                self.assertEqual(svg.attrib["role"], "img")
                self.assertEqual(
                    len(svg.findall(f".//{namespace}path[@class='leadership-wheel__petal']")),
                    8,
                )
                tracks = svg.findall(
                    f".//{namespace}path[@class='leadership-wheel__track']"
                )
                self.assertEqual(len(tracks), 8)
                self.assertTrue(all(t.attrib["fill-opacity"] == "0.045" for t in tracks))
                petals = svg.findall(
                    f".//{namespace}path[@class='leadership-wheel__petal']"
                )
                for score, petal in zip(scores, petals):
                    self.assertIn("Q ", petal.attrib["d"])
                    self.assertIn(f"A {49 * score} {49 * score}", petal.attrib["d"])
                hubs = svg.findall(
                    f".//{namespace}circle[@class='leadership-wheel__hub']"
                )
                self.assertEqual(len(hubs), 1)
                self.assertEqual(hubs[0].attrib["r"], "19")
                self.assertEqual(
                    len(svg.findall(f".//{namespace}text[@class='leadership-wheel__score']")),
                    8,
                )
                self.assertEqual(
                    len(svg.findall(f".//{namespace}text[@class='leadership-wheel__trait']")),
                    8,
                )
                self.assertEqual(
                    len(svg.findall(f".//{namespace}text[@class='leadership-wheel__quadrant']")),
                    4,
                )
                self.assertEqual(
                    len(svg.findall(f".//{namespace}line")),
                    4,
                )
                self.assertIsNotNone(svg.find(f"{namespace}title"))
                self.assertIsNotNone(svg.find(f"{namespace}desc"))

    def test_team_flower_reuses_leadership_svg_exactly_and_retains_stive_scores(self):
        from xml.etree import ElementTree
        from django.utils.translation import override
        from apps.processes.services.team_styles import build_team_style_profile

        # Source order is not the chart order: Connector belongs to the
        # upper-left quadrant and must sit next to Catalyst in the flower.
        source_scores = {
            "Catalyst": (2.3, 2),
            "Director": (1.4, 1),
            "Energiser": (4.3, 4),
            "Architect": (5, 5),
            "Harmoniser": (3.2, 3),
            "Analyst": (1.8, 2),
            "Auditor": (2.5, 3),
            "Connector": (4.7, 5),
        }
        competencies = [
            {
                "competency": name,
                "stive": raw,
                "stive_rounded": displayed,
            }
            for name, (raw, displayed) in source_scores.items()
        ]
        svg_ns = "{http://www.w3.org/2000/svg}"
        expected_display_order = [5, 2, 1, 4, 5, 3, 2, 3]

        for language in ("sv", "en"):
            with self.subTest(language=language), override(language):
                profile = build_team_style_profile(competencies)
                self.assertTrue(profile["available"])
                self.assertTrue(profile["complete"])
                self.assertEqual(len(profile["styles"]), 8)
                self.assertEqual(len(profile["chart_styles"]), 8)
                # STIVE source and result ranking remain independent of
                # the visual order and the SVG itself.
                self.assertEqual(
                    {
                        style["key"]: style["raw_value"]
                        for style in profile["chart_styles"]
                    },
                    {
                        "catalyst": 2.3, "director": 1.4, "energiser": 4.3,
                        "architect": 5.0, "harmoniser": 3.2, "analyst": 1.8,
                        "auditor": 2.5, "connector": 4.7,
                    },
                )
                self.assertEqual(
                    [style["key"] for style in profile["styles"]],
                    [
                        "architect", "connector", "energiser", "harmoniser",
                        "auditor", "catalyst", "analyst", "director",
                    ],
                )
                svg = ElementTree.fromstring(profile["chart_svg"])
                self.assertEqual(svg.tag, f"{svg_ns}svg")
                self.assertIn("leadership-report__wheel", svg.attrib["class"])
                self.assertIn("team-style-flower__wheel", svg.attrib["class"])
                self.assertEqual(
                    svg.attrib["aria-labelledby"],
                    "team-style-wheel-title team-style-wheel-desc",
                )
                self.assertEqual(
                    len(svg.findall(f".//{svg_ns}path[@class='leadership-wheel__petal']")),
                    8,
                )
                self.assertEqual(
                    len(svg.findall(f".//{svg_ns}path[@class='leadership-wheel__track']")),
                    8,
                )
                rendered_scores = [
                    int(node.text)
                    for node in svg.findall(
                        f".//{svg_ns}text[@class='leadership-wheel__score']"
                    )
                ]
                self.assertEqual(rendered_scores, expected_display_order)
                self.assertEqual(
                    len(svg.findall(f".//{svg_ns}text[@class='leadership-wheel__quadrant']")),
                    4,
                )
                # Match SOVA's compass quadrants, rather than the cardinal
                # axes used by the shared Leadership report.
                quadrants = svg.findall(
                    f".//{svg_ns}text[@class='leadership-wheel__quadrant']"
                )
                self.assertEqual(
                    [(q.attrib["x"], q.attrib["y"], q.attrib["text-anchor"])
                     for q in quadrants],
                    [
                        ("70", "95", "start"), ("830", "95", "end"),
                        ("830", "685", "end"), ("70", "685", "start"),
                    ],
                )
                self.assertEqual(
                    {(line.attrib["x2"], line.attrib["y2"])
                     for line in svg.findall(f".//{svg_ns}line")},
                    {
                        ("205", "390"), ("450", "145"),
                        ("695", "390"), ("450", "635"),
                    },
                )
                # Connector/Catalyst NW, Director/Energiser NE,
                # Architect/Harmoniser SE and Analyst/Auditor SW.
                traits = svg.findall(
                    f".//{svg_ns}text[@class='leadership-wheel__trait']"
                )
                trait_points = [
                    (float(t.find(f"{svg_ns}tspan").attrib["x"]),
                     float(t.find(f"{svg_ns}tspan").attrib["y"]))
                    for t in traits
                ]
                for quadrant_index, (x, y) in enumerate(trait_points):
                    self.assertEqual(x < 450, quadrant_index in (0, 1, 6, 7))
                    self.assertEqual(y < 390, quadrant_index in (0, 1, 2, 3))
                self.assertEqual(
                    len(svg.findall(f".//{svg_ns}circle[@class='leadership-wheel__hub']")),
                    1,
                )
                rendered = render_to_string(
                    "customer/processes/partials/candidate_insights/tabs/_team_styles.html",
                    {"team_style_profile": profile},
                )
                self.assertIn('class="leadership-report__wheel team-style-flower__wheel"', rendered)
                self.assertNotIn("<canvas", rendered)
                self.assertNotIn('class="team-styles-footer"', rendered)
                self.assertNotIn('id="team-style-chart-values"', rendered)
                self.assertIn('class="team-report__page-header"', rendered)

    def test_team_svg_matches_leadership_visuals_and_pdf_export(self):
        team = self.source(
            "templates/customer/processes/partials/_team_styles.html"
        )
        styles = self.source("static/css/talena/pages/team-styles.css")
        svg_builder = self.source("apps/reports/services/leadership_report.py")
        pdf = self.source("static/js/talena/candidate-report-export.js")
        self.assertIn("{% if team_style_use_svg %}", team)
        self.assertIn("{{ team_style_profile.chart_svg|safe }}", team)
        self.assertIn("{% else %}", team)
        self.assertIn("data-team-style-chart", team)
        self.assertIn(".team-style-polar-wrap.team-style-polar-wrap--svg", styles)
        self.assertIn(".team-style-flower__wheel", styles)
        self.assertIn("min-width: 0;", styles)
        self.assertIn("svg_id_prefix: str =", svg_builder)
        self.assertIn('svg_extra_class: str =', svg_builder)
        self.assertIn('team-report", selector: "#reports-subpanel-team-report"', pdf)
        self.assertIn('const clone = source.cloneNode(true);', pdf)
        self.assertIn('const liveCanvases = source.querySelectorAll("canvas");', pdf)

    def test_leadership_introduction_preserves_copy_in_readable_sections(self):
        import re
        from apps.reports.services.leadership_report import (
            _load_leadership_report_data,
            _structure_leadership_introduction,
            build_leadership_report_content,
        )

        for language in ("sv", "en"):
            with self.subTest(language=language):
                original = _load_leadership_report_data()[language]["introduction"]["body"]
                structured = _structure_leadership_introduction(original, language)
                report = build_leadership_report_content(language, [])

                self.assertEqual(report["introduction_sections"], structured)
                self.assertEqual(len(structured["paragraphs"]), 3)
                self.assertEqual(len(structured["model_paragraphs"]), 2)
                self.assertEqual(len(structured["quadrants"]), 4)
                self.assertTrue(structured["model_heading"])
                self.assertTrue(all(x["title"] and x["description"]
                                    for x in structured["quadrants"]))

                # Every original word remains in the same order; only the
                # PDF-era line wraps are replaced with readable paragraphs.
                displayed = [
                    *structured["paragraphs"],
                    structured["model_heading"],
                    *structured["model_paragraphs"],
                    *(f'• {item["title"]}: {item["description"]}'
                      for item in structured["quadrants"]),
                ]
                self.assertEqual(
                    re.sub(r"\s+", " ", original.strip()),
                    " ".join(displayed),
                )

    def test_leadership_quadrants_use_one_frame_and_two_rows(self):
        from django.utils.translation import override
        from apps.reports.services.leadership_report import (
            _SOURCE_NAMES,
            build_leadership_report_content,
        )

        path = (
            "customer/processes/partials/candidate_insights/"
            "tabs/_leadership_report.html"
        )
        source = self.source("templates/" + path)
        css = self.source("static/css/talena/pages/team-styles.css")
        scores = [
            {"competency": names[0], "stive": 3}
            for names in _SOURCE_NAMES.values()
        ]
        for language in ("sv", "en"):
            with self.subTest(language=language), override(language):
                report = build_leadership_report_content(language, scores)
                self.assertTrue(report["has_results"])
                html = render_to_string(
                    path, {"leadership_report_content": report}
                )
                self.assertEqual(
                    html.count('class="leadership-report__quadrant '), 4
                )
                self.assertEqual(
                    html.count('class="leadership-report__competency-card"'), 8
                )
                self.assertEqual(
                    html.count('class="leadership-report__competency-name"'), 8
                )
                self.assertEqual(
                    html.count('class="leadership-report__guidance-explainer"'), 8
                )
                self.assertEqual(
                    html.count('class="leadership-report__guidance-summary"'), 8
                )
                self.assertEqual(html.count('role="meter"'), 8)
                self.assertEqual(html.count('aria-valuenow="3"'), 8)
                self.assertEqual(html.count('class="leadership-report__model-quadrant"'), 4)
                intro_html = html.split(
                    '<section class="leadership-report__intro"', 1
                )[1].split("</section>", 1)[0]
                self.assertEqual(intro_html.count("<p>"), 5)
                self.assertNotIn("insight-summary-content mb-4 team-style-profile-card", html)
                self.assertNotIn('class="team-style-ranked-list"', html)
                self.assertIn("leadership-report__model-title", html)
                self.assertIn("leadership-report__model-quadrants", html)
                self.assertIn(
                    report["introduction_sections"]["quadrants"][0]["description"],
                    html,
                )

        # CSS is scoped to the Leadership report, not Team, personality,
        # Motivation or other candidate sections.
        self.assertIn(
            "#reports-subpanel-leadership-report .leadership-report__intro {",
            css,
        )
        self.assertIn("background: #f8f5f2;", css)
        self.assertIn("font-size: 0.7rem;", css)
        self.assertIn(
            "#reports-subpanel-leadership-report .leadership-report__competency-card + "
            ".leadership-report__competency-card", css,
        )
        self.assertIn("border-top: 1px solid #eee9e5;", css)
        self.assertIn(
            "#reports-subpanel-leadership-report .leadership-report__quadrant-heading", css
        )
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", css)
        self.assertIn("@media (max-width: 420px)", css)

    def test_leadership_introduction_uses_full_card_width(self):
        css = self.source("static/css/talena/pages/team-styles.css")
        template = self.source(
            "templates/customer/processes/partials/candidate_insights/"
            "tabs/_leadership_report.html"
        )
        self.assertIn(
            ".leadership-report__intro-text {\n  max-width: none;\n  width: 100%;",
            css,
        )
        self.assertNotIn("max-width: 84ch;", css)
        self.assertIn(
            ".leadership-report__intro-copy {\n  width: 100%;\n  min-width: 0;",
            css,
        )
        self.assertIn('class="leadership-report__intro-copy"', template)
        self.assertIn('class="leadership-report__intro-text"', template)

    def test_leadership_meter_segments_fill_from_left_for_all_scores(self):
        import re
        from apps.reports.services.leadership_report import (
            _SOURCE_NAMES,
            build_leadership_report_content,
        )

        css = self.source("static/css/talena/pages/team-styles.css")
        template = self.source(
            "templates/customer/processes/partials/candidate_insights/"
            "tabs/_leadership_report.html"
        )
        self.assertIn("segment <= competency.score_rounded", template)
        self.assertIn("segment == competency.score_rounded", template)
        self.assertIn(
            ".leadership-report__competency-scale .response-style-scale__segment--filled,",
            css,
        )
        self.assertIn(
            "background: var(--talena-coral, #ff6f61) !important;",
            css,
        )

        for score in range(1, 6):
            for language in ("sv", "en"):
                with self.subTest(score=score, language=language):
                    competencies = [
                        {"competency": aliases[0], "stive": score}
                        for aliases in _SOURCE_NAMES.values()
                    ]
                    report = build_leadership_report_content(language, competencies)
                    html = render_to_string(
                        "customer/processes/partials/candidate_insights/"
                        "tabs/_leadership_report.html",
                        {"leadership_report_content": report},
                    )
                    meters = re.findall(
                        r'class="response-style-scale response-style-scale--linear '
                        r'team-style-result__scale leadership-report__competency-scale"'
                        r'[^>]*aria-valuenow="(\d+)"[^>]*>\s*'
                        r'<div class="response-style-scale__segments">(.*?)</div>',
                        html, re.S,
                    )
                    self.assertEqual(len(meters), 8)
                    for now, segments_html in meters:
                        self.assertEqual(int(now), score)
                        segments = re.findall(
                            r'<span class="response-style-scale__segment([^"]*)"',
                            segments_html,
                        )
                        self.assertEqual(len(segments), 5)
                        self.assertEqual(
                            [
                                index + 1 for index, classes in enumerate(segments)
                                if "response-style-scale__segment--filled" in classes
                            ],
                            list(range(1, score + 1)),
                        )
                        self.assertEqual(
                            [
                                index + 1 for index, classes in enumerate(segments)
                                if "response-style-scale__segment--marker" in classes
                            ],
                            [score],
                        )

    def test_derailment_intro_matches_leadership_warm_box_in_both_languages(self):
        from html import unescape
        from django.utils.translation import override

        css = self.source("static/css/talena/pages/team-styles.css")
        tmpl = self.source(
            "templates/customer/processes/partials/candidate_insights/"
            "tabs/_derailment_report.html"
        )
        self.assertIn('class="derailment-report__intro-copy"', tmpl)
        self.assertIn('class="derailment-report__intro-text"', tmpl)
        self.assertIn('id="derailment-intro-title"', tmpl)
        self.assertIn("background: #f8f5f2;", css)
        self.assertIn(
            "#reports-subpanel-derailment-report .derailment-report__intro {",
            css,
        )
        self.assertIn(
            "#reports-subpanel-derailment-report .derailment-report__intro-text {",
            css,
        )
        self.assertIn(
            "width: 100%;\n  max-width: none;\n  color: #716a67;\n"
            "  font-size: 0.7rem;",
            css,
        )
        self.assertIn(
            "#reports-subpanel-derailment-report .derailment-report__intro-copy {",
            css,
        )
        self.assertIn(
            "grid-template-columns: 2.3rem minmax(0, 1fr);",
            css,
        )

        for language in ("sv", "en"):
            with self.subTest(language=language), override(language):
                report = build_derailment_report_content(language, [
                    {"competency": "Dependent", "sten_rounded": 7}
                ])
                html = render_to_string(
                    "customer/processes/partials/candidate_insights/"
                    "tabs/_derailment_report.html",
                    {"derailment_report_content": report},
                )
                self.assertEqual(
                    html.count('class="derailment-report__intro"'), 1
                )
                self.assertIn(report["introduction_title"], html)
                self.assertIn(report["introduction"], unescape(html))
                self.assertIn('aria-labelledby="derailment-intro-title"', html)

    def test_missing_results_do_not_generate_an_interpretation(self):
        result = build_derailment_report_content("sv", [])
        self.assertFalse(result["has_results"])
        self.assertEqual(result["factors"], [])

    def test_reports_tab_grey_when_personality_missing_like_personality_tab(self):
        from django.utils.translation import override

        path = "customer/processes/partials/candidate_insights/_navigation.html"
        for language in ("sv", "en"):
            with self.subTest(language=language), override(language):
                for has_personality in (False, True):
                    html = render_to_string(path, {
                        "has_personality_results": has_personality,
                        "has_motivation_results": True,
                        "has_ability_results": True,
                    })
                    for tab in ("personality", "reports", "motivation", "cognitive"):
                        with self.subTest(tab=tab, has_personality=has_personality):
                            before_tab = html.split(
                                'data-insights-tab="' + tab + '"'
                            )[0].rsplit("<button", 1)[-1]
                            self.assertIn('role="tab"', before_tab)
                            should_be_muted = (
                                not has_personality
                                and tab in ("personality", "reports")
                            )
                            self.assertEqual(
                                "opacity-50" in before_tab,
                                should_be_muted,
                            )
                    self.assertIn('aria-controls="candidate-insights-panel-reports"', html)

    def test_report_empty_states_match_team_empty_state_in_both_languages(self):
        from html import unescape
        from django.utils.translation import override
        from apps.reports.services.leadership_report import (
            build_leadership_report_content,
        )

        shared = (
            'include "customer/processes/partials/'
            'candidate_insights/_missing_assessment.html"'
        )
        for path in (
            "templates/customer/processes/partials/candidate_insights/"
            "tabs/_team_styles.html",
            "templates/customer/processes/partials/candidate_insights/"
            "tabs/_leadership_report.html",
            "templates/customer/processes/partials/candidate_insights/"
            "tabs/_derailment_report.html",
        ):
            self.assertIn(shared, self.source(path))

        for language in ("sv", "en"):
            with self.subTest(language=language), override(language):
                leadership = build_leadership_report_content(language, [])
                derailment = build_derailment_report_content(language, [])
                self.assertFalse(leadership["has_results"])
                self.assertFalse(derailment["has_results"])

                reports = (
                    (
                        "team",
                        "customer/processes/partials/candidate_insights/tabs/_team_styles.html",
                        {"team_style_profile": {"available": False}},
                        "users",
                    ),
                    (
                        "leadership",
                        "customer/processes/partials/candidate_insights/tabs/_leadership_report.html",
                        {"leadership_report_content": leadership},
                        "compass",
                    ),
                    (
                        "derailment",
                        "customer/processes/partials/candidate_insights/tabs/_derailment_report.html",
                        {"derailment_report_content": derailment},
                        "activity",
                    ),
                )
                for name, template, context, icon in reports:
                    with self.subTest(report=name):
                        html = render_to_string(template, context)
                        self.assertEqual(
                            html.count("combined-questions-empty-state__icon"), 1
                        )
                        self.assertIn("combined-questions-empty-state", html)
                        self.assertIn(f'data-feather="{icon}"', html)
                        self.assertIn("personality-questions-section-title", html)
                        self.assertIn("text-muted small mb-0 mx-auto", html)
                        if name == "leadership":
                            self.assertIn(leadership["empty_title"], html)
                            self.assertIn(leadership["empty_body"], unescape(html))
                            self.assertNotIn("leadership-report__empty", html)
                        if name == "derailment":
                            self.assertIn(derailment["empty_title"], html)
                            self.assertIn(derailment["empty_body"], unescape(html))
                            self.assertNotIn("derailment-report__empty", html)
