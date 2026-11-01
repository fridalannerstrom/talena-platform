"""#363: Source-backed AI disclosure and Overview terminology.

This tests explicit source selectors and no accidental labelling of static
assessment values, interview notes, or the candidate-facing report.
"""
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override


class CandidateAiProvenanceTests(SimpleTestCase):
    def source(self, path):
        return (Path(settings.BASE_DIR) / path).read_text(encoding="utf-8")

    def test_overview_tab_name_in_both_languages(self):
        template = "customer/processes/partials/candidate_insights/_navigation.html"
        with override("sv"):
            html = render_to_string(template, {})
            self.assertIn("Överblick", html)
            self.assertNotIn(">Sammanfattning<", html)
        with override("en"):
            html = render_to_string(template, {})
            self.assertIn("Overview", html)
            self.assertNotIn(">Summary<", html)

    def test_summary_interpretation_has_correct_translation(self):
        source = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_overview.html"
        )
        self.assertIn("Sammanfattande tolkning", source)
        self.assertIn("Summary interpretation", source)
        self.assertNotIn('{% trans "Overall interpretation" %}', source)

    def test_badges_use_ai_output_selectors_not_heading_keywords(self):
        script = self.source("static/js/talena/candidate-ai-badges.js")
        self.assertIn('["#purposeFitResult",', script)
        self.assertIn('"#purposeFitSummary"', script)
        self.assertIn("[data-personality-ai-interpretation]", script)
        self.assertIn("[data-motivation-ai-interpretation]", script)
        self.assertIn("[data-cognitive-ai-interpretation]", script)
        self.assertIn("[data-personality-questions-list]", script)
        self.assertIn("[data-motivation-questions-list]", script)
        self.assertIn("[data-cognitive-questions-list]", script)
        self.assertIn("[data-after-interview-block-content]", script)
        self.assertIn("data-manager-report-ai-text", script)
        self.assertNotIn("MAJOR_AI_HEADING_SELECTORS", script)
        self.assertNotIn("test results are AI generated", script.lower())
        self.assertNotIn("candidate_results/", script)
        self.assertNotIn("test-score", script)

    def test_badge_is_real_accessible_dom_text_not_css_content(self):
        script = self.source("static/js/talena/candidate-ai-badges.js")
        style = self.source("static/css/talena/pages/candidate-eyebrows.css")
        self.assertIn('badge.setAttribute("aria-label", value)', script)
        self.assertIn("AI-genererat", script)
        self.assertIn("AI-assisted", script)
        self.assertIn("@media print", style)
        self.assertIn(".talena-ai-generated-badge", style)
        self.assertNotIn('content: "AI-genererat"', style)

    def test_structured_overall_picture_badge_requires_generated_content(self):
        script = self.source("static/js/talena/structured-overall-picture.js")
        self.assertIn('kicker.hidden = !hasGenerated;', script)
        self.assertIn("sectionHasAI", script)
        self.assertIn("hasRawSourceLeak", script)

    def test_manual_manager_edits_are_ai_assisted(self):
        manager = self.source("static/js/talena/after-interview-tabs.js")
        script = self.source("static/js/talena/candidate-ai-badges.js")
        self.assertIn('dataset.managerReportManuallyEdited', manager)
        self.assertIn('field.dataset.managerReportManuallyEdited === "true"', script)
        self.assertIn('data-after-interview-ai-origin', script)
        self.assertIn('body.dataset.afterInterviewAiOrigin = "true"', manager)

    def test_candidate_result_portal_is_not_ai_labelled(self):
        script = self.source("static/js/talena/candidate-ai-badges.js")
        self.assertIn('[data-candidate-insights-workspace]', script)
        self.assertNotIn("candidate_results/_candidate_result_tab", script)
        self.assertNotIn(".candidate-result-portal", script)
