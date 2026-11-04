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



# Shape confirmed from a 2026-11-03 Sova production score callback.
# All names and results here are synthetic. Never commit raw candidate payloads.
REAL_SOVA_GUARD_SHAPE = {
    "status": 2,
    "status_description": "Concerns Detected",
    "integrity_findings": [
        {
            "diagnostic": 1, "diagnostic_status": 1,
            "activities": [
                {"activity": "TQ Personality", "status": 1},
                {"activity": "TQ Motivation", "status": 1},
            ],
        },
        {
            "diagnostic": 2, "diagnostic_status": 1,
            "activities": [
                {"activity": "TQ Personality", "status": 1},
                {"activity": "TQ Motivation", "status": 1},
            ],
        },
        {
            "diagnostic": 3, "diagnostic_status": 1,
            "activities": [
                {"activity": "TQ Personality", "status": 1},
                {"activity": "TQ Motivation", "status": 1},
            ],
        },
        {
            "diagnostic": 4, "diagnostic_status": 2,
            "activities": [
                {"activity": "TQ Personality", "status": 2},
                {"activity": "TQ Motivation", "status": 2},
                {"activity": "TQ Verbal Reasoning", "status": 1},
                {"activity": "TQ Numerical Reasoning", "status": 2},
                {"activity": "TQ Logical Reasoning", "status": 1},
            ],
        },
    ],
}


class RealSovaIntegrityFindingsTests(SimpleTestCase):
    def _parsed(self):
        return extract_integrity_guard({
            "overall_status": "completed",  # overall assessment status, not Guard
            "integrity_guard": REAL_SOVA_GUARD_SHAPE,
        })

    def test_parses_four_numeric_diagnostics_with_per_test_states(self):
        data = self._parsed()
        self.assertEqual(data["overall_status"], 2)
        self.assertEqual(data["diagnostics"], {
            "ip_address": 1,
            "devices_used": 1,
            "browser_patrolling": 1,
            "question_engagement": 2,
        })
        self.assertEqual(len(data["sources"]), 1)
        findings = data["sources"][0]["findings"]
        self.assertEqual(len(findings), 4)
        self.assertEqual(findings[3]["activities"][0], {
            "name": "TQ Personality", "status": 2,
        })

    def test_display_matches_real_sova_recruiter_icons(self):
        display = integrity_guard_for_display(self._parsed())
        self.assertEqual(display["state"], "concern")
        checks = display["entries"][0]["diagnostics"]
        self.assertEqual(
            [item["name_sv"] for item in checks],
            ["IP-adress", "Använda enheter", "Byte av flik eller webbläsare", "Svarsmönster"],
        )
        self.assertEqual([item["state"] for item in checks], [
            "clear", "clear", "clear", "concern",
        ])
        self.assertEqual(
            {item["name"]: item["state"] for item in checks[3]["activities"]},
            {
                "TQ Personality": "concern",
                "TQ Motivation": "concern",
                "TQ Verbal Reasoning": "clear",
                "TQ Numerical Reasoning": "concern",
                "TQ Logical Reasoning": "clear",
            },
        )

    def test_existing_invitation_uses_original_payload_without_retake(self):
        legacy_stored = {
            "overall_status": 2,
            "overall_description": "Concerns Detected",
            "diagnostics": {},
            "sources": [{
                "path": "payload.integrity_guard",
                "overall_status": 2,
                "overall_description": "Concerns Detected",
                "diagnostics": {},
            }],
        }
        invitation = TestInvitation(
            integrity_guard=legacy_stored,
            sova_payload={"integrity_guard": REAL_SOVA_GUARD_SHAPE},
        )
        self.assertEqual(len(invitation.integrity_guard_display["entries"][0]["diagnostics"]), 4)
        self.assertEqual(invitation.integrity_guard, legacy_stored)

    def test_unknown_diagnostic_kept_neutral_without_guessing_label(self):
        value = {"integrity_guard": {
            "status": 2,
            "integrity_findings": [{
                "diagnostic": 99, "diagnostic_status": 2,
                "activities": [{"activity": "PQ", "status": 2}],
            }],
        }}
        entry = integrity_guard_for_display(extract_integrity_guard(value))["entries"][0]
        self.assertEqual(entry["diagnostics"][0]["name_sv"], "Kontroll 99")
        self.assertEqual(entry["diagnostics"][0]["activities"][0]["state"], "concern")

    def test_does_not_infer_individual_states_from_overall_warning(self):
        value = {"integrity_guard": {
            "status": 2,
            "integrity_findings": [{
                "diagnostic": 4, "diagnostic_status": 2,
                "activities": [{"activity": "Personality"}],
            }],
        }}
        entry = integrity_guard_for_display(extract_integrity_guard(value))["entries"][0]
        self.assertEqual(entry["diagnostics"][0]["state"], "concern")
        self.assertEqual(entry["diagnostics"][0]["activities"], [])

    def test_non_guard_personality_competency_does_not_get_parsed(self):
        self.assertIsNone(extract_integrity_guard({
            "activities": [{"activity": "PQ", "competencies": [
                {"competency": "Integrity", "sten": 5, "status": 2},
            ]}],
        }))


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
        header, body = html.split('<div class="talena-ig-panel__body">', 1)
        self.assertIn("Teknisk övervakningsinformation", header)
        self.assertIn('<span class="talena-ig-panel__subtitle">Teknisk övervakningsinformation</span>', header)
        self.assertIn("Avvikelser behöver granskas", body)
        self.assertIn('talena-ig-panel__status--concern', body)
        self.assertIn("betyder inte att kandidaten har fuskat", html)
        self.assertIn("IP-adress", html)
        self.assertNotIn("AI-genererat", html)
        en = self.render_panel({"overall_status": 3}, "en")
        self.assertIn("Monitoring error", en)
        self.assertIn("No AI interpretation is used.", en)

    def test_real_sova_findings_render_all_checks_in_both_languages(self):
        invitation = TestInvitation(
            integrity_guard={},
            sova_payload={"integrity_guard": REAL_SOVA_GUARD_SHAPE},
        )
        with override("sv"):
            html = render_to_string(
                "customer/processes/partials/_integrity_guard_panel.html",
                {"invitation": invitation},
            )
        self.assertIn("Svarsmönster", html)
        self.assertIn("IP-adress", html)
        self.assertIn("TQ Personality", html)
        self.assertIn("TQ Numerical Reasoning", html)
        self.assertIn("Avvikelse", html)
        self.assertIn("Övervakade tester", html)
        self.assertNotIn("Concerns Detected", html)
        with override("en"):
            english = render_to_string(
                "customer/processes/partials/_integrity_guard_panel.html",
                {"invitation": invitation},
            )
        self.assertIn("Question engagement", english)
        self.assertIn("Monitored assessments", english)
        self.assertIn("Concern", english)

    def test_report_starts_collapsed_and_keeps_status_in_expanded_body(self):
        html = self.render_panel({"overall_status": 2, "diagnostics": {"ip_address": 2}})
        self.assertIn('<details class="talena-ig-panel" data-integrity-guard-panel>', html)
        self.assertIn('<summary class="talena-ig-panel__toggle">', html)
        self.assertIn("Visa detaljer", html)
        self.assertIn("Dölj detaljer", html)
        self.assertIn("Avvikelser behöver granskas", html)
        self.assertNotIn('<details class="talena-ig-panel" data-integrity-guard-panel open', html)
        self.assertIn("IP-adress", html)
        self.assertIn('data-integrity-guard-guide', html)

    def test_compact_summary_does_not_spotlight_concern_but_explains_when_opened(self):
        for language, subtitle, explicit_status in (
            ("sv", "Teknisk övervakningsinformation", "Avvikelser behöver granskas"),
            ("en", "Technical monitoring information", "Concerns need review"),
        ):
            with self.subTest(language=language):
                html = self.render_panel({"overall_status": 2}, language)
                summary, details = html.split('<div class="talena-ig-panel__body">', 1)
                self.assertIn(subtitle, summary)
                self.assertIn(
                    '<span class="talena-ig-panel__subtitle">' + subtitle + '</span>',
                    summary,
                )
                self.assertIn(explicit_status, details)
        css = (Path(settings.BASE_DIR) / "static/css/talena/pages/integrity-guard.css").read_text(encoding="utf-8")
        self.assertIn("width:20px; height:20px; margin-left:5px", css)
        self.assertIn("width:24px; height:24px; border-radius:7px", css)

    def test_guide_is_collapsed_and_cautionary_in_both_languages(self):
        swedish = self.render_panel({"overall_status": 1})
        self.assertIn("Så tolkar du Integrity Guard", swedish)
        self.assertIn("En flagga är inte bevis på fusk.", swedish)
        self.assertIn("om hjälpmedlen är tillåtna", swedish)
        self.assertIn('<details class="talena-ig-panel__guide" data-integrity-guard-guide>', swedish)
        english = self.render_panel({"overall_status": 3}, "en")
        self.assertIn("How to interpret Integrity Guard", english)
        self.assertIn("A flag does not prove cheating.", english)
        self.assertIn("if those aids are permitted", english)
        self.assertIn("Show details", english)

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

    def test_production_sova_findings_shape_persists_without_other_result_changes(self):
        response = self.post({"integrity_guard": REAL_SOVA_GUARD_SHAPE})
        self.assertEqual(response.status_code, 200)
        self.invitation.refresh_from_db()
        data = self.invitation.integrity_guard
        self.assertEqual(data["overall_status"], 2)
        self.assertEqual(len(data["sources"][0]["findings"]), 4)
        self.assertEqual(data["diagnostics"]["question_engagement"], 2)
        self.assertEqual(len(data["sources"][0]["findings"][3]["activities"]), 5)
        self.assertIsNone(self.invitation.project_results)

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
