"""Company-wide, platform-admin-only Integrity Guard display preference.

All data is synthetic. The setting is presentation-only, not a Sova flag.
"""
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import Company
from apps.processes.models import Candidate, TestInvitation, TestProcess


class IntegrityGuardVisibilityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username="platform-ig-admin", email="platform-ig-admin@example.test",
            password="test-pass-ig",
        )
        self.customer = User.objects.create_user(
            username="ig-customer", email="ig-customer@example.test",
            password="test-pass-ig",
        )
        self.staff_only = User.objects.create_user(
            username="ig-staff", email="ig-staff@example.test",
            password="test-pass-ig", is_staff=True,
        )
        self.company = Company.objects.create(name="Synthetic IG Customer")
        self.other = Company.objects.create(name="Other Synthetic Customer")
        self.process = TestProcess.objects.create(
            name="Synthetic IG Process", company=self.company, created_by=self.customer,
            account_code="TEST", project_code="PQ",
        )
        self.candidate = Candidate.objects.create(
            first_name="Synthetic", last_name="Candidate",
            email="ig-candidate@example.test",
        )
        self.invitation = TestInvitation.objects.create(
            process=self.process, candidate=self.candidate,
            integrity_guard={"overall_status": 2, "diagnostics": {"question_engagement": 2}},
        )
        self.url = reverse("accounts:company_integrity_guard_visibility", args=[self.company.pk])

    def test_default_visible_and_hiding_does_not_erase_sova_evidence(self):
        self.assertTrue(self.company.integrity_guard_visible)
        self.assertTrue(self.invitation.integrity_guard_display["visible"])
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {"integrity_guard_visible": "0"})
        self.assertRedirects(response, reverse("accounts:company_detail", args=[self.company.pk]))
        self.company.refresh_from_db()
        self.assertFalse(self.company.integrity_guard_visible)
        self.invitation.refresh_from_db()
        self.assertFalse(self.invitation.integrity_guard_display["visible"])
        self.assertEqual(self.invitation.integrity_guard["overall_status"], 2)
        self.assertTrue(self.other.integrity_guard_visible)

        self.client.post(self.url, {"integrity_guard_visible": "1"})
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.integrity_guard_display["state"], "concern")

    def test_company_choice_covers_all_projects_but_not_other_companies(self):
        second_process = TestProcess.objects.create(
            name="Second project", company=self.company, created_by=self.admin,
            account_code="TEST", project_code="MQ",
        )
        second_candidate = Candidate.objects.create(
            first_name="Second", email="second-ig@example.test",
        )
        second_inv = TestInvitation.objects.create(
            process=second_process, candidate=second_candidate,
            integrity_guard={"overall_status": 1},
        )
        other_process = TestProcess.objects.create(
            name="Other company project", company=self.other, created_by=self.admin,
            account_code="TEST", project_code="PQ",
        )
        third_candidate = Candidate.objects.create(
            first_name="Third", email="third-ig@example.test",
        )
        other_inv = TestInvitation.objects.create(
            process=other_process, candidate=third_candidate,
            integrity_guard={"overall_status": 1},
        )
        self.company.integrity_guard_visible = False
        self.company.save(update_fields=["integrity_guard_visible"])
        self.assertFalse(self.invitation.integrity_guard_display["visible"])
        self.assertFalse(second_inv.integrity_guard_display["visible"])
        self.assertTrue(other_inv.integrity_guard_display["visible"])

    def test_badge_and_panel_not_rendered_when_hidden(self):
        self.company.integrity_guard_visible = False
        self.company.save(update_fields=["integrity_guard_visible"])
        badge = render_to_string(
            "customer/processes/partials/_integrity_guard_badge.html",
            {"inv": self.invitation},
        )
        panel = render_to_string(
            "customer/processes/partials/_integrity_guard_panel.html",
            {"invitation": self.invitation},
        )
        self.assertNotIn("talena-ig-shield", badge)
        self.assertNotIn("data-integrity-guard-panel", panel)
        self.assertNotIn("Integrity Guard", panel)

    def test_only_platform_admin_can_change_visibility(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.post(self.url, {"integrity_guard_visible": "0"}).status_code, 403)
        self.client.force_login(self.staff_only)
        self.assertEqual(self.client.post(self.url, {"integrity_guard_visible": "0"}).status_code, 403)
        self.company.refresh_from_db()
        self.assertTrue(self.company.integrity_guard_visible)

    def test_invalid_value_and_get_do_not_change_setting(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.client.post(self.url, {"integrity_guard_visible": "anything"}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {}).status_code, 400)
        self.company.refresh_from_db()
        self.assertTrue(self.company.integrity_guard_visible)

    def test_csrf_required_for_admin_write(self):
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.admin)
        response = protected.post(self.url, {"integrity_guard_visible": "0"})
        self.assertEqual(response.status_code, 403)
        self.company.refresh_from_db()
        self.assertTrue(self.company.integrity_guard_visible)

    def test_project_override_and_reset_to_company_default(self):
        project_url = reverse(
            "accounts:project_integrity_guard_visibility", args=[self.process.pk],
        )
        self.assertIsNone(self.process.integrity_guard_visible_override)
        self.assertTrue(self.process.integrity_guard_visible_in_talena)

        # Project inherits the disabled company setting by default.
        self.company.integrity_guard_visible = False
        self.company.save(update_fields=["integrity_guard_visible"])
        self.assertFalse(self.invitation.integrity_guard_display["visible"])

        self.client.force_login(self.admin)
        response = self.client.post(project_url, {"integrity_guard_visible": "1"})
        self.assertRedirects(
            response, reverse("processes:process_detail", args=[self.process.pk]),
            fetch_redirect_response=False,
        )
        self.process.refresh_from_db()
        self.invitation.refresh_from_db()
        self.assertIs(self.process.integrity_guard_visible_override, True)
        self.assertTrue(self.invitation.integrity_guard_display["visible"])
        self.assertEqual(self.invitation.integrity_guard["overall_status"], 2)

        self.client.post(project_url, {"integrity_guard_visible": "0"})
        self.process.refresh_from_db()
        self.assertIs(self.process.integrity_guard_visible_override, False)
        self.assertFalse(self.invitation.integrity_guard_display["visible"])

        self.client.post(project_url, {"integrity_guard_visible": "default"})
        self.process.refresh_from_db()
        self.assertIsNone(self.process.integrity_guard_visible_override)
        self.assertFalse(self.invitation.integrity_guard_display["visible"])

        # Once inherited again, later changes at company level apply.
        self.company.integrity_guard_visible = True
        self.company.save(update_fields=["integrity_guard_visible"])
        self.assertTrue(self.invitation.integrity_guard_display["visible"])

    def test_project_override_is_isolated_to_its_own_project(self):
        other_process = TestProcess.objects.create(
            name="Other project", company=self.company, created_by=self.customer,
            account_code="TEST", project_code="MQ",
        )
        other_candidate = Candidate.objects.create(
            first_name="Second", email="second-project-ig@example.test",
        )
        other_inv = TestInvitation.objects.create(
            process=other_process, candidate=other_candidate,
            integrity_guard={"overall_status": 1},
        )
        self.client.force_login(self.admin)
        url = reverse(
            "accounts:project_integrity_guard_visibility", args=[self.process.pk],
        )
        self.client.post(url, {"integrity_guard_visible": "0"})
        self.assertFalse(self.invitation.integrity_guard_display["visible"])
        self.assertTrue(other_inv.integrity_guard_display["visible"])
        other_process.refresh_from_db()
        self.assertIsNone(other_process.integrity_guard_visible_override)

    def test_project_toggle_rejects_customers_and_staff_only(self):
        url = reverse(
            "accounts:project_integrity_guard_visibility", args=[self.process.pk],
        )
        for user in (self.customer, self.staff_only):
            self.client.force_login(user)
            self.assertEqual(
                self.client.post(url, {"integrity_guard_visible": "0"}).status_code,
                403,
            )
        self.process.refresh_from_db()
        self.assertIsNone(self.process.integrity_guard_visible_override)

    def test_project_toggle_validates_payload_and_requires_post_csrf(self):
        url = reverse(
            "accounts:project_integrity_guard_visibility", args=[self.process.pk],
        )
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(
            self.client.post(url, {"integrity_guard_visible": "invalid"}).status_code,
            400,
        )
        self.assertEqual(self.client.post(url, {}).status_code, 400)
        self.assertEqual(
            self.client.post(
                reverse("accounts:project_integrity_guard_visibility", args=[99999999]),
                {"integrity_guard_visible": "0"},
            ).status_code, 404,
        )
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.admin)
        self.assertEqual(
            protected.post(url, {"integrity_guard_visible": "0"}).status_code, 403,
        )
        self.process.refresh_from_db()
        self.assertIsNone(self.process.integrity_guard_visible_override)
