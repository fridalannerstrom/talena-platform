"""Prevent reintroduction of sensitive debugging on critical data paths.

Static checks supplement, but do not replace, runtime log/telemetry review.
"""
import ast
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class SensitiveDebugLoggingContractTests(SimpleTestCase):
    """Sensitive Sova and AI paths must not write raw data to stdout."""

    PATHS_WITH_NO_PRINTS = (
        "apps/core/integrations/sova.py",
        "apps/core/integrations/views.py",
        "apps/core/webhooks.py",
        "apps/core/middleware.py",
        "apps/core/ai/motivation_questions.py",
        "apps/core/ai/cognitive_questions.py",
    )

    def test_no_print_calls_in_sensitive_integration_and_ai_paths(self):
        for path in self.PATHS_WITH_NO_PRINTS:
            with self.subTest(path=path):
                source = (Path(settings.BASE_DIR) / path).read_text(
                    encoding="utf-8"
                )
                tree = ast.parse(source, filename=path)
                unsafe = [
                    node.lineno
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                ]
                self.assertEqual(
                    unsafe, [],
                    f"{path}: print() can leak candidate/provider data",
                )

    def test_legacy_webhook_raw_dumping_remains_disabled(self):
        root = Path(settings.BASE_DIR)
        webhook = (root / "apps/core/webhooks.py").read_text(encoding="utf-8")
        sova = (root / "apps/core/integrations/sova.py").read_text(
            encoding="utf-8"
        )
        middleware = (root / "apps/core/middleware.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "SOVA_WEBHOOK_DEBUG_TO_FILE",
            "debug_webhooks",
            "dict(request.headers)",
            "WEBHOOK RAW FULL",
            "WEBHOOK JSON PRETTY",
        ):
            self.assertNotIn(forbidden, webhook)
        self.assertNotIn("r.text", sova)
        self.assertNotIn("request.get_full_path()", middleware)
