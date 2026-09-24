from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.personality_interpretation import (
    apply_personality_interpretation_event,
    build_motivation_results_for_personality_owner,
    build_personality_interpretation_prompt,
    create_empty_personality_interpretation,
)
from apps.core.ai.personality_motivation_interaction_policy import (
    install_personality_motivation_interaction_policy,
)
from apps.core.ai.prompt_templates import AI_PROMPT_REGISTRY


class PersonalityMotivationInteractionTests(SimpleTestCase):
    def setUp(self):
        install_personality_motivation_interaction_policy()

    def _owner(self):
        owner = SimpleNamespace(
            candidate=SimpleNamespace(
                first_name="Test",
                last_name="Candidate",
                email="test@example.com",
            ),
            selected_personality_traits=[],
            sova_activities=[
                {
                    "activity": "Personality Assessment",
                    "competencies": [
                        {"competency": "Empathy", "sten_rounded": 6},
                        {"competency": "Tolerance", "sten_rounded": 4},
                        {"competency": "Listening", "sten_rounded": 8},
                        {"competency": "Warmth", "sten_rounded": 5},
                    ],
                }
            ],
        )
        owner.process = SimpleNamespace(
            purpose="recruitment",
            is_historical=False,
            role_context=SimpleNamespace(
                purpose_data={},
                get_context_for_purpose=lambda purpose: {
                    "context_text": "Role context for customer conversations."
                },
            ),
        )
        return owner

    def test_dedicated_admin_prompt_is_registered(self):
        definition = AI_PROMPT_REGISTRY[
            "personality_motivation_interaction"
        ]
        self.assertEqual(
            definition["name"],
            "Personality · Interaction with motivation",
        )
        self.assertEqual(definition["category"], "Personality")
        self.assertIn(
            "KEEP THE MEASURES DISTINCT",
            definition["defaults"]["en"],
        )
        self.assertIn(
            "HÅLL ISÄR MÄTNINGARNA",
            definition["defaults"]["sv"],
        )

    def test_empty_interpretation_contains_motivation_interaction_field(self):
        result = create_empty_personality_interpretation(
            owner=SimpleNamespace(),
            language_code="en",
        )
        self.assertEqual(result["motivation_interaction"], "")

    def test_motivation_interaction_event_updates_draft(self):
        draft = create_empty_personality_interpretation(
            owner=SimpleNamespace(),
            language_code="en",
        )
        apply_personality_interpretation_event(
            draft,
            {
                "type": "motivation_interaction",
                "text": "  Personality and motivation may reinforce each other.  ",
            },
        )
        self.assertEqual(
            draft["motivation_interaction"],
            "Personality and motivation may reinforce each other.",
        )

    def test_active_owner_uses_available_motivation_results(self):
        owner = SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=[
                {
                    "activity": "Motivation Questionnaire",
                    "competencies": [
                        {"competency": "Autonomy", "stive_rounded": 5},
                        {"competency": "Stability", "stive_rounded": 2},
                    ],
                }
            ],
        )
        results = build_motivation_results_for_personality_owner(owner)
        by_name = {item["name"]: item for item in results}
        self.assertEqual(by_name["Autonomy"]["score"], 5)
        self.assertEqual(by_name["Stability"]["score"], 2)
        self.assertTrue(by_name["Autonomy"]["definition"])

    @patch(
        "apps.core.ai.prompt_templates.get_global_ai_guidance",
        return_value="GLOBAL GUIDANCE",
    )
    @patch(
        "apps.core.ai.prompt_templates.get_ai_feature_prompt_instructions",
        return_value="BOX GUIDANCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.build_motivation_evidence_text",
        return_value="MOTIVATION EVIDENCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.build_personality_evidence_text",
        return_value="RAW PERSONALITY EVIDENCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.get_ai_feature_prompt_instructions",
        return_value="LEGACY SECTION GUIDANCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.get_ai_prompt_instructions",
        return_value="LEGACY OVERALL GUIDANCE",
    )
    def test_prompt_uses_result_summary_context_and_box_specific_guidance(
        self,
        _legacy_overall,
        _legacy_feature,
        _raw_personality,
        _motivation_evidence,
        _feature_prompt,
        _global_prompt,
    ):
        prompt = build_personality_interpretation_prompt(
            owner=self._owner(),
            personality_results=[{"name": "Empathy", "sten": 6}],
            motivation_results=[{"name": "Affiliation", "score": 5}],
            language_code="en",
        )

        self.assertNotIn("RAW PERSONALITY EVIDENCE", prompt)
        self.assertIn("TALENA SHARED PERSONALITY AI INPUT", prompt)
        self.assertIn("PERSONALITY TRAIT: Empathy", prompt)
        self.assertIn("CANDIDATE-SPECIFIC RESULT SUMMARY", prompt)
        self.assertIn("Role context for customer conversations.", prompt)
        self.assertIn("MOTIVATION EVIDENCE", prompt)
        self.assertIn("GLOBAL GUIDANCE", prompt)
        self.assertIn("BOX GUIDANCE", prompt)
        self.assertIn(
            "Process context may explain where,\nwhen or why a supported interaction matters",
            prompt,
        )
        self.assertNotIn(
            "Do not use PROCESS CONTEXT, process purpose",
            prompt,
        )
        self.assertIn(
            '{"type":"motivation_interaction","text":',
            prompt,
        )

    @patch(
        "apps.core.ai.prompt_templates.get_global_ai_guidance",
        return_value="GLOBAL GUIDANCE",
    )
    @patch(
        "apps.core.ai.prompt_templates.get_ai_feature_prompt_instructions",
        return_value="BOX GUIDANCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.build_motivation_evidence_text",
        return_value="No motivation assessment results are available.",
    )
    @patch(
        "apps.core.ai.personality_interpretation.get_ai_feature_prompt_instructions",
        return_value="LEGACY SECTION GUIDANCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.get_ai_prompt_instructions",
        return_value="LEGACY OVERALL GUIDANCE",
    )
    def test_prompt_requires_empty_interaction_when_motivation_is_missing(
        self,
        _legacy_overall,
        _legacy_feature,
        _motivation_evidence,
        _feature_prompt,
        _global_prompt,
    ):
        prompt = build_personality_interpretation_prompt(
            owner=self._owner(),
            personality_results=[{"name": "Empathy", "sten": 6}],
            motivation_results=[],
            language_code="en",
        )
        self.assertIn(
            "No motivation assessment data is available.",
            prompt,
        )
        self.assertIn(
            '{"type":"motivation_interaction","text":""}',
            prompt,
        )
