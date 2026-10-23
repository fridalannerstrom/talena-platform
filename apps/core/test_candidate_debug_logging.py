"""Regression guard: do not print candidate or AI data in remaining application paths.

Avoid console dumps of Sova metadata, imported candidate filenames, generated
AI sections and Pinecone identifiers/responses. No external I/O is performed.
"""
import ast
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase


class CandidatePrivacyLoggingRegressionTests(SimpleTestCase):
    FILES = (
        "apps/core/ai/ingest.py",
        "apps/reports/services/candidate_insights.py",
        "apps/processes/services/historical_assessment_import.py",
        "apps/processes/services/candidate_insights.py",
        "apps/accounts/views.py",
    )

    def test_no_print_in_candidate_sensitive_modules(self):
        root = Path(settings.BASE_DIR)
        for path in self.FILES:
            with self.subTest(path=path):
                tree = ast.parse(
                    (root / path).read_text(encoding="utf-8"), filename=path
                )
                lines = [
                    node.lineno for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                ]
                self.assertEqual(lines, [], f"Potential raw PII printing in {path}")
