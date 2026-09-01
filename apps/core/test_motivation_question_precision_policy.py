from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.motivation_question_precision_policy import (
    _motivation_precision_instruction,
    _motivation_snapshot,
)


class _RoleContext:
    purpose_data = {}

    def __init__(self, text):
        self.text = text

    def get_context_for_purpose(self, purpose_key):
        return {"context_text": self.text}


class MotivationQuestionPrecisionPolicyTests(SimpleTestCase):
    def _owner(self, context_text):
        candidate = SimpleNamespace(
            first_name="Frida",
            last_name="Test",
            email="frida@example.com",
        )
        process = SimpleNamespace(
            purpose="recruitment",
            is_historical=False,
            role_context=_RoleContext(context_text),
        )
        return SimpleNamespace(candidate=candidate, process=process)

    def test_snapshot_preserves_factor_meaning_and_relative_importance(self):
        snapshot = _motivation_snapshot(
            [
                {"name": "Risk", "score": 5},
                {"name": "Autonomy", "score": 3},
                {"name": "Recognition", "score": 2},
            ]
        )

        self.assertIn("Risk: more prominent motivational driver", snapshot)
        self.assertIn("scope to take calculated risks and act despite uncertainty", snapshot)
        self.assertIn("Autonomy: mid-range motivational importance", snapshot)
        self.assertIn("Freedom to organise one's own time and approach to work", snapshot)
        self.assertIn("Recognition: less central motivational driver", snapshot)
        self.assertIn("Visibility, praise and public acknowledgement", snapshot)

    def test_factor_definition_is_source_of_truth_not_literal_factor_name(self):
        prompt = _motivation_precision_instruction(
            self._owner("Recruitment for a cashier role at ICA."),
            [{"name": "Risk", "score": 5}],
        )
        normalised = " ".join(prompt.split())

        self.assertIn("factor's supplied Meaning/definition as the source of truth", normalised)
        self.assertIn("The factor name is only a label", normalised)
        self.assertIn("responds when an unexpected or uncertain situation requires judgement", normalised)
        self.assertIn("rather than asking them to describe taking risks for its own sake", normalised)

    def test_process_context_must_shape_question_scenario(self):
        prompt = _motivation_precision_instruction(
            self._owner("Recruitment for a cashier role at ICA with customer-facing work."),
            [{"name": "Autonomy", "score": 3}],
        )
        normalised = " ".join(prompt.split())

        self.assertIn("Recruitment for a cashier role at ICA", normalised)
        self.assertIn("Every question must feel plausible for THIS process", normalised)
        self.assertIn("Motivation evidence determines WHAT is explored; context determines WHERE and HOW", normalised)
        self.assertIn("Do not invent detailed duties", normalised)

    def test_visible_why_requires_both_factor_and_process_trace(self):
        prompt = _motivation_precision_instruction(
            self._owner("Recruitment for a cashier role at ICA."),
            [{"name": "Recognition", "score": 3}],
        )
        normalised = " ".join(prompt.split())

        self.assertIn("which motivation factor or profile pattern made the question relevant", normalised)
        self.assertIn("why exploring that pattern is useful in the supplied process context", normalised)
        self.assertIn("only explains why the topic matters for the role is too generic", normalised)
        self.assertIn("does not need to repeat that wording mechanically for every question", normalised)
