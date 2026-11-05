"""Synthetic contract tests for the internal Talena audit explorer (#432/#434)."""
import csv
from io import StringIO
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company, User
from apps.activity.models import ActivityEvent


class PlatformActivityLogTests(TestCase):
    def setUp(self):
        self.platform_admin = User.objects.create_user(
            username="platform-admin", password="x", role=User.Role.ADMIN,
        )
        self.customer = User.objects.create_user(
            username="customer-log", password="x", email="customer@example.test",
            role=User.Role.CUSTOMER,
        )
        self.staff_only = User.objects.create_user(
            username="staff-only", password="x", role=User.Role.CUSTOMER,
            is_staff=True,
        )
        self.company_a = Company.objects.create(name="Alpha customer")
        self.company_b = Company.objects.create(name="Beta customer")
        self.first = ActivityEvent.objects.create(
            company=self.company_a, actor=self.customer,
            verb=ActivityEvent.Verb.CANDIDATE_ADDED,
            meta={"sova_payload": "SECRET_TEST_PAYLOAD", "interview_text": "PRIVATE_NOTES"},
        )
        self.second = ActivityEvent.objects.create(
            company=self.company_b,
            verb=ActivityEvent.Verb.COMPANY_UPDATED,
            meta={"api_token": "SECRET_API_TOKEN"},
        )
        self.list_url = reverse("core:admin_activity_log")
        self.export_url = reverse("core:admin_activity_export")

    def test_only_platform_admin_can_read_and_export_cross_customer_data(self):
        for user in (self.customer, self.staff_only):
            self.client.force_login(user)
            for url in (self.list_url, self.export_url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)
            self.assertFalse(
                ActivityEvent.objects.filter(
                    verb=ActivityEvent.Verb.ADMIN_LOG_ACCESSED,
                    actor=user,
                ).exists()
            )

        self.client.force_login(self.platform_admin)
        html = self.client.get(
            self.list_url, HTTP_ACCEPT_LANGUAGE="sv",
        ).content.decode("utf-8")
        self.assertIn("Alpha customer", html)
        self.assertIn("Beta customer", html)
        self.assertIn("Aktivitetslogg", html)
        self.assertNotIn("SECRET_TEST_PAYLOAD", html)
        self.assertNotIn("SECRET_API_TOKEN", html)
        self.assertNotIn("PRIVATE_NOTES", html)
        self.assertTrue(
            ActivityEvent.objects.filter(
                verb=ActivityEvent.Verb.ADMIN_LOG_ACCESSED,
                actor=self.platform_admin,
                company__isnull=True,
            ).exists()
        )

    def test_filters_are_server_scoped_and_pagination_is_safe(self):
        self.client.force_login(self.platform_admin)
        filtered = self.client.get(self.list_url, {
            "company": self.company_a.pk,
            "category": "candidate",
            "q": "Alpha",
        }, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertEqual(filtered.status_code, 200)
        html = filtered.content.decode("utf-8")
        self.assertIn("Alpha customer", html)
        self.assertNotIn("Beta customer", html)
        self.assertIn("Kandidat", html)

        by_verb = self.client.get(self.list_url, {
            "verb": ActivityEvent.Verb.COMPANY_UPDATED,
        })
        self.assertIn("Beta customer", by_verb.content.decode("utf-8"))
        self.assertNotIn("Alpha customer", by_verb.content.decode("utf-8"))

        # Raw meta isn't searchable, and untrusted query syntax is ignored.
        secret = self.client.get(
            self.list_url, {"q": "SECRET_API_TOKEN"}, HTTP_ACCEPT_LANGUAGE="sv",
        )
        self.assertContains(secret, "Inga händelser för filtren")
        self.client.get(self.list_url, {"from": "nonsense", "page": "huge"})

    def test_csv_exposes_only_safe_ids_and_logs_prepared_export(self):
        self.client.force_login(self.platform_admin)
        response = self.client.get(self.export_url, {
            "company": self.company_a.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        content = response.content.decode("utf-8")
        data = list(csv.DictReader(StringIO(content)))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["event_type"], ActivityEvent.Verb.CANDIDATE_ADDED)
        self.assertEqual(data[0]["company_id"], str(self.company_a.pk))
        self.assertNotIn("SECRET_TEST_PAYLOAD", content)
        self.assertNotIn("PRIVATE_NOTES", content)
        self.assertNotIn("Alpha customer", content)
        self.assertNotIn(self.customer.email, content)
        audit = ActivityEvent.objects.get(
            verb=ActivityEvent.Verb.ADMIN_LOG_EXPORTED,
            actor=self.platform_admin,
        )
        self.assertIsNone(audit.company_id)
        self.assertEqual(audit.meta, {"schema": 1, "scope": "csv_prepared"})

    def test_from_to_range_is_utc_and_does_not_backfill_history(self):
        self.client.force_login(self.platform_admin)
        tomorrow = (timezone.now() + timedelta(days=1)).date().isoformat()
        response = self.client.get(
            self.list_url, {"from": tomorrow}, HTTP_ACCEPT_LANGUAGE="sv",
        )
        html = response.content.decode("utf-8")
        self.assertContains(response, "Inga händelser för filtren")
        self.assertNotIn("Alpha customer", html)

    def test_activity_log_does_not_call_message_or_expose_meta(self):
        self.client.force_login(self.platform_admin)
        response = self.client.get(self.list_url, HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "Activity log")
        self.assertNotContains(response, "SECRET_API_TOKEN")
        self.assertNotContains(response, "SECRET_TEST_PAYLOAD")
        self.assertEqual(
            ActivityEvent.objects.filter(verb=ActivityEvent.Verb.ADMIN_LOG_ACCESSED).count(),
            1,
        )
