"""#355: scoped structured Helhetsbild evidence and stable report shape."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai import structured_overall_picture as report


class StructuredOverallPictureTests(SimpleTestCase):
    def setUp(self):
        self.owner = SimpleNamespace(candidate=SimpleNamespace(first_name="Synthetic", last_name="Candidate"))
        self.shared = {"purpose_label": "Recruitment", "context_text": "Role requires collaboration."}
        self.notes = {
            "general_notes": "Candidate explains how work is planned.",
            "question_evidence": {"items": [
                {"source": "cognitive", "question": "How did you analyse the figures?",
                 "saved_answer_or_note": "Checked the numbers twice."},
                {"source": "personality", "question": "How did you collaborate?",
                 "saved_answer_or_note": "Asked colleagues for feedback."},
            ]},
            "has_evidence": True,
        }

    def test_registers_four_independent_bilingual_admin_prompts(self):
        from apps.core.ai.prompt_templates import AI_PROMPT_REGISTRY
        for key in report.PROMPT_KEYS.values():
            self.assertIn(key, AI_PROMPT_REGISTRY)
            for lang in ("sv", "en"):
                self.assertIn("Testbild", AI_PROMPT_REGISTRY[key]["defaults"][lang])

    def test_skill_units_use_only_actual_available_areas_in_order(self):
        with patch.object(report, "extract_cognitive_results", return_value=[
            {"key": "verbal", "percentile": 45},
            {"key": "numerical", "percentile": 63},
        ]):
            units = report._subject_evidence(self.owner, "skills", "sv", self.shared, self.notes)
        self.assertEqual([unit["key"] for unit in units], ["numerical", "verbal"])
        self.assertEqual([unit["title"] for unit in units], ["Numerisk", "Verbal"])
        self.assertNotIn("logical", str(units))

    def test_motivation_uses_real_ranked_scores_without_raw_technical_heading(self):
        with patch.object(report, "extract_motivation_results", return_value=[
            {"name": "Enjoyment", "score": 3.1, "definition": "Enjoying work"},
            {"name": "Learning", "score": 4.9, "definition": "Learning"},
            {"name": "Authority", "score": 4.6, "definition": "Leadership"},
            {"name": "Quality", "score": 4.3, "definition": "Quality"},
        ]):
            units = report._subject_evidence(self.owner, "motivation", "en", self.shared, self.notes)
        self.assertEqual([u["title"] for u in units], ["Learning", "Authority", "Quality"])

    def test_question_context_stays_with_matching_category_only(self):
        notes = report._notes_for_category(self.notes, "skills")
        self.assertEqual(len(notes["question_evidence"]), 1)
        self.assertEqual(notes["question_evidence"][0]["question"], "How did you analyse the figures?")

    def test_synthesis_does_not_contain_failed_items(self):
        sections = {
            "skills": {"items": [
                {"title": "Numerisk", "testbild": "Evidence", "intervjun": "Account", "status": "completed"},
                {"title": "Logisk", "testbild": "Old", "intervjun": "Old", "status": "failed"},
            ]},
            "motivation": {"items": []}, "personality": {"items": []},
        }
        with patch.object(report, "_guidance", return_value=("Protected", "Final")):
            prompt = report._synthesis_prompt(self.owner, sections, self.shared, "sv")
        self.assertIn("Evidence", prompt)
        self.assertNotIn('"testbild": "Old"', prompt)

    def test_legacy_markdown_only_emits_completed_items(self):
        state = {"language": "sv", "sections": {
            "skills": {"items": [
                {"title": "Numerisk", "testbild": "Possible indication",
                 "intervjun": "Candidate account", "status": "completed"},
                {"title": "Logisk", "status": "failed", "testbild": "Old", "intervjun": "Old"},
            ]},
            "synthesis": {"status": "completed", "text": "Final synthesis"},
        }}
        markdown = report._legacy_markdown(state)
        self.assertIn("#### Testbild", markdown)
        self.assertIn("#### Intervjun", markdown)
        self.assertIn("Final synthesis", markdown)
        self.assertNotIn("### Logisk", markdown)

    def test_item_prompt_contains_no_unrelated_assessment_fields(self):
        with patch.object(report, "_guidance", return_value=("Protected", "Specific")):
            text = report._item_prompt(
                self.owner, "skills",
                {"key": "numerical", "title": "Numerisk",
                 "evidence": {"test": "numerical", "percentile": 63}},
                self.shared, report._notes_for_category(self.notes, "skills"), "sv"
            )
        self.assertIn("How did you analyse the figures?", text)
        self.assertNotIn("How did you collaborate?", text)
        self.assertNotIn("personal_email", text)

    def test_selected_personality_themes_reject_unknown_traits(self):
        traits = [
            {"key": "Empathy", "title": "Empathy", "evidence": {"summary": "Likes cooperation"}},
            {"key": "Planning", "title": "Planning", "evidence": {"summary": "Organises activities"}},
        ]
        with patch.object(report, "_guidance", return_value=("Protected", "Specific")), patch.object(
            report, "_completion", return_value={"themes": [
                {"title": "Collaboration in practice", "traits": ["Empathy", "nonexistent"]},
                {"title": "Planning and execution", "traits": ["Planning"]},
            ]}
        ):
            selected = report._theme_selection(self.owner, self.shared, traits, self.notes, "en")
        self.assertEqual(selected[0]["traits"], ["Empathy"])
        self.assertEqual(len(selected), 2)
