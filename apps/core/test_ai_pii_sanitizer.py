"""Regression tests for all outbound OpenAI payloads (#300).

No external calls, model download, candidate database or real API key needed.
"""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import SimpleTestCase

from apps.core.ai.pii_sanitizer import (
    PrivacySanitizationError,
    sanitize_ai_payload,
    sanitize_ai_text,
)
from apps.core.ai.openai_client import PrivacySafeOpenAI, get_openai_client


class LocalPIISanitizerTests(SimpleTestCase):
    def test_swedish_interview_example_masks_identifiers_not_evidence(self):
        original = (
            "Jag intervjuade Anna Svensson som arbetar med kundservice. "
            "Mejla anna.svensson@example.se eller ring 070-123 45 67. "
            "Personnummer 19900101-1234. "
            "Hon fick STEN 8 i Adaptability och 62:a percentilen."
        )
        clean = sanitize_ai_text(original)
        for value in ("Anna Svensson", "anna.svensson@example.se",
                      "070-123 45 67", "19900101-1234"):
            self.assertNotIn(value, clean)
        for expected in ("[PERSON]", "[EMAIL]", "[PHONE]", "[PERSONAL_ID]",
                         "kundservice", "STEN 8", "Adaptability", "percentilen"):
            self.assertIn(expected, clean)

    def test_english_interview_example_masks_names_email_and_phone(self):
        original = (
            "I spoke with John Smith after the interview. "
            "Email john.smith@example.com, phone +1 415 555 2671. "
            "The assessment showed Customer Service STIVE 4 of 5."
        )
        clean = sanitize_ai_text(original)
        self.assertNotIn("John Smith", clean)
        self.assertNotIn("john.smith@example.com", clean)
        self.assertNotIn("+1 415 555 2671", clean)
        self.assertIn("Customer Service STIVE 4 of 5", clean)

    def test_email_with_sentence_punctuation_is_still_masked(self):
        text = "Email john@example.org. Mail anna.svensson@example.se!"
        sanitized = sanitize_ai_text(text)
        self.assertNotIn("john@example.org", sanitized)
        self.assertNotIn("anna.svensson@example.se", sanitized)
        self.assertIn("[EMAIL].", sanitized)
        self.assertIn("[EMAIL]!", sanitized)

    def test_preserves_psychometric_terms_context_and_scores(self):
        source = (
            "Social Desirability: 8. Customer Service: STIVE 4 of 5. "
            "People Development: STIVE 3. Talent Qode assessment. "
            "Candidate Insights. Interview Summary. STEN 7."
        )
        self.assertEqual(sanitize_ai_text(source), source)

    def test_structured_json_keeps_keys_types_and_technical_metadata(self):
        payload = {
            "candidate": {
                "first_name": "Anna Svensson",
                "email": "anna.svensson@example.se",
                "interview_notes": "Call John Smith at 070-123 45 67.",
                "scores": [{"name": "Adaptability", "sten_rounded": 8, "score": 3.5}],
            },
            "project_id": 123,
            "is_historical": False,
        }
        result = sanitize_ai_payload(payload)
        self.assertEqual(result["candidate"]["first_name"], "[PERSON]")
        self.assertEqual(result["candidate"]["email"], "[EMAIL]")
        self.assertNotIn("John Smith", result["candidate"]["interview_notes"])
        self.assertIn("[PHONE]", result["candidate"]["interview_notes"])
        self.assertEqual(result["candidate"]["scores"], payload["candidate"]["scores"])
        self.assertEqual(result["project_id"], 123)
        self.assertIs(result["is_historical"], False)
        self.assertEqual(payload["candidate"]["email"], "anna.svensson@example.se")

    def test_serialized_json_preserves_field_names(self):
        payload = json.dumps({
            "candidate": "Anna Svensson",
            "contact_email": "anna@example.se",
            "score": 8,
        }, ensure_ascii=False)
        result = json.loads(sanitize_ai_payload(payload))
        self.assertEqual(result["candidate"], "[PERSON]")
        self.assertEqual(result["contact_email"], "[EMAIL]")
        self.assertEqual(result["score"], 8)

    def test_refuses_unexpected_payload_type_or_huge_text(self):
        with self.assertRaises(PrivacySanitizationError):
            sanitize_ai_payload(object())
        with self.assertRaises(PrivacySanitizationError):
            sanitize_ai_text("x" * 2_000_001)

    @patch.dict(os.environ, {"TALENA_PII_NER_SV_MODEL": "missing-model"})
    @patch("apps.core.ai.pii_sanitizer._local_ner",
           side_effect=RuntimeError("unavailable"))
    def test_missing_configured_model_fails_closed(self, _local_ner):
        with self.assertRaises(PrivacySanitizationError):
            sanitize_ai_text("Interview with Anna Svensson.")

    @patch.dict(os.environ, {
        "TALENA_PII_NER_SV_MODEL": "local-sv-test",
        "TALENA_PII_NER_EN_MODEL": "",
        "TALENA_PII_MASK_ORGANIZATIONS": "1",
        "TALENA_PII_MASK_LOCATIONS": "1",
    })
    @patch("apps.core.ai.pii_sanitizer._local_ner")
    def test_local_ner_masks_person_org_place_when_enabled(self, local_ner):
        def model(text):
            return SimpleNamespace(ents=[
                SimpleNamespace(
                    start_char=text.index(term),
                    end_char=text.index(term) + len(term),
                    label_=kind,
                )
                for term, kind in (
                    ("Freja Norrström", "PER"),
                    ("Acme Technologies", "ORG"),
                    ("Sundsvall", "LOC"),
                )
            ])
        local_ner.return_value = model
        result = sanitize_ai_text(
            "Freja Norrström arbetar på Acme Technologies i Sundsvall."
        )
        for term in ("Freja Norrström", "Acme Technologies", "Sundsvall"):
            self.assertNotIn(term, result)
        self.assertIn("[PERSON]", result)
        self.assertIn("[ORGANIZATION]", result)
        self.assertIn("[LOCATION]", result)


class OpenAIPrivacyBoundaryTests(SimpleTestCase):
    def setUp(self):
        self.raw_client = Mock()
        self.client = PrivacySafeOpenAI(self.raw_client)

    def test_chat_completions_masks_system_and_user_content(self):
        messages = [
            {"role": "system", "content": "Contact Anna Svensson."},
            {"role": "user", "content": (
                "Ring 070-123 45 67 and email anna@example.se; STEN 8."
            )},
        ]
        self.client.chat.completions.create(
            model="gpt-test", messages=messages, stream=True
        )
        kwargs = self.raw_client.chat.completions.create.call_args.kwargs
        sent = str(kwargs["messages"])
        self.assertNotIn("Anna Svensson", sent)
        self.assertNotIn("070-123 45 67", sent)
        self.assertNotIn("anna@example.se", sent)
        self.assertIn("STEN 8", sent)
        self.assertTrue(kwargs["stream"])
        self.assertEqual(messages[0]["content"], "Contact Anna Svensson.")

    def test_embedding_input_is_masked_before_model_request(self):
        self.client.embeddings.create(
            model="text-embedding-3-large",
            input=["Anna Svensson 070-123 45 67", "Customer Service: STIVE 4"],
        )
        kwargs = self.raw_client.embeddings.create.call_args.kwargs
        self.assertNotIn("Anna Svensson", str(kwargs["input"]))
        self.assertNotIn("070-123 45 67", str(kwargs["input"]))
        self.assertIn("Customer Service: STIVE 4", kwargs["input"])

    def test_responses_instructions_and_input_are_masked(self):
        self.client.responses.create(
            model="gpt-test",
            instructions="Talk to John Smith.",
            input=[{"role": "user", "content": "Email john@example.org."}],
        )
        kwargs = self.raw_client.responses.create.call_args.kwargs
        self.assertNotIn("John Smith", kwargs["instructions"])
        self.assertNotIn("john@example.org", str(kwargs["input"]))

    def test_sanitizer_failure_never_reaches_any_api(self):
        with patch(
            "apps.core.ai.openai_client.sanitize_ai_payload",
            side_effect=PrivacySanitizationError("blocked"),
        ):
            for kind in ("chat", "embedding", "response"):
                with self.subTest(kind=kind), self.assertRaises(PrivacySanitizationError):
                    if kind == "chat":
                        self.client.chat.completions.create(
                            model="gpt", messages=[{"role": "user", "content": "hi"}]
                        )
                    elif kind == "embedding":
                        self.client.embeddings.create(model="embed", input="hi")
                    else:
                        self.client.responses.create(model="gpt", input="hi")
        self.raw_client.chat.completions.create.assert_not_called()
        self.raw_client.embeddings.create.assert_not_called()
        self.raw_client.responses.create.assert_not_called()

    def test_raw_openai_sdk_is_only_constructed_in_privacy_entrypoint(self):
        root = Path(settings.BASE_DIR) / "apps"
        for path in root.rglob("*.py"):
            if (
                path.name == "openai_client.py"
                or path.name.startswith("test")
                or "migrations" in path.parts
            ):
                continue
            source = path.read_text(encoding="utf-8")
            with self.subTest(filename=str(path.relative_to(root))):
                self.assertNotIn("OpenAI(", source)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "fake-test-only"})
    @patch("apps.core.ai.openai_client.OpenAI")
    def test_public_client_factory_returns_the_safe_wrapper(self, raw_openai):
        client = get_openai_client()
        self.assertIsInstance(client, PrivacySafeOpenAI)
        self.assertTrue(callable(client.chat.completions.create))
        self.assertTrue(callable(client.embeddings.create))
        self.assertFalse(hasattr(client, "_raw"))
        raw_openai.assert_called_once_with(api_key="fake-test-only")
