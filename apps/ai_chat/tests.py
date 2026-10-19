"""Regression tests: legacy free-form and candidate AI chat is disabled (#302)."""

from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class DisabledChatEndpointTests(SimpleTestCase):
    """All legacy chat routes must refuse requests before touching OpenAI."""

    def test_chat_page_does_not_render(self):
        response = self.client.get(reverse("ai_chat:chat"))
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "chat-input", status_code=404)

    def test_nonstreaming_api_rejects_direct_requests(self):
        url = reverse("ai_chat:chat_api")
        with patch("apps.core.ai.chat.ask_ai") as ask_ai:
            for method in ("get", "post"):
                with self.subTest(method=method):
                    response = getattr(self.client, method)(
                        url,
                        data='{"message":"Please evaluate this candidate"}'
                        if method == "post" else None,
                        content_type="application/json",
                    )
                    self.assertEqual(response.status_code, 404)
            ask_ai.assert_not_called()

    def test_streaming_api_rejects_candidate_and_general_chat(self):
        url = reverse("ai_chat:chat_stream_api")
        payloads = [
            '{"message":"How do I use Talena?"}',
            '{"message":"Assess this person","process_id":1,"candidate_id":17}',
            '{"message":"Summarize candidate","process_id":2,"candidate_id":18,"is_historical":true}',
        ]
        with (
            patch("openai.OpenAI") as openai_client,
            patch(
                "apps.ai_chat.services.candidate_chat_context.build_candidate_chat_context"
            ) as context_builder,
        ):
            for payload in payloads:
                with self.subTest(payload=payload):
                    response = self.client.post(
                        url, data=payload, content_type="application/json"
                    )
                    self.assertEqual(response.status_code, 404)
                    self.assertNotIn("candidate", response.content.decode().lower())
            openai_client.assert_not_called()
            context_builder.assert_not_called()

    def test_old_chat_endpoints_are_blocked_even_without_login(self):
        for name in ("ai_chat:chat", "ai_chat:chat_api", "ai_chat:chat_stream_api"):
            with self.subTest(name=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)


class DisabledCandidateChatUITests(SimpleTestCase):
    def test_candidate_and_admin_templates_have_no_chat_widgets(self):
        root = Path(settings.BASE_DIR)
        paths = [
            "templates/customer/processes/_candidate_detail_sheet.html",
            "templates/admin/accounts/companies/company_candidate_sheet.html",
        ]
        forbidden = (
            "data-candidate-ai-widget",
            "js-candidate-ai-form",
            "js-candidate-ai-input",
            "data-chat-stream-url",
            "candidate-ai-floating-launcher",
        )
        for path in paths:
            with self.subTest(path=path):
                content = (root / path).read_text(encoding="utf-8")
                for fragment in forbidden:
                    self.assertNotIn(fragment, content)

    def test_legacy_chat_javascript_is_not_initialized(self):
        source = (
            Path(settings.BASE_DIR)
            / "templates/customer/processes/process_base.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("initCandidateAiChat(", source)
        self.assertNotIn(".js-candidate-ai-form", source)
        self.assertIn("initCandidateInsightsWorkspace(document);", source)
        self.assertIn("initGlobalAiUpdate(document);", source)

    def test_other_ai_generators_still_registered(self):
        from apps.processes import urls as process_urls

        patterns = [str(item.pattern) for item in process_urls.urlpatterns]
        self.assertTrue(
            any("candidate" in pattern for pattern in patterns),
            "Candidate process endpoints should remain registered.",
        )
