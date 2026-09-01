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

    def test_why_contract_keeps_candidate_fingerprint_without_repeating_score_direction(self):
        prompt = _personality_precision_instruction(
            self._owner(["Adaptability"]),
            [{"name": "Adaptability", "sten": 2}],
        )
        normalised = " ".join(prompt.split())

        self.assertIn("Every why field must leave a visible candidate fingerprint", normalised)
        self.assertIn("does NOT need to explicitly say", normalised)
        self.assertIn("vary how the candidate fingerprint is expressed", normalised)
        self.assertIn("Do not make most why fields begin with or revolve around", normalised)
        self.assertIn("profile tension", normalised)
        self.assertIn("balanced or context-dependent pattern", normalised)
        self.assertIn("why is INVALID", normalised)
        self.assertIn("candidate-specific personality evidence or hypothesis", normalised)

    def test_full_set_requires_varied_use_of_personality_evidence(self):
        prompt = _personality_precision_instruction(
            self._owner(["Adaptability", "Conceptual", "Networking"]),
            [
                {"name": "Adaptability", "sten": 2},
                {"name": "Conceptual", "sten": 8},
                {"name": "Networking", "sten": 5},
            ],
        )
        normalised = " ".join(prompt.split())

        self.assertIn("Do not over-focus the full question set on the most extreme results", normalised)
        self.assertIn("Variation is a quality requirement", normalised)
        self.assertIn("mid-range or situational patterns", normalised)
        self.assertIn("meaningful contrasts", normalised)
        self.assertIn("Does it feel varied rather than dominated by high/low commentary?", normalised)

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
