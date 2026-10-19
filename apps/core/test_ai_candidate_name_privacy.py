"""Regression tests for #298: candidate identity must not reach OpenAI."""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.ai.candidate_name_privacy import redact_candidate_name
from apps.core.ai.shared_context import build_shared_ai_context
from apps.ai_chat.services.candidate_chat_context import (
    build_live_candidate_profile,
    build_historical_chat_profile,
)


class CandidateNamePrivacyTests(SimpleTestCase):
    def setUp(self):
        self.candidate = SimpleNamespace(
            id=319,
            first_name="Mira",
            last_name="Nordberg",
            email="mira.nordberg@example.invalid",
        )
        self.process = SimpleNamespace(
            purpose="hiring",
            role_context=None,
            is_historical=False,
        )
        self.owner = SimpleNamespace(candidate=self.candidate, process=self.process)

    def assert_no_candidate_identifiers(self, payload):
        content = str(payload).casefold()
        for item in ("mira", "nordberg", "mira nordberg", "mira.nordberg@example.invalid"):
            self.assertNotIn(item, content)

    def test_redacts_known_names_and_email_in_free_text(self):
        prompt = (
            "Mira Nordberg said Mira completed the assessment. "
            "NORDberg wrote to mira.nordberg@example.invalid. "
            "Mirabelle works in another department."
        )
        clean = redact_candidate_name(prompt, self.candidate)
        self.assertIn("CANDIDATE_A", clean)
        self.assertIn("Mirabelle", clean)
        self.assert_no_candidate_identifiers(clean)

    def test_generic_candidate_label_does_not_corrupt_prompt_schema(self):
        synthetic_candidate = SimpleNamespace(
            first_name="Test",
            last_name="Candidate",
            email="test.candidate@example.invalid",
        )
        prompt = (
            'CANDIDATE DATA: {"candidate": {"reference": "CANDIDATE_A"}}. '
            "Test Candidate completed an interview. "
            "Send to test.candidate@example.invalid."
        )
        cleaned = redact_candidate_name(prompt, synthetic_candidate)
        self.assertIn('"candidate":', cleaned)
        self.assertIn("CANDIDATE DATA", cleaned)
        self.assertNotIn("Test Candidate", cleaned)
        self.assertNotIn("test.candidate@example.invalid", cleaned)

    def test_shared_context_never_exposes_candidate_name_or_email_in_name_fields(self):
        context = build_shared_ai_context(self.owner)
        self.assertEqual(context["candidate_name"], "CANDIDATE_A")
        self.assertEqual(context["candidate_first_name"], "CANDIDATE_A")
        self.assertIs(context["candidate"], self.candidate)  # Internal use only.

    def test_live_candidate_chat_context_omits_identifiers(self):
        invitation = SimpleNamespace(
            candidate=self.candidate,
            sova_activities=[],
            project_results={},
            overall_score=None,
        )
        result = build_live_candidate_profile(invitation)
        self.assertEqual(result["candidate"], {"reference": "CANDIDATE_A"})
        self.assert_no_candidate_identifiers(result)
        self.assertNotIn("email", result["candidate"])
        self.assertNotIn("id", result["candidate"])

    @patch("apps.ai_chat.services.candidate_chat_context.build_historical_candidate_profile")
    def test_historical_candidate_chat_context_omits_identifiers(self, build_profile):
        build_profile.return_value = {}
        result = build_historical_chat_profile(SimpleNamespace(candidate=self.candidate))
        self.assertEqual(result["candidate"], {"reference": "CANDIDATE_A"})
        self.assert_no_candidate_identifiers(result)

    @patch("apps.core.ai.candidate_summary.get_ai_system_language_instruction", return_value="")
    @patch("apps.core.ai.candidate_summary.build_candidate_prompt")
    @patch("apps.core.ai.candidate_summary.get_openai_client")
    def test_summary_outbound_messages_omit_names(
        self, get_client, build_prompt, _language
    ):
        from apps.core.ai.candidate_summary import stream_candidate_summary

        build_prompt.return_value = (
            "Interview notes: Mira Nordberg met with Mira. "
            "Send follow-up to mira.nordberg@example.invalid."
        )
        get_client.return_value.chat.completions.create.return_value = []
        list(stream_candidate_summary(self.owner, language_code="sv"))
        kwargs = get_client.return_value.chat.completions.create.call_args.kwargs
        self.assert_no_candidate_identifiers(kwargs["messages"])
        self.assertIn("CANDIDATE_A", str(kwargs["messages"]))

    @patch("apps.core.ai.personality_interpretation.get_ai_system_language_instruction", return_value="")
    @patch("apps.core.ai.personality_interpretation.build_motivation_results_for_personality_owner", return_value=[])
    @patch("apps.core.ai.personality_interpretation.build_personality_interpretation_prompt")
    @patch("apps.core.ai.personality_interpretation.get_openai_client")
    def test_personality_outbound_messages_omit_names(
        self, get_client, build_prompt, _motivation, _language
    ):
        from apps.core.ai.personality_interpretation import stream_personality_interpretation

        build_prompt.return_value = "Mira Nordberg and Mira describe leadership."
        get_client.return_value.chat.completions.create.return_value = []
        list(
            stream_personality_interpretation(
                owner=self.owner,
                personality_results=[{"name": "Creativity", "sten": 8}],
                language_code="en",
            )
        )
        kwargs = get_client.return_value.chat.completions.create.call_args.kwargs
        self.assert_no_candidate_identifiers(kwargs["messages"])

    @patch("apps.core.ai.decision_support.build_post_interview_content_block_prompt")
    @patch("apps.core.ai.decision_support.get_openai_client")
    def test_after_interview_outbound_messages_omit_name_in_notes(
        self, get_client, build_prompt
    ):
        from apps.core.ai.decision_support import stream_post_interview_content_block

        build_prompt.return_value = (
            "Saved question: How did Mira Nordberg lead? "
            "Interviewer notes: Mira said yes, email mira.nordberg@example.invalid."
        )
        get_client.return_value.chat.completions.create.return_value = [
            SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        delta=SimpleNamespace(content="Text"),
                        finish_reason="stop",
                    )
                ]
            )
        ]
        list(
            stream_post_interview_content_block(
                owner=self.owner,
                block_key="overall_picture",
                language_code="sv",
            )
        )
        kwargs = get_client.return_value.chat.completions.create.call_args.kwargs
        self.assert_no_candidate_identifiers(kwargs["messages"])
        self.assertIn("CANDIDATE_A", str(kwargs["messages"]))

    @patch("apps.candidate_results.interpretation.normalise_candidate_result_content", return_value={})
    @patch("apps.candidate_results.interpretation._parse_json_content", return_value={})
    @patch("apps.candidate_results.interpretation.build_candidate_result_prompt")
    @patch("apps.candidate_results.interpretation.build_candidate_result_source")
    @patch("apps.candidate_results.interpretation.get_openai_client")
    def test_candidate_result_outbound_messages_omit_name(
        self, get_client, build_source, build_prompt, _parse, _normalise
    ):
        from apps.candidate_results.interpretation import generate_candidate_result_content

        build_source.return_value = {"available_result_areas": {}}
        build_prompt.return_value = (
            "Name: Mira Nordberg. Email: mira.nordberg@example.invalid.",
            {},
        )
        get_client.return_value.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))]
        )
        generate_candidate_result_content(self.owner, language_code="en")
        kwargs = get_client.return_value.chat.completions.create.call_args.kwargs
        self.assert_no_candidate_identifiers(kwargs["messages"])

    def test_no_direct_name_interpolation_remains_in_ai_prompt_sources(self):
        """Prevent accidental reintroduction of the old inline name template."""
        from pathlib import Path

        root = Path(__file__).resolve().parent / "ai"
        sources = list(root.glob("*.py"))
        sources.append(root.parent.parent / "candidate_results" / "interpretation.py")
        for path in sources:
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("{candidate.first_name} {candidate.last_name}", source)
                self.assertNotIn('Name: {shared_context["candidate_name"]}', source)
