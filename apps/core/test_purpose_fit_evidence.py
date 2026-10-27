"""AI Overview evidence must use the candidate's approved assessment interpretations."""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.core.ai.motivation_interpretation import (
    build_motivation_top_three_evidence,
    build_motivation_summary_supplement,
)
from apps.core.ai.openai_client import PrivacySafeOpenAI
from apps.processes.services.cognitive_insights import (
    build_cognitive_ai_evidence,
    build_owner_cognitive_ai_evidence,
    build_owner_cognitive_summary_supplement,
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


class MotivationSummaryCoverageTests(SimpleTestCase):
    def test_omitted_top_factor_gets_approved_text_without_stive_score(self):
        owner = SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=[{
                "activity": "Motivation Questionnaire",
                "competencies": [
                    {"competency": "Authority", "stive": 4.7},
                    {"competency": "Variation", "stive": 4.9},
                    {"competency": "Recognition", "stive": 4.8},
                ],
            }],
        )

        supplement = build_motivation_summary_supplement(
            owner,
            "Motivation för variation och erkännande kan öka engagemanget.",
            language_code="sv",
        )

        self.assertIn("Auktoritet", supplement)
        self.assertIn(FACTOR_CONTENT["authority"]["top_text"], supplement)
        self.assertNotIn("STIVE", supplement)
        self.assertNotIn("4.7", supplement)


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


class CognitiveSummaryCoverageTests(SimpleTestCase):
    def _owner(self, *, activities=None):
        return SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=activities or [],
        )

    def test_missing_swedish_cognitive_results_get_approved_text_without_scores(self):
        owner = self._owner(activities=[
            {
                "activity": "Sova Logical Reasoning Assessment",
                "competencies": [{"percentile": 10}],
            },
            {
                "activity": "Sova Numerical Reasoning Assessment",
                "competencies": [{"percentile": 2}],
            },
            {
                "activity": "Sova Verbal Reasoning Assessment",
                "competencies": [{"percentile": 3}],
            },
        ])

        supplement = build_owner_cognitive_summary_supplement(
            owner,
            "Personen verkar samarbetsvillig och uppskattar variation.",
            language_code="sv",
        )

        self.assertIn("Färdighetsresultaten kompletterar bilden", supplement)
        self.assertIn("identifiera mönster och dra logiska slutsatser", supplement)
        self.assertIn("förstå och arbeta med numerisk information", supplement)
        self.assertIn("förstå och utvärdera skriftlig information", supplement)
        self.assertNotIn("percentil", supplement.casefold())
        self.assertNotIn("STEN", supplement)
        self.assertNotIn("STIVE", supplement)

    def test_covered_cognitive_domains_are_not_duplicated(self):
        owner = self._owner(activities=[
            {
                "activity": "Sova Logical Reasoning Assessment",
                "competencies": [{"percentile": 10}],
            },
            {
                "activity": "Sova Numerical Reasoning Assessment",
                "competencies": [{"percentile": 2}],
            },
            {
                "activity": "Sova Verbal Reasoning Assessment",
                "competencies": [{"percentile": 3}],
            },
        ])

        supplement = build_owner_cognitive_summary_supplement(
            owner,
            (
                "Kandidaten kan ha en preferens för att dra logiska slutsatser. "
                "Numerisk information kan upplevas utmanande och skriftlig "
                "information kan ta längre tid att bearbeta."
            ),
            language_code="sv",
        )

        self.assertEqual("", supplement)


class PurposeFitCognitiveCoverageStreamTests(SimpleTestCase):
    def test_omitted_cognitive_results_are_supplemented_before_done(self):
        from apps.core.ai.purpose_fit import stream_candidate_purpose_fit

        owner = SimpleNamespace(
            candidate=SimpleNamespace(
                first_name="Anna",
                last_name="Example",
                email="anna@example.test",
            ),
            process=SimpleNamespace(is_historical=False, purpose="development"),
            sova_activities=[
                {
                    "activity": "Motivation Questionnaire",
                    "competencies": [
                        {"competency": "Authority", "stive": 4.7},
                        {"competency": "Variation", "stive": 4.9},
                        {"competency": "Recognition", "stive": 4.8},
                    ],
                },
                {
                    "activity": "Sova Logical Reasoning Assessment",
                    "competencies": [{"percentile": 10}],
                },
                {
                    "activity": "Sova Numerical Reasoning Assessment",
                    "competencies": [{"percentile": 2}],
                },
                {
                    "activity": "Sova Verbal Reasoning Assessment",
                    "competencies": [{"percentile": 3}],
                },
            ],
        )
        raw = Mock()
        model_text = (
            json.dumps({
                "type": "summary_delta",
                "text": "Personen uppskattar variation och erkännande.",
            })
            + "\n"
            + json.dumps({"type": "done"})
            + "\n"
        )
        raw.chat.completions.create.return_value = iter([
            SimpleNamespace(
                choices=[SimpleNamespace(
                    delta=SimpleNamespace(content=model_text)
                )]
            )
        ])

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
                return_value="Synthetic prompt.",
            ),
        ):
            events = list(
                stream_candidate_purpose_fit(owner, language_code="sv")
            )

        summaries = [event for event in events if event["type"] == "summary_delta"]
        self.assertEqual(len(summaries), 2)
        self.assertIn("Auktoritet", summaries[1]["text"])
        self.assertIn("Färdighetsresultaten kompletterar bilden", summaries[1]["text"])
        self.assertIn("förstå och arbeta med numerisk information", summaries[1]["text"])
        self.assertEqual(events[-1]["type"], "done")


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
        self.assertIn("OVERALL INTERPRETATION COVERAGE", first_prompt)
        self.assertIn("name every listed factor", first_prompt)
        self.assertIn("statement about each ability result", first_prompt)
        self.assertIn("a two-sentence personality-only", first_prompt)
        self.assertIn("overview is incomplete.", first_prompt)
        self.assertIn("raw STEN, STIVE, or percentile values", first_prompt)
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
