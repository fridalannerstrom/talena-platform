"""#401/#431: Overview starts with test evidence and mirrors existing area AI text."""
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override


TEMPLATE = "customer/processes/partials/candidate_insights/tabs/_overview.html"


class OverviewAreaInterpretationsTests(SimpleTestCase):
    def render_overview(self, *, language="sv", areas=("cognitive", "personality", "motivation"),
                        missing=(), outdated=()):
        context = {
            "LANGUAGE_CODE": language,
            "has_any_results": bool(areas),
            "is_historical": False,
            "all_assessments_completed": True,
            "candidate": SimpleNamespace(id=1),
            "process": SimpleNamespace(id=1),
            "invitation": SimpleNamespace(ai_purpose_fit={"summary": "LEGACY_OVERALL_AI_SUMMARY"}),
            "has_cognitive_assessments_in_process": "cognitive" in areas,
            "has_completed_cognitive_results": "cognitive" in areas,
            "has_ability_results": "cognitive" in areas,
            "has_personality_assessment_in_process": "personality" in areas,
            "has_personality_results": "personality" in areas,
            "has_motivation_assessment_in_process": "motivation" in areas,
            "has_motivation_results": "motivation" in areas,
            "assessment_keys_in_process": (),
            "candidate_insights": {"cognitive_results": []},
            "personality_profile": {"sections": []},
            "motivation_insights": {"motivators": []},
        }
        for key in ("cognitive", "personality", "motivation"):
            context[key + "_interpretation"] = {
                "interpretation": "" if key in missing else key.upper() + "_SOURCE_INTERPRETATION"
            }
            context[key + "_interpretation_status"] = (
                "outdated" if key in outdated else "completed"
            )
        with override(language):
            return render_to_string(TEMPLATE, context)

    def test_results_appear_before_existing_area_interpretations_in_both_languages(self):
        for language in ("sv", "en"):
            with self.subTest(language=language):
                html = self.render_overview(language=language)
                self.assertLess(
                    html.index("candidate-result-overview__grid"),
                    html.index('data-overview-interpretation-card="cognitive"'),
                )
                self.assertLess(
                    html.index('data-overview-interpretation-card="cognitive"'),
                    html.index('data-overview-interpretation-card="personality"'),
                )
                self.assertLess(
                    html.index('data-overview-interpretation-card="personality"'),
                    html.index('data-overview-interpretation-card="motivation"'),
                )
                for key in ("COGNITIVE", "PERSONALITY", "MOTIVATION"):
                    self.assertIn(key + "_SOURCE_INTERPRETATION", html)
                self.assertNotIn("LEGACY_OVERALL_AI_SUMMARY", html)
                self.assertNotIn('id="purposeFitSummary"', html)
                self.assertNotIn('id="purposeFitResult"', html)
                self.assertNotIn("js-regenerate-purpose-fit", html)
                self.assertNotIn("personality-area-summaries", html)
                self.assertIn("Sammanfattande tolkning" if language == "sv"
                              else "Summary interpretation", html)

    def test_missing_areas_have_no_card_and_missing_interpretations_use_placeholder(self):
        html = self.render_overview(areas=("motivation",), missing=("motivation",))
        self.assertIn('data-overview-interpretation-card="motivation"', html)
        self.assertNotIn('data-overview-interpretation-card="personality"', html)
        self.assertNotIn('data-overview-interpretation-card="cognitive"', html)
        self.assertIn('data-overview-interpretation-empty="motivation"', html)
        self.assertIn("Ingen tolkning har skapats", html)

    def test_outdated_interpretation_is_hidden_until_refreshed(self):
        html = self.render_overview(areas=("personality",), outdated=("personality",))
        self.assertIn('data-overview-interpretation-card="personality"', html)
        self.assertIn('data-overview-interpretation-content="personality"', html)
        self.assertIn("Tolkningen behöver uppdateras", html)
        # The stale text exists in the DOM only as a hidden source for compatibility,
        # but must not be presented as a current interpretation.
        self.assertIn("talena-overview-interpretations__text d-none", html)

    def test_empty_state_does_not_generate_a_summary(self):
        html = self.render_overview(areas=())
        self.assertIn("Inga testresultat tillgängliga ännu", html)
        self.assertNotIn('data-overview-interpretation-card=', html)

    def test_frontend_mirrors_area_sources_without_overview_ai_requests(self):
        root = Path(settings.BASE_DIR)
        js = (root / "static/js/talena/candidate-ai-badges.js").read_text(encoding="utf-8")
        template = (root / "templates/customer/processes/partials/candidate_insights/tabs/_overview.html").read_text(encoding="utf-8")
        self.assertIn("syncOverviewInterpretations", js)
        self.assertIn('data-status', js)
        for selector in (
            "[data-cognitive-ai-interpretation]",
            "[data-personality-ai-interpretation]",
            "[data-motivation-ai-interpretation]",
        ):
            self.assertIn(selector, js)
        self.assertNotIn("process_candidate_purpose_fit_stream", template)
        self.assertNotIn("process_candidate_purpose_fit_regenerate", template)
