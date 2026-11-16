"""#504: refreshed pre-interview content must have the same response styles as Personality."""
from types import SimpleNamespace

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
