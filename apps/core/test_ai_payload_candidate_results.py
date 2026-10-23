"""Candidate result generation must not send complete Sova payloads to OpenAI.

Uses synthetic fixtures and a mocked raw SDK. Nothing is sent over the network.
"""
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.core.ai.openai_client import PrivacySafeOpenAI
from apps.candidate_results.interpretation import (
    build_candidate_result_source,
    generate_candidate_result_content,
)


class CandidateResultMinimisationTests(SimpleTestCase):
    def _invitation(self):
        return SimpleNamespace(
            candidate=SimpleNamespace(
                first_name="Anna",
                last_name="Example",
                email="anna@example.test",
            ),
            process=SimpleNamespace(
                purpose="Interview preparation",
                job_title="Analyst",
                role_context=SimpleNamespace(
                    get_current_context_text=lambda: "Analytical reasoning"
                ),
            ),
            # Identifiers, confidential metadata and report links MUST NOT
            # be forwarded merely because Sova saved them on the invitation.
            sova_activities=[{
                "activity": "Logical reasoning",
                "sova_person_id": "SOVA-RAW-ID-741928",
                "private_url": "https://example.test/private/sova-report-741928",
            }],
            project_results={"internal_reference": "PROJECT-PRIVATE-741928"},
            sova_reports=[{"url": "https://example.test/report-secret-741928"}],
            ai_summary="The candidate has analytical strengths.",
            ai_personality_interpretation={},
            ai_motivation_interpretation={},
            ai_cognitive_interpretation={},
        )

    def _areas(self):
        return {
            "personality": {"available": True, "evidence": "STEN 8 Adaptability"},
            "skills": {
                "available": True,
                "evidence": {
                    "cognitive_results": [
                        {"key": "logical", "percentile": 72}
                    ]
                },
            },
            "motivation": {"available": False, "evidence": {}},
        }

    def test_canonical_source_excludes_unfiltered_sova_objects(self):
        invitation = self._invitation()
        with patch(
            "apps.candidate_results.interpretation._candidate_result_areas",
            return_value=self._areas(),
        ):
            source = build_candidate_result_source(invitation)

        data = json.dumps(source, ensure_ascii=False)
        self.assertNotIn("assessment_evidence", source)
        for secret in (
            "SOVA-RAW-ID-741928",
            "PROJECT-PRIVATE-741928",
            "sova-report-741928",
            "report-secret-741928",
        ):
            self.assertNotIn(secret, data)
        self.assertIn("STEN 8", data)
        self.assertIn('"percentile": 72', data)

    def test_final_sdk_payload_excludes_raw_sova_ids_and_urls_sv_en(self):
        for language in ("sv", "en"):
            with self.subTest(language=language):
                invitation = self._invitation()
                raw = Mock()
                raw.chat.completions.create.return_value = SimpleNamespace(
                    choices=[SimpleNamespace(
                        message=SimpleNamespace(content='{"introduction": {"body": "Welcome"}}')
                    )]
                )
                with (
                    patch(
                        "apps.candidate_results.interpretation._candidate_result_areas",
                        return_value=self._areas(),
                    ),
                    patch(
                        "apps.candidate_results.interpretation.get_candidate_result_prompt_metadata",
                        return_value={},
                    ),
                    patch(
                        "apps.candidate_results.interpretation.get_ai_feature_prompt_instructions",
                        return_value="Use only supplied data.",
                    ),
                    patch(
                        "apps.candidate_results.interpretation.get_global_ai_guidance",
                        return_value="Respect user privacy.",
                    ),
                    patch(
                        "apps.candidate_results.interpretation.get_ai_language_instruction",
                        return_value="Use the required language.",
                    ),
                    patch(
                        "apps.candidate_results.interpretation.get_ai_system_language_instruction",
                        return_value="Use the required language.",
                    ),
                    patch(
                        "apps.candidate_results.interpretation.get_openai_client",
                        return_value=PrivacySafeOpenAI(raw),
                    ),
                ):
                    content, _, _ = generate_candidate_result_content(
                        invitation, language_code=language,
                    )

                self.assertIn("introduction", content)
                call = raw.chat.completions.create.call_args.kwargs
                payload = json.dumps(call["messages"], ensure_ascii=False)
                for secret in (
                    "SOVA-RAW-ID-741928",
                    "PROJECT-PRIVATE-741928",
                    "sova-report-741928",
                    "report-secret-741928",
                    "anna@example.test",
                ):
                    self.assertNotIn(secret, payload)
                self.assertIn("STEN 8", payload)
                self.assertIn("72", payload)
                self.assertEqual(call["response_format"]["type"], "json_object")
