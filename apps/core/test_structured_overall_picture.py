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
        with patch("apps.core.ai.cognitive_interpretation.extract_cognitive_results", return_value=[
            {"key": "verbal", "percentile": 45},
            {"key": "numerical", "percentile": 63},
        ]):
            units = report._subject_evidence(self.owner, "skills", "sv", self.shared, self.notes)
        self.assertEqual([unit["key"] for unit in units], ["numerical", "verbal"])
        self.assertEqual([unit["title"] for unit in units], ["Numerisk", "Verbal"])
        self.assertNotIn("logical", str(units))
        self.assertTrue(all("percentile" not in u["evidence"] for u in units))

    def test_motivation_uses_real_ranked_scores_without_raw_technical_heading(self):
        with patch("apps.core.ai.motivation_interpretation.extract_motivation_results", return_value=[
            {"name": "Enjoyment", "score": 3.1, "definition": "Enjoying work"},
            {"name": "Learning", "score": 4.9, "definition": "Learning"},
            {"name": "Authority", "score": 4.6, "definition": "Leadership"},
            {"name": "Quality", "score": 4.3, "definition": "Quality"},
        ]):
            units = report._subject_evidence(self.owner, "motivation", "en", self.shared, self.notes)
        self.assertEqual([u["title"] for u in units], ["Learning", "Authority", "Quality"])
        self.assertTrue(all("score" not in u["evidence"] for u in units))

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
                 "evidence": {"test": "numerical", "approved_result_interpretation": "Approved result meaning"}},
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

    def test_full_orchestration_keeps_units_separate_and_completes_synthesis_last(self):
        self.owner.ai_post_interview_decision_support = {}
        categories = {
            "skills": [{"key": "numerical", "title": "Numerisk",
                        "evidence": {"approved_result_interpretation": "Approved numeric interpretation"}}],
            "motivation": [{"key": "factor_1", "title": "Lärande",
                            "evidence": {"name": "Lärande", "definition": "Approved source description"}}],
            "personality": [{"key": "Empathy", "title": "Empati",
                             "evidence": {"summary": "Explores others' needs"}}],
        }
        prompts = []

        def evidence(_owner, category, language, _shared, _notes):
            return categories.get(category, [])

        def completion(prompt, _owner, **kwargs):
            prompts.append(prompt)
            if "Respond as JSON object with a single key text" in prompt:
                return {"text": "Integrated, grounded synthesis."}
            return {"testbild": "Assessment only.", "intervjun": "Interview only."}

        with (
            patch.object(report, "_state", return_value={"schema": 1, "sections": {}, "language": ""}),
            patch.object(report, "_save"),
            patch.object(report, "_subject_evidence", side_effect=evidence),
            patch.object(report, "_theme_selection", return_value=[
                {"key": "theme_1", "title": "Samarbete i praktiken", "traits": ["Empathy"]}
            ]),
            patch.object(report, "_guidance", return_value=("Protected", "Scoped")),
            patch.object(report, "_completion", side_effect=completion),
            patch.object(report, "build_shared_ai_context", return_value=self.shared),
            patch("apps.core.ai.post_interview_question_evidence_policy.get_post_interview_note_evidence",
                  return_value=self.notes),
        ):
            events = list(report.generate_structured_overall_picture(
                self.owner, language_code="sv",
            ))
        self.assertEqual(len(prompts), 4)
        self.assertTrue(all("percentile" not in prompt and "STIVE" not in prompt for prompt in prompts))
        self.assertEqual([e["section"] for e in events if e["type"] == "structured_item_complete"],
                         ["skills", "motivation", "personality"])
        self.assertEqual(events[-1]["data"]["sections"]["synthesis"]["status"], "completed")
        self.assertIn("Integrated, grounded synthesis", events[-1]["markdown"])
