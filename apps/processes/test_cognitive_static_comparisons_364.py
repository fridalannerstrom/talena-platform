"""#364: existing approved cognitive comparisons in customer/admin result cards."""
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from apps.processes.services.cognitive_insights import (
    build_cognitive_insight_results,
)
from apps.reports.libraries.cognitive.candidate_result_content import (
    candidate_cognitive_level_key,
    resolve_candidate_skill_text,
)


class CognitiveStaticComparisonTests(SimpleTestCase):
    def _results(self, percentile, key="numerical", lang="sv"):
        params = {
            "verbal_percentile": None,
            "logical_percentile": None,
            "numerical_percentile": None,
            "language_code": lang,
        }
        params[f"{key}_percentile"] = percentile
        results = build_cognitive_insight_results(**params)
        return next(result for result in results if result["key"] == key)

    def _render(self, language, numerical=50, logical=None, verbal=None):
        with override(language):
            results = build_cognitive_insight_results(
                numerical_percentile=numerical,
                logical_percentile=logical,
                verbal_percentile=verbal,
            )
            return render_to_string(
                "customer/processes/partials/candidate_insights/cognitive/_results.html",
                {"candidate_insights": {"cognitive_results": results}},
            )

    def test_every_boundary_uses_the_shared_approved_candidate_norm_mapping(self):
        cases = (
            (0, "very-low"),
            (9, "very-low"),
            (10, "low"),
            (24, "low"),
            (25, "average"),
            (74, "average"),
            (75, "high"),
            (90, "high"),
            (91, "very-high"),
            (100, "very-high"),
        )
        for language in ("sv", "en"):
            for test_key in ("numerical", "logical", "verbal"):
                for percentile, band in cases:
                    with self.subTest(language=language, key=test_key, percentile=percentile):
                        result = self._results(percentile, test_key, language)
                        self.assertTrue(result["completed"])
                        self.assertEqual(result["level_key"], band)
                        self.assertEqual(result["level_key"], candidate_cognitive_level_key(percentile))
                        self.assertTrue(result["interpretation"])
                        # The candidate-facing text is separately phrased in "du"
                        # but must resolve the same approved norm band and subject.
                        self.assertTrue(resolve_candidate_skill_text(test_key, percentile, language))

    def test_norm_text_changes_at_exact_boundaries(self):
        for language in ("sv", "en"):
            for key in ("numerical", "logical", "verbal"):
                for before, after in ((9, 10), (24, 25), (74, 75), (90, 91)):
                    with self.subTest(language=language, key=key, boundary=after):
                        left = self._results(before, key, language)
                        right = self._results(after, key, language)
                        self.assertNotEqual(left["interpretation"], right["interpretation"])
                        self.assertNotEqual(left["level_key"], right["level_key"])

    def test_static_text_appears_once_beneath_norm_graph_for_completed_assessments(self):
        for language in ("sv", "en"):
            with self.subTest(language=language):
                markup = self._render(language, numerical=50, logical=10, verbal=91)
                for key in ("numerical", "logical", "verbal"):
                    self.assertEqual(markup.count(f'data-cognitive-static-comparison="{key}"'), 1)
                    expected = self._results(
                        {"numerical": 50, "logical": 10, "verbal": 91}[key], key, language
                    )["interpretation"]
                    self.assertEqual(markup.count(expected), 1)
                self.assertNotIn("AI-generated insight", markup)
                self.assertNotIn("AI-genererad insikt", markup)
                self.assertIn("cognitive-comparison__bar", markup)
                self.assertIn("cognitive-result-card__static-comparison", markup)
                self.assertLess(
                    markup.index('class="cognitive-comparison__bar"'),
                    markup.index('data-cognitive-static-comparison="logical"'),
                )

    def test_missing_results_have_no_comparison_or_fabricated_findings(self):
        for language in ("sv", "en"):
            with self.subTest(language=language):
                markup = self._render(language, numerical=None, logical=None, verbal=None)
                self.assertEqual(markup.count("cognitive-result-card--missing"), 3)
                self.assertNotIn("data-cognitive-static-comparison=", markup)
                self.assertNotIn("The candidate may find", markup)
                self.assertNotIn("Kandidaten kan ha lättare", markup)
                self.assertNotIn("Kandidaten har sannolikt", markup)

    def test_one_completed_assessment_does_not_create_comparison_for_missing_ones(self):
        markup = self._render("sv", numerical=40, logical=None, verbal=None)
        self.assertEqual(markup.count('data-cognitive-static-comparison="numerical"'), 1)
        self.assertNotIn('data-cognitive-static-comparison="logical"', markup)
        self.assertNotIn('data-cognitive-static-comparison="verbal"', markup)
