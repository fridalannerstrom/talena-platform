from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase

from apps.core.ai.purpose_fit import build_assessment_evidence
from apps.core.ai.decision_support import (
    _extract_json_events_from_buffer,
    _post_get_content_block_prompt_instructions,
    build_post_interview_decision_support_prompt,
    build_pre_interview_evidence,
    stream_post_interview_decision_support,
)

from apps.processes.models import AIPromptTemplate


class PostInterviewPromptContractTests(SimpleTestCase):
    def test_evidence_uses_authoritative_sova_top_three_motivators(self):
        owner = SimpleNamespace(
            sova_activities=[
                {
                    "activity": "Motivation Questionnaire",
                    "competencies": [
                        {"competency": "Variety", "stive": 4.8},
                        {"competency": "Customer Service", "stive": 4.5},
                        {"competency": "People Development", "stive": 4.2},
                        {"competency": "Creativity", "stive": 3.9},
                        {"competency": "Making a Difference", "stive": 3.7},
                    ],
                },
            ],
            ai_purpose_fit={},
            ai_purpose_fit_status="not_started",
            ai_personality_interpretation={},
            ai_personality_interpretation_status="not_started",
            ai_motivation_interpretation={},
            ai_motivation_interpretation_status="not_started",
            ai_cognitive_interpretation={},
            ai_cognitive_interpretation_status="not_started",
            ai_response_style_guidance={},
            ai_response_style_guidance_status="not_started",
            ai_personality_questions={},
            ai_motivation_questions={},
            ai_cognitive_questions={},
        )

        with patch(
            "apps.core.ai.purpose_fit.build_assessment_evidence",
            return_value=("", 0),
        ):
            evidence = build_pre_interview_evidence(
                owner,
                language_code="sv",
            )["evidence_text"]

        self.assertIn(
            "AUTHORITATIVE TOP THREE MOTIVATION FACTORS",
            evidence,
        )
        self.assertLess(
            evidence.index("1. Variation — STIVE 4.8 of 5"),
            evidence.index("2. Kundservice — STIVE 4.5 of 5"),
        )
        self.assertLess(
            evidence.index("2. Kundservice — STIVE 4.5 of 5"),
            evidence.index(
                "3. Människors utveckling — STIVE 4.2 of 5"
            ),
        )
        self.assertIn(
            "1. Variation — STIVE 4.8 of 5",
            evidence,
        )
        self.assertNotIn("Customer Service", evidence)
        self.assertNotIn("People Development", evidence)
        self.assertNotIn("Making a Difference", evidence)
        self.assertNotIn("Creativity", evidence)
        self.assertNotIn("3. Kreativitet", evidence)



    def test_opaque_sova_activity_name_is_not_exposed_as_evidence(self):
        owner = SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=[
                {
                    "activity": "0085_MQ_Sova_Motivation_Research",
                    "competencies": [
                        {"competency": "Variety", "stive": 4.8},
                    ],
                },
            ],
        )

        evidence, count = build_assessment_evidence(
            owner,
            language_code="sv",
        )

        self.assertEqual(count, 1)
        self.assertIn("Motivation:", evidence)
        self.assertIn("Variation: stive 4.8", evidence)
        self.assertNotIn("Variety", evidence)
        self.assertNotIn("0085_MQ_Sova_Motivation_Research", evidence)


    def test_content_block_prompts_are_isolated_from_legacy_guidance(self):
        owner = SimpleNamespace(
            interview_notes="Interview notes",
            ai_pre_interview_decision_support={},
        )

        shared_context = {
            "candidate": SimpleNamespace(
                first_name="Test",
                last_name="Candidate",
            ),
            "purpose_label": "Purpose",
            "context_text": "Role context",
        }
        evidence = {
            "evidence_text": "Assessment evidence",
            "has_evidence": True,
        }

        def feature_prompt(*, key, language, default=None):
            return f"PROMPT::{key}"

        with (
            patch(
                "apps.core.ai.post_interview_question_evidence_policy.get_post_interview_note_evidence",
                return_value={
                    "general_notes": "Interview notes",
                    "has_general_notes": True,
                    "question_evidence": {
                        "text": "",
                        "count": 0,
                        "has_evidence": False,
                    },
                    "has_question_evidence": False,
                    "has_evidence": True,
                },
            ),
            patch(
                "apps.core.ai.decision_support.get_global_ai_guidance",
                return_value="GLOBAL GUIDANCE",
            ),
            patch(
                "apps.core.ai.decision_support.get_ai_feature_prompt_instructions",
                side_effect=feature_prompt,
            ),
            patch(
                "apps.core.ai.decision_support.build_shared_ai_context",
                return_value=shared_context,
            ),
            patch(
                "apps.core.ai.decision_support.build_pre_interview_evidence",
                return_value=evidence,
            ),
        ):
            prompt = build_post_interview_decision_support_prompt(
                owner,
                language_code="sv",
            )

        self.assertIn("GLOBAL AI GUIDANCE — PROTECTED BOUNDARIES ONLY", prompt)
        self.assertIn(
            "OVERALL_PICTURE GUIDANCE\nPROMPT::post_interview_overall_picture",
            prompt,
        )
        self.assertIn(
            "OPTIONAL LEGACY COMPATIBILITY EVENTS",
            prompt,
        )
        self.assertIn(
            "FINAL ADMINISTRATOR CONTENT AUTHORITY",
            prompt,
        )
        self.assertIn(
            "PROMPT::post_interview_overall_picture",
            prompt,
        )
        self.assertNotIn(
            "PROMPT::post_interview_decision_support",
            prompt,
        )
        self.assertIn(
            "sole authority for that value",
            prompt,
        )
        self.assertNotIn(
            "default word count",
            prompt,
        )
        self.assertNotIn(
            '"blocks": {"overall_picture"',
            prompt,
        )

        self.assertIn("Inside each user-facing content_blocks string, use simple Markdown", prompt)
        self.assertIn("Never include HTML", prompt)


    def test_stream_parser_accepts_literal_multiline_content_block_text(self):
        events, remainder = _extract_json_events_from_buffer(
            '{"type":"content_blocks","blocks":{"overall_picture":"Första stycket.\n\nAndra stycket."}}'
        )

        self.assertEqual(remainder, "")
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0]["blocks"]["overall_picture"],
            "Första stycket.\n\nAndra stycket.",
        )



class PostInterviewPromptOverrideCompatibilityTests(TestCase):
    def test_legacy_overall_picture_override_is_used_when_canonical_is_missing(self):
        AIPromptTemplate.objects.create(
            key="overall_picture",
            name="Legacy overall picture",
            language="sv",
            prompt_text="LEGACY HELHETSBILD PROMPT",
            is_active=True,
        )

        prompt = _post_get_content_block_prompt_instructions(
            key="overall_picture",
            language="sv",
        )

        self.assertEqual(prompt, "LEGACY HELHETSBILD PROMPT")

    def test_canonical_override_has_priority_over_legacy_override(self):
        AIPromptTemplate.objects.create(
            key="overall_picture",
            name="Legacy overall picture",
            language="sv",
            prompt_text="LEGACY HELHETSBILD PROMPT",
            is_active=True,
        )
        AIPromptTemplate.objects.create(
            key="post_interview_overall_picture",
            name="Overall picture",
            language="sv",
            prompt_text="CANONICAL HELHETSBILD PROMPT",
            is_active=True,
        )

        prompt = _post_get_content_block_prompt_instructions(
            key="overall_picture",
            language="sv",
        )

        self.assertEqual(prompt, "CANONICAL HELHETSBILD PROMPT")



class PostInterviewStreamLimitTests(SimpleTestCase):
    def test_output_limit_is_configured_and_truncation_is_reported(self):
        owner = SimpleNamespace(
            interview_notes="Interview notes",
        )
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="length",
                    delta=SimpleNamespace(content=None),
                )
            ]
        )
        create = Mock(return_value=[response])
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            )
        )
        note_evidence = {
            "general_notes": "Interview notes",
            "has_general_notes": True,
            "question_evidence": {
                "text": "",
                "count": 0,
                "has_evidence": False,
            },
            "has_question_evidence": False,
            "has_evidence": True,
        }

        with (
            patch(
                "apps.core.ai.post_interview_question_evidence_policy.get_post_interview_note_evidence",
                return_value=note_evidence,
            ),
            patch(
                "apps.core.ai.decision_support.build_pre_interview_evidence",
                return_value={"has_evidence": True},
            ),
            patch(
                "apps.core.ai.decision_support.build_post_interview_decision_support_prompt",
                return_value="Prompt",
            ),
            patch(
                "apps.core.ai.decision_support._post_get_prompt_debug_info",
                return_value={},
            ),
            patch(
                "apps.core.ai.decision_support.get_openai_client",
                return_value=client,
            ),
            patch(
                "apps.core.ai.decision_support.get_chat_model",
                return_value="gpt-4o-mini",
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "12,000-token output limit",
            ):
                list(
                    stream_post_interview_decision_support(
                        owner=owner,
                        language_code="sv",
                    )
                )

        create.assert_called_once()
        self.assertEqual(
            create.call_args.kwargs["max_completion_tokens"],
            12000,
        )
