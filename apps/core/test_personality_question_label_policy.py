from django.test import SimpleTestCase

from apps.core.ai.personality_question_label_policy import (
    _ensure_question_labels,
    _normalise_prompt_limits,
    _questions_have_valid_labels,
    _replace_selected_traits_and_questions,
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

    def test_single_selected_trait_is_safe_to_restore(self):
        questions = [
            {
                "question": "Question one",
                "traits": [],
                "why": "Why one",
                "listen_for": "Listen one",
            }
        ]

        result = _ensure_question_labels(
            questions,
            ["Analytical"],
        )

        self.assertEqual(result[0]["traits"], ["Analytical"])

    def test_multiple_selected_traits_are_not_guessed(self):
        questions = [
            {
                "question": "Question one",
                "traits": [],
                "why": "Why one",
                "listen_for": "Listen one",
            }
        ]

        result = _ensure_question_labels(
            questions,
            ["Analytical", "Supporting"],
        )

        self.assertEqual(result[0]["traits"], [])

    def test_valid_label_check_rejects_missing_metadata(self):
        events = [
            {
                "type": "selected_traits",
                "items": ["Analytical", "Supporting"],
            },
            {
                "type": "questions",
                "items": [
                    {
                        "question": "Question one",
                        "traits": [],
                    }
                ],
            },
        ]

        self.assertFalse(_questions_have_valid_labels(events))

    def test_fallback_questions_define_their_own_selected_labels(self):
        events = [
            {
                "type": "selected_traits",
                "items": ["Analytical", "Supporting"],
            },
            {
                "type": "questions",
                "items": [],
            },
            {"type": "done"},
        ]
        fallback_questions = [
            {
                "question": "Question one",
                "traits": ["Supporting"],
                "why": "Why",
                "listen_for": "Listen",
            },
            {
                "question": "Question two",
                "traits": ["Analytical"],
                "why": "Why",
                "listen_for": "Listen",
            },
        ]

        result = _replace_selected_traits_and_questions(
            events,
            fallback_questions,
        )

        self.assertTrue(_questions_have_valid_labels(result))
        self.assertEqual(
            result[0],
            {
                "type": "selected_traits",
                "items": ["Supporting", "Analytical"],
            },
        )

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
