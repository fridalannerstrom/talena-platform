"""Ticket #87: company invitation email defaults, isolation and send behaviour."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Company
from apps.emails.models import CompanyInvitationTemplate, EmailLog, EmailTemplate
from apps.emails.utils import get_default_invitation_template, resolve_invitation_template
from apps.processes.models import Candidate, TestInvitation, TestProcess
from apps.processes.services.send_tests import send_assessments_and_emails


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CompanyInvitationTemplateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="qode-admin", email="admin@example.test",
            password="admin-test-password", role="admin",
        )
        self.customer = User.objects.create_user(
            username="qode-user", email="customer@example.test",
            password="user-test-password", role="customer",
        )
        self.company = Company.objects.create(name="Example Company")
        self.other_company = Company.objects.create(name="Another Company")
        self.process = TestProcess.objects.create(
            name="Developer hiring",
            company=self.company,
            account_code="TEST",
            project_code="PROJECT",
            created_by=self.admin,
            candidate_language="sv",
            selected_tests=["personality"],
        )
        self.other_process = TestProcess.objects.create(
            name="Another hiring process",
            company=self.other_company,
            account_code="TEST",
            project_code="OTHER",
            created_by=self.admin,
            candidate_language="sv",
        )

    def company_template(self, company=None, language="sv", active=True):
        return CompanyInvitationTemplate.objects.create(
            company=company or self.company,
            language=language,
            subject="Test for {company_name}: {process_name}",
            body="Hello {first_name}! Start here: {assessment_url}",
            is_active=active,
        )

    def test_company_template_used_for_multiple_processes(self):
        self.company_template()
        another = TestProcess.objects.create(
            name="Manager hiring", company=self.company,
            account_code="TEST", project_code="MANAGER",
            created_by=self.admin,
        )
        for process in (self.process, another):
            selected = resolve_invitation_template(process, "sv")
            self.assertEqual(selected["source"], "company")
            self.assertIn("{company_name}", selected["subject"])

    def test_legacy_seeded_process_default_does_not_hide_company_default(self):
        original = get_default_invitation_template("sv")
        seeded = EmailTemplate.objects.create(
            process=self.process, template_type="invitation", language="sv",
            **original,
        )
        self.company_template()
        selected = resolve_invitation_template(self.process, "sv", seeded)
        self.assertEqual(selected["source"], "company")

    def test_custom_process_template_still_overrides_company_default(self):
        self.company_template()
        custom = EmailTemplate.objects.create(
            process=self.process, template_type="invitation", language="sv",
            subject="Custom {process_name}",
            body="Hello {first_name}: {assessment_url}",
        )
        selected = resolve_invitation_template(self.process, "sv", custom)
        self.assertEqual(selected["source"], "process")
        self.assertEqual(selected["subject"], custom.subject)

    def test_inactive_process_override_falls_back_to_company(self):
        self.company_template()
        inactive = EmailTemplate.objects.create(
            process=self.process, template_type="invitation", language="sv",
            subject="Old custom", body="Old body {assessment_url}",
            is_active=False,
        )
        self.assertEqual(resolve_invitation_template(self.process, "sv", inactive)["source"], "company")

    def test_fallback_and_other_company_isolation(self):
        self.company_template()
        self.assertEqual(resolve_invitation_template(self.other_process, "sv")["source"], "talena")
        self.assertEqual(resolve_invitation_template(self.process, "en")["source"], "talena")
        CompanyInvitationTemplate.objects.filter(company=self.company).update(is_active=False)
        self.assertEqual(resolve_invitation_template(self.process, "sv")["source"], "talena")

    def test_company_template_unique_per_language(self):
        from django.db import IntegrityError, transaction
        self.company_template()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.company_template()

    def test_only_admin_can_edit_and_preview_company(self):
        url = reverse("emails:admin_edit_company_invitation_template", args=[self.company.pk])
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {
            "subject": "Unauthorized", "body": "{assessment_url}", "is_active": "on",
        }).status_code, 403)
        self.assertFalse(CompanyInvitationTemplate.objects.exists())

        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Live preview")
        self.assertContains(response, "Example Company")
        # A GET must not silently create a company template.
        self.assertFalse(CompanyInvitationTemplate.objects.exists())

    def test_admin_can_save_edit_disable_and_switch_language(self):
        self.client.force_login(self.admin)
        url = reverse("emails:admin_edit_company_invitation_template", args=[self.company.pk])
        data = {
            "subject": "Hello {first_name}, welcome to {company_name}",
            "body": "Take part in {process_name}: {assessment_url}",
            "is_active": "on",
        }
        response = self.client.post(url + "?language=en", data)
        self.assertEqual(response.status_code, 302)
        template = CompanyInvitationTemplate.objects.get(company=self.company, language="en")
        self.assertTrue(template.is_active)
        self.assertEqual(template.subject, data["subject"])
        self.assertEqual(resolve_invitation_template(self.process, "en")["source"], "company")

        data.update({"subject": "Updated {company_name}", "is_active": ""})
        self.assertEqual(self.client.post(url + "?language=en", data).status_code, 302)
        template.refresh_from_db()
        self.assertEqual(template.subject, data["subject"])
        self.assertFalse(template.is_active)
        self.assertEqual(resolve_invitation_template(self.process, "en")["source"], "talena")
        self.assertFalse(CompanyInvitationTemplate.objects.filter(company=self.company, language="sv").exists())

    def test_invalid_placeholder_and_missing_link_are_rejected(self):
        self.client.force_login(self.admin)
        url = reverse("emails:admin_edit_company_invitation_template", args=[self.company.pk])
        response = self.client.post(url, {
            "subject": "Hello {unknown_field}",
            "body": "Hello {first_name}",
            "is_active": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Include {assessment_url}")
        self.assertFalse(CompanyInvitationTemplate.objects.exists())

    def test_admin_process_editor_displays_inherited_company_copy(self):
        self.company_template()
        self.client.force_login(self.admin)
        url = reverse(
            "emails:admin_edit_company_process_invitation_template",
            args=[self.company.id, self.process.id],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["using_company_template"])
        self.assertEqual(response.context["form"]["subject"].value(), "Test for {company_name}: {process_name}")

    @patch("apps.processes.services.send_tests.log_event")
    @patch("apps.processes.services.send_tests.register_sent_assessments")
    @patch("apps.core.integrations.sova.SovaClient")
    def test_send_uses_company_template_with_rendered_values_and_fallback(
        self, client_class, usage_mock, event_mock,
    ):
        self.company_template()
        client = client_class.return_value
        client.get_accounts_with_projects.return_value = []
        client.order_assessment.return_value = {"url": "https://example.test/assessment"}
        candidate = Candidate.objects.create(
            first_name="Anna", last_name="Candidate", email="anna@example.test",
        )
        invitation = TestInvitation.objects.create(
            process=self.process, candidate=candidate, status="created",
        )

        result = send_assessments_and_emails(
            process=self.process, invitations=[invitation], actor_user=self.admin,
        )
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["sent_count"], 1)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Test for Example Company: Developer hiring")
        self.assertIn("Hello Anna!", mail.outbox[0].body)
        self.assertIn("https://example.test/assessment", mail.outbox[0].body)
        snapshot = EmailLog.objects.get(invitation=invitation)
        self.assertEqual(snapshot.subject, mail.outbox[0].subject)
        self.assertEqual(snapshot.body_snapshot, mail.outbox[0].body)
        client.order_assessment.assert_called_once()

        # A second company without a template uses Talena's default.
        other_candidate = Candidate.objects.create(
            first_name="Elin", last_name="Test", email="elin@example.test",
        )
        other_invitation = TestInvitation.objects.create(
            process=self.other_process, candidate=other_candidate,
        )
        result = send_assessments_and_emails(
            process=self.other_process, invitations=[other_invitation], actor_user=self.admin,
        )
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["sent_count"], 1)
        self.assertEqual(mail.outbox[1].subject, get_default_invitation_template("sv")["subject"])
        self.assertIn("https://example.test/assessment", mail.outbox[1].body)
