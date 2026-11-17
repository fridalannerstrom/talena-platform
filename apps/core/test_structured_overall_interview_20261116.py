"""Regression tests for strict, server-side Helhetsbild interview-area isolation."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai import structured_overall_picture as report
from apps.core.ai.interview_note_areas import split_interview_notes_by_area


class OverallPictureInterviewAreaIsolationTests(SimpleTestCase):
    def setUp(self):
        self.notes = {
            "general_notes": (
                "### Intervjuunderlag: Personlighet\n"
                "ONLY_PERSONALITY: Jag prioriterade med hjälp av kalendern.\n\n"
                "### Intervjuunderlag: Motivation\n"
                "ONLY_MOTIVATION: Jag får energi av variation.\n\n"
                "### Intervjuunderlag: Färdighet\n"
                "ONLY_SKILLS: Jag jämförde olika siffror och upptäckte felet."
            ),
            "question_evidence": {"items": [
                {
                    "source": "personality",
                    "question": "ONLY_PERSONALITY_QUESTION",
                    "saved_answer_or_note": "ONLY_PERSONALITY_ANSWER",
                },
                {
                    "source": "motivation",
                    "question": "ONLY_MOTIVATION_QUESTION",
                    "saved_answer_or_note": "ONLY_MOTIVATION_ANSWER",
                },
                {
                    "source": "cognitive",
                    "question": "ONLY_SKILLS_QUESTION",
                    "saved_answer_or_note": "ONLY_SKILLS_ANSWER",
                },
            ]},
        }

    def test_each_area_only_receives_its_own_text_and_question_answers(self):
        expected = {
            "personality": ("ONLY_PERSONALITY:", "ONLY_PERSONALITY_QUESTION"),
            "motivation": ("ONLY_MOTIVATION:", "ONLY_MOTIVATION_QUESTION"),
            "skills": ("ONLY_SKILLS:", "ONLY_SKILLS_QUESTION"),
        }
        for category, (text, question) in expected.items():
            with self.subTest(category=category):
                scoped = report._notes_for_category(self.notes, category)
                self.assertIn(text, scoped["general_notes"])
                self.assertEqual(len(scoped["question_evidence"]), 1)
                self.assertEqual(scoped["question_evidence"][0]["question"], question)
                for other, (other_text, other_question) in expected.items():
                    if other != category:
                        self.assertNotIn(other_text, str(scoped))
                        self.assertNotIn(other_question, str(scoped))

    def test_personality_notes_can_inform_multiple_personality_themes(self):
        themes = [
            {"key": "theme_1", "title": "Planering och målfokus"},
            {"key": "theme_2", "title": "Stress och press"},
        ]
        with patch.object(
            report, "_completion", side_effect=AssertionError("No AI router should run")
        ):
            assigned = report._assign_personality_interview_evidence(
                None, themes, self.notes, "sv",
            )
        for item in assigned.values():
            self.assertIn("ONLY_PERSONALITY:", item["general_notes"])
            self.assertEqual(len(item["question_evidence"]), 1)
            self.assertNotIn("ONLY_MOTIVATION", str(item))
            self.assertNotIn("ONLY_SKILLS", str(item))
        self.assertIsNot(
            assigned["theme_1"]["question_evidence"],
            assigned["theme_2"]["question_evidence"],
        )

    def test_actual_ai_prompts_cannot_see_other_fields(self):
        items = {
            "skills": {"title": "Logisk", "evidence": {"test": "logical"}},
            "motivation": {"title": "Variation", "evidence": {"name": "Variation"}},
            "personality": {
                "title": "Planering och målfokus", "scope": "prioritering",
                "evidence": {"traits": [{"summary": "Värderar tydlig planering"}]},
            },
        }
        expected = {
            "personality": "ONLY_PERSONALITY",
            "motivation": "ONLY_MOTIVATION",
            "skills": "ONLY_SKILLS",
        }
        owner = SimpleNamespace()
        with patch.object(report, "_guidance", return_value=("Global rules", "Scoped guidance")):
            for category, item in items.items():
                with self.subTest(category=category):
                    prompt = report._item_prompt(
                        owner, category, item, {"purpose_label": "Recruitment"},
                        report._notes_for_category(self.notes, category), "sv",
                    )
                    self.assertIn("INTERVIEW MATERIAL FROM THIS AREA ONLY", prompt)
                    self.assertIn(expected[category], prompt)
                    for other, marker in expected.items():
                        if other != category:
                            self.assertNotIn(marker, prompt)

    def test_empty_area_does_not_inherit_other_areas_or_invent_interview_text(self):
        notes = {
            "general_notes": (
                "### Intervjuunderlag: Personlighet\n"
                "Only a personality account is present."
            ),
            "question_evidence": {"items": []},
        }
        scoped = report._notes_for_category(notes, "skills")
        self.assertEqual(scoped, {"general_notes": "", "question_evidence": []})
        with patch.object(report, "_completion", return_value={
            "testbild": "Testet ger en indikation.",
            "intervjun": "Påhittad intervjuberättelse.",
        }):
            testbild, interview = report._generate_validated_item(
                SimpleNamespace(), "Färdighet test evidence",
                language="sv", category="skills", notes=scoped,
            )
        self.assertEqual(testbild, "Testet ger en indikation.")
        self.assertEqual(interview, report.MISSING_INTERVIEW["sv"])

    def test_legacy_notes_are_not_guessed_into_other_areas(self):
        legacy = "Ett äldre odelat intervjuunderlag med blandade teman."
        sections = split_interview_notes_by_area(legacy)
        self.assertEqual(sections["personality"], legacy)
        self.assertEqual(sections["motivation"], "")
        self.assertEqual(sections["skills"], "")
        for category in ("skills", "motivation"):
            scoped = report._notes_for_category({
                "general_notes": legacy, "question_evidence": {"items": []},
            }, category)
            self.assertEqual(scoped["general_notes"], "")

    def test_old_prefix_and_repeated_headings_follow_existing_ui_contract(self):
        notes = (
            "Äldre osorterat underlag.\n\n"
            "### Intervjuunderlag: Motivation\nMotiv A\n\n"
            "### Intervjuunderlag: Färdighet\nNumerisk A\n\n"
            "### Intervjuunderlag: Motivation\nMotiv B"
        )
        fields = split_interview_notes_by_area(notes)
        self.assertEqual(fields["personality"], "Äldre osorterat underlag.")
        self.assertEqual(fields["motivation"], "Motiv A\n\nMotiv B")
        self.assertEqual(fields["skills"], "Numerisk A")
