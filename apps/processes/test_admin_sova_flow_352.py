"""Regression coverage for ticket #352: Talena admin creates and sends Sova tests.

All identities and Sova responses are synthetic. No external calls are made.
"""
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company, CompanyMember, OrgUnit, User, UserOrgUnitAccess
from apps.processes.models import Candidate, TestInvitation, TestProcess


class AdminSovaFlow352Tests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin-352",
            email="admin-352@example.test",
            password="test-password",
        )
        self.customer = User.objects.create_user(
            username="customer-352",
            email="customer-352@example.test",
            password="test-password",
        )
        self.company = Company.objects.create(name="Synthetic Customer A")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Unit A", unit_code="A-352",
        )
        CompanyMember.objects.create(
            company=self.company,
            user=self.customer,
            primary_org_unit=self.unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.customer, org_unit=self.unit, permission="editor",
        )
        self.process = TestProcess.objects.create(
            name="Admin Sova recruitment",
            company=self.company,
            org_unit=self.unit,
            created_by=self.customer,
            account_code="MODERN",
            project_code="PQ",
            selected_tests=["personality"],
            candidate_language="en",
        )
        self.detail_url = reverse(
            "accounts:company_process_detail",
            args=[self.company.pk, self.process.pk],
        )
        self.add_url = reverse(
            "accounts:admin_process_add_candidate", args=[self.process.pk],
        )
        self.send_url = reverse(
            "accounts:admin_process_send_tests", args=[self.process.pk],
        )
        self.client.force_login(self.admin)

    def _candidate(self, email="candidate-352@example.test", status="created"):
        candidate = Candidate.objects.create(
            first_name="Test",
            last_name="Candidate",
            email=email,
        )
        inv = TestInvitation.objects.create(
            process=self.process,
            candidate=candidate,
            status=status,
            source="invited",
        )
        return candidate, inv

    def test_company_admin_page_exposes_add_and_send_controls(self):
        _, invitation = self._candidate()
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.add_url)
        self.assertContains(response, self.send_url)
        self.assertContains(response, 'id="admin-company-send-tests"')
        self.assertContains(
            response, f'name="invitation_ids" value="{invitation.pk}"',
        )

    def test_candidate_form_page_renders_without_missing_template(self):
        response = self.client.get(self.add_url, {"next": self.detail_url})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "candidate", status_code=200)
        self.assertContains(response, 'name="next"')
        self.assertContains(response, self.process.name)

    def test_candidate_add_is_idempotent_and_redirects_back_to_company(self):
        payload = {
            "first_name": "Anna", "last_name": "Example",
            "email": "ANNA-352@example.test", "next": self.detail_url,
        }
        for _ in range(2):
            response = self.client.post(self.add_url, payload)
            self.assertRedirects(
                response, self.detail_url, fetch_redirect_response=False,
            )
        candidate = Candidate.objects.get(email="anna-352@example.test")
        self.assertEqual(
            TestInvitation.objects.filter(
                process=self.process, candidate=candidate,
            ).count(), 1,
        )

    def test_removed_candidate_is_not_implicitly_reactivated(self):
        _, invitation = self._candidate()
        invitation.removed_from_process_at = timezone.now()
        invitation.save(update_fields=["removed_from_process_at"])
        response = self.client.post(
            self.add_url,
            {
                "first_name": "Test", "last_name": "Candidate",
                "email": invitation.candidate.email,
                "next": self.detail_url,
            },
        )
        self.assertEqual(response.status_code, 302)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.removed_from_process_at)
        self.assertEqual(
            TestInvitation.objects.filter(process=self.process).count(), 1,
        )

    def test_send_calls_shared_service_only_for_pending_invitations_in_this_process(self):
        _, pending = self._candidate()
        _, completed = self._candidate("completed-352@example.test", "completed")
        _, expired = self._candidate("expired-352@example.test", "expired")

        other = TestProcess.objects.create(
            name="Other company's project",
            company=Company.objects.create(name="Synthetic Customer B"),
            created_by=self.customer,
            account_code="MODERN",
            project_code="MQ",
        )
        other_candidate = Candidate.objects.create(
            first_name="Another", last_name="Candidate",
            email="other-tenant-352@example.test",
        )
        other_invitation = TestInvitation.objects.create(
            process=other, candidate=other_candidate, status="created",
        )

        with patch(
            "apps.accounts.views.send_assessments_and_emails",
            return_value={"sent_count": 1, "skipped_count": 0, "errors": []},
        ) as send:
            response = self.client.post(
                self.send_url,
                {
                    "next": self.detail_url,
                    "invitation_ids": [
                        str(pending.pk), str(completed.pk), str(expired.pk),
                        str(other_invitation.pk),
                    ],
                },
            )

        self.assertRedirects(
            response, self.detail_url, fetch_redirect_response=False,
        )
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs["process"], self.process)
        self.assertEqual(kwargs["actor_user"], self.admin)
        self.assertEqual(kwargs["context"], "admin")
        self.assertEqual([inv.pk for inv in kwargs["invitations"]], [pending.pk])
        self.assertTrue(
            TestInvitation.objects.filter(pk=other_invitation.pk).exists(),
        )

    def test_send_errors_do_not_expose_candidate_data_or_provider_response(self):
        _, invitation = self._candidate()
        with patch(
            "apps.accounts.views.send_assessments_and_emails",
            return_value={
                "sent_count": 0,
                "skipped_count": 0,
                "errors": [{
                    "email": "private-352@example.test",
                    "error": "AUTH_TOKEN_SECRET_352",
                }],
            },
        ):
            response = self.client.post(
                self.send_url, {"invitation_ids": [str(invitation.pk)]},
            )
        rendered_messages = " ".join(
            str(msg) for msg in get_messages(response.wsgi_request)
        )
        self.assertNotIn("private-352@example.test", rendered_messages)
        self.assertNotIn("AUTH_TOKEN_SECRET_352", rendered_messages)
        self.assertIn("Sova", rendered_messages)

    def test_missing_sova_configuration_fails_gracefully(self):
        _, invitation = self._candidate()
        with patch(
            "apps.accounts.views.send_assessments_and_emails",
            side_effect=KeyError("SOVA_PASSWORD"),
        ):
            response = self.client.post(
                self.send_url, {"invitation_ids": [str(invitation.pk)]},
            )
        self.assertEqual(response.status_code, 302)
        rendered_messages = " ".join(
            str(msg) for msg in get_messages(response.wsgi_request)
        )
        self.assertNotIn("SOVA_PASSWORD", rendered_messages)

    def test_non_admin_cannot_add_or_send_even_for_own_company(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(self.add_url).status_code, 403)
        self.assertEqual(
            self.client.post(self.add_url, {
                "first_name": "No", "last_name": "Access",
                "email": "forbidden-352@example.test",
            }).status_code, 403,
        )
        self.assertEqual(
            self.client.post(self.send_url, {"invitation_ids": ["1"]}).status_code,
            403,
        )
        self.assertFalse(
            Candidate.objects.filter(email="forbidden-352@example.test").exists()
        )

    def test_archived_or_historical_projects_do_not_send(self):
        _, invitation = self._candidate()
        self.process.is_archived = True
        self.process.save(update_fields=["is_archived"])
        self.assertEqual(self.client.get(self.add_url).status_code, 403)
        with patch("apps.accounts.views.send_assessments_and_emails") as send:
            response = self.client.post(
                self.send_url, {"invitation_ids": [str(invitation.pk)]},
            )
        self.assertEqual(response.status_code, 302)
        send.assert_not_called()

    @patch("apps.accounts.views.log_event")
    @patch("apps.accounts.views.SovaClient")
    def test_admin_creation_uses_modern_projects_and_saves_customer_language(
        self, sova_cls, _log_event,
    ):
        sova_cls.return_value.get_template_accounts_with_projects.return_value = [{
            "name": "Talena Modern Projects",
            "code": "MODERN",
            "projects": [
                {"code": "PQ", "name": "PQ", "id": 352},
            ],
        }]
        url = reverse(
            "accounts:company_process_create", args=[self.company.pk],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="candidate_language"')

        response = self.client.post(url, {
            "name": "Created via admin",
            "purpose": "hiring",
            "org_unit": str(self.unit.pk),
            "project_owner": str(self.customer.pk),
            "selected_tests": ["personality"],
            "candidate_language": "en",
            "project_completion_notifications_enabled": "on",
        })
        self.assertEqual(response.status_code, 302, response.content[:1000])
        created = TestProcess.objects.get(name="Created via admin")
        self.assertEqual(created.company, self.company)
        self.assertEqual(created.org_unit, self.unit)
        self.assertEqual(created.account_code, "MODERN")
        self.assertEqual(created.project_code, "PQ")
        self.assertEqual(created.candidate_language, "en")
        self.assertEqual(created.selected_tests, ["personality"])
        self.assertEqual(created.created_by, self.customer)
        self.assertEqual(created.created_by_admin, self.admin)

        # Own-only users must still be able to see projects explicitly
        # created for them by a Talena administrator.
        UserOrgUnitAccess.objects.filter(
            user=self.customer, org_unit=self.unit,
        ).update(permission="own")
        self.client.force_login(self.customer)
        customer_list = self.client.get(reverse("processes:process_list"))
        self.assertEqual(customer_list.status_code, 200)
        self.assertContains(customer_list, "Created via admin")
        self.client.force_login(self.admin)

    @patch("apps.accounts.views.SovaClient")
    def test_admin_creation_rejects_unit_of_another_company(self, sova_cls):
        sova_cls.return_value.get_template_accounts_with_projects.return_value = [{
            "name": "Talena Modern Projects", "code": "MODERN",
            "projects": [{"code": "PQ", "name": "PQ", "id": 352}],
        }]
        outsider_company = Company.objects.create(name="Outside Customer")
        outsider_unit = OrgUnit.objects.create(
            company=outsider_company, name="Outside unit", unit_code="OUT-352",
        )
        response = self.client.post(
            reverse("accounts:company_process_create", args=[self.company.pk]),
            {
                "name": "Invalid cross-tenant process",
                "purpose": "hiring",
                "org_unit": str(outsider_unit.pk),
                "selected_tests": ["personality"],
                "candidate_language": "sv",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("org_unit", response.context["form"].errors)
        self.assertFalse(
            TestProcess.objects.filter(name="Invalid cross-tenant process").exists(),
        )
