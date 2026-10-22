"""GDPR #301: synthetic final-SDK-boundary tests for interview and team AI.

All OpenAI calls use a mocked raw SDK. No candidate records, API keys, or
outbound provider requests are needed.
"""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.core.ai.openai_client import PrivacySafeOpenAI


class SavedAIInterpretationSourcesTests(SimpleTestCase):
    def test_preinterview_evidence_explicitly_reuses_selected_saved_fields(self):
        from apps.core.ai.decision_support import build_pre_interview_evidence

        owner = SimpleNamespace(
            ai_purpose_fit={
                "summary": "SYNTHETIC OVERVIEW SUMMARY",
                "key_alignment": ["SYNTHETIC ALIGNMENT"],
                "internal_case_id": "PRIVATE_INTERNAL_ID_MUST_NOT_BE_IN_THIS_SECTION",
            },
            ai_purpose_fit_status="completed",
            ai_personality_interpretation={
                "interpretation": "SYNTHETIC PERSONALITY SUMMARY",
                "profile_dynamics": "SYNTHETIC PERSONALITY DYNAMICS",
                "supportive_patterns": ["SYNTHETIC SUPPORTIVE PATTERN"],
            },
            ai_personality_interpretation_status="completed",
            ai_motivation_interpretation={
                "interpretation": "SYNTHETIC MOTIVATION SUMMARY",
                "engagement_conditions": ["SYNTHETIC ENGAGEMENT CONDITION"],
            },
            ai_motivation_interpretation_status="completed",
            ai_cognitive_interpretation={
                "interpretation": "SYNTHETIC COGNITIVE SUMMARY",
                "considerations": ["SYNTHETIC COGNITIVE CAUTION"],
            },
            ai_cognitive_interpretation_status="completed",
            ai_response_style_guidance={
                "summary": "SYNTHETIC RESPONSE STYLE",
            },
            ai_response_style_guidance_status="completed",
            ai_personality_questions={"questions": []},
            ai_motivation_questions={"questions": []},
            ai_cognitive_questions={"questions": []},
        )
        with patch(
            "apps.core.ai.decision_support._build_motivation_assessment_evidence",
            return_value="SYNTHETIC TOP THREE MOTIVATORS",
        ):
            result = build_pre_interview_evidence(owner, language_code="sv")

        text = result["evidence_text"]
        for expected in (
            "SYNTHETIC OVERVIEW SUMMARY",
            "SYNTHETIC ALIGNMENT",
            "SYNTHETIC PERSONALITY SUMMARY",
            "SYNTHETIC PERSONALITY DYNAMICS",
            "SYNTHETIC SUPPORTIVE PATTERN",
            "SYNTHETIC TOP THREE MOTIVATORS",
            "SYNTHETIC MOTIVATION SUMMARY",
            "SYNTHETIC ENGAGEMENT CONDITION",
            "SYNTHETIC COGNITIVE SUMMARY",
            "SYNTHETIC COGNITIVE CAUTION",
            "SYNTHETIC RESPONSE STYLE",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("PRIVATE_INTERNAL_ID_MUST_NOT_BE_IN_THIS_SECTION", text)
        self.assertEqual(
            set(result["source_names"]),
            {
                "AI Overview", "Personality interpretation",
                "Motivation assessment results", "Motivation interpretation",
                "Cognitive interpretation", "Response-style guidance",
            },
        )


class PostInterviewFinalBoundaryTests(SimpleTestCase):
    def test_each_section_masks_identifiers_and_keeps_exact_question_context(self):
        from apps.core.ai.decision_support import stream_post_interview_content_block

        candidate = SimpleNamespace(
            first_name="Anna", last_name="Svensson",
            email="anna.svensson@example.test",
        )
        owner = SimpleNamespace(candidate=candidate)
        for language in ("sv", "en"):
            for block_key in ("overall_picture", "interview_summary"):
                with self.subTest(language=language, section=block_key):
                    raw = Mock()
                    raw.chat.completions.create.return_value = iter([
                        SimpleNamespace(
                            choices=[SimpleNamespace(
                                delta=SimpleNamespace(content="Synthetic result."),
                                finish_reason="stop",
                            )]
                        )
                    ])
                    context = {
                        "candidate": candidate,
                        "purpose_label": "Hiring",
                        "context_text": "Customer Service role, Anna Svensson",
                    }
                    notes = {
                        "has_evidence": True,
                        "has_question_evidence": True,
                        "general_notes": (
                            "Anna Svensson coordinated tasks. "
                            "anna.svensson@example.test. STEN 8."
                        ),
                        "question_evidence": {
                            "text": (
                                "Question: How do you delegate? "
                                "Saved answer/note: Anna described delegation."
                            ),
                        },
                    }
                    with (
                        patch(
                            "apps.core.ai.decision_support.build_shared_ai_context",
                            return_value=context,
                        ),
                        patch(
                            "apps.core.ai.post_interview_question_evidence_policy.get_post_interview_note_evidence",
                            return_value=notes,
                        ),
                        patch(
                            "apps.core.ai.decision_support.build_pre_interview_evidence",
                            return_value={
                                "has_evidence": True,
                                "evidence_text": "SYNTHETIC SAVED AI ASSESSMENT",
                            },
                        ),
                        patch(
                            "apps.core.ai.decision_support.get_global_ai_guidance",
                            return_value="Use supplied evidence only.",
                        ),
                        patch(
                            "apps.core.ai.decision_support._post_get_content_block_prompt_instructions",
                            return_value="Generate only this specific section.",
                        ),
                        patch(
                            "apps.core.ai.decision_support._post_get_ai_language_instruction",
                            return_value="Swedish" if language == "sv" else "English",
                        ),
                        patch(
                            "apps.core.ai.decision_support.get_openai_client",
                            return_value=PrivacySafeOpenAI(raw),
                        ),
                    ):
                        events = list(
                            stream_post_interview_content_block(
                                owner=owner, block_key=block_key, language_code=language
                            )
                        )

                    self.assertEqual(events[-1]["type"], "content_block_done")
                    kwargs = raw.chat.completions.create.call_args.kwargs
                    sent = json.dumps(kwargs["messages"], ensure_ascii=False)
                    for identifier in (
                        "Anna Svensson", "anna.svensson@example.test",
                        "Anna described",
                    ):
                        self.assertNotIn(identifier, sent)
                    self.assertIn("CANDIDATE_A", sent)
                    self.assertIn("STEN 8", sent)
                    self.assertIn("How do you delegate?", sent)
                    self.assertIn("Customer Service", sent)
                    self.assertEqual(kwargs["messages"][1]["role"], "user")
                    self.assertTrue(kwargs["stream"])
                    if block_key == "interview_summary":
                        self.assertIn(
                            "Omitted for this section; focus on what the interview evidence itself adds.",
                            sent,
                        )
                        self.assertNotIn("SYNTHETIC SAVED AI ASSESSMENT", sent)
                    else:
                        self.assertIn("SYNTHETIC SAVED AI ASSESSMENT", sent)


class ManagerReportRelatedFinalBoundaryTests(SimpleTestCase):
    def test_personality_stream_masks_manager_report_prompt_text(self):
        from apps.core.ai.personality_interpretation import (
            stream_personality_interpretation,
        )

        candidate = SimpleNamespace(
            first_name="Helena", last_name="Lind",
            email="helena.lind@example.test",
        )
        owner = SimpleNamespace(candidate=candidate)
        raw = Mock()
        raw.chat.completions.create.return_value = iter([])
        with (
            patch(
                "apps.core.ai.personality_interpretation.build_motivation_results_for_personality_owner",
                return_value=[],
            ),
            patch(
                "apps.core.ai.personality_interpretation.build_personality_interpretation_prompt",
                return_value=(
                    "Manager report testbild and candidate_describes. "
                    "Helena Lind said STEN 8. helena.lind@example.test"
                ),
            ),
            patch(
                "apps.core.ai.personality_interpretation.get_ai_system_language_instruction",
                return_value="Write in Swedish",
            ),
            patch(
                "apps.core.ai.personality_interpretation.get_openai_client",
                return_value=PrivacySafeOpenAI(raw),
            ),
        ):
            list(stream_personality_interpretation(
                owner=owner,
                personality_results=[{"trait": "Adaptability", "sten": 8}],
                language_code="sv",
            ))

        sent = json.dumps(
            raw.chat.completions.create.call_args.kwargs["messages"],
            ensure_ascii=False,
        )
        self.assertNotIn("Helena Lind", sent)
        self.assertNotIn("helena.lind@example.test", sent)
        self.assertIn("CANDIDATE_A", sent)
        self.assertIn("STEN 8", sent)
        self.assertIn("Manager report testbild", sent)


class TeamInsightsFinalBoundaryTests(SimpleTestCase):
    def test_aggregates_and_free_text_sanitized_local_signature_excluded(self):
        from apps.teams.ai_insights import generate_team_insight

        raw = Mock()
        raw.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="Neutral synthetic team insight.")
            )]
        )
        team = SimpleNamespace()
        context = {
            "team_goals": ["Better collaboration"],
            "team_description": "Anna Svensson led this team.",
            "team_context": "Contact anna.svensson@example.test. STEN 8.",
            "team_member_count": 2,
            "members_with_usable_assessment_results": 2,
            "members_missing_usable_assessment_results": 0,
            "team_style_summary": [
                {"style": "Customer Service", "team_average": 4.5,
                 "members_with_score": 2},
            ],
        }
        with (
            patch(
                "apps.teams.ai_insights.build_team_insight_input",
                return_value=(
                    context, "PRIVATE_SOURCE_SIGNATURE_SHOULD_STAY_LOCAL",
                    2, 2, {"local_candidate_id": 678910},
                ),
            ),
            patch(
                "apps.teams.ai_insights.get_ai_prompt_instructions",
                return_value="Use aggregate results only.",
            ),
            patch(
                "apps.teams.ai_insights.get_openai_client",
                return_value=PrivacySafeOpenAI(raw),
            ),
            patch(
                "apps.processes.models.AIPromptTemplate.objects.filter"
            ) as prompt_filter,
            patch(
                "apps.teams.models.TeamAIInsight.objects.update_or_create",
                return_value=(SimpleNamespace(content="ok"), True),
            ) as save_mock,
        ):
            prompt_filter.return_value.first.return_value = None
            result = generate_team_insight(
                team=team, insight_type="collaboration",
                accessible_processes=object(),
                user=object(), language="sv",
            )

        self.assertEqual(result.content, "ok")
        sent = json.dumps(
            raw.chat.completions.create.call_args.kwargs["messages"],
            ensure_ascii=False,
        )
        for secret in (
            "Anna Svensson", "anna.svensson@example.test",
            "PRIVATE_SOURCE_SIGNATURE_SHOULD_STAY_LOCAL",
            "678910", "local_candidate_id",
        ):
            self.assertNotIn(secret, sent)
        for expected in (
            "[PERSON]", "[EMAIL]", "Better collaboration",
            "Customer Service", "STEN 8",
        ):
            self.assertIn(expected, sent)
        self.assertEqual(raw.chat.completions.create.call_count, 1)
        self.assertEqual(save_mock.call_count, 1)
