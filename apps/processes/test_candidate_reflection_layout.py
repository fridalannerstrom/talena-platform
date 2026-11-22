"""Regression: candidate reflection shares the other insight tabs' visual rhythm."""
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override


class CandidateReflectionLayoutTests(SimpleTestCase):
    def _read(self, path):
        return (Path(settings.BASE_DIR) / path).read_text(encoding="utf-8")

    def test_reflection_uses_standard_heading_and_eyebrow_in_both_languages(self):
        for language, label, title in (
            ("sv", "Kandidatens perspektiv", "Kandidatens reflektion"),
            ("en", "Candidate perspective", "Candidate reflection"),
        ):
            with self.subTest(language=language), override(language):
                html = render_to_string(
                    "customer/processes/partials/candidate_insights/_candidate_reflection.html",
                    {
                        "LANGUAGE_CODE": language,
                        "candidate_reflection": {
                            "has_feedback": False,
                            "title": "Personality",
                            "body": "Example source text",
                            "groups": [],
                            "points": [],
                        },
                    },
                )
                self.assertIn(
                    'class="candidate-reflection__eyebrow insight-summary-kicker"',
                    html,
                )
                self.assertIn(
                    'class="candidate-reflection__title insight-summary-title"',
                    html,
                )
                self.assertIn('class="candidate-reflection__heading-copy"', html)
                self.assertIn(label, html)
                self.assertIn(title, html)
                self.assertIn("Example source text", html)

    def test_reflection_is_shared_across_personality_motivation_and_skills(self):
        for area in ("personality", "motivation", "cognitive"):
            with self.subTest(area=area):
                template = self._read(
                    f"templates/customer/processes/partials/candidate_insights/tabs/_{area}.html"
                )
                self.assertIn(
                    'candidate_insights/_candidate_reflection.html',
                    template,
                )
                self.assertIn(
                    'data-insights-subpanel="candidate-reflection"',
                    template,
                )

    def test_panel_has_one_inset_and_pdf_button_uses_existing_heading_row(self):
        css = self._read("static/css/talena/pages/candidate-insight-tabs.css")
        js = self._read("static/js/talena/candidate-report-export.js")
        self.assertIn(
            '.candidate-insights-subpanel[data-insights-subpanel="candidate-reflection"] > .candidate-reflection',
            css,
        )
        self.assertIn("padding: 0;", css)
        self.assertIn(".candidate-reflection__heading-copy", css)
        self.assertIn("flex-wrap: nowrap;", css)
        self.assertIn('".candidate-insight-page-header, .candidate-reflection__intro"', js)
        self.assertIn("header.append(toolbar)", js)

    def test_customer_and_admin_load_versioned_styles(self):
        for path in (
            "templates/customer/processes/_process_header.html",
            "templates/admin/accounts/partials/_candidate_customer_styles.html",
        ):
            self.assertIn(
                "candidate-insight-tabs.css' %}?v=20261122-reflection-layout-v2",
                self._read(path),
            )
        for path in (
            "templates/customer/core/layouts/customer_base.html",
            "templates/customer/processes/process_base.html",
        ):
            self.assertIn(
                "candidate-report-export.js' %}?v=20261122-reflection-header-v2",
                self._read(path),
            )
