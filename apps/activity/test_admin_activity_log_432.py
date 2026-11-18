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
        self.assertEqual(
            [row["company"] for row in filtered.context["events"]],
            ["Alpha customer"],
        )
        self.assertIn("Kandidat", html)

        by_verb = self.client.get(self.list_url, {
            "verb": ActivityEvent.Verb.COMPANY_UPDATED,
        })
        self.assertEqual(
            [row["company"] for row in by_verb.context["events"]],
            ["Beta customer"],
        )

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
        self.assertIn("no-store", response["Cache-Control"])
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
        self.assertEqual(response.context["events"], [])

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

    def test_customer_tab_is_default_and_admin_audit_is_separate(self):
        audit = ActivityEvent.objects.create(
            company=None,
            verb=ActivityEvent.Verb.ADMIN_LOG_ACCESSED,
            actor=self.platform_admin,
        )
        customer_ai = ActivityEvent.objects.create(
            company=self.company_a,
            verb=ActivityEvent.Verb.AI_CALL_SUCCEEDED,
            meta={"schema": 1, "feature": "overall_picture"},
        )
        admin_on_behalf_of_customer = ActivityEvent.objects.create(
            company=self.company_a, actor=self.platform_admin,
            verb=ActivityEvent.Verb.CANDIDATE_ADDED,
        )
        system_on_behalf_of_customer = ActivityEvent.objects.create(
            company=self.company_a, actor=None,
            verb=ActivityEvent.Verb.TEST_COMPLETED,
        )
        self.client.force_login(self.platform_admin)
        customer = self.client.get(self.list_url, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertEqual(customer.status_code, 200)
        self.assertEqual(customer.context["active_scope"], "customer")
        self.assertContains(customer, "Kundaktivitet")
        self.assertContains(customer, "Kundernas aktiviteter")
        self.assertNotContains(customer, "Vad är loggåtkomst?")
        self.assertEqual(set(e["id"] for e in customer.context["events"]), {
            self.first.pk, self.second.pk, customer_ai.pk,
            system_on_behalf_of_customer.pk,
        })
        self.assertNotIn(audit.pk, [e["id"] for e in customer.context["events"]])
        self.assertNotIn(admin_on_behalf_of_customer.pk,
                         [e["id"] for e in customer.context["events"]])
        self.assertTrue(any(e["category"] == "ai" for e in customer.context["events"]))
        self.assertNotIn("audit", [key for key, _ in customer.context["categories"]])

        admin = self.client.get(self.list_url, {"scope": "admin"}, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(admin.context["active_scope"], "admin")
        self.assertContains(admin, "Vad är loggåtkomst?")
        self.assertContains(admin, "Adminaktiviteter")
        admin_ids = {e["id"] for e in admin.context["events"]}
        self.assertIn(audit.pk, admin_ids)
        self.assertIn(admin_on_behalf_of_customer.pk, admin_ids)
        self.assertNotIn(customer_ai.pk, admin_ids)
        self.assertNotIn(system_on_behalf_of_customer.pk, admin_ids)
        self.assertNotIn(self.first.pk, admin_ids)
        self.assertIn("audit", [key for key, _ in admin.context["categories"]])

    def test_customer_and_admin_csv_have_the_same_server_side_scope(self):
        admin_tenant = ActivityEvent.objects.create(
            company=self.company_a, actor=self.platform_admin,
            verb=ActivityEvent.Verb.COMPANY_UPDATED,
        )
        internal = ActivityEvent.objects.create(
            actor=self.platform_admin, company=None,
            verb=ActivityEvent.Verb.ADMIN_LOG_ACCESSED,
        )
        self.client.force_login(self.platform_admin)
        customer = self.client.get(self.export_url)
        customer_data = list(csv.DictReader(StringIO(customer.content.decode("utf-8"))))
        self.assertEqual({int(row["event_id"]) for row in customer_data},
                         {self.first.pk, self.second.pk})
        self.assertNotIn(str(internal.pk), [row["event_id"] for row in customer_data])
        admin = self.client.get(self.export_url, {"scope": "admin"})
        admin_data = list(csv.DictReader(StringIO(admin.content.decode("utf-8"))))
        ids = {int(row["event_id"]) for row in admin_data}
        self.assertIn(internal.pk, ids)
        self.assertIn(admin_tenant.pk, ids)
        self.assertNotIn(self.first.pk, ids)
        self.assertNotIn(self.second.pk, ids)
        self.assertNotIn("Alpha customer", admin.content.decode("utf-8"))

    def test_scope_survives_filters_and_pagination_and_invalid_scope_is_safe(self):
        # Force 31 customer events and 40 admin audit events. Both views must
        # paginate independently; switching tabs cannot leak the other page.
        for index in range(30):
            ActivityEvent.objects.create(
                company=self.company_a, actor=self.customer,
                verb=ActivityEvent.Verb.CANDIDATE_ADDED,
            )
        for index in range(40):
            ActivityEvent.objects.create(
                company=None, actor=self.platform_admin,
                verb=ActivityEvent.Verb.ADMIN_LOG_ACCESSED,
            )
        self.client.force_login(self.platform_admin)
        customer = self.client.get(self.list_url, {"scope": "customer"})
        self.assertEqual(customer.context["page_obj"].paginator.count, 32)
        self.assertEqual(len(customer.context["events"]), 30)
        self.assertContains(customer, "scope=customer&amp;page=2")
        admin = self.client.get(self.list_url, {"scope": "admin", "page": "2"})
        self.assertEqual(admin.context["page_obj"].paginator.count, 41)
        self.assertEqual(len(admin.context["events"]), 11)
        self.assertContains(admin, 'name="scope" value="admin"')
        self.assertContains(admin, "scope=admin&amp;page=1")
        bad = self.client.get(self.list_url, {"scope": "all",
                                              "category": "audit"})
        self.assertEqual(bad.context["active_scope"], "customer")
        self.assertEqual(bad.context["events"], [])
        self.assertNotIn("audit", [key for key, _ in bad.context["categories"]])

    def test_ai_events_are_labelled_by_category_in_customer_tab(self):
        ActivityEvent.objects.create(
            company=self.company_a,
            verb=ActivityEvent.Verb.AI_CALL_SUCCEEDED,
            meta={"schema": 1, "feature": "overall_picture"},
        )
        self.client.force_login(self.platform_admin)
        response = self.client.get(self.list_url, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI-anrop")
        ai_rows = [row for row in response.context["events"]
                   if row["verb"] == ActivityEvent.Verb.AI_CALL_SUCCEEDED]
        self.assertEqual(len(ai_rows), 1)
        self.assertEqual(ai_rows[0]["category"], "ai")


    def test_customer_sees_only_completed_manager_pdf_not_preparation(self):
        # The previously displayed double rows are two distinct audit records,
        # but only the browser-confirmed PDF is a customer activity.
        prepared = ActivityEvent.objects.create(
            company=self.company_a, actor=self.customer,
            verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
            meta={"report": "manager_report", "status": "prepared"},
        )
        generated = ActivityEvent.objects.create(
            company=self.company_a, actor=self.customer,
            verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_GENERATED,
            meta={
                "report": "manager_report",
                "status": "client_reported_generated",
                "prepared_event_id": prepared.pk,
            },
        )
        # A failed/abandoned preparation must not imply a finished PDF.
        abandoned = ActivityEvent.objects.create(
            company=self.company_b, actor=self.customer,
            verb=ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
        )
        self.client.force_login(self.platform_admin)

        customer = self.client.get(
            self.list_url, {"category": "reports"}, HTTP_ACCEPT_LANGUAGE="sv"
        )
        self.assertEqual(customer.status_code, 200)
        self.assertEqual([item["id"] for item in customer.context["events"]],
                         [generated.pk])
        self.assertEqual(customer.context["page_obj"].paginator.count, 1)
        self.assertNotIn(
            ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED,
            [code for code, _ in customer.context["verbs"]],
        )
        self.assertContains(customer, "Chefsrapport PDF genererad")
        self.assertNotContains(customer, "Chefsrapport PDF förberedd")

        # Filtering by the legacy technical verb must not bypass the scope.
        hidden = self.client.get(
            self.list_url, {"verb": ActivityEvent.Verb.MANAGER_REPORT_PDF_PREPARED}
        )
        self.assertEqual(hidden.context["events"], [])

        customer_csv = self.client.get(
            self.export_url, {"category": "reports"}
        )
        customer_rows = list(csv.DictReader(
            StringIO(customer_csv.content.decode("utf-8"))
        ))
        self.assertEqual(
            [int(row["event_id"]) for row in customer_rows], [generated.pk]
        )

        admin = self.client.get(
            self.list_url, {"scope": "admin", "category": "reports"},
        )
        self.assertEqual({item["id"] for item in admin.context["events"]},
                         {prepared.pk, abandoned.pk})
        self.assertNotIn(generated.pk,
                         [item["id"] for item in admin.context["events"]])
        admin_csv = self.client.get(
            self.export_url, {"scope": "admin", "category": "reports"}
        )
        admin_rows = list(csv.DictReader(
            StringIO(admin_csv.content.decode("utf-8"))
        ))
        self.assertEqual({int(row["event_id"]) for row in admin_rows},
                         {prepared.pk, abandoned.pk})

        # The original preparation records are preserved unchanged.
        self.assertTrue(ActivityEvent.objects.filter(pk=prepared.pk).exists())
        self.assertTrue(ActivityEvent.objects.filter(pk=abandoned.pk).exists())
