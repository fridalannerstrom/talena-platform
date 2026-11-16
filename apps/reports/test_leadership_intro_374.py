"""#374: Long Leadership report introduction is collapsed on screen.

Tests the real localized report content, shared customer/admin template,
responsive CSS and full-text PDF export behaviour, with synthetic scores.
"""
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from apps.reports.services.leadership_report import (
    _SOURCE_NAMES,
    build_leadership_report_content,
)

TEMPLATE = "customer/processes/partials/candidate_insights/tabs/_leadership_report.html"


class LeadershipIntroductionAccordion374Tests(SimpleTestCase):
    def report(self, language):
        scores = [
            {"competency": names[0], "stive": 3}
            for names in _SOURCE_NAMES.values()
        ]
        report = build_leadership_report_content(language, scores)
        self.assertTrue(report["has_results"])
        return report

    def test_collapsed_by_default_with_keyboard_accessible_summary_both_languages(self):
        for language, show, hide in (
            ("sv", "Visa förklaring", "Dölj förklaring"),
            ("en", "Show explanation", "Hide explanation"),
        ):
            with self.subTest(language=language), override(language):
                report = self.report(language)
                html = render_to_string(TEMPLATE, {"leadership_report_content": report})
                intro = html.split('<section class="leadership-report__intro"', 1)[1]
                intro = intro.split("</section>", 1)[0]

                self.assertIn('<details class="leadership-report__intro-disclosure">', intro)
                self.assertNotIn('<details class="leadership-report__intro-disclosure" open', intro)
                self.assertIn('<summary class="leadership-report__intro-summary">', intro)
                self.assertIn('id="leadership-intro-title"', intro)
                self.assertIn('aria-labelledby="leadership-intro-title"', html)
                self.assertIn(report["introduction"]["title"], intro)
                self.assertIn(show, intro)
                self.assertIn(hide, intro)
                self.assertIn('class="leadership-report__intro-body"', intro)
                # Intro text is still part of the DOM, simply collapsed by
                # the browser until summary is activated.
                self.assertIn(report["introduction_sections"]["paragraphs"][0], intro)
                self.assertIn(report["introduction_sections"]["model_heading"], intro)
                self.assertLess(
                    intro.index('<summary class="leadership-report__intro-summary">'),
                    intro.index('class="leadership-report__intro-body"'),
                )
                self.assertIn("</details>", intro)
                self.assertIn("leadership-report__competency-card", html)

    def test_legacy_unstructured_introduction_is_also_collapsible(self):
        for language in ("sv", "en"):
            with self.subTest(language=language), override(language):
                report = self.report(language)
                report["introduction_sections"] = None
                report["introduction"]["body"] = "Legacy report explanation"
                html = render_to_string(TEMPLATE, {"leadership_report_content": report})
                self.assertIn("Legacy report explanation", html)
                self.assertIn('class="leadership-report__intro-disclosure"', html)
                self.assertIn('class="leadership-report__intro-text"', html)

    def test_mobile_styles_and_pdf_include_full_text(self):
        css = (
            Path(settings.BASE_DIR) / "static/css/talena/pages/team-styles.css"
        ).read_text(encoding="utf-8")
        export = (
            Path(settings.BASE_DIR) / "static/js/talena/candidate-report-export.js"
        ).read_text(encoding="utf-8")
        pdf_css = (
            Path(settings.BASE_DIR) / "static/css/talena/pages/candidate-report-export.css"
        ).read_text(encoding="utf-8")
        self.assertIn("leadership-report__intro-summary", css)
        self.assertIn("leadership-report__intro-disclosure[open]", css)
        self.assertIn("leadership-report__intro-body", css)
        self.assertIn("flex-wrap: wrap;", css)
        self.assertIn("focus-visible", css)
        self.assertIn("@media (max-width: 420px)", css)
        # The existing export clones and expands ALL native details, so
        # document PDFs retain the full explanation even when collapsed onscreen.
        self.assertIn(
            'clone.querySelectorAll("details").forEach(details => { details.open = true; });',
            export,
        )
        self.assertIn(
            '.talena-candidate-pdf-stage[data-candidate-pdf-report="leadership-report"] .leadership-report__intro-action',
            pdf_css,
        )

    def test_unavailable_report_remains_neutral_empty_state(self):
        report = build_leadership_report_content("sv", [])
        with override("sv"):
            html = render_to_string(TEMPLATE, {"leadership_report_content": report})
        self.assertFalse(report["has_results"])
        self.assertNotIn("leadership-report__intro-disclosure", html)
        self.assertIn(report["empty_title"], html)
