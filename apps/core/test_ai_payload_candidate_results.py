"""Candidate result content is built from approved static libraries."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.candidate_results.interpretation import generate_candidate_result_content


class CandidateResultStaticContentTests(SimpleTestCase):
    def _invitation(self):
        return SimpleNamespace(
            candidate=SimpleNamespace(
                first_name="Anna",
                last_name="Example",
                email="anna@example.test",
            ),
            process=SimpleNamespace(is_historical=False),
            # Private identifiers and report links must never enter the report.
            sova_activities=[
                {
                    "activity": "Personality",
                    "sova_person_id": "SOVA-RAW-ID-741928",
                    "private_url": "https://example.test/private/sova-report-741928",
                    "competencies": [
                        {"competency": "Teamwork", "sten": 8},
                    ],
                },
                {
                    "activity": "Logical reasoning",
                    "sova_person_id": "SOVA-RAW-ID-741928",
                    "private_url": "https://example.test/report-secret-741928",
                    "competencies": [
                        {"competency": "Logical reasoning", "percentile": 72},
                    ],
                },
            ],
            project_results={"internal_reference": "PROJECT-PRIVATE-741928"},
            sova_reports=[{"url": "https://example.test/report-secret-741928"}],
            ai_summary="AI summary must not appear in the candidate report.",
            ai_personality_interpretation={"interpretation": "AI personality text."},
            ai_motivation_interpretation={"interpretation": "AI motivation text."},
            ai_cognitive_interpretation={"interpretation": "AI cognitive text."},
        )

    @patch(
        "apps.core.ai.openai_client.get_openai_client",
        side_effect=AssertionError("Candidate results must not call OpenAI."),
    )
    def test_static_report_excludes_raw_payload_and_ai_text_in_both_locales(
        self, get_client
    ):
        for language in ("sv", "en"):
            with self.subTest(language=language):
                content, metadata, fingerprint = generate_candidate_result_content(
                    self._invitation(), language_code=language
                )
                data = json.dumps(content, ensure_ascii=False).casefold()

                self.assertIn("introduction", content)
                self.assertEqual(metadata["content_version"], "candidate-static-v1")
                self.assertTrue(fingerprint)
                for secret in (
                    "sova-raw-id-741928",
                    "project-private-741928",
                    "sova-report-741928",
                    "report-secret-741928",
                    "anna@example.test",
                    "ai summary must not appear",
                    "ai personality text",
                    "ai motivation text",
                    "ai cognitive text",
                ):
                    self.assertNotIn(secret, data)
                self.assertNotIn("sten", data)
                self.assertNotIn("percentile", data)
                self.assertNotIn("72", data)

        get_client.assert_not_called()
