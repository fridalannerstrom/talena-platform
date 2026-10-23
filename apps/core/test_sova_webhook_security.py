"""HTTP regression tests for the legacy, public Sova webhook route.

All events are synthetic. No Sova/OpenAI traffic is initiated.
"""
import json

from django.test import TestCase, override_settings
from django.urls import reverse


class LegacySovaWebhookAuthorizationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url = reverse("core:sova_webhook")

    def send(self, *, secret=None):
        extra = {}
        if secret is not None:
            extra["HTTP_X_TALENA_WEBHOOK_SECRET"] = secret
        return self.client.post(
            self.url,
            data=json.dumps({"request_id": "synthetic-unmatched-request"}),
            content_type="application/json",
            **extra,
        )

    @override_settings(
        SOVA_WEBHOOK_TEST_SECRET="synthetic-test-secret",
        SOVA_WEBHOOK_PROD_SECRET="synthetic-prod-secret",
        SOVA_WEBHOOK_SHARED_SECRET="",
    )
    def test_missing_or_invalid_secret_is_rejected(self):
        for header in (None, "", "wrong-value"):
            with self.subTest(header=header):
                response = self.send(secret=header)
                self.assertEqual(response.status_code, 401)

    @override_settings(
        SOVA_WEBHOOK_TEST_SECRET="",
        SOVA_WEBHOOK_PROD_SECRET="",
        SOVA_WEBHOOK_SHARED_SECRET="",
    )
    def test_empty_config_fails_closed(self):
        self.assertEqual(self.send(secret="arbitrary-header").status_code, 401)

    @override_settings(
        SOVA_WEBHOOK_TEST_SECRET="synthetic-test-secret",
        SOVA_WEBHOOK_PROD_SECRET="synthetic-prod-secret",
        SOVA_WEBHOOK_SHARED_SECRET="",
    )
    def test_configured_test_or_prod_secret_reaches_normal_processing(self):
        for secret in ("synthetic-test-secret", "synthetic-prod-secret"):
            with self.subTest(secret=secret):
                response = self.send(secret=secret)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "ignored")

    def test_non_post_requests_are_rejected(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
