"""#439: updated candidate personality copy without undoing #431/#365/#366."""
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from apps.reports.libraries.personality.builder import build_graph_segments


OVERVIEW = "customer/processes/partials/candidate_insights/tabs/_overview.html"
PERSONALITY_RESULTS = "customer/processes/partials/candidate_insights/personality/_results.html"
NEW_SV = "Mitten är situationsbaserat, medan pilmarkörerna visar varsitt föredragna beteende."
NEW_EN = (
    "The centre indicates situation-dependent behaviour, while the arrow markers "
    "show each preferred behaviour."
)


class PersonalityCopy439Tests(SimpleTestCase):
    def _personality_data(self, language):
        trait = {
            "label": "Samarbete" if language == "sv" else "Cooperation",
            "low_pole": "Självständig" if language == "sv" else "Independent",
            "high_pole": "Samarbetsinriktad" if language == "sv" else "Collaborative",
            "graph_segments": build_graph_segments(6),
            "summary": "Testtext",
            "indicators": [],
        }
        return {"sections": [{"section_name": "Personality", "traits": [trait]}]}

    def _render_overview(self, language):
        with override(language):
            return render_to_string(OVERVIEW, {
                "LANGUAGE_CODE": language,
                "has_any_results": True,
                "all_assessments_completed": True,
                "has_personality_assessment_in_process": True,
                "has_personality_results": True,
                "personality_profile": self._personality_data(language),
                "has_motivation_assessment_in_process": False,
                "has_motivation_results": False,
                "has_cognitive_assessments_in_process": False,
                "has_completed_cognitive_results": False,
                "candidate_insights": {"cognitive_results": []},
                "personality_interpretation": {"interpretation": "Existing personality AI text"},
                "personality_interpretation_status": "completed",
                "assessment_keys_in_process": [],
            })

    def _render_results(self, language):
        with override(language):
            return render_to_string(PERSONALITY_RESULTS, {
                "LANGUAGE_CODE": language,
                "candidate": SimpleNamespace(first_name="Alex"),
                "has_personality_results": True,
                "personality_profile": self._personality_data(language),
                "response_styles": [],
                "profile_contrast_analysis": {"available_dimension_count": 0, "activated_contrasts": []},
            })

    def test_overview_and_personality_result_descriptions_match_in_both_languages(self):
        for language, expected in [("sv", NEW_SV), ("en", NEW_EN)]:
            with self.subTest(language=language):
                overview = self._render_overview(language)
                results = self._render_results(language)
                self.assertIn(expected, overview)
                self.assertIn(expected, results)
                self.assertNotIn("Mitten är neutral", overview + results)
                self.assertNotIn("Left pole", overview + results)
                self.assertNotIn("personality-overview-chart__legend", overview + results)
                # Remove only decorative labels, not real graph positions.
                self.assertIn("personality-overview-item__segment--selected", overview + results)
                self.assertIn("personality-overview-item__arrow", overview + results)
                self.assertIn('class="personality-trait-card__pole-label"', results)

        results_sv = self._render_results("sv")
        results_en = self._render_results("en")
        self.assertIn(
            "Utforska personens övergripande personlighetsdrag och underliggande indikatorer.",
            results_sv,
        )
        self.assertIn(
            "Explore the person's main personality traits and underlying indicators.",
            results_en,
        )

    def test_current_overview_decisions_survive_and_legacy_overview_blocks_stay_gone(self):
        overview_sv = self._render_overview("sv")
        self.assertIn("Sammanfattande tolkning", overview_sv)
        self.assertIn("Existing personality AI text", overview_sv)
        self.assertNotIn("Vad som stödjer syftet", overview_sv)
        self.assertNotIn("Potentiella styrkor", overview_sv)
        self.assertNotIn('id="purposeFitSummary"', overview_sv)
        self.assertNotIn("js-regenerate-purpose-fit", overview_sv)
        self.assertIn("candidate-result-overview__grid", overview_sv)

    def test_parent_workspace_heading_copy_is_approved_and_not_legacy(self):
        workspace = (
            Path(settings.BASE_DIR) /
            "templates/customer/processes/partials/candidate_insights/_workspace.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Utforska insikter kopplat till personens personlighetsresultat.",
            workspace,
        )
        self.assertIn(
            "Explore insights based on the person's personality assessment results.",
            workspace,
        )
        self.assertNotIn(
            '{% trans "Explore the candidate’s overall personality traits', workspace,
        )
        # The panel is provided through the included _final_output partial.
        self.assertIn(
            '{% include "customer/processes/partials/candidate_insights/tabs/_final_output.html" %}',
            workspace,
        )
