from django.test import SimpleTestCase

from apps.core.ai.personality_question_label_policy import (
    _ensure_question_labels,
    _normalise_prompt_limits,
)


class PersonalityQuestionLabelPolicyTests(SimpleTestCase):
    def test_prompt_raises_trait_limit_and_requires_labels(self):
        prompt = """
- the application currently supports a maximum of 6 selected traits
The application supports up to 6 suggested trait objects.
If administrator guidance does not require substantive why,
listen_for or trait tagging, preserve those technical fields using
an empty string or empty array as appropriate.
""".strip()

        result = _normalise_prompt_limits(prompt)

        self.assertIn("maximum of 8 selected traits", result)
        self.assertIn("up to 8 suggested trait objects", result)
        self.assertIn(
            "Every generated personality question must contain at least one valid item",
            result,
        )
        self.assertIn("traits array is never optional", result)

    def test_missing_question_labels_are_distributed_across_selection(self):
        questions = [
            {
                "question": "Question one",
                "traits": [],
                "why": "Why one",
                "listen_for": "Listen one",
            },
            {
                "question": "Question two",
                "traits": [],
                "why": "Why two",
                "listen_for": "Listen two",
            },
            {
                "question": "Question three",
                "traits": ["Analytical"],
                "why": "Why three",
                "listen_for": "Listen three",
            },
        ]

        result = _ensure_question_labels(
            questions,
            ["Analytical", "Supporting"],
        )

        self.assertEqual(result[0]["traits"], ["Analytical"])
        self.assertEqual(result[1]["traits"], ["Supporting"])
        self.assertEqual(result[2]["traits"], ["Analytical"])

    def test_no_selection_does_not_invent_a_label(self):
        questions = [
            {
                "question": "Question one",
                "traits": [],
                "why": "",
                "listen_for": "",
            }
        ]

        result = _ensure_question_labels(questions, [])

        self.assertEqual(result[0]["traits"], [])
