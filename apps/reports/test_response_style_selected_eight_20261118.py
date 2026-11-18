"""#435 follow-up: both response-style views use exactly eight selected traits."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import SimpleTestCase

from apps.reports.libraries.personality.communication_guidance import (
    REQUIRED_PROFILE_TRAITS,
    PROFILE_MIDDLE_THRESHOLD,
    PROFILE_CLEAR_THRESHOLD,
    build_static_communication_guidance,
)
from apps.reports.libraries.personality.content import TRAIT_PROFILE_CONTENT
from apps.processes.project_personality_trait_selection import (
    REQUIRED_PROJECT_TRAITS,
    save_project_personality_trait_overrides,
    project_response_style_trait_names,
)


class EightSelectedTraitsProfileTests(SimpleTestCase):
    def setUp(self):
        self.traits = list(TRAIT_PROFILE_CONTENT)
        self.assertGreaterEqual(len(self.traits), 18)
        self.selected = self.traits[:8]

    def profile(self, selected_scores, other_score=5):
        return {"sections": [
            {"traits": [
                {"name": key, "sten": score}
                for key, score in zip(self.selected, selected_scores)
            ] + [
                {"name": key, "sten": other_score}
                for key in self.traits[8:]
            ]}
        ]}

    def test_thresholds_and_selected_trait_count(self):
        self.assertEqual(REQUIRED_PROFILE_TRAITS, 8)
        self.assertEqual(REQUIRED_PROJECT_TRAITS, 8)
        self.assertEqual(PROFILE_MIDDLE_THRESHOLD, 4)
        self.assertEqual(PROFILE_CLEAR_THRESHOLD, 5)

    def test_four_middle_traits_yields_situational(self):
        # Four middle, four clear. The other ten (clear) must not affect it.
        out = build_static_communication_guidance(
            self.profile([4, 5, 6, 7, 1, 2, 9, 10], other_score=9),
            [], language="sv", selected_traits=self.selected,
        )
        self.assertEqual(out["profile_title"], "Situationsbaserad profil")
        self.assertEqual(out["profile_status"], "middle")
        self.assertEqual(out["middle_trait_count"], 4)
        self.assertEqual(out["clear_trait_count"], 4)
        self.assertEqual(out["available_trait_count"], 8)

    def test_five_clear_traits_yields_clear_in_both_languages(self):
        profile = self.profile([1, 2, 3, 8, 9, 4, 5, 7], other_score=5)
        sv = build_static_communication_guidance(
            profile, [], language="sv", selected_traits=self.selected,
        )
        en = build_static_communication_guidance(
            profile, [], language="en", selected_traits=self.selected,
        )
        self.assertEqual(sv["profile_title"], "Tydlig profil")
        self.assertEqual(en["profile_title"], "Clear profile")
        self.assertEqual(sv["clear_trait_count"], 5)
        self.assertEqual(sv["middle_trait_count"], 3)

    def test_selected_names_not_all_18_control_classification(self):
        # All other ten are in the middle but the selected 8 are clear.
        out = build_static_communication_guidance(
            self.profile([1, 2, 3, 8, 9, 10, 2, 3], other_score=5),
            [], selected_traits=self.selected,
        )
        self.assertEqual(out["profile_status"], "clear")
        # Conversely, middle among all 18 must not create a situational
        # classification when all selected traits are clear.

    def test_exactly_eight_distinct_selected_with_all_scores_required(self):
        profile = self.profile([4, 5, 6, 7, 1, 2, 8, 9])
        for selected in (None, [], self.selected[:7],
                         self.selected[:7] + [self.selected[0]],
                         self.selected + [self.traits[8]]):
            with self.subTest(selected=selected):
                result = build_static_communication_guidance(
                    profile, [], selected_traits=selected,
                )
                self.assertEqual(result["profile_status"], "unavailable")
                self.assertEqual(result["profile_title"], "")

        profile["sections"][0]["traits"] = [
            item for item in profile["sections"][0]["traits"]
            if item["name"] != self.selected[0]
        ]
        result = build_static_communication_guidance(
            profile, [], selected_traits=self.selected,
        )
        self.assertEqual(result["profile_status"], "unavailable")
        self.assertEqual(result["available_trait_count"], 7)

    def test_social_desirability_remains_independent_of_project_selection(self):
        guidance = build_static_communication_guidance(
            self.profile([2] * 8),
            [{"key": "social_desirability", "available": True, "value": 2}],
            language="sv", selected_traits=[],
        )
        self.assertEqual(guidance["profile_status"], "unavailable")
        self.assertTrue(guidance["social_desirability_available"])
        self.assertIn(
            "självkritisk",
            guidance["social_desirability_guidance"]["interpretation"],
        )

    def test_shared_process_selection_is_the_single_source(self):
        fake_process = SimpleNamespace(pk=123)
        with patch(
            "apps.processes.project_personality_trait_selection."
            "get_project_personality_trait_selection",
            return_value=[{"name": key} for key in self.selected],
        ) as get_selection:
            self.assertEqual(
                project_response_style_trait_names(fake_process),
                self.selected,
            )
            get_selection.assert_called_once_with(
                fake_process, generate=False,
            )
        with patch(
            "apps.processes.project_personality_trait_selection."
            "get_project_personality_trait_selection",
            return_value=[{"name": key} for key in self.selected[:5]],
        ):
            self.assertEqual(
                project_response_style_trait_names(fake_process), [],
            )

    def test_manual_project_selection_requires_eight_or_auto_mode(self):
        role_context = SimpleNamespace(
            purpose_data={}, save=Mock(),
        )
        with self.assertRaisesRegex(ValueError, "exactly eight"):
            save_project_personality_trait_overrides(
                role_context, purpose_key="hiring",
                context_text="Synthetic role", selected_traits=self.selected[:7],
            )
        self.assertEqual(role_context.purpose_data, {})
        saved = save_project_personality_trait_overrides(
            role_context, purpose_key="hiring",
            context_text="Synthetic role", selected_traits=self.selected,
        )
        self.assertEqual(saved, self.selected)
        self.assertEqual(
            role_context.purpose_data["hiring"]["personality_question_traits"],
            self.selected,
        )
        # Unchecking all explicitly chooses the AI recommendation path,
        # which itself must return exactly eight unique approved traits.
        self.assertEqual(save_project_personality_trait_overrides(
            role_context, purpose_key="hiring",
            context_text="Synthetic role", selected_traits=[],
        ), [])

    def test_both_candidate_paths_supply_the_same_project_eight(self):
        # Contract check avoids an external Sova request or a database here.
        from pathlib import Path
        from django.conf import settings
        source = (Path(settings.BASE_DIR) / "apps/processes/views.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            source.count("selected_traits=project_response_style_trait_names(process)"),
            3,
        )
