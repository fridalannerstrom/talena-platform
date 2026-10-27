"""AI Overview evidence must use the candidate's approved assessment interpretations."""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.core.ai.motivation_interpretation import (
    build_motivation_top_three_evidence,
)
from apps.core.ai.openai_client import PrivacySafeOpenAI
from apps.processes.services.cognitive_insights import (
    build_cognitive_ai_evidence,
    build_owner_cognitive_ai_evidence,
)
from apps.processes.templatetags.motivation_i18n import FACTOR_CONTENT


class MotivationTopThreeEvidenceTests(SimpleTestCase):
    def _owner(self, *, historical=False, competencies=None):
        return SimpleNamespace(
            process=SimpleNamespace(is_historical=historical),
            sova_activities=[{
                "activity": "Motivation Questionnaire",
                "competencies": competencies or [],
            }],
        )

    def test_active_top_three_uses_precise_stive_and_approved_swedish_text(self):
        owner = self._owner(competencies=[
            {"competency": "Risk", "stive": 4.86, "stive_rounded": 5},
            {"competency": "Commercial focus", "stive": 4.63, "stive_rounded": 5},
            {"competency": "Stability", "stive": 4.41, "stive_rounded": 4},
            {"competency": "Learning", "stive": 3.99, "stive_rounded": 4},
        ])

        evidence = build_motivation_top_three_evidence(
            owner,
            language_code="sv",
        )

        self.assertIn("STIVE 4.86", evidence)
        self.assertIn("STIVE 4.63", evidence)
        self.assertIn("STIVE 4.41", evidence)
        self.assertIn(FACTOR_CONTENT["risk"]["top_text"], evidence)
        self.assertIn(FACTOR_CONTENT["commercial_focus"]["top_text"], evidence)
        self.assertIn(FACTOR_CONTENT["stability"]["top_text"], evidence)
        self.assertNotIn(FACTOR_CONTENT["learning"]["top_text"], evidence)

    def test_historical_top_three_uses_profile_stive_values(self):
        owner = SimpleNamespace(process=SimpleNamespace(is_historical=True))
        profile = {
            "motivation_competencies": [
                {"competency": "Learning", "stive": 4.8, "score": 4.8},
                {"competency": "Risk", "stive": 4.2, "score": 4.2},
            ]
        }
        with patch(
            "apps.processes.services.candidate_profile.build_historical_candidate_profile",
            return_value=profile,
        ):
            evidence = build_motivation_top_three_evidence(
                owner,
                language_code="en",
            )

        self.assertIn("Learning — STIVE 4.8", evidence)
        self.assertIn("Risk — STIVE 4.2", evidence)
        self.assertLess(evidence.index("Learning"), evidence.index("Risk"))

    def test_tied_scores_have_deterministic_canonical_order(self):
        owner = self._owner(competencies=[
            {"competency": "Risk", "stive": 4.5},
            {"competency": "Attachment", "stive": 4.5},
            {"competency": "Commercial focus", "stive": 4.5},
            {"competency": "Stability", "stive": 4.0},
        ])

        evidence = build_motivation_top_three_evidence(owner, language_code="en")

        self.assertLess(evidence.index("Attachment"), evidence.index("Commercial focus"))
        self.assertLess(evidence.index("Commercial focus"), evidence.index("Risk"))
        self.assertNotIn("Stability — STIVE", evidence)


class CognitiveEvidenceTests(SimpleTestCase):
    def test_approved_cognitive_text_includes_percentile_in_english_and_swedish(self):
        english = build_cognitive_ai_evidence(
            {"numerical": 5},
            language_code="en",
        )
        swedish = build_cognitive_ai_evidence(
            {"numerical": 5},
            language_code="sv",
        )

        self.assertIn("percentile 5", english)
        self.assertIn(
            "considerably more difficult than most people in the reference group",
            english,
        )
        self.assertIn("percentil 5", swedish)
        self.assertIn(
            "Kandidaten kan uppleva det som betydligt svårare än de flesta i",
            swedish,
        )
        self.assertIn(
            "förstå och arbeta med numerisk information",
            swedish,
        )

    def test_historical_cognitive_evidence_reads_profile_percentiles(self):
        owner = SimpleNamespace(process=SimpleNamespace(is_historical=True))
        with patch(
            "apps.processes.services.candidate_profile.build_historical_candidate_profile",
            return_value={
                "ability_results": {
                    "numerical": {"percentile": 19},
                    "verbal": None,
                    "logical": None,
                }
            },
        ):
            evidence = build_owner_cognitive_ai_evidence(
                owner,
                language_code="en",
            )

        self.assertIn("percentile 19", evidence)
        self.assertIn("find it more difficult than many others", evidence)


class PurposeFitAssessmentPromptTests(SimpleTestCase):
    def _owner(self, motivation, percentile):
        return SimpleNamespace(
            candidate=SimpleNamespace(
                first_name="Anna",
                last_name="Example",
                email="anna@example.test",
            ),
            process=SimpleNamespace(
                is_historical=False,
                purpose="development",
                role_context=None,
            ),
            sova_activities=[
                {
                    "activity": "Personality",
                    "competencies": [
                        {"competency": "Adaptability", "sten": 7},
                    ],
                },
                {
                    "activity": "Motivation Questionnaire",
                    "competencies": motivation,
                },
                {
                    "activity": "Numerical reasoning",
                    "competencies": [
                        {"competency": "Numerical reasoning", "percentile": percentile},
                    ],
                },
            ],
        )

    def test_prompt_combines_distinct_motivation_and_skill_evidence(self):
        from apps.core.ai.purpose_fit import build_purpose_fit_prompt

        first = self._owner(
            [{"competency": "Risk", "stive": 4.9}],
            5,
        )
        second = self._owner(
            [{"competency": "Learning", "stive": 4.9}],
            95,
        )
        examples = {
            "title": "AI overview",
            "summary_1": "Summary",
            "support_1": "Support",
            "consider_1": "Consider",
            "next_step": "Next",
            "context_note": "Context",
        }

        with (
            patch(
                "apps.core.ai.purpose_fit.build_shared_ai_context",
                side_effect=lambda owner: {
                    "candidate": owner.candidate,
                    "purpose_label": "Development",
                    "purpose_key": "development",
                    "context_text": "",
                },
            ),
            patch(
                "apps.core.ai.purpose_fit.get_purpose_fit_output_examples",
                return_value=examples,
            ),
            patch(
                "apps.core.ai.purpose_fit.get_ai_prompt_instructions",
                return_value="ADMIN_SENTINEL_358",
            ),
            patch(
                "apps.core.ai.purpose_fit.get_ai_feature_prompt_instructions",
                return_value="Feature guidance",
            ),
            patch(
                "apps.core.ai.purpose_fit.build_owner_personality_ai_evidence_text",
                return_value="PERSONALITY_INDICATOR_STEN_SENTINEL",
            ) as personality_builder,
        ):
            first_prompt = build_purpose_fit_prompt(first, language_code="en")
            second_prompt = build_purpose_fit_prompt(second, language_code="en")

        self.assertIn("ADMIN_SENTINEL_358", first_prompt)
        self.assertIn("PERSONALITY_INDICATOR_STEN_SENTINEL", first_prompt)
        self.assertIn("INTERVIEW EVIDENCE LIMIT", first_prompt)
        self.assertIn("No interview notes or interview examples are supplied", first_prompt)
        self.assertIn("Risk — STIVE 4.9", first_prompt)
        self.assertIn("percentile 5", first_prompt)
        self.assertIn("considerably more difficult", first_prompt)
        self.assertIn("Learning — STIVE 4.9", second_prompt)
        self.assertIn("percentile 95", second_prompt)
        self.assertIn("considerably easier", second_prompt)
        self.assertNotEqual(first_prompt, second_prompt)
        personality_builder.assert_any_call(
            first,
            language_code="en",
            include_indicator_details=True,
        )


class PurposeFitFinalPayloadTests(SimpleTestCase):
    def test_final_sdk_payload_contains_admin_sentinel_and_redacts_candidate_pii(self):
        from apps.core.ai.purpose_fit import stream_candidate_purpose_fit

        owner = SimpleNamespace(
            candidate=SimpleNamespace(
                first_name="Anna",
                last_name="Example",
                email="anna@example.test",
            ),
            process=SimpleNamespace(is_historical=False, purpose="development"),
        )
        raw = Mock()
        raw.chat.completions.create.return_value = iter([])

        with (
            patch(
                "apps.core.ai.purpose_fit.get_openai_client",
                return_value=PrivacySafeOpenAI(raw),
            ),
            patch(
                "apps.core.ai.purpose_fit.get_chat_model",
                return_value="mock-model",
            ),
            patch(
                "apps.core.ai.purpose_fit.get_ai_system_language_instruction",
                return_value="Use only supplied evidence.",
            ),
            patch(
                "apps.core.ai.purpose_fit.build_purpose_fit_prompt",
                return_value=(
                    "ADMIN_SENTINEL_358. Candidate: Anna Example. "
                    "Email: anna@example.test. MOTIVATION STIVE 4.8; "
                    "COGNITIVE percentile 7; PERSONALITY indicator STEN 8."
                ),
            ),
        ):
            list(stream_candidate_purpose_fit(owner, language_code="en"))

        call = raw.chat.completions.create.call_args.kwargs
        payload = json.dumps(call["messages"], ensure_ascii=False)
        self.assertIn("ADMIN_SENTINEL_358", payload)
        self.assertIn("CANDIDATE_A", payload)
        self.assertIn("MOTIVATION STIVE 4.8", payload)
        self.assertIn("COGNITIVE percentile 7", payload)
        self.assertIn("PERSONALITY indicator STEN 8", payload)
        self.assertNotIn("Anna Example", payload)
        self.assertNotIn("anna@example.test", payload)
        self.assertTrue(call["stream"])
