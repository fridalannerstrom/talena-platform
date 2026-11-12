from django.test import SimpleTestCase

from apps.processes.personality_question_selection_policy import (
    MAX_PERSONALITY_COMPETENCIES,
    MAX_PERSONALITY_TRAITS,
    _selection_limit,
    _stream_event_from_result,
)


class PersonalityQuestionSelectionPolicyTests(SimpleTestCase):
    def test_trait_mode_allows_eight(self):
        self.assertEqual(
            _selection_limit(["Analytical", "Supporting"]),
            MAX_PERSONALITY_TRAITS,
        )
        self.assertEqual(MAX_PERSONALITY_TRAITS, 8)

    def test_competency_mode_keeps_six(self):
        self.assertEqual(
            _selection_limit(["competency::Collaboration"]),
            MAX_PERSONALITY_COMPETENCIES,
        )
        self.assertEqual(MAX_PERSONALITY_COMPETENCIES, 6)

    def test_question_stream_uses_normalised_labels(self):
        raw_event = {
            "type": "questions",
            "items": [
                {
                    "question": "Question one",
                    "traits": [],
                }
            ],
        }
        result = {
            "questions": [
                {
                    "question": "Question one",
                    "traits": ["Analytical"],
                    "why": "Why",
                    "listen_for": "Listen",
                }
            ]
        }

        public_event = _stream_event_from_result(
            raw_event,
            result,
        )

        self.assertEqual(
            public_event["items"][0]["traits"],
            ["Analytical"],
        )

    def test_selected_trait_stream_uses_normalised_selection(self):
        raw_event = {
            "type": "selected_traits",
            "items": ["A", "B"],
        }
        result = {
            "selected_traits": [
                "A", "B", "C", "D", "E", "F", "G", "H"
            ]
        }

        public_event = _stream_event_from_result(
            raw_event,
            result,
        )

        self.assertEqual(len(public_event["items"]), 8)
