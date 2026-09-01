from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.personality_question_precision_policy import (
    _personality_precision_instruction,
    _selected_personality_snapshot,
)


class PersonalityQuestionPrecisionPolicyTests(SimpleTestCase):
    def _owner(self, selected):
        return SimpleNamespace(selected_personality_traits=selected)

    def test_snapshot_preserves_selected_trait_and_qualitative_direction(self):
        owner = self._owner(["Adaptability", "Conceptual", "Networking"])
        snapshot = _selected_personality_snapshot(
            owner,
            [
                {"name": "Adaptability", "sten": 2},
                {"name": "Conceptual", "sten": 8},
                {"name": "Networking", "sten": 5},
                {"name": "Emotional stability", "sten": 9},
            ],
        )

        self.assertIn("Adaptability: clearer low-side indication", snapshot)
        self.assertIn("Conceptual: clearer high-side indication", snapshot)
        self.assertIn("Networking: more mid-range indication", snapshot)
        self.assertNotIn("Emotional stability", snapshot)

    def test_why_contract_requires_candidate_specific_direction_not_role_only(self):
        prompt = _personality_precision_instruction(
            self._owner(["Adaptability"]),
            [{"name": "Adaptability", "sten": 2}],
        )
        normalised = " ".join(prompt.split())

        self.assertIn("Every why field must leave a visible candidate fingerprint", normalised)
        self.assertIn("State the direction or pattern qualitatively", normalised)
        self.assertIn("why is INVALID", normalised)
        self.assertIn("this is central for a project coordinator", normalised)
        self.assertIn("without also explaining the candidate-specific personality indication", normalised)

    def test_construct_fidelity_blocks_semantic_drift(self):
        prompt = _personality_precision_instruction(
            self._owner(["Conceptual"]),
            [{"name": "Conceptual", "sten": 8}],
        )
        normalised = " ".join(prompt.split())

        self.assertIn("Preserve construct fidelity", normalised)
        self.assertIn("treating Conceptual as Analytical", normalised)
        self.assertIn("trait name/tag and question wording refer to different constructs", normalised)
        self.assertIn("Talena trait definition", normalised)
