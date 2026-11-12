from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.core.ai.motivation_question_precision_policy import (
    _motivation_precision_instruction,
    _motivation_snapshot,
    _normalise_swedish_user_facing_text,
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

    def test_risk_factor_forbids_literal_risk_question_without_context_support(self):
        prompt = _motivation_precision_instruction(
            self._owner("Recruitment for a cashier role at ICA."),
            [{"name": "Risk", "score": 5}],
        )
        normalised = " ".join(prompt.split())

        self.assertIn("HARD RULE FOR RISK", normalised)
        self.assertIn("do NOT ask the candidate to describe", normalised)
        self.assertIn("kalkylerade risker", normalised)
        self.assertIn("unexpected events or acting without full certainty", normalised)
        self.assertIn("does it violate the HARD RULE FOR RISK", normalised)

    def test_process_context_must_shape_question_scenario(self):
        prompt = _motivation_precision_instruction(
            self._owner("Recruitment for a cashier role at ICA with customer-facing work."),
            [{"name": "Autonomy", "score": 3}],
        )
        normalised = " ".join(prompt.split())

        self.assertIn("Recruitment for a cashier role at ICA", normalised)
        self.assertIn("Every question must feel plausible for THIS process", normalised)
        self.assertIn("Motivation evidence determines WHAT is explored; context determines WHERE and HOW", normalised)
        self.assertIn("At least two of three generated questions", normalised)
        self.assertIn("concrete situation, setting, responsibility or phrase", normalised)
        self.assertIn("role/context must shape the scenario itself", normalised)
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

    def test_swedish_output_uses_talena_factor_names_and_natural_importance_wording(self):
        prompt = _motivation_precision_instruction(
            self._owner("Ska jobba i kassa på ICA."),
            [
                {"name": "Affiliation", "score": 3},
                {"name": "Recognition", "score": 3},
                {"name": "Autonomy", "score": 3},
            ],
            language_code="sv",
        )
        normalised = " ".join(prompt.split())

        self.assertIn("SWEDISH USER-FACING MOTIVATION LANGUAGE", normalised)
        self.assertIn("Affiliation -> Samhörighet", normalised)
        self.assertIn("Recognition -> Erkännande", normalised)
        self.assertIn("Autonomy -> Självständighet", normalised)
        self.assertIn("har måttlig betydelse för motivationen", normalised)
        self.assertIn("Avoid mechanical phrases such as \"måttligt viktig faktor\"", normalised)
        self.assertIn("Do not expose English source labels", normalised)

    def test_swedish_output_normalizer_removes_english_factor_labels(self):
        affiliation = _normalise_swedish_user_facing_text(
            "Denna fråga kopplar till den måttligt viktiga faktorn Affiliation "
            "och hur social interaktion påverkar Fridas engagemang."
        )
        recognition = _normalise_swedish_user_facing_text(
            "Denna fråga handlar om faktorn Recognition, som är av måttlig vikt, "
            "och hjälper till att förstå hur erkännande påverkar Frida."
        )

        self.assertNotIn("Affiliation", affiliation)
        self.assertNotIn("Recognition", recognition)
        self.assertIn("Samhörighet", affiliation)
        self.assertIn("Erkännande", recognition)
        self.assertIn("har måttlig betydelse för motivationen", affiliation)
        self.assertIn("har måttlig betydelse för motivationen", recognition)
