"""Synthetic regression coverage for opted-in Talena AI metering (#435)."""
import csv
import io
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import Company, User
from apps.activity.models import ActivityEvent
from apps.activity.services import customer_visible_activity
from apps.core.ai.openai_client import PrivacySafeOpenAI
from apps.core.ai.pii_sanitizer import PrivacySanitizationError
from apps.core.ai.usage_metrics import record_ai_call
from apps.processes.models import TestProcess


class AIClientMeteringTests(SimpleTestCase):
    def setUp(self):
        self.raw = Mock()
        self.messages = [{"role": "user", "content": "Safe test"}]

    @patch("apps.core.ai.openai_client.sanitize_ai_payload", side_effect=lambda x: x)
    @patch("apps.core.ai.openai_client.record_ai_call")
    def test_disabled_by_default_does_not_change_provider_request(self, record, sanitize):
        with patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "0"}):
            client = PrivacySafeOpenAI(self.raw, feature="personality_questions")
            client.chat.completions.create(
                model="gpt-test", messages=self.messages, stream=True,
            )
        record.assert_not_called()
        self.assertNotIn("stream_options", self.raw.chat.completions.create.call_args.kwargs)

    @patch("apps.core.ai.openai_client.sanitize_ai_payload", side_effect=lambda x: x)
    @patch("apps.core.ai.openai_client.record_ai_call")
    def test_usage_only_stream_event_is_not_forwarded_to_existing_consumers(self, record, sanitize):
        content = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))], usage=None)
        usage_chunk = SimpleNamespace(
            choices=[],
            usage=SimpleNamespace(prompt_tokens=17, completion_tokens=9, total_tokens=26),
        )
        self.raw.chat.completions.create.return_value = iter([content, usage_chunk])
        with patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"}):
            client = PrivacySafeOpenAI(self.raw, feature="personality_questions")
            stream = client.chat.completions.create(
                model="gpt-test", messages=self.messages, stream=True,
            )
            self.assertEqual(list(stream), [content])
        self.assertEqual(
            self.raw.chat.completions.create.call_args.kwargs["stream_options"],
            {"include_usage": True},
        )
        record.assert_called_once()
        self.assertEqual(record.call_args.kwargs["outcome"], "succeeded")
        self.assertIs(record.call_args.kwargs["usage"], usage_chunk.usage)

    @patch("apps.core.ai.openai_client.sanitize_ai_payload", side_effect=lambda x: x)
    @patch("apps.core.ai.openai_client.record_ai_call")
    def test_partial_stream_is_distinct_from_success(self, record, sanitize):
        self.raw.chat.completions.create.return_value = iter([
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="one"))], usage=None),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="two"))], usage=None),
        ])
        with patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"}):
            client = PrivacySafeOpenAI(self.raw, feature="post_interview")
            stream = client.chat.completions.create(
                model="gpt-test", messages=self.messages, stream=True,
            )
            next(stream)
            stream.close()
        self.assertEqual(record.call_args.kwargs["outcome"], "incomplete")

    @patch("apps.core.ai.openai_client.sanitize_ai_payload", side_effect=lambda x: x)
    @patch("apps.core.ai.openai_client.record_ai_call")
    def test_stream_exception_is_failed_not_successful(self, record, sanitize):
        def broken_stream():
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="partial"))], usage=None)
            raise RuntimeError("private provider message")
        self.raw.chat.completions.create.return_value = broken_stream()
        with patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"}):
            client = PrivacySafeOpenAI(self.raw, feature="overall_picture")
            with self.assertRaises(RuntimeError):
                list(client.chat.completions.create(
                    model="gpt-test", messages=self.messages, stream=True,
                ))
        record.assert_called_once()
        self.assertEqual(record.call_args.kwargs["outcome"], "failed")
        self.assertNotIn("private provider message", repr(record.call_args))

    @patch("apps.core.ai.openai_client.sanitize_ai_payload", side_effect=lambda x: x)
    @patch("apps.core.ai.openai_client.record_ai_call")
    def test_sdk_error_preserves_original_error_and_logs_no_exception_text(self, record, sanitize):
        self.raw.chat.completions.create.side_effect = RuntimeError("secret provider response")
        with patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"}):
            client = PrivacySafeOpenAI(self.raw, feature="motivation_questions")
            with self.assertRaises(RuntimeError):
                client.chat.completions.create(model="gpt-test", messages=self.messages)
        self.assertEqual(record.call_args.kwargs["outcome"], "failed")
        self.assertNotIn("secret provider response", repr(record.call_args))

    @patch("apps.core.ai.openai_client.record_ai_call")
    @patch("apps.core.ai.openai_client.sanitize_ai_payload",
           side_effect=PrivacySanitizationError("blocked"))
    def test_rejected_sensitive_payload_never_counts_as_provider_call(self, sanitize, record):
        with patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"}):
            client = PrivacySafeOpenAI(self.raw, feature="motivation_questions")
            with self.assertRaises(PrivacySanitizationError):
                client.chat.completions.create(model="gpt-test", messages=self.messages)
        self.raw.chat.completions.create.assert_not_called()
        record.assert_not_called()


class AIStatisticsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="ai-metrics-admin", email="ai-metrics-admin@example.test",
            password="not-used",
        )
        self.outsider = User.objects.create_user(
            username="ai-metrics-outsider", email="outsider@example.test",
            password="not-used",
        )
        self.company = Company.objects.create(name="Synthetic metrics tenant")
        self.other_company = Company.objects.create(name="Other metrics tenant")
        self.process = TestProcess.objects.create(
            company=self.company, created_by=self.admin,
            name="Synthetic metrics process", purpose="hiring",
            account_code="MODERN", project_code="PQ",
            selected_tests=["personality"],
        )
        self.url = reverse("core:admin_ai_statistics")
        self.export_url = reverse("core:admin_ai_statistics_export")

    @patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"})
    def test_metadata_has_allowlist_and_project_tenant_but_no_candidate_or_prompt(self):
        record_ai_call(
            feature="personality_questions", operation="chat", model="gpt-4o-mini",
            outcome="succeeded", owner=SimpleNamespace(process=self.process),
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3, total_tokens=13),
        )
        event = ActivityEvent.objects.get(verb=ActivityEvent.Verb.AI_CALL_SUCCEEDED)
        self.assertEqual(event.company_id, self.company.pk)
        self.assertEqual(event.process_id, self.process.pk)
        self.assertIsNone(event.candidate_id)
        self.assertIsNone(event.actor_id)
        self.assertEqual(event.meta["total_tokens"], 13)
        self.assertEqual(set(event.meta), {
            "schema", "feature", "operation", "model", "usage_available",
            "prompt_tokens", "completion_tokens", "total_tokens",
        })
        self.assertEqual(customer_visible_activity(ActivityEvent.objects.all()).count(), 0)

    @patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"})
    def test_invalid_feature_model_and_usage_cannot_pollute_audit(self):
        record_ai_call(
            feature="arbitrary candidate@example.test", operation="chat",
            model="gpt-4o-mini", outcome="succeeded", process=self.process,
        )
        self.assertEqual(ActivityEvent.objects.count(), 0)
        record_ai_call(
            feature="overall_picture", operation="chat",
            model="candidate@example.test with secret", outcome="succeeded",
            process=self.process, usage=SimpleNamespace(total_tokens="12"),
        )
        event = ActivityEvent.objects.get()
        self.assertEqual(event.meta["model"], "unidentified")
        self.assertFalse(event.meta["usage_available"])
        self.assertNotIn("total_tokens", event.meta)

    def _events(self):
        for company, feature, verb, tokens in (
            (self.company, "overall_picture", ActivityEvent.Verb.AI_CALL_SUCCEEDED, 25),
            (self.company, "overall_picture", ActivityEvent.Verb.AI_CALL_FAILED, None),
            (self.other_company, "team_insights", ActivityEvent.Verb.AI_CALL_SUCCEEDED, 10),
        ):
            meta = {"schema": 1, "feature": feature, "operation": "chat",
                    "model": "gpt-test", "usage_available": tokens is not None}
            if tokens is not None:
                meta.update({"prompt_tokens": tokens - 5,
                             "completion_tokens": 5, "total_tokens": tokens})
            ActivityEvent.objects.create(verb=verb, company=company, meta=meta)

    def test_only_platform_admin_can_read_dashboard_or_aggregate_export(self):
        self._events()
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(self.export_url).status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {"company": str(self.company.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["totals"]["count"], 2)
        self.assertEqual(response.context["totals"]["succeeded"], 1)
        self.assertEqual(response.context["totals"]["failed"], 1)
        self.assertEqual(response.context["totals"]["tokens"], 25)
        self.assertContains(response, 'class="talena-ai-stats"')
        export = self.client.get(self.export_url, {"company": str(self.company.pk)})
        self.assertEqual(export.status_code, 200)
        data = list(csv.reader(io.StringIO(export.content.decode("utf-8"))))
        self.assertEqual(len(data), 2)
        self.assertEqual(data[1][2], "overall_picture")
        self.assertNotIn("other_company", export.content.decode("utf-8"))
        self.assertNotIn("Synthetic metrics", export.content.decode("utf-8"))

    def test_empty_state_and_invalid_dates_are_handled(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {"from": "2026-13-55", "to": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["totals"]["count"], 0)
        self.assertEqual(response.context["feature_rows"], [])
