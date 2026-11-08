"""Regression checks for the customer-facing copy changes in #440.

The test deliberately scopes terminology changes to presentation. Sova assessment
identifiers, persisted interpretation JSON and the #437 questions UI are untouched.
"""

from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override


class Ticket440CopyTests(SimpleTestCase):
    def source(self, relative_path):
        return (Path(settings.BASE_DIR) / relative_path).read_text(encoding="utf-8")

    def test_insight_headers_and_introductions_share_one_workspace_source(self):
        source = self.source(
            "templates/customer/processes/partials/candidate_insights/_workspace.html"
        )
        self.assertIn('{% trans "Insikter" as candidate_insights_eyebrow %}', source)
        self.assertIn(
            "Utforska insikter kopplat till personens motivationsresultat.", source
        )
        self.assertIn(
            "Utforska insikter kopplat till personens färdighetsresultat.", source
        )
        self.assertIn(
            "Explore insights based on the person's motivation assessment results.",
            source,
        )
        self.assertIn(
            "Explore insights based on the person's skills assessment results.", source
        )
        self.assertEqual(source.count("section_eyebrow=candidate_insights_eyebrow"), 4)

    def test_motivation_title_is_localized_even_for_existing_saved_ai_title(self):
        template = (
            "customer/processes/partials/"
            "candidate_insights/motivation/_interpretation.html"
        )
        context = {
            "motivation_interpretation": {
                "title": "Motivation interpretation",
                "interpretation": "Saved assessment interpretation.",
            },
            "motivation_interpretation_status": "completed",
        }
        with override("sv"):
            html = render_to_string(template, context)
            self.assertRegex(
                html,
                r'<h2 class="insight-summary-title mb-1">\s*Motivationstolkning\s*</h2>',
            )
        with override("en"):
            html = render_to_string(template, context)
            self.assertIn("Motivation interpretation", html)

    def test_skills_interpretation_has_swedish_copy_without_touching_question_label(self):
        source = self.source(
            "templates/customer/processes/partials/candidate_insights/tabs/_cognitive.html"
        )
        self.assertIn("Färdighetstolkning", source)
        self.assertIn(
            "En praktisk tolkning av de tillgängliga färdighetsresultaten", source
        )
        self.assertIn("Färdighetstester kan ge ytterligare underlag", source)
        self.assertIn("Tolkar färdighetsresultaten…", source)
        self.assertIn("{{ cognitive_interview_meta.questions_label }}", source)
        self.assertNotIn("Färdighetsfrågor", source)

        js_template = self.source("templates/customer/processes/process_base.html")
        self.assertIn(
            '{% trans "Färdighetstolkning" as js_cognitive_interpretation %}',
            js_template,
        )

    def test_sova_report_urls_and_permissions_are_unchanged(self):
        source = self.source(
            "templates/customer/processes/partials/candidate_insights/_workspace.html"
        )
        self.assertIn("Sovas originalrapporter", source)
        self.assertIn("Original Sova reports", source)
        self.assertIn("{% if not is_historical and sova_reports_for_ui %}", source)
        self.assertIn('href="{{ report.url }}"', source)
        self.assertIn('rel="noopener noreferrer"', source)

    def test_person_terminology_is_local_to_explanatory_copy(self):
        motivation = self.source(
            "templates/customer/processes/partials/candidate_insights/motivation/_results.html"
        )
        self.assertIn("personens mer framträdande", motivation)
        self.assertIn("personens motivationsprofil", motivation)
        self.assertIn("personens egna reflektioner", motivation)
        self.assertIn(
            '{% trans "The candidate" as motivation_candidate_fallback %}',
            motivation,
        )
        catalogue = self.source("locale/sv/LC_MESSAGES/django.po")
        self.assertIn('msgstr "Färdighetstolkning"', catalogue)
        self.assertIn(
            'msgstr "Generera en ny färdighetstolkning"', catalogue
        )

    def test_ai_labels_still_target_generated_text_only(self):
        source = self.source("static/js/talena/candidate-ai-badges.js")
        self.assertIn("[data-motivation-ai-interpretation]", source)
        self.assertIn("[data-cognitive-ai-interpretation]", source)
        self.assertNotIn(
            '["[data-cognitive-interpretation-root]", "h2.insight-summary-title"',
            source,
        )
