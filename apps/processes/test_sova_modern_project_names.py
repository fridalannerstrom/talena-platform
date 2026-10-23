"""Regression tests based on the actual 31 project titles in Sova Modern Projects."""
from itertools import combinations

from django.test import SimpleTestCase

from apps.processes.services.process_recommendations import (
    TEST_ORDER,
    extract_tests_from_project_name,
    normalize_test_combination,
    resolve_sova_template,
)


# These titles match the projects shown in the Talena Modern Projects account.
# Ordering of V/N/L in names is not necessarily the same as TEST_ORDER.
MODERN_PROJECT_NAMES = [
    "MQ + V + N + L",
    "MQ + N + L",
    "MQ + V + L",
    "MQ + V + N",
    "MQ + N",
    "MQ + V",
    "MQ + L",
    "PQ + MQ + V + L",
    "PQ + MQ + V + N",
    "N + L",
    "V + L",
    "V + N",
    "PQ + MQ + N + L",
    "PQ + MQ + L",
    "PQ + MQ + N",
    "PQ + MQ + V",
    "L",
    "N",
    "V",
    "MQ",
    "PQ + V",
    "PQ + N",
    "PQ + V + N",
    "PQ + N + L",
    "PQ",
    "PQ + L + V",
    "V + N + L",
    "PQ + V + N + L",
    "PQ + L",
    "PQ + MQ",
    "PQ + MQ + V + N + L",
]

CODES = {
    "PQ": "personality",
    "MQ": "motivation",
    "V": "verbal",
    "L": "logical",
    "N": "numerical",
}


class SovaModernProjectNamesTests(SimpleTestCase):
    def test_actual_modern_projects_cover_all_31_combinations_exactly_once(self):
        self.assertEqual(len(MODERN_PROJECT_NAMES), 31)

        project_cards = []
        parsed = []
        for name in MODERN_PROJECT_NAMES:
            expected = normalize_test_combination(
                [CODES[token.strip()] for token in name.split("+")]
            )
            actual = normalize_test_combination(extract_tests_from_project_name(name))
            self.assertEqual(actual, expected, msg=name)
            parsed.append(actual)
            project_cards.append({
                "title": name,
                "project_code": name,
                "tests": extract_tests_from_project_name(name),
            })

        all_combinations = {
            tuple(items)
            for size in range(1, len(TEST_ORDER) + 1)
            for items in combinations(TEST_ORDER, size)
        }
        self.assertEqual(set(parsed), all_combinations)
        self.assertEqual(len(set(parsed)), len(parsed))

        # Simulate selecting every possible test combination in Talena's wizard.
        for combination in all_combinations:
            with self.subTest(selection=combination):
                match = resolve_sova_template(combination, project_cards)
                self.assertIsNotNone(match)
                self.assertEqual(
                    normalize_test_combination(match["tests"]),
                    combination,
                )

    def test_pq_does_not_match_projects_with_extra_ability_tests(self):
        cards = [
            {"title": name, "tests": extract_tests_from_project_name(name)}
            for name in ["PQ + V", "PQ + N", "PQ + L + V", "PQ"]
        ]
        self.assertEqual(
            resolve_sova_template(["personality"], cards)["title"], "PQ"
        )

    def test_pq_mq_v_resolves_exactly(self):
        cards = [
            {"title": name, "tests": extract_tests_from_project_name(name)}
            for name in MODERN_PROJECT_NAMES
        ]
        self.assertEqual(
            resolve_sova_template(
                ["personality", "motivation", "verbal"], cards
            )["title"],
            "PQ + MQ + V",
        )

    def test_short_codes_do_not_match_inside_unrelated_words(self):
        self.assertEqual(extract_tests_from_project_name("Test pictures"), [])
        self.assertEqual(extract_tests_from_project_name("Modern Project"), [])
        self.assertEqual(
            extract_tests_from_project_name("Personlighet + Verbal förmåga"),
            ["personality", "verbal"],
        )
        self.assertEqual(
            extract_tests_from_project_name("MQ / N _ V | L"),
            ["motivation", "verbal", "logical", "numerical"],
        )
