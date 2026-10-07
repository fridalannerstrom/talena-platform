from copy import deepcopy

from django.test import SimpleTestCase

from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)
from apps.reports.libraries.personality import profile_contrasts
from apps.core.ai.response_style_guidance import (
    apply_response_style_guidance_event,
)


class ProfileContrastRuleTests(SimpleTestCase):
    def _profile(self, scores=None, *, duplicate_keys=()):
        scores = scores or {}
        duplicate_keys = set(duplicate_keys)
        sections = []
        for section in TRAIT_AND_INDICATOR_PROFILE["sections"]:
            traits = []
            for trait_definition in section["traits"]:
                trait_key = trait_definition["trait_name"].lower().replace("-", "_").replace(" ", "_")
                trait = {
                    "canonical_key": trait_key,
                    "label": trait_definition["trait_name"],
                    "sten": scores.get(trait_key),
                    "mapping_status": "matched" if trait_key not in duplicate_keys else "duplicate",
                    "indicators": [],
                }
                for name in trait_definition["indicators"]:
                    key = name.lower().replace("&", "and").replace("-", " ").replace(" ", "_")
                    trait["indicators"].append({
                        "canonical_key": key,
                        "label": name,
                        "sten": scores.get(key),
                        "mapping_status": "matched" if key not in duplicate_keys else "duplicate",
                    })
                traits.append(trait)
            sections.append({"traits": traits})
        return {"sections": sections}


class ProfileContrastCatalogTests(ProfileContrastRuleTests):
    def test_reviewed_catalog_does_not_activate_pairs_below_threshold(self):
        scores = {"sensitivity": 4, "teamwork": 7}
        result = profile_contrasts.build_profile_contrast_analysis(
            self._profile(scores), language="sv"
        )
        self.assertEqual(result["activated_contrasts"], [])
        self.assertEqual(result["catalog_version"], profile_contrasts.CONTRAST_CATALOG_VERSION)
        self.assertTrue(result["neutral_message"])

    def test_expert_approved_pair_activates_with_values_and_source(self):
        result = profile_contrasts.build_profile_contrast_analysis(
            self._profile({"sensitivity": 8, "teamwork": 3}), language="sv"
        )
        hit = next(
            item for item in result["activated_contrasts"]
            if item["id"] == "cooperative_sensitivity_teamwork"
        )
        self.assertEqual((hit["left_sten"], hit["right_sten"]), (8, 3))
        self.assertEqual(hit["rule_version"], "veronika-2026-10-07-v1")
        self.assertIn("Veronika", hit["approval_source"])
        self.assertEqual(hit["strength"], 1)
        self.assertEqual(hit["right_dimensions"], "Sensitivity")
        self.assertEqual(hit["left_dimensions"], "Teamwork")
        self.assertEqual(hit["context_dimensions"], "")

    def test_middle_score_is_shown_as_context_not_as_a_pole(self):
        result = profile_contrasts.build_profile_contrast_analysis(
            self._profile({"sensitivity": 6, "teamwork": 1}), language="sv"
        )
        hit = next(
            item for item in result["activated_contrasts"]
            if item["id"] == "cooperative_sensitivity_teamwork"
        )
        self.assertEqual(hit["right_dimensions"], "")
        self.assertEqual(hit["left_dimensions"], "Teamwork")
        self.assertEqual(hit["context_dimensions"], "Sensitivity")

    def test_approved_pair_uses_only_its_versioned_rule_and_available_data(self):
        catalog = list(deepcopy(profile_contrasts.CONTRAST_CATALOG))
        catalog[0].update({
            "approved": True,
            "activation_rule": {
                "mode": "left_higher_by",
                "minimum_difference": 4,
            },
            "rule_version": "expert-rule-v1",
            "approval_source": "psychometric-review",
            "display_priority": 10,
        })
        profile = self._profile({"sensitivity": 9, "teamwork": 3})
        with self.settings():  # isolate the global catalogue override
            original = profile_contrasts.CONTRAST_CATALOG
            profile_contrasts.CONTRAST_CATALOG = tuple(catalog)
            try:
                first = profile_contrasts.build_profile_contrast_analysis(profile)
                second = profile_contrasts.build_profile_contrast_analysis(profile)
            finally:
                profile_contrasts.CONTRAST_CATALOG = original

        self.assertEqual(first["activated_contrasts"], second["activated_contrasts"])
        self.assertEqual(len(first["activated_contrasts"]), 1)
        self.assertEqual(first["activated_contrasts"][0]["id"], catalog[0]["id"])
        self.assertEqual(first["activated_contrasts"][0]["left_sten"], 9)
        self.assertEqual(first["activated_contrasts"][0]["right_sten"], 3)

    def test_duplicate_dimensions_are_not_used_or_double_counted(self):
        profile = self._profile(
            {"sensitivity": 8, "teamwork": 2},
            duplicate_keys={"sensitivity"},
        )
        result = profile_contrasts.build_profile_contrast_analysis(profile)
        self.assertEqual(result["available_dimension_count"], 1)
        self.assertEqual(result["ambiguous_dimension_keys"], [])
        self.assertFalse(result["show_middle_profile"])

    def test_middle_profile_requires_ten_results_and_sufficient_coverage(self):
        all_keys = []
        for section in TRAIT_AND_INDICATOR_PROFILE["sections"]:
            for trait in section["traits"]:
                all_keys.append(trait["trait_name"].lower().replace("-", "_").replace(" ", "_"))
                all_keys.extend(
                    name.lower().replace("&", "and").replace("-", " ").replace(" ", "_")
                    for name in trait["indicators"]
                )
        middle_scores = {key: 5 for key in all_keys[:36]}
        result = profile_contrasts.build_profile_contrast_analysis(
            self._profile(middle_scores), language="en"
        )
        self.assertTrue(result["show_middle_profile"])
        self.assertEqual(result["middle_profile_count"], 36)
        self.assertIn("4–7", result["middle_profile_note"])

    def test_ai_event_can_only_phrase_supplied_approved_pairs(self):
        allowed = [{
            "id": "approved-pair",
            "left_label": "Sensitivity",
            "left_sten": 8,
            "right_label": "Teamwork",
            "right_sten": 3,
            "rule_version": "expert-v1",
        }]
        guidance = {"profile_contrasts": []}

        result = apply_response_style_guidance_event(
            guidance,
            {
                "type": "profile_contrasts",
                "items": [
                    {
                        "id": "approved-pair",
                        "question": "Could this vary by situation?",
                        "left_sten": 1,
                    },
                    {
                        "id": "invented-pair",
                        "question": "An unsupported claim.",
                    },
                ],
            },
            allowed_profile_contrasts=allowed,
        )

        self.assertEqual(len(result["profile_contrasts"]), 1)
        self.assertEqual(result["profile_contrasts"][0]["left_sten"], 8)
        self.assertEqual(
            result["profile_contrasts"][0]["question"],
            "Could this vary by situation?",
        )

    def test_incomplete_or_non_middle_profiles_get_neutral_middle_state(self):
        profile = self._profile({key: 5 for key in [
            "cooperative", "sensitivity", "teamwork", "agreeableness",
            "empathy", "tolerance", "listening", "warmth",
            "supporting", "developing_others",
        ]})
        result = profile_contrasts.build_profile_contrast_analysis(profile)
        self.assertFalse(result["show_middle_profile"])
        self.assertEqual(result["middle_profile_note"], "")
        self.assertTrue(result["insufficient_data_message"])
