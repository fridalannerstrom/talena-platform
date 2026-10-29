"""Synthetic regression tests for Sova Integrity Guard score-push ingestion.

These fixtures describe supported possible payload shapes; they are NOT
claimed to be captured from the real Sova sandbox.
"""
import json
import os
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from apps.accounts.models import Company
from apps.processes.models import Candidate, TestInvitation, TestProcess
from apps.core.integrations.integrity_guard import extract_integrity_guard


class IntegrityGuardParserTests(SimpleTestCase):
    def test_nested_project_score_and_camel_case_fields(self):
        payload = {
            "projectResults": {
                "projectScores": [{
                    "integrityGuard": {
                        "overallStatus": "2",
                        "statusDescription": "Some checks require review",
                        "diagnostics": [
                            {"name": "IP Address", "status": 1},
                            {"name": "Browser Patrolling", "status": "2"},
                            {"name": "Not monitored", "status": 0},
                            {"name": "No status"},
                        ],
                    }
                }]
            }
        }
        parsed = extract_integrity_guard(payload)
        self.assertEqual(parsed["overall_status"], 2)
        self.assertEqual(parsed["overall_description"], "Some checks require review")
        self.assertEqual(parsed["diagnostics"], {
            "ip_address": 1,
            "browser_patrolling": 2,
        })
        self.assertEqual(len(parsed["sources"]), 1)

    def test_not_monitored_zero_is_valid(self):
        self.assertEqual(
            extract_integrity_guard({"integrity_guard_status": 0})["overall_status"], 0
        )

    def test_flattened_diagnostic_object(self):
        result = extract_integrity_guard({
            "project_results": {
                "integrityGuardStatus": "3",
                "integrityGuardDescription": "Monitoring failed",
                "integrityGuardDiagnostics": {"device_switching": {"status": 3}},
            }
        })
        self.assertEqual(result["overall_status"], 3)
        self.assertEqual(result["overall_description"], "Monitoring failed")
        self.assertEqual(result["diagnostics"], {"device_switching": 3})

    def test_guard_object_with_direct_diagnostic_statuses(self):
        result = extract_integrity_guard({"integrity_guard": {
            "status": 1, "ip_address_status": 1, "device_status": 2,
        }})
        self.assertEqual(result["diagnostics"], {"ip_address": 1, "device": 2})

    def test_retains_separate_sources_for_multiple_assessments(self):
        result = extract_integrity_guard({"activities": [
            {"integrity_guard": {"status": 1, "diagnostics": {"ip": 1}}},
            {"integrity_guard": {"status": 2, "diagnostics": {"browser": 2}}},
        ]})
        self.assertEqual(len(result["sources"]), 2)
        self.assertEqual(result["sources"][1]["overall_status"], 2)

    def test_missing_or_unrelated_integrity_competency_does_not_match(self):
        self.assertIsNone(extract_integrity_guard({
            "activities": [{"competencies": [{"competency": "Integrity", "score": 2}]}],
            "project_results": {"overall_score": 87},
        }))
        self.assertIsNone(extract_integrity_guard({"activities": []}))
        self.assertIsNone(extract_integrity_guard({"integrity_guard_status": 7}))
        self.assertIsNone(extract_integrity_guard({"integrity_guard_status": True}))
        self.assertIsNone(extract_integrity_guard(None))

    def test_only_explicitly_monitored_diagnostics_are_included(self):
        result = extract_integrity_guard({"integrity_guard": {
            "overall_status": 0,
            "diagnostics": {
                "ip": 0,
                "device": None,
                "browser": 1,
                "response_pattern": "3",
            },
        }})
        self.assertEqual(result["overall_status"], 0)
        self.assertEqual(result["diagnostics"], {"browser": 1, "response_pattern": 3})


@override_settings(SOVA_WEBHOOK_TEST_SECRET="synthetic-test-secret")
class IntegrityGuardIngestTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="integrity-test@example.com",
            email="integrity-test@example.com",
            password="synthetic-test-password",
        )
        company = Company.objects.create(name="Synthetic Sova Company")
        process = TestProcess.objects.create(
            name="Synthetic Sova Project",
            company=company,
            project_code="synthetic-project",
            account_code="synthetic-account",
            created_by=user,
        )
        candidate = Candidate.objects.create(
            first_name="Synthetic",
            last_name="Candidate",
            email="integrity-synthetic-candidate@example.com",
        )
        self.invitation = TestInvitation.objects.create(
            process=process, candidate=candidate,
            request_id="synthetic-integrity-request", status="sent",
        )

    def _post(self, extra=None, secret="synthetic-test-secret"):
        payload = {
            "request_id": "synthetic-integrity-request",
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

    def test_saves_guard_scores_and_description_from_webhook(self):
        response = self._post({"project_results": {
            "project_scores": [{
                "integrity_guard": {
                    "overall_status": 2,
                    "description": "Please review",
                    "diagnostics": {"ip_address": 1, "browser_patrolling": 2},
                }
            }]
        }})
        self.assertEqual(response.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard["overall_status"], 2)
        self.assertEqual(self.invitation.integrity_guard["overall_description"], "Please review")
        self.assertEqual(self.invitation.integrity_guard["diagnostics"], {
            "ip_address": 1, "browser_patrolling": 2,
        })
        self.assertIn("project_scores", self.invitation.project_results)

    def test_follow_up_without_guard_does_not_erase_prior_result(self):
        self._post({"integrity_guard": {"status": 1, "diagnostics": {"ip": 1}}})
        self.assertEqual(self._post().status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard["overall_status"], 1)

    def test_absent_guard_leaves_unmonitored_assessments_untouched(self):
        self.assertEqual(self._post({"project_results": {"overall_score": 12}}).status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard, {})
        self.assertEqual(self.invitation.project_results, {"overall_score": 12})

    def test_zero_status_persists(self):
        self.assertEqual(self._post({"integrity_guard_status": 0}).status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard["overall_status"], 0)

    def test_wrong_webhook_secret_rejected_without_updating_guard(self):
        self.assertEqual(self._post({"integrity_guard_status": 2}, secret="wrong").status_code, 401)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard, {})

    @override_settings(
        DEBUG=True,
        ENVIRONMENT="local",
        SOVA_LOCAL_CALLBACK_BASE_URL="https://museum-scuff-guts.ngrok-free.dev",
        SOVA_LOCAL_CALLBACK_TOKEN="T" * 48,
    )
    @patch.dict(os.environ, {"SOVA_ENV_BASE": "https://api-test.sovaonline.com"})
    def test_local_callback_accepts_valid_token_without_header(self):
        response = self.client.post(
            "/integrations/sova/local/" + ("T" * 48) + "/",
            data=json.dumps({
                "request_id": "synthetic-integrity-request",
                "overall_status": "in progress",
                "integrity_guard": {"status": 2, "diagnostics": {"browser": 2}},
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard["overall_status"], 2)

    @override_settings(
        DEBUG=True,
        ENVIRONMENT="local",
        SOVA_LOCAL_CALLBACK_BASE_URL="https://museum-scuff-guts.ngrok-free.dev",
        SOVA_LOCAL_CALLBACK_TOKEN="T" * 48,
    )
    @patch.dict(os.environ, {"SOVA_ENV_BASE": "https://api-test.sovaonline.com"})
    def test_local_callback_rejects_wrong_token(self):
        response = self.client.post(
            "/integrations/sova/local/" + ("F" * 48) + "/",
            data=json.dumps({
                "request_id": "synthetic-integrity-request",
                "integrity_guard": {"status": 2},
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard, {})

    @override_settings(
        DEBUG=False,
        ENVIRONMENT="prod",
        ALLOWED_HOSTS=["testserver"],
        SOVA_LOCAL_CALLBACK_BASE_URL="https://museum-scuff-guts.ngrok-free.dev",
        SOVA_LOCAL_CALLBACK_TOKEN="T" * 48,
    )
    @patch.dict(os.environ, {"SOVA_ENV_BASE": "https://api-test.sovaonline.com"})
    def test_local_callback_is_disabled_in_production(self):
        response = self.client.post(
            "/integrations/sova/local/" + ("T" * 48) + "/",
            data=json.dumps({"request_id": "synthetic-integrity-request"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)


    @override_settings(
        DEBUG=True,
        ENVIRONMENT="local",
        SOVA_LOCAL_CALLBACK_BASE_URL="https://museum-scuff-guts.ngrok-free.dev",
        SOVA_LOCAL_CALLBACK_TOKEN="T" * 48,
    )
    @patch.dict(os.environ, {"SOVA_ENV_BASE": "https://api-test.sovaonline.com"})
    @patch("apps.processes.services.send_tests.log_event")
    @patch("apps.processes.services.send_tests.register_sent_assessments")
    @patch("apps.processes.services.send_tests.EmailMultiAlternatives")
    @patch("apps.processes.services.send_tests.EmailLog.objects.create")
    @patch("apps.processes.services.send_tests.EmailTemplate.objects.filter")
    @patch("apps.core.integrations.sova.SovaClient")
    def test_new_sandbox_order_includes_both_callback_urls(
        self, sova_client_cls, template_filter, email_log_create,
        email_cls, register_usage, log_event,
    ):
        from apps.processes.services.send_tests import send_assessments_and_emails

        self.invitation.status = "created"
        self.invitation.save(update_fields=["status"])
        sova_client = sova_client_cls.return_value
        sova_client.get_accounts_with_projects.return_value = []
        sova_client.order_assessment.return_value = {
            "url": "https://assessment.example.test/synthetic-test"
        }
        template_filter.return_value.first.return_value = None
        email_log_create.return_value = MagicMock(id=505)
        email_cls.return_value.send.return_value = 1

        result = send_assessments_and_emails(
            process=self.invitation.process,
            invitations=[self.invitation],
            actor_user=self.invitation.process.created_by,
        )
        self.assertEqual(result["sent_count"], 1, result["errors"])

        payload = sova_client.order_assessment.call_args.args[1]
        callback = (
            "https://museum-scuff-guts.ngrok-free.dev/integrations/sova/local/"
            + ("T" * 48) + "/"
        )
        self.assertEqual(payload["status_callback_url"], callback)
        self.assertEqual(payload["results_callback_url"], callback)
        register_usage.assert_called_once()


class LocalSovaCallbackConfigTests(SimpleTestCase):
    @override_settings(
        DEBUG=True, ENVIRONMENT="local",
        SOVA_LOCAL_CALLBACK_BASE_URL="https://museum-scuff-guts.ngrok-free.dev",
        SOVA_LOCAL_CALLBACK_TOKEN="T" * 48,
    )
    @patch.dict(os.environ, {"SOVA_ENV_BASE": "https://api-test.sovaonline.com"})
    def test_generates_local_callback_url_from_ngrok_only(self):
        from apps.core.integrations.local_callbacks import get_local_sova_callback_url

        url = get_local_sova_callback_url()
        self.assertEqual(
            url,
            "https://museum-scuff-guts.ngrok-free.dev/integrations/sova/local/"
            + ("T" * 48) + "/",
        )

    @override_settings(DEBUG=True, ENVIRONMENT="local",
                       SOVA_LOCAL_CALLBACK_BASE_URL="", SOVA_LOCAL_CALLBACK_TOKEN="")
    def test_disabled_by_default(self):
        from apps.core.integrations.local_callbacks import get_local_sova_callback_url

        self.assertIsNone(get_local_sova_callback_url())

    @override_settings(DEBUG=True, ENVIRONMENT="local",
                       SOVA_LOCAL_CALLBACK_BASE_URL="http://localhost:8000",
                       SOVA_LOCAL_CALLBACK_TOKEN="T" * 48)
    @patch.dict(os.environ, {"SOVA_ENV_BASE": "https://api-test.sovaonline.com"})
    def test_rejects_insecure_or_non_ngrok_callback(self):
        from apps.core.integrations.local_callbacks import get_local_sova_callback_url

        with self.assertRaises(ValueError):
            get_local_sova_callback_url()

    @override_settings(DEBUG=True, ENVIRONMENT="local",
                       SOVA_LOCAL_CALLBACK_BASE_URL="https://museum-scuff-guts.ngrok-free.dev",
                       SOVA_LOCAL_CALLBACK_TOKEN="T" * 48)
    @patch.dict(os.environ, {"SOVA_ENV_BASE": "https://api.sovaonline.com"})
    def test_rejects_production_sova_api(self):
        from apps.core.integrations.local_callbacks import get_local_sova_callback_url

        with self.assertRaises(ValueError):
            get_local_sova_callback_url()

    @override_settings(DEBUG=False, ENVIRONMENT="prod",
                       SOVA_LOCAL_CALLBACK_BASE_URL="https://museum-scuff-guts.ngrok-free.dev",
                       SOVA_LOCAL_CALLBACK_TOKEN="T" * 48)
    def test_never_generates_callback_in_production(self):
        from apps.core.integrations.local_callbacks import get_local_sova_callback_url

        self.assertIsNone(get_local_sova_callback_url())
