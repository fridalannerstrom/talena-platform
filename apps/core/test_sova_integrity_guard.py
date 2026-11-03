"""Ticket #195/#88/#89/#90: Sova Integrity Guard (no AI integration).

All payloads are synthetic: no production assessment data or credentials.
"""
import json
from types import SimpleNamespace
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils.translation import override

from apps.accounts.models import Company
from apps.core.integrations.integrity_guard import (
    extract_integrity_guard, integrity_guard_for_display, without_integrity_guard,
)
from apps.processes.models import Candidate, TestInvitation, TestProcess


class IntegrityGuardParserTests(SimpleTestCase):
    def test_nested_camelcase_and_list_diagnostics(self):
        payload = {
            "projectResults": {
                "projectScores": [{
                    "integrityGuard": {
                        "overallStatus": "2",
                        "statusDescription": "Manual review suggested",
                        "diagnostics": [
                            {"name": "IP Address", "status": 1},
                            {"name": "Browser Patrolling", "status": "2"},
                            {"name": "Unavailable", "status": 0},
                            {"name": "Missing status"},
                        ],
                    },
                }],
            },
        }
        data = extract_integrity_guard(payload)
        self.assertEqual(data["overall_status"], 2)
        self.assertEqual(data["overall_description"], "Manual review suggested")
        self.assertEqual(data["diagnostics"], {
            "ip_address": 1, "browser_patrolling": 2,
        })
        self.assertEqual(len(data["sources"]), 1)

    def test_flattened_status_zero_is_not_dropped(self):
        self.assertEqual(
            extract_integrity_guard({"integrityGuardStatus": 0})["overall_status"], 0,
        )

    def test_individual_assessments_retained_and_highest_concern_visible(self):
        data = extract_integrity_guard({"activities": [
            {"integrity_guard": {"status": 1, "diagnostics": {"ip_address": 1}}},
            {"integrity_guard": {"status": 2, "diagnostics": {"tab_switching": 2}}},
        ]})
        self.assertEqual(len(data["sources"]), 2)
        display = integrity_guard_for_display(data)
        self.assertEqual(display["state"], "concern")
        self.assertEqual(len(display["entries"]), 2)
        self.assertEqual(display["entries"][1]["diagnostics"][0]["state"], "concern")

    def test_error_is_not_confused_with_concern_or_clear(self):
        self.assertEqual(
            integrity_guard_for_display(extract_integrity_guard({
                "integrity_guard": {
                    "status": 3, "diagnostics": {"device_switching": 3},
                },
            }))["state"], "error",
        )
        self.assertEqual(
            integrity_guard_for_display({"overall_status": 1, "diagnostics": {"ip": 2}})["state"],
            "concern",
        )

    def test_missing_and_not_monitored_are_not_all_clear(self):
        self.assertFalse(integrity_guard_for_display({})["visible"])
        self.assertFalse(integrity_guard_for_display(None)["visible"])
        self.assertEqual(
            integrity_guard_for_display({"overall_status": 0})["state"], "not_monitored",
        )
        self.assertEqual(
            integrity_guard_for_display({"overall_description": "Monitoring pending"})["state"],
            "unknown",
        )
        for data in (
            {"activities": []},
            {"activities": [{"competency": "Integrity", "score": 2}]},
            {"integrity_guard_status": 9},
            {"integrity_guard_status": True},
        ):
            self.assertIsNone(extract_integrity_guard(data))

    def test_diagnostics_only_for_monitored_and_invalid_types_rejected(self):
        guard = extract_integrity_guard({"integrity_guard": {
            "overall_status": "1",
            "diagnostics": {
                "ip": 0, "browser": 1, "device": None,
                "engagement": "3", "invalid": True,
            },
        }})
        self.assertEqual(guard["diagnostics"], {"browser": 1, "engagement": 3})


class IntegrityGuardNoAITests(SimpleTestCase):
    def test_recursively_strips_guard_from_score_payload_without_mutation(self):
        payload = {
            "project_scores": [{
                "competency": "Integrity",
                "score": 8,
                "integrityGuard": {
                    "diagnostics": {"ip_address": 2},
                    "overallStatus": 2,
                },
            }],
            "integrity_guard_status": 2,
            "other": {"integrity_guard_data": {"status": 3}, "score": 6},
        }
        cleaned = without_integrity_guard(payload)
        self.assertNotIn("integrity_guard", json.dumps(cleaned).lower())
        self.assertNotIn("integrityGuard", json.dumps(cleaned))
        self.assertEqual(cleaned["project_scores"][0]["competency"], "Integrity")
        self.assertEqual(cleaned["other"]["score"], 6)
        self.assertIn("integrityGuard", payload["project_scores"][0])

    def test_existing_ai_context_cannot_embed_monitoring_data(self):
        from apps.ai_chat.services.candidate_chat_context import build_live_candidate_profile
        invitation = SimpleNamespace(
            sova_activities=[{
                "activity": "Personality",
                "status": "completed",
                "competencies": [{"competency": "Integrity", "sten": 6}],
                "integrity_guard": {"status": 2},
            }],
            project_results={
                "overall_score": 42,
                "scores": [
                    {"name": "Numerical", "score": 6,
                     "integrityGuard": {"overallStatus": 3}},
                ],
                "integrity_guard_status": 2,
            },
            overall_score=42,
        )
        profile = build_live_candidate_profile(invitation)
        body = json.dumps(profile)
        self.assertNotIn("integrity_guard", body.lower())
        self.assertNotIn("integrityGuard", body)
        self.assertIn('"score": 6', body)

    def test_assessment_evidence_never_passes_ig_status_to_ai(self):
        from apps.core.ai.purpose_fit import build_assessment_evidence
        invitation = SimpleNamespace(
            process=SimpleNamespace(is_historical=False),
            sova_activities=[{
                "activity": "Personality Questionnaire",
                "competencies": [{"competency": "Integrity", "sten": 6}],
                "integrityGuard": {"overallStatus": 2},
            }],
        )
        text, count = build_assessment_evidence(invitation)
        self.assertGreater(count, 0)
        self.assertNotIn("integrityGuard", text)
        self.assertNotIn("overallStatus", text)


class IntegrityGuardTemplateTests(SimpleTestCase):
    def render_panel(self, data, language="sv"):
        invitation = TestInvitation(integrity_guard=data)
        with override(language):
            return render_to_string(
                "customer/processes/partials/_integrity_guard_panel.html",
                {"invitation": invitation},
            )

    def test_appears_with_fixed_copy_and_no_ai_badge(self):
        html = self.render_panel({
            "overall_status": 2,
            "diagnostics": {"ip_address": 2, "device": 1},
        })
        self.assertIn("Integrity Guard", html)
        self.assertIn("Avvikelser behöver granskas", html)
        self.assertIn("betyder inte att kandidaten har fuskat", html)
        self.assertIn("IP-adress", html)
        self.assertNotIn("AI-genererat", html)
        en = self.render_panel({"overall_status": 3}, "en")
        self.assertIn("Monitoring error", en)
        self.assertIn("No AI interpretation is used.", en)

    def test_missing_guard_has_no_panel(self):
        self.assertNotIn('data-integrity-guard-panel', self.render_panel({}))

    def test_sova_description_is_escaped_in_html(self):
        html = self.render_panel({
            "overall_status": 2,
            "overall_description": "<script>danger()</script>",
        })
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>danger()</script>", html)

    def test_customer_and_admin_views_have_only_internal_guard(self):
        root = Path(settings.BASE_DIR)
        for path in (
            "templates/customer/processes/process_detail.html",
            "templates/admin/accounts/customer/process_detail.html",
            "templates/admin/accounts/companies/company_process_detail.html",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "_integrity_guard_badge.html",
                    (root / path).read_text(encoding="utf-8"),
                )
        for path in (
            "templates/customer/processes/_candidate_detail_sheet.html",
            "templates/admin/accounts/customer/candidate_detail.html",
            "templates/admin/accounts/companies/company_candidate_sheet.html",
        ):
            with self.subTest(path=path):
                self.assertIn(
                    "_integrity_guard_panel.html",
                    (root / path).read_text(encoding="utf-8"),
                )
        # Nothing in the candidate-facing portal or report mentions monitoring.
        self.assertNotIn(
            "integrity_guard",
            (root / "templates/candidate_results/_candidate_result_tab.html")
            .read_text(encoding="utf-8"),
        )


@override_settings(
    SOVA_WEBHOOK_TEST_SECRET="integrity-test-only-secret",
    SOVA_WEBHOOK_PROD_SECRET="",
    SOVA_WEBHOOK_SHARED_SECRET="",
)
class IntegrityGuardIngestTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="ig-only@example.test", email="ig-only@example.test",
            password="not-a-real-password",
        )
        company = Company.objects.create(name="IG synthetic company")
        process = TestProcess.objects.create(
            name="IG test project", company=company,
            project_code="SYNTHETIC", account_code="TEST",
            created_by=user,
        )
        candidate = Candidate.objects.create(
            first_name="Test", last_name="Person",
            email="ig-synthetic-candidate@example.test",
        )
        self.invitation = TestInvitation.objects.create(
            process=process, candidate=candidate,
            request_id="synthetic-ig-request", status="sent",
        )

    def post(self, extra=None, secret="integrity-test-only-secret"):
        payload = {
            "request_id": "synthetic-ig-request",
            "overall_status": "in progress",
            "activities": [],
        }
        payload.update(extra or {})
        return self.client.post(
            "/integrations/sova/ingest/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_TALENA_WEBHOOK_SECRET=secret,
        )

    def test_receives_stores_and_preserves_diagnostics(self):
        result = self.post({"project_results": {
            "project_scores": [{
                "integrity_guard": {
                    "status": 2, "description": "Review this test",
                    "diagnostics": {"ip_address": 1, "browser_patrolling": 2},
                },
            }],
        }})
        self.assertEqual(result.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard["overall_status"], 2)
        self.assertEqual(self.invitation.integrity_guard["overall_description"], "Review this test")
        self.assertEqual(self.invitation.integrity_guard["diagnostics"]["browser_patrolling"], 2)
        self.assertIn("project_scores", self.invitation.project_results)

    def test_missing_guard_never_breaks_or_erases_previous_value(self):
        self.assertEqual(self.post({"integrity_guard_status": 0}).status_code, 200)
        self.assertEqual(self.post({"project_results": {"overall_score": 87}}).status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard["overall_status"], 0)
        self.assertEqual(self.invitation.project_results["overall_score"], 87)
        self.assertEqual(self.invitation.status, "started")

    def test_legacy_assessments_without_guard_continue_working(self):
        self.assertEqual(self.post({"project_results": {"overall_score": 42}}).status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard, {})
        self.assertEqual(self.invitation.project_results["overall_score"], 42)

    def test_wrong_webhook_secret_cannot_store_guard(self):
        response = self.post({"integrity_guard_status": 2}, secret="wrong")
        self.assertEqual(response.status_code, 401)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard, {})
