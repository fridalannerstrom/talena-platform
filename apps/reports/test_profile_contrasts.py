from django.test import SimpleTestCase

from apps.reports.libraries.personality.definitions import (
    TRAIT_AND_INDICATOR_PROFILE,
)
from apps.reports.libraries.personality import profile_contrasts


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
    def _activated_ids(self, scores):
        result = profile_contrasts.build_profile_contrast_analysis(
            self._profile(scores), language="sv"
        )
        return result["activated_contrasts"]

    def test_high_left_low_right_activates_at_inclusive_extremes(self):
        result = self._activated_ids({"sensitivity": 8, "teamwork": 3})
        hit = next(item for item in result if item["id"] == "cooperative_sensitivity_teamwork")
        self.assertEqual((hit["left_sten"], hit["right_sten"]), (8, 3))
        self.assertEqual(hit["hypothesis"],
                         "Kan vara lyhörd för andra men behöver troligtvis inte föredra att arbeta tillsammans med dem")

    def test_high_right_low_left_activates_in_the_declared_direction(self):
        result = self._activated_ids({"tolerance": 3, "listening": 8})
        self.assertIn("empathy_tolerance_listening", {item["id"] for item in result})

    def test_opposite_direction_does_not_activate_a_one_way_pattern(self):
        result = self._activated_ids({"sensitivity": 3, "teamwork": 8})
        self.assertNotIn("cooperative_sensitivity_teamwork", {item["id"] for item in result})

    def test_seven_and_four_do_not_count_as_extremes(self):
        for scores in (
            {"sensitivity": 7, "teamwork": 3},
            {"sensitivity": 8, "teamwork": 4},
            {"sensitivity": 4, "teamwork": 7},
        ):
            result = profile_contrasts.build_profile_contrast_analysis(self._profile(scores))
            self.assertNotIn(
                "cooperative_sensitivity_teamwork",
                {item["id"] for item in result["activated_contrasts"]},
            )

    def test_middle_rule_is_removed(self):
        all_keys = []
        for section in TRAIT_AND_INDICATOR_PROFILE["sections"]:
            for trait in section["traits"]:
                all_keys.append(trait["trait_name"].lower().replace("-", "_").replace(" ", "_"))
                all_keys.extend(
                    name.lower().replace("&", "and").replace("-", " ").replace(" ", "_")
                    for name in trait["indicators"]
                )
        result = profile_contrasts.build_profile_contrast_analysis(
            self._profile({key: 5 for key in all_keys[:36]}), language="en"
        )
        self.assertEqual(result["activated_contrasts"], [])
        self.assertNotIn("show_middle_profile", result)
        self.assertNotIn("middle_profile_note", result)
        self.assertNotIn("middle_profile_count", result)

    def test_each_catalog_pair_uses_fixed_extreme_thresholds_and_direction(self):
        self.assertEqual(len(profile_contrasts.CONTRAST_CATALOG), 42)
        for entry in profile_contrasts.CONTRAST_CATALOG:
            self.assertIn(entry["high_side"], {"left", "right"})
            self.assertEqual(profile_contrasts.LOW_MAXIMUM, 3)
            self.assertEqual(profile_contrasts.HIGH_MINIMUM, 8)

    def test_duplicate_dimensions_are_not_used(self):
        result = profile_contrasts.build_profile_contrast_analysis(
            self._profile(
                {"sensitivity": 8, "teamwork": 2},
                duplicate_keys={"sensitivity"},
            )
        )
        self.assertEqual(result["activated_contrasts"], [])
        self.assertEqual(result["available_dimension_count"], 1)
