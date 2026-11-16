"""Regression tests for Overall picture interview evidence availability.

The scenarios reflect the reported defect: saved examples about logical
troubleshooting, verbal reasoning, pressure, planning and motivation existed
in general notes, but strict routing made the generated report say none did.
"""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai import structured_overall_picture as report


class OverallPictureCompleteInterviewTests(SimpleTestCase):
    def setUp(self):
        self.notes = {
            "general_notes": (
                "Färdighet:\n"
                "Logisk\n"
                "Jag felsökte ett rekryteringsformulär genom att göra testansökningar "
                "och ändra en sak i taget tills jag hittade länken som orsakade felet.\n"
                "Verbal\n"
                "Jag jämförde texten i kravprofilen med mötesanteckningarna och "
                "frågade chefen om projektledning kunde uppfylla kravet.\n"
                "Motivation\n"
                "Jag får energi av att växla mellan search, möten och intervjuer.\n"
                "När flera uppgifter blev akuta sorterade jag efter tidskritikalitet "
                "och informerade tidigt när jag inte skulle hinna.\n"
                "Jag ändrade mina searchmeddelanden när färre kandidater svarade."
            ),
            "question_evidence": {"items": [
                {
                    "source": "personality",
                    "question": "Hur planerar du många parallella processer?",
                    "saved_answer_or_note": "Jag använder kalendern och ATS och prioriterar under dagen.",
                },
                {
                    "source": "cognitive",
                    "question": "Hur såg du ett mönster i ansökningarna?",
                    "saved_answer_or_note": "Jag jämförde olika ansökningsvägar systematiskt.",
                },
            ]},
        }

    def test_logical_and_verbal_areas_see_real_general_notes(self):
        for skill in ("logical", "verbal"):
            with self.subTest(skill=skill):
                data = report._notes_for_category(self.notes, "skills", item_key=skill)
                self.assertIn("felsökte ett rekryteringsformulär", data["general_notes"])
                self.assertIn("jämförde texten i kravprofilen", data["general_notes"])
                self.assertEqual(len(data["question_evidence"]), 2)

    def test_motivation_notes_are_not_discarded_from_general_interview_field(self):
        data = report._notes_for_category(self.notes, "motivation", item_key="factor_1")
        self.assertIn("Jag får energi av att växla", data["general_notes"])
        self.assertIn("När flera uppgifter blev akuta", data["general_notes"])

    def test_personality_notes_can_inform_multiple_themes(self):
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
            self.assertIn("tidskritikalitet", item["general_notes"])
            self.assertEqual(len(item["question_evidence"]), 2)
        self.assertIsNot(
            assigned["theme_1"]["question_evidence"],
            assigned["theme_2"]["question_evidence"],
        )

    def test_prompt_keeps_test_and_interview_sources_separate(self):
        item = {
            "key": "theme_1", "title": "Planering och målfokus",
            "scope": "prioritering och omplanering",
            "evidence": {"traits": [{"summary": "Prefers flexible plans."}]},
        }
        owner = SimpleNamespace()
        with patch.object(report, "_guidance", return_value=("Global rules", "Scoped guidance")):
            prompt = report._item_prompt(
                owner, "personality", item, {"purpose_label": "Recruitment"},
                report._notes_for_category(self.notes, "personality"), "sv",
            )
        self.assertIn("ASSESSMENT FOR THIS AREA ONLY", prompt)
        self.assertIn("COMPLETE INTERVIEW MATERIAL", prompt)
        self.assertIn("Prefers flexible plans.", prompt)
        self.assertIn("Jag ändrade mina searchmeddelanden", prompt)
        self.assertIn("Testbild must use ONLY the assessment evidence", prompt)
        self.assertIn("Intervjun must use ONLY factual statements", prompt)
