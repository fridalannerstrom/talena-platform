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
        "apps.core.ai.personality_interpretation.build_motivation_evidence_text",
        return_value="MOTIVATION EVIDENCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.build_personality_evidence_text",
        return_value="PERSONALITY EVIDENCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.build_shared_ai_context",
        return_value={
            "candidate_name": "Test Candidate",
            "purpose_label": "Recruitment",
            "context_text": "Role context",
        },
    )
    @patch(
        "apps.core.ai.personality_interpretation.get_ai_feature_prompt_instructions",
        return_value="SECTION GUIDANCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.get_ai_prompt_instructions",
        return_value="OVERALL GUIDANCE",
    )
    def test_prompt_protects_personality_motivation_evidence_boundary(
        self,
        _overall_prompt,
        _feature_prompt,
        _shared_context,
        _personality_evidence,
        _motivation_evidence,
    ):
        prompt = build_personality_interpretation_prompt(
            owner=SimpleNamespace(),
            personality_results=[{"name": "Empathy", "score": 8}],
            motivation_results=[{"name": "Affiliation", "score": 5}],
            language_code="en",
        )
        self.assertIn("PERSONALITY EVIDENCE", prompt)
        self.assertIn("MOTIVATION EVIDENCE", prompt)
        self.assertIn(
            "must be grounded only in\nthe supplied PERSONALITY ASSESSMENT DATA and MOTIVATION ASSESSMENT DATA",
            prompt,
        )
        self.assertIn(
            "Do not use PROCESS CONTEXT, process purpose",
            prompt,
        )
        self.assertIn(
            '{"type":"motivation_interaction","text":',
            prompt,
        )

    @patch(
        "apps.core.ai.personality_interpretation.build_motivation_evidence_text",
        return_value="No motivation assessment results are available.",
    )
    @patch(
        "apps.core.ai.personality_interpretation.build_personality_evidence_text",
        return_value="PERSONALITY EVIDENCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.build_shared_ai_context",
        return_value={
            "candidate_name": "Test Candidate",
            "purpose_label": "Recruitment",
            "context_text": "",
        },
    )
    @patch(
        "apps.core.ai.personality_interpretation.get_ai_feature_prompt_instructions",
        return_value="SECTION GUIDANCE",
    )
    @patch(
        "apps.core.ai.personality_interpretation.get_ai_prompt_instructions",
        return_value="OVERALL GUIDANCE",
    )
    def test_prompt_requires_empty_interaction_when_motivation_is_missing(
        self,
        _overall_prompt,
        _feature_prompt,
        _shared_context,
        _personality_evidence,
        _motivation_evidence,
    ):
        prompt = build_personality_interpretation_prompt(
            owner=SimpleNamespace(),
            personality_results=[{"name": "Empathy", "score": 8}],
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
