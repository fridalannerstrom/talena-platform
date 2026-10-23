"""Synthetic HTTP checks for the historically public Sova callback route.

All test events are synthetic, unmatched IDs. No external provider traffic.
"""
import json

from django.test import TestCase, override_settings
from django.urls import reverse


class LegacySovaWebhookAuthorizationTests(TestCase):
    def send(self, *, secret=None):
        headers = {}
        if secret is not None:
            headers["HTTP_X_TALENA_WEBHOOK_SECRET"] = secret
        return self.client.post(
            reverse("core:sova_webhook"),
            data=json.dumps({"request_id": "synthetic-unmatched-request"}),
            content_type="application/json",
            **headers,
        )

    @override_settings(
        SOVA_WEBHOOK_TEST_SECRET="synthetic-test-secret",
        SOVA_WEBHOOK_PROD_SECRET="synthetic-prod-secret",
        SOVA_WEBHOOK_SHARED_SECRET="",
    )
    def test_missing_or_invalid_secret_is_rejected(self):
        for header in (None, "", "wrong-value"):
            with self.subTest(header=header):
                self.assertEqual(self.send(secret=header).status_code, 401)

    @override_settings(
        SOVA_WEBHOOK_TEST_SECRET="",
        SOVA_WEBHOOK_PROD_SECRET="",
        SOVA_WEBHOOK_SHARED_SECRET="",
    )
    def test_no_secrets_configured_fails_closed(self):
        self.assertEqual(self.send(secret="arbitrary-header").status_code, 401)

    @override_settings(
        SOVA_WEBHOOK_TEST_SECRET="synthetic-test-secret",
        SOVA_WEBHOOK_PROD_SECRET="synthetic-prod-secret",
        SOVA_WEBHOOK_SHARED_SECRET="",
    )
    def test_configured_secrets_reach_normal_processing(self):
        for secret in ("synthetic-test-secret", "synthetic-prod-secret"):
            with self.subTest(secret=secret):
                response = self.send(secret=secret)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["status"], "ignored")

    def test_get_is_rejected(self):
        response = self.client.get(reverse("core:sova_webhook"))
        self.assertEqual(response.status_code, 405)
