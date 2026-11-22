"""Regression: Personality trait tags must survive in Prepare for interview."""
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from apps.processes.views import build_combined_candidate_questions


PRE_INTERVIEW_TEMPLATE = (
    "customer/processes/partials/candidate_insights/tabs/_questions.html"
)


class PreInterviewPersonalityTraitTagsTests(SimpleTestCase):
    def _source(self):
        return SimpleNamespace(
            ai_personality_questions={
                "questions": [
                    {
                        "question": "Describe a time you worked closely with others.",
                        "traits": ["Cooperative", "Empathy"],
                        "why": "Teamwork matters for the role.",
                        "listen_for": "A concrete example.",
                    },
                    {
                        "question": "Describe an independent decision.",
                        "traits": [],
                    },
                ],
            },
            ai_personality_questions_status="completed",
            ai_motivation_questions={
                "questions": [
                    {
                        "question": "What motivates you at work?",
                        "traits": ["Fake motivation trait"],
                    }
                ]
            },
            ai_motivation_questions_status="completed",
            ai_motivation_interpretation={},
            ai_cognitive_questions={},
            ai_cognitive_interpretation={},
        )

    def _render(self, language="sv"):
        combined = build_combined_candidate_questions(self._source())
        with override(language):
            html = render_to_string(PRE_INTERVIEW_TEMPLATE, {
                "combined_question_sections": combined["sections"],
                "combined_question_count": combined["total_count"],
                "has_combined_questions": combined["has_questions"],
                "LANGUAGE_CODE": language,
                "has_personality_results": True,
                "has_motivation_results": True,
            })
        return combined, html

    def test_combined_builder_preserves_only_saved_personality_trait_associations(self):
        combined = build_combined_candidate_questions(self._source())
        personality = next(s for s in combined["sections"] if s["key"] == "personality")
        self.assertEqual(
            personality["questions"][0]["traits"], ["Cooperative", "Empathy"]
        )
        self.assertEqual(personality["questions"][1]["traits"], [])
        self.assertEqual(personality["questions"][0]["why"], "Teamwork matters for the role.")

    def test_personality_trait_tags_render_localized_under_prepare_for_interview(self):
        for language, first, second in (
            ("sv", "Samverkande", "Empati"),
            ("en", "Cooperative", "Empathy"),
        ):
            with self.subTest(language=language):
                _, html = self._render(language)
                self.assertIn("Describe a time you worked closely with others.", html)
                self.assertIn('<div class="personality-question-card__traits">', html)
                self.assertIn(f"<span>{first}</span>", html)
                self.assertIn(f"<span>{second}</span>", html)
                self.assertIn("Teamwork matters for the role.", html)
                self.assertEqual(
                    html.count('<div class="personality-question-card__traits">'),
                    1,
                )
                # Motivation tags are not personality traits and must not be shown.
                self.assertNotIn("<span>Fake motivation trait</span>", html)

    def test_old_personality_questions_without_traits_still_render(self):
        source = self._source()
        source.ai_personality_questions = {"questions": [
            {"question": "Legacy personality question without traits"},
        ]}
        combined = build_combined_candidate_questions(source)
        with override("sv"):
            html = render_to_string(PRE_INTERVIEW_TEMPLATE, {
                "combined_question_sections": combined["sections"],
                "combined_question_count": combined["total_count"],
                "has_combined_questions": combined["has_questions"],
                "LANGUAGE_CODE": "sv",
            })
        self.assertIn("Legacy personality question without traits", html)
        self.assertNotIn('class="personality-question-card__traits"', html)

    def test_pre_interview_uses_the_same_trait_chip_style_as_personality(self):
        css = (Path(settings.BASE_DIR) / "static/css/talena/polish.css").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "[data-personality-questions-root]\n.personality-question-card__traits span,",
            css,
        )
        self.assertIn(
            "[data-combined-questions-root]\n.personality-question-card__traits span {",
            css,
        )
