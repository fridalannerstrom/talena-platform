from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.candidate_question_fingerprint_policy import (
    _cognitive_fingerprint_instruction,
    _motivation_fingerprint_instruction,
    _personality_fingerprint_instruction,
)


class _RoleContext:
    purpose_data = {}

    def __init__(self, text):
        self.text = text

    def get_context_for_purpose(self, purpose_key):
        return {"context_text": self.text}


def _compact(text):
    """Collapse prompt formatting so tests assert semantics, not line wrapping."""
    return " ".join(str(text or "").split())


class CandidateQuestionFingerprintPolicyTests(SimpleTestCase):
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
        return SimpleNamespace(
            candidate=candidate,
            process=process,
        )

    def test_single_cognitive_result_requires_every_question_to_stay_on_that_ability(self):
        owner = self._owner(
            "Project coordinator role with changing priorities, multiple stakeholders "
            "and responsibility for schedules and delivery follow-up."
        )

        prompt = _compact(
            _cognitive_fingerprint_instruction(
                owner,
                [
                    {
                        "label": "Numerical reasoning",
                        "percentile": 2,
                    }
                ],
            )
        )

        self.assertIn("ONLY ONE COMPLETED COGNITIVE RESULT IS AVAILABLE", prompt)
        self.assertIn("Numerical reasoning", prompt)
        self.assertIn("EVERY generated cognitive question", prompt)
        self.assertIn("standalone questions about collaboration", prompt)
        self.assertIn("project priority", prompt)
        self.assertIn("Process context may make the situation realistic", prompt)
        self.assertIn("context must never replace the cognitive result", prompt)

    def test_cognitive_why_must_trace_the_candidate_result_not_only_role_relevance(self):
        owner = self._owner(
            "Key Account Manager role using sales data and forecasts to support decisions."
        )

        prompt = _compact(
            _cognitive_fingerprint_instruction(
                owner,
                [{"label": "Numerical reasoning", "percentile": 2}],
            )
        )

        self.assertIn("visible evidence trace", prompt)
        self.assertIn("which cognitive ability/result pattern", prompt)
        self.assertIn("only says the topic is important for the role", prompt)
        self.assertIn("sales data and forecasts", prompt)

    def test_personality_why_requires_candidate_specific_profile_evidence(self):
        owner = self._owner(
            "Project coordinator role requiring coordination across functions and "
            "adaptation when priorities change."
        )

        prompt = _compact(_personality_fingerprint_instruction(owner))

        self.assertIn("candidate-specific personality hypothesis", prompt)
        self.assertIn("actual personality direction", prompt)
        self.assertIn("visible evidence trace", prompt)
        self.assertIn("this explores teamwork", prompt)
        self.assertIn("adaptation when priorities change", prompt)

    def test_motivation_questions_keep_profile_as_basis_and_context_as_scene(self):
        owner = self._owner(
            "Leadership development process focused on leading through change and "
            "supporting other people's development."
        )

        prompt = _compact(_motivation_fingerprint_instruction(owner))

        self.assertIn("actual supplied motivation factor", prompt)
        self.assertIn("Context sets the scene", prompt)
        self.assertIn("motivation profile determines", prompt)
        self.assertIn("generic why", prompt)
        self.assertIn("leading through change", prompt)
