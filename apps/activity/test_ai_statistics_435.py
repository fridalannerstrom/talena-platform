"""Synthetic regression coverage for opted-in Talena AI metering (#435)."""
import csv
import io
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.http import StreamingHttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from apps.accounts.models import Company, User
from apps.activity.models import ActivityEvent
from apps.activity.services import customer_visible_activity
from apps.core.ai.openai_client import PrivacySafeOpenAI
from apps.core.ai.usage_metrics import ai_usage_actor_scope
from apps.core.middleware import AIPiiMaskingNoticeMiddleware
from apps.core.ai.pii_sanitizer import PrivacySanitizationError
from apps.core.ai.usage_metrics import record_ai_call
from apps.processes.models import Candidate, TestInvitation, TestProcess
from apps.processes.interview_question_models import ManagerReportTextEditEvent


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

    @patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"})
    def test_candidate_and_actor_derive_only_from_authenticated_request_and_invitation(self):
        candidate = Candidate.objects.create(
            first_name="Synthetic", last_name="Candidate", email="safe.test@example.test",
        )
        invitation = TestInvitation.objects.create(
            process=self.process, candidate=candidate,
        )
        with ai_usage_actor_scope(self.outsider.pk):
            record_ai_call(
                feature="personality_interpretation", operation="chat",
                model="gpt-test", outcome="succeeded", owner=invitation,
            )
        event = ActivityEvent.objects.get(verb=ActivityEvent.Verb.AI_CALL_SUCCEEDED)
        self.assertEqual(event.company_id, self.company.pk)
        self.assertEqual(event.process_id, self.process.pk)
        self.assertEqual(event.candidate_id, candidate.pk)
        self.assertEqual(event.actor_id, self.outsider.pk)
        self.assertNotIn("Synthetic", str(event.meta))
        self.assertNotIn("safe.test@example.test", str(event.meta))
        self.assertEqual(customer_visible_activity(ActivityEvent.objects.all()).count(), 0)

        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        row = response.context["call_rows"][0]
        self.assertEqual(row["company"], self.company.name)
        self.assertEqual(row["actor"], self.outsider.get_username())
        self.assertEqual(row["candidate"], str(candidate))
        self.assertEqual(row["process"], self.process.name)
        self.assertContains(response, str(candidate))

    @patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"})
    def test_owner_shaped_payload_cannot_spoof_candidate_link(self):
        candidate = Candidate.objects.create(
            first_name="Not", last_name="Attributed", email="not-attributed@example.test",
        )
        fake_owner = SimpleNamespace(
            process=self.process, candidate=candidate, candidate_id=candidate.pk,
        )
        record_ai_call(
            feature="personality_interpretation", operation="chat",
            model="gpt-test", outcome="succeeded", owner=fake_owner,
        )
        event = ActivityEvent.objects.get(verb=ActivityEvent.Verb.AI_CALL_SUCCEEDED)
        self.assertIsNone(event.candidate_id)
        self.assertIsNone(event.actor_id)

    def test_existing_event_without_actor_and_candidate_is_not_backfilled(self):
        self._events()
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {"company": str(self.company.pk)})
        self.assertEqual(response.status_code, 200)
        rows = response.context["call_rows"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["company"] == self.company.name for row in rows))
        self.assertTrue(all(row["actor"] is None for row in rows))
        self.assertTrue(all(row["candidate"] is None for row in rows))
        self.assertNotIn(self.other_company.name, [row["company"] for row in rows])

    def test_detail_rows_are_paginated_without_sensitive_csv_expansion(self):
        for n in range(29):
            ActivityEvent.objects.create(
                company=self.company, verb=ActivityEvent.Verb.AI_CALL_SUCCEEDED,
                meta={"schema": 1, "feature": "overall_picture", "operation": "chat"},
            )
        self.client.force_login(self.admin)
        first = self.client.get(self.url)
        second = self.client.get(self.url, {"page": "2"})
        self.assertEqual(first.context["call_page"].paginator.count, 29)
        self.assertEqual(len(first.context["call_rows"]), 25)
        self.assertEqual(len(second.context["call_rows"]), 4)
        self.assertContains(first, "page=2")
        exported = self.client.get(self.export_url)
        self.assertEqual(exported.status_code, 200)
        self.assertNotIn(self.admin.email, exported.content.decode("utf-8"))
        self.assertNotIn(self.company.name, exported.content.decode("utf-8"))

    @patch.dict(os.environ, {"TALENA_AI_USAGE_LOGGING_ENABLED": "1"})
    @patch("apps.core.ai.openai_client.sanitize_ai_payload", side_effect=lambda x: x)
    def test_authenticated_user_survives_deferred_stream_without_cross_request_leak(self, sanitize):
        candidate = Candidate.objects.create(
            first_name="Deferred", last_name="Candidate", email="deferred@example.test",
        )
        invitation = TestInvitation.objects.create(process=self.process, candidate=candidate)
        raw = Mock()
        raw.chat.completions.create.side_effect = lambda **kwargs: iter([
            SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content="ok"))],
                usage=None,
            ),
        ])

        def view(request):
            def chunks():
                client = PrivacySafeOpenAI(
                    raw, feature="personality_interpretation", owner=invitation,
                )
                for item in client.chat.completions.create(
                    model="gpt-test", messages=[{"role": "user", "content": "test"}],
                    stream=True,
                ):
                    yield item.choices[0].delta.content
            return StreamingHttpResponse(
                chunks(), content_type="text/plain",
            )

        mw = AIPiiMaskingNoticeMiddleware(view)
        request = RequestFactory().get("/synthetic/")
        request.user = self.outsider
        response = mw(request)
        # At this point the view has returned and the middleware has exited
        # its initial request context: the provider work is still deferred.
        self.assertEqual("".join(chunk.decode() if isinstance(chunk, bytes) else chunk
                                 for chunk in response.streaming_content), "ok")
        event = ActivityEvent.objects.get(verb=ActivityEvent.Verb.AI_CALL_SUCCEEDED)
        self.assertEqual(event.actor_id, self.outsider.pk)
        self.assertEqual(event.candidate_id, candidate.pk)

        # A second request with an anonymous user must never inherit that ID.
        from django.contrib.auth.models import AnonymousUser
        request2 = RequestFactory().get("/synthetic/")
        request2.user = AnonymousUser()
        list(mw(request2).streaming_content)
        latest = ActivityEvent.objects.filter(
            verb=ActivityEvent.Verb.AI_CALL_SUCCEEDED,
        ).order_by("-pk").first()
        self.assertIsNone(latest.actor_id)
        self.assertEqual(latest.candidate_id, candidate.pk)

    def test_operational_metrics_reuse_existing_events_but_not_internal_audit_or_ai(self):
        candidate = Candidate.objects.create(
            first_name="Synthetic", last_name="Stats", email="stats@example.test",
        )
        operational_events = [
            ActivityEvent.Verb.INVITE_SENT,
            ActivityEvent.Verb.TEST_COMPLETED,
            ActivityEvent.Verb.CANDIDATE_RESULT_LINK_OPENED,
            ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED,
        ]
        for verb in operational_events:
            ActivityEvent.objects.create(
                company=self.company, process=self.process,
                candidate=candidate, verb=verb,
            )
        # Preparing a PDF is not proof of a completed export.
        ActivityEvent.objects.create(
            company=self.company, process=self.process,
            verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
        )
        ActivityEvent.objects.create(
            company=None, actor=self.admin, verb=ActivityEvent.Verb.ADMIN_LOG_ACCESSED,
        )
        ActivityEvent.objects.create(
            company=self.company, process=self.process,
            verb=ActivityEvent.Verb.AI_CALL_SUCCEEDED,
            meta={"schema": 1, "feature": "overall_picture"},
        )
        ActivityEvent.objects.create(
            company=self.other_company, verb=ActivityEvent.Verb.INVITE_SENT,
        )
        ManagerReportTextEditEvent.objects.create(
            process=self.process, candidate=candidate, actor=self.admin,
            action=ManagerReportTextEditEvent.Action.SAVED,
            block_key="testbild", language_code="sv", version=1,
        )
        ManagerReportTextEditEvent.objects.create(
            process=self.process, candidate=candidate, actor=self.admin,
            action=ManagerReportTextEditEvent.Action.RESTORED_AI,
            block_key="testbild", language_code="sv", version=2,
        )

        self.client.force_login(self.admin)
        response = self.client.get(self.url, {
            "company": str(self.company.pk), "feature": "overall_picture",
        })
        self.assertEqual(response.status_code, 200)
        operational = response.context["operational"]
        totals = operational["totals"]
        self.assertEqual(totals["events"], 4)
        self.assertEqual(totals["companies"], 1)
        self.assertEqual(totals["projects"], 1)
        self.assertEqual(totals["invitations"], 1)
        self.assertEqual(totals["assessments_completed"], 1)
        self.assertEqual(totals["candidate_report_opens"], 1)
        self.assertEqual(totals["confirmed_manager_pdfs"], 1)
        self.assertEqual(totals["manager_text_edits"], 1)
        self.assertEqual(sum(group["count"] for group in operational["categories"]), 4)
        self.assertContains(response, "operational-metrics")
        self.assertContains(response, 'class="talena-ai-stats__operational"')

        # Opening either admin statistics or the activity log must not change
        # customer activity totals, even though access itself is audited.
        second = self.client.get(self.url, {"company": str(self.company.pk)})
        self.assertEqual(second.context["operational"]["totals"]["events"], 4)
        self.assertEqual(second.context["operational"]["totals"]["manager_text_edits"], 1)

    def test_operational_empty_state_is_zero_only_for_instrumented_events(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        operational = response.context["operational"]
        self.assertEqual(operational["totals"]["events"], 0)
        self.assertEqual(operational["totals"]["manager_text_edits"], 0)
        self.assertTrue(all(item["width"] == 0 for item in operational["categories"]))
        self.assertContains(response, 'talena-ai-stats__category-row')
