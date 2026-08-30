from django.test import SimpleTestCase

from apps.processes.interview_config import (
    get_interview_section_config,
)


class InterviewSectionConfigTests(SimpleTestCase):
    def test_interview_defaults_remain_centralised(self):
        cognitive = get_interview_section_config("cognitive")
        motivation = get_interview_section_config("motivation")
        personality = get_interview_section_config("personality")

        self.assertEqual(cognitive["order"], 1)
        self.assertEqual(cognitive["question_count"], 3)
        self.assertEqual(cognitive["estimated_minutes"], 10)

        self.assertEqual(motivation["order"], 2)
        self.assertEqual(motivation["question_count"], 3)
        self.assertEqual(motivation["estimated_minutes"], 10)

        self.assertEqual(personality["order"], 3)
        self.assertEqual(personality["question_count"], 8)
        self.assertEqual(personality["estimated_minutes"], 20)

    def test_section_guidance_is_localised_for_swedish(self):
        section = get_interview_section_config(
            "motivation",
            language_code="sv-SE",
        )

        self.assertEqual(
            section["guidance_label"],
            "Så använder du frågorna",
        )
        self.assertEqual(
            section["transition_label"],
            "Förslag på övergång",
        )
        self.assertIn("motivation", section["transition"].lower())

    def test_section_guidance_defaults_to_english(self):
        section = get_interview_section_config(
            "personality",
            language_code="de",
        )

        self.assertEqual(
            section["guidance_label"],
            "How to use these questions",
        )
        self.assertEqual(
            section["transition_label"],
            "Suggested transition",
        )
