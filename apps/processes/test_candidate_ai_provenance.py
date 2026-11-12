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
        self.assertIn('["[data-overview-interpretation-card]",', script)
        self.assertNotIn('["#purposeFitCard", "#purposeFitTitle"', script)
        self.assertNotIn('"#purposeFitSummary"', script)
        self.assertIn("[data-personality-ai-interpretation]", script)
        self.assertIn("[data-motivation-ai-interpretation]", script)
        self.assertIn("[data-cognitive-ai-interpretation]", script)
        # The broad "Questions" header is followed by an informational
        # introduction rather than AI-written prose, so it is left unbadged.
        self.assertNotIn('["[data-personality-questions-root]", ".personality-questions-header h2"', script)
        self.assertNotIn('["[data-motivation-questions-root]", ".personality-questions-header h2"', script)
        self.assertNotIn('["[data-cognitive-questions-root]", ".personality-questions-header h2"', script)
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
        self.assertIn("AI-generated", script)
        self.assertNotIn('"AI-assisterat"', script)
        self.assertNotIn('"AI-assisted"', script)
        self.assertIn("@media print", style)
        self.assertIn(".talena-ai-generated-badge", style)
        self.assertNotIn('content: "AI-genererat"', style)

    def test_structured_overall_picture_badge_requires_generated_content(self):
        script = self.source("static/js/talena/structured-overall-picture.js")
        self.assertIn("sectionHasAI", script)
        self.assertIn('addAiText("Testbild", item.testbild)', script)
        self.assertIn('addAiText(tr("Intervjun", "Interview"), item.intervjun)', script)
        self.assertNotIn("kicker.hidden", script)
        self.assertIn("hasRawSourceLeak", script)

    def test_manual_manager_edits_are_ai_assisted(self):
        manager = self.source("static/js/talena/after-interview-tabs.js")
        script = self.source("static/js/talena/candidate-ai-badges.js")
        self.assertIn('dataset.managerReportManuallyEdited', manager)
        self.assertIn('field.dataset.managerReportManuallyEdited === "true"', script)
        self.assertIn('data-after-interview-ai-origin', script)
        self.assertIn('body.dataset.afterInterviewAiOrigin = "true"', manager)

    def test_badges_only_at_direct_ai_text_headings(self):
        script = self.source("static/js/talena/candidate-ai-badges.js")
        self.assertNotIn('["[data-cognitive-interpretation-root]", "h2.insight-summary-title"', script)
        self.assertNotIn('["[data-motivation-ai-root]", "h2.insight-summary-title"', script)
        self.assertNotIn('["[data-personality-ai-root]", "[data-personality-ai-title]"', script)
        self.assertNotIn('["#candidate-insights-panel-prepare-interview > .final-output-card"', script)
        self.assertNotIn('["[data-post-interview-section]", "h3.insight-summary-title"', script)
        self.assertNotIn('["[data-personality-questions-root]", ".personality-questions-header h2"', script)
        self.assertIn('["[data-cognitive-interpretation-root] .purpose-fit-section"', script)
        self.assertIn('["[data-motivation-ai-root] .purpose-fit-section"', script)
        self.assertIn('["[data-pre-interview-content] > .purpose-fit-section:first-child"', script)
        self.assertIn('["[data-post-interview-content] > .purpose-fit-section:first-child"', script)

    def test_ai_badge_typography_is_smaller_and_lighter(self):
        style = self.source("static/css/talena/pages/candidate-eyebrows.css")
        self.assertIn("font-size: .62rem;", style)
        self.assertIn("font-weight: 550;", style)
        self.assertIn("font-size: .6rem;", style)

    def test_candidate_result_portal_is_not_ai_labelled(self):
        script = self.source("static/js/talena/candidate-ai-badges.js")
        self.assertIn('[data-candidate-insights-workspace]', script)
        self.assertNotIn("candidate_results/_candidate_result_tab", script)
        self.assertNotIn(".candidate-result-portal", script)
