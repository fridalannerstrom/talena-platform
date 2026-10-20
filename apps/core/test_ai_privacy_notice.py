"""No raw personal data in UI telemetry. Masking is acknowledged only if sent."""

import json
from unittest.mock import Mock

from django.http import JsonResponse, StreamingHttpResponse
from django.test import RequestFactory, SimpleTestCase

from apps.core.ai.openai_client import PrivacySafeOpenAI
from apps.core.middleware import AIPiiMaskingNoticeMiddleware


class AIPiiMaskingNoticeTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.raw = Mock()
        self.client = PrivacySafeOpenAI(self.raw)

    def _send(self, message="Anna Svensson was interviewed."):
        return self.client.chat.completions.create(
            model="test",
            messages=[{"role": "user", "content": message}],
        )

    def test_sends_only_boolean_header_when_text_was_masked(self):
        def view(request):
            self._send("Anna Svensson got STEN 8. anna@example.se")
            return JsonResponse({"ok": True})

        response = AIPiiMaskingNoticeMiddleware(view)(self.factory.get("/test/"))
        self.assertEqual(response["X-Talena-AI-PII-Masked"], "1")
        self.assertNotIn("Anna", str(response.headers))
        self.assertNotIn("anna@example.se", str(response.headers))
        self.assertEqual(response.json() if hasattr(response, "json") else
                         json.loads(response.content), {"ok": True})
        args = self.raw.chat.completions.create.call_args.kwargs
        self.assertNotIn("Anna Svensson", str(args["messages"]))
        self.assertNotIn("anna@example.se", str(args["messages"]))
        self.assertIn("STEN 8", str(args["messages"]))

    def test_does_not_report_masking_when_no_identifier_changed(self):
        def view(request):
            self._send("Customer Service STIVE 4. STEN 8.")
            return JsonResponse({"ok": True})

        response = AIPiiMaskingNoticeMiddleware(view)(self.factory.get("/test/"))
        self.assertNotIn("X-Talena-AI-PII-Masked", response)
        self.assertEqual(self.raw.chat.completions.create.call_count, 1)

    def test_does_not_report_preexisting_placeholders(self):
        def view(request):
            self._send("Candidate CANDIDATE_A has STEN 8.")
            return JsonResponse({"ok": True})

        response = AIPiiMaskingNoticeMiddleware(view)(self.factory.get("/test/"))
        self.assertNotIn("X-Talena-AI-PII-Masked", response)

    def test_only_reports_after_sdk_accepts_request(self):
        self.raw.chat.completions.create.side_effect = RuntimeError("Network failure")

        def view(request):
            try:
                self._send("Anna Svensson was interviewed.")
            except RuntimeError:
                pass
            return JsonResponse({"error": "AI generation failed"}, status=502)

        response = AIPiiMaskingNoticeMiddleware(view)(self.factory.get("/test/"))
        self.assertNotIn("X-Talena-AI-PII-Masked", response)

    def test_multiple_calls_send_only_boolean_and_no_raw_data(self):
        def view(request):
            self._send("Anna Svensson sent an email.")
            self._send("John Smith completed the interview.")
            return JsonResponse({"ok": True})

        response = AIPiiMaskingNoticeMiddleware(view)(self.factory.get("/test/"))
        self.assertEqual(response["X-Talena-AI-PII-Masked"], "1")
        self.assertEqual(len(response["X-Talena-AI-PII-Masked"]), 1)

    def test_stream_emits_one_privacy_event_only_after_masked_send(self):
        def stream():
            yield '{"type":"started"}\n'
            self._send("Anna Svensson completed the assessment.")
            yield '{"type":"completed"}\n'

        def view(request):
            return StreamingHttpResponse(
                stream(), content_type="application/x-ndjson; charset=utf-8"
            )

        response = AIPiiMaskingNoticeMiddleware(view)(self.factory.get("/test/"))
        self.assertNotIn("X-Talena-AI-PII-Masked", response)
        chunks = list(response.streaming_content)
        events = [json.loads(chunk) for chunk in chunks]
        self.assertEqual(
            [event["type"] for event in events],
            ["started", "ai_privacy_masked", "completed"],
        )
        self.assertNotIn("Anna Svensson", "".join(chunks))

    def test_no_stream_notice_without_actual_masking(self):
        def stream():
            yield '{"type":"started"}\n'
            self._send("Customer Service STIVE 4.")
            yield '{"type":"completed"}\n'

        response = AIPiiMaskingNoticeMiddleware(
            lambda request: StreamingHttpResponse(
                stream(), content_type="application/x-ndjson"
            )
        )(self.factory.get("/test/"))
        events = [json.loads(chunk) for chunk in response.streaming_content]
        self.assertEqual([e["type"] for e in events], ["started", "completed"])

    def test_request_context_is_not_reused_by_later_request(self):
        def view(request):
            if request.GET.get("redact"):
                self._send("Anna Svensson interviewed.")
            return JsonResponse({"ok": True})

        middleware = AIPiiMaskingNoticeMiddleware(view)
        first = middleware(self.factory.get("/test/?redact=1"))
        later = middleware(self.factory.get("/test/"))
        self.assertEqual(first["X-Talena-AI-PII-Masked"], "1")
        self.assertNotIn("X-Talena-AI-PII-Masked", later)

    def test_sdk_embedding_and_responses_are_also_covered(self):
        def view(request):
            self.client.embeddings.create(model="embed", input="anna@example.se")
            self.client.responses.create(model="test", input="John Smith")
            return JsonResponse({"ok": True})

        response = AIPiiMaskingNoticeMiddleware(view)(self.factory.get("/test/"))
        self.assertEqual(response["X-Talena-AI-PII-Masked"], "1")
        self.assertEqual(
            self.raw.embeddings.create.call_args.kwargs["input"], "[EMAIL]"
        )
        self.assertEqual(
            self.raw.responses.create.call_args.kwargs["input"], "[PERSON]"
        )

    def test_customer_layout_includes_bilingual_privacy_notice(self):
        from pathlib import Path
        from django.conf import settings

        root = Path(settings.BASE_DIR)
        base = (root / "templates/customer/core/layouts/customer_base.html").read_text(
            encoding="utf-8"
        )
        js = (root / "static/js/talena/ai-privacy-notice.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("ai-privacy-notice.js", base)
        self.assertIn("ai-privacy-notice.css", base)
        self.assertIn("Personuppgifter har maskats", js)
        self.assertIn("Personal data has been masked", js)
        self.assertIn('const EVENT_TYPE = "ai_privacy_masked"', js)
        self.assertIn('const HEADER = "X-Talena-AI-PII-Masked"', js)
        self.assertNotIn("localStorage", js)
