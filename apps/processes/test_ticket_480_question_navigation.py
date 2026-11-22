"""#480: Interview questions are only visible in Prepare for interview.

The per-assessment generation hooks remain mounted (but non-navigable) so
questions can continue to stream and refresh the combined interview plan.
"""
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.test import SimpleTestCase

from apps.processes.views import build_combined_candidate_questions


TABS = "templates/customer/processes/partials/candidate_insights/tabs/"


class InterviewQuestionNavigationTests(SimpleTestCase):
    def _source(self, name):
        return (Path(settings.BASE_DIR) / TABS / name).read_text(encoding="utf-8")

    def test_no_duplicate_questions_tab_or_panel_in_assessment_subnavigation(self):
        for name in ("_personality.html", "_motivation.html", "_cognitive.html"):
            with self.subTest(template=name):
                source = self._source(name)
                self.assertNotIn('data-insights-subtab="questions"', source)
                self.assertNotIn('data-insights-subpanel="questions"', source)
                self.assertNotIn('aria-controls="personality-subpanel-questions"', source)
                self.assertNotIn('aria-controls="motivation-subpanel-questions"', source)
                self.assertNotIn('aria-controls="cognitive-subpanel-questions"', source)
                # Results, interpretation and candidate reflections are unchanged.
                self.assertIn('data-insights-subtab="results"', source)
                self.assertIn('data-insights-subtab="interpretation"', source)

    def test_hidden_generation_hooks_survive_for_all_three_assessments(self):
        configs = (
            ("_personality.html", "personality", "data-personality-questions-root"),
            ("_motivation.html", "motivation", "data-motivation-questions-root"),
            ("_cognitive.html", "cognitive", "data-cognitive-questions-root"),
        )
        for filename, area, hook in configs:
            with self.subTest(area=area):
                source = self._source(filename)
                self.assertIn(
                    f'class="d-none" hidden aria-hidden="true" data-interview-questions-generator="{area}"',
                    source,
                )
                if area == "personality":
                    # Personality root lives in a nested partial.
                    self.assertIn('personality/_questions.html', source)
                else:
                    self.assertIn(hook, source)
                self.assertNotIn(f'id="{area}-subpanel-questions"', source)

    def test_saved_questions_still_feed_prepare_for_interview(self):
        owner = SimpleNamespace(
            ai_personality_questions={
                "questions": [{"question": "Personality follow-up", "traits": ["Empathy"]}],
            },
            ai_personality_questions_status="completed",
            ai_motivation_questions={
                "questions": [{"question": "Motivation follow-up"}],
            },
            ai_motivation_questions_status="completed",
            ai_motivation_interpretation={},
            ai_cognitive_questions={
                "questions": [{"question": "Cognitive follow-up"}],
            },
            ai_cognitive_questions_status="completed",
            ai_cognitive_interpretation={},
        )
        result = build_combined_candidate_questions(owner)
        self.assertEqual(
            {section["key"]: section["questions"][0]["question"] for section in result["sections"]},
            {
                "personality": "Personality follow-up",
                "motivation": "Motivation follow-up",
                "cognitive": "Cognitive follow-up",
            },
        )
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(next(section for section in result["sections"] if section["key"] == "cognitive")["questions"][0]["traits"], [])

        prepare = self._source("_questions.html")
        self.assertIn("interview_combined_sections", prepare)
        self.assertIn("section.questions", prepare)
        self.assertIn("item.traits", prepare)

    def test_generation_and_refresh_js_remains_available(self):
        source = (
            Path(settings.BASE_DIR) / "templates/customer/processes/process_base.html"
        ).read_text(encoding="utf-8")
        for hook in (
            "[data-personality-questions-root]",
            "[data-motivation-questions-root]",
            "[data-cognitive-questions-root]",
            "[data-combined-questions-root]",
        ):
            with self.subTest(hook=hook):
                self.assertIn(hook, source)
        self.assertIn("candidate-ai-content-updated", source)
        self.assertIn("refreshCandidateCombinedQuestions", source)
