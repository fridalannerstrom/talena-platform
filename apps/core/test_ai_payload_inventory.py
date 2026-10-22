"""Privacy contract for active OpenAI callsites and representative final SDK payloads.

Only invented persons and mocked SDK clients are used. Nothing reaches OpenAI.
"""
import ast
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.test import SimpleTestCase

from apps.core.ai.openai_client import PrivacySafeOpenAI


def _qualified_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


class _OpenAICallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.function_stack = []
        self.calls = []
        self.factory_count = 0

    def visit_FunctionDef(self, node):
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        name = _qualified_name(node.func)
        if name == "get_openai_client":
            self.factory_count += 1
        if name.endswith(".chat.completions.create"):
            self.calls.append((self.function_stack[-1] if self.function_stack else None, "chat"))
        elif name.endswith(".embeddings.create"):
            self.calls.append((self.function_stack[-1] if self.function_stack else None, "embeddings"))
        elif name.endswith(".responses.create"):
            self.calls.append((self.function_stack[-1] if self.function_stack else None, "responses"))
        self.generic_visit(node)


class OpenAICallsiteManifestTests(SimpleTestCase):
    def test_every_sdk_callsite_has_a_reviewed_manifest_entry(self):
        root = Path(settings.BASE_DIR)
        manifest = json.loads(
            (root / "docs/security/301-openai-callsites.json").read_text(
                encoding="utf-8"
            )
        )
        entries = {item["path"]: item for item in manifest["entries"]}
        self.assertEqual(len(entries), len(manifest["entries"]))
        observed = {}
        for path in sorted((root / "apps").rglob("*.py")):
            if (
                path.name.startswith("test")
                or "migrations" in path.parts
                or path.name == "openai_client.py"
            ):
                continue
            visitor = _OpenAICallVisitor()
            visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
            if visitor.calls or visitor.factory_count:
                observed[path.relative_to(root).as_posix()] = visitor

        self.assertEqual(
            set(observed), set(entries),
            "New/removed AI callsite requires #301 manifest review."
        )
        for path, visitor in observed.items():
            item = entries[path]
            self.assertEqual(
                Counter(name for name, _ in visitor.calls),
                Counter(item["functions"]),
                path + ": SDK calls changed; inspect raw/final data contract."
            )
            self.assertEqual(len(visitor.calls), item["calls"], path)
            self.assertGreater(visitor.factory_count, 0, path)
            self.assertTrue(item["data"], path + " is missing data categories")
            self.assertTrue(item["status"], path + " is missing reachability status")
        self.assertEqual(sum(len(v.calls) for v in observed.values()), 22)
        self.assertEqual(len(observed), 16)

    def test_manifest_distinguishes_inactive_chat_and_shadowed_code(self):
        root = Path(settings.BASE_DIR)
        data = json.loads(
            (root / "docs/security/301-openai-callsites.json").read_text(
                encoding="utf-8"
            )
        )
        entries = {item["path"]: item for item in data["entries"]}
        self.assertEqual(
            entries["apps/core/ai/chat.py"]["status"],
            "inactive_chat_route_disabled",
        )
        self.assertEqual(
            entries["apps/core/ai/decision_support.py"]["status"],
            "active_plus_shadowed_legacy_definition",
        )
        self.assertIn(
            "not_verified_network_payloads", data["status"]
        )


class FinalOpenAIPayloadTests(SimpleTestCase):
    """Inspect kwargs passed to the raw SDK mock, after PrivacySafeOpenAI."""

    def _raw_client(self):
        raw = Mock()
        raw.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))]
        )
        raw.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2])]
        )
        return raw

    def test_flexible_insights_sanitizes_real_prompt_builder_input_sv_en(self):
        from apps.reports.services.candidate_insights import (
            generate_general_candidate_insights,
        )

        for language in ("sv", "en"):
            with self.subTest(language=language):
                raw = self._raw_client()
                wrapped = PrivacySafeOpenAI(raw)
                with (
                    patch(
                        "apps.reports.services.candidate_insights.get_openai_client",
                        return_value=wrapped,
                    ),
                    patch(
                        "apps.reports.services.candidate_insights._normalise_general_insights",
                        return_value={"summary": {"headline": "Neutral"}},
                    ),
                    patch(
                        "apps.reports.services.candidate_insights.get_ai_system_language_instruction",
                        return_value="Write using the supplied evidence.",
                    ),
                ):
                    generate_general_candidate_insights(
                        candidate_name="CANDIDATE_A",
                        insight_input={
                            "personality": {
                                "sample_note": (
                                    "Anna Svensson answered the interview. "
                                    "anna.svensson@example.test 070-123 45 67. "
                                    "STEN 8 in Adaptability."
                                ),
                                "sten": 8,
                            }
                        },
                        language_code=language,
                    )
                kwargs = raw.chat.completions.create.call_args.kwargs
                payload = json.dumps(kwargs["messages"], ensure_ascii=False)
                for secret in (
                    "Anna Svensson", "anna.svensson@example.test",
                    "070-123 45 67",
                ):
                    self.assertNotIn(secret, payload)
                for expected in (
                    "[PERSON]", "[EMAIL]", "[PHONE]", "STEN 8",
                    "Adaptability",
                ):
                    self.assertIn(expected, payload)
                self.assertEqual(kwargs["messages"][1]["role"], "user")
                self.assertEqual(kwargs["response_format"]["type"], "json_object")

    def test_candidate_summary_redacts_known_name_even_when_only_first_used(self):
        from apps.core.ai.candidate_summary import stream_candidate_summary

        candidate = SimpleNamespace(
            first_name="Frida", last_name="Example",
            email="frida@example.test",
        )
        owner = SimpleNamespace(candidate=candidate)
        for language in ("sv", "en"):
            with self.subTest(language=language):
                raw = self._raw_client()
                raw.chat.completions.create.return_value = iter([])
                wrapped = PrivacySafeOpenAI(raw)
                with (
                    patch(
                        "apps.core.ai.candidate_summary.get_openai_client",
                        return_value=wrapped,
                    ),
                    patch(
                        "apps.core.ai.candidate_summary.build_candidate_prompt",
                        return_value=(
                            "Frida answered the interview. "
                            "Frida Example scored STEN 8. "
                            "Contact: frida@example.test."
                        ),
                    ),
                    patch(
                        "apps.core.ai.candidate_summary.get_ai_system_language_instruction",
                        return_value="Neutral language instruction.",
                    ),
                ):
                    list(stream_candidate_summary(owner, language_code=language))

                sent = json.dumps(
                    raw.chat.completions.create.call_args.kwargs["messages"],
                    ensure_ascii=False,
                )
                self.assertNotIn("Frida", sent)
                self.assertNotIn("Example", sent)
                self.assertNotIn("frida@example.test", sent)
                self.assertIn("CANDIDATE_A", sent)
                self.assertIn("STEN 8", sent)
                self.assertTrue(
                    raw.chat.completions.create.call_args.kwargs["stream"]
                )

    def test_real_embedding_helper_sanitizes_before_sdk(self):
        from apps.core.ai.rag import embed_text

        raw = self._raw_client()
        with patch(
            "apps.core.ai.rag.get_openai_client",
            return_value=PrivacySafeOpenAI(raw),
        ):
            result = embed_text(
                "Research note by Anna Svensson, anna@example.test. "
                "Customer Service STIVE 4."
            )

        self.assertEqual(result, [0.1, 0.2])
        sent = raw.embeddings.create.call_args.kwargs["input"]
        self.assertNotIn("Anna Svensson", sent)
        self.assertNotIn("anna@example.test", sent)
        self.assertIn("Customer Service STIVE 4", sent)
        raw.chat.completions.create.assert_not_called()
