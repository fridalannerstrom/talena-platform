"""#504: refreshed pre-interview content must have the same response styles as Personality."""
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from apps.processes.views import build_pre_interview_response_styles_context


RESPONSE_STYLES_TEMPLATE = (
    "customer/processes/partials/candidate_insights/personality/"
    "_response_styles_content.html"
)


class PreInterviewResponseStylesRefreshTests(SimpleTestCase):
    def test_refresh_rebuilds_existing_personality_data_in_swedish(self):
        owner = SimpleNamespace(
            sova_payload={},
            sova_activities=[{
                "activity": "Sova Personality Questionnaire",
                "status": "completed",
                "competencies": [{
                    "competency": "Social Desirability",
                    "sten": 2,
                    "sten_rounded": 2,
                }],
            }],
        )
        process = SimpleNamespace(is_historical=False)

        with override("sv"):
            context = build_pre_interview_response_styles_context(
                process, owner, language="sv",
            )
            self.assertTrue(context["has_personality_results"])
            self.assertTrue(any(
                style["key"] == "social_desirability" and style["available"]
                for style in context["response_styles"]
            ))

            html = render_to_string(RESPONSE_STYLES_TEMPLATE, {
                **context,
                "candidate": SimpleNamespace(first_name="Alex"),
                "response_styles_contrasts_heading_id": (
                    "preInterviewProfileContrastsHeading"
                ),
            })

        self.assertIn("Svarsstilar", html)
        self.assertIn("Social önskvärdhet", html)
        self.assertIn("Möjliga nyanser att utforska", html)
        self.assertIn("preInterviewProfileContrastsHeading", html)
        self.assertNotIn("Personality results are not yet available", html)

    def test_refresh_without_personality_data_does_not_invent_results(self):
        owner = SimpleNamespace(sova_payload={}, sova_activities=[])
        process = SimpleNamespace(is_historical=False)
        with override("sv"):
            context = build_pre_interview_response_styles_context(
                process, owner, language="sv",
            )
            self.assertFalse(context["has_personality_results"])
            html = render_to_string(RESPONSE_STYLES_TEMPLATE, {
                **context, "candidate": SimpleNamespace(first_name="Alex"),
            })
        self.assertIn("Det finns ännu inget personlighetsresultat", html)
        self.assertIn("Resultat ännu inte tillgängligt", html)

    def test_response_styles_and_questions_share_a_single_card(self):
        base = Path(settings.BASE_DIR) / "templates/customer/processes/partials/candidate_insights/tabs"
        interview = (base / "_final_output.html").read_text(encoding="utf-8")
        questions = (base / "_questions.html").read_text(encoding="utf-8")

        wrapper = interview.index('data-pre-interview-content-card')
        styles = interview.index('data-pre-interview-response-styles', wrapper)
        divider = interview.index('pre-interview-content-card__divider', styles)
        question_include = interview.index('tabs/_questions.html', divider)
        self.assertLess(wrapper, styles)
        self.assertLess(styles, divider)
        self.assertLess(divider, question_include)
        self.assertIn('pre-interview-content-card > .combined-questions-card', questions)
        self.assertIn('border: 0 !important;', questions)
        self.assertIn('border-top: 1px solid var(--talena-border);', questions)

    def test_pre_interview_shares_page_shell_with_personality(self):
        base = Path(settings.BASE_DIR) / (
            "templates/customer/processes/partials/candidate_insights"
        )
        interview = (base / "tabs/_final_output.html").read_text(
            encoding="utf-8"
        )
        questions = (base / "tabs/_questions.html").read_text(
            encoding="utf-8"
        )
        header = (base / "_panel_header.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('class="candidate-insights-panel candidate-insight-page"', interview)
        self.assertIn('section_title=pre_interview_title', interview)
        self.assertIn('section_eyebrow=pre_interview_eyebrow', interview)
        self.assertIn('section_description=pre_interview_description', interview)
        self.assertIn("_panel_header.html", interview)
        self.assertIn('candidate-insight-page-header', header)
        self.assertIn('candidate-insight-page-title', header)
        self.assertIn('padding: 1.25rem 1.5rem 1.5rem;', questions)
        self.assertIn('border-radius: 0;', questions)
        self.assertIn('response_styles_interview_mode=True', interview)

    def test_communication_strategy_heading_is_only_used_pre_interview(self):
        owner = SimpleNamespace(
            sova_payload={},
            sova_activities=[{
                "activity": "Sova Personality Questionnaire",
                "competencies": [{
                    "competency": "Social Desirability",
                    "sten_rounded": 2,
                }],
            }],
        )
        with override("sv"):
            context = build_pre_interview_response_styles_context(
                SimpleNamespace(is_historical=False), owner, language="sv",
            )
            context["candidate"] = SimpleNamespace(first_name="Alex")
            original = render_to_string(RESPONSE_STYLES_TEMPLATE, context)
            interview = render_to_string(
                RESPONSE_STYLES_TEMPLATE,
                {**context, "response_styles_interview_mode": True},
            )

        self.assertIn("Svarsstilar", original)
        self.assertNotIn("Kommunikationsstrategi", original)
        self.assertIn('<h2 class="insight-summary-title mb-1">', original)
        self.assertIn("Kommunikationsstrategi", interview)
        self.assertIn('<h3 class="insight-summary-sub-title mb-1">', interview)
        self.assertNotIn("<h2 class=\"insight-summary-title mb-1\">", interview)

    def test_interview_questions_use_section_eyebrow_and_larger_headings(self):
        base = Path(settings.BASE_DIR)
        questions = (
            base / "templates/customer/processes/partials/"
            "candidate_insights/tabs/_questions.html"
        ).read_text(encoding="utf-8")
        eyebrow_script = (
            base / "static/js/talena/candidate-eyebrows.js"
        ).read_text(encoding="utf-8")

        self.assertIn("data-pre-interview-questions-eyebrow", questions)
        self.assertIn("Intervjufrågor", questions)
        self.assertIn("Interview questions", questions)
        self.assertIn("combined-questions-main-title", questions)
        self.assertIn("combined-question-section__title", questions)
        self.assertIn("font-size: clamp(1.55rem, 1.95vw, 1.8rem)", questions)
        self.assertIn("font-size: clamp(1.1rem, 1.4vw, 1.2rem)", questions)
        self.assertIn("margin: 1.65rem 0 1.9rem;", questions)
        self.assertIn(
            'hasAttribute("data-pre-interview-questions-eyebrow")',
            eyebrow_script,
        )
