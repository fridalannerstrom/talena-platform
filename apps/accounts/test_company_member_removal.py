"""Regression tests for Talena-admin company membership removal."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    Company, CompanyMember, OrgUnit, UserInvite, UserOrgUnitAccess,
)
from apps.activity.models import ActivityEvent
from apps.processes.models import TestProcess


User = get_user_model()


class CompanyMemberRemovalTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="talena-admin", email="admin@example.com", password="test-password"
        )
        self.member = User.objects.create_user(
            username="multicompany", email="member@example.com", password="test-password"
        )
        self.company = Company.objects.create(name="Company A")
        self.other_company = Company.objects.create(name="Company B")
        self.unit = OrgUnit.objects.create(
            company=self.company, name="Account A", unit_code="A"
        )
        self.other_unit = OrgUnit.objects.create(
            company=self.other_company, name="Account B", unit_code="B"
        )
        self.membership = CompanyMember.objects.create(
            company=self.company, user=self.member, primary_org_unit=self.unit
        )
        CompanyMember.objects.create(
            company=self.other_company, user=self.member,
            primary_org_unit=self.other_unit,
        )
        UserOrgUnitAccess.objects.create(
            user=self.member, org_unit=self.unit, permission="editor"
        )
        UserOrgUnitAccess.objects.create(
            user=self.member, org_unit=self.other_unit, permission="editor"
        )
        self.invite = UserInvite.objects.create(
            company=self.company, user=self.member, created_by=self.admin,
        )
        self.other_invite = UserInvite.objects.create(
            company=self.other_company, user=self.member, created_by=self.admin,
        )
        self.url = reverse(
            "accounts:company_member_remove", args=[self.company.pk, self.member.pk]
        )
        self.client.force_login(self.admin)

    def test_removes_only_selected_company_access_and_logs_action(self):
        response = self.client.post(self.url)
        self.assertRedirects(
            response, reverse("accounts:company_users", args=[self.company.pk])
        )
        self.assertTrue(User.objects.filter(pk=self.member.pk).exists())
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)
        self.assertFalse(CompanyMember.objects.filter(
            company=self.company, user=self.member
        ).exists())
        self.assertTrue(CompanyMember.objects.filter(
            company=self.other_company, user=self.member
        ).exists())
        self.assertFalse(UserOrgUnitAccess.objects.filter(
            user=self.member, org_unit=self.unit
        ).exists())
        self.assertTrue(UserOrgUnitAccess.objects.filter(
            user=self.member, org_unit=self.other_unit
        ).exists())
        self.invite.refresh_from_db()
        self.other_invite.refresh_from_db()
        self.assertIsNotNone(self.invite.revoked_at)
        self.assertIsNone(self.other_invite.revoked_at)
        event = ActivityEvent.objects.get(
            company=self.company,
            verb=ActivityEvent.Verb.COMPANY_MEMBER_REMOVED,
        )
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.meta["user_id"], self.member.pk)
        self.assertEqual(event.meta["user_email"], self.member.email)
        self.assertFalse(event.meta["account_deactivated"])
        self.assertEqual(event.meta["remaining_company_memberships"], 1)

    def test_removing_last_company_deactivates_user_without_deleting_history(self):
        """The account remains auditable, but is no longer usable for login."""
        project = TestProcess.objects.create(
            name="Legacy project", company=self.other_company,
            org_unit=self.other_unit, created_by=self.member,
            account_code="B", project_code="keep-history",
        )
        self.client.post(self.url)
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)
        self.assertEqual(self.member.company_memberships.count(), 1)

        last_url = reverse(
            "accounts:company_member_remove",
            args=[self.other_company.pk, self.member.pk],
        )
        self.assertRedirects(
            self.client.post(last_url),
            reverse("accounts:company_users", args=[self.other_company.pk]),
        )
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.assertTrue(User.objects.filter(pk=self.member.pk).exists())
        self.assertEqual(self.member.company_memberships.count(), 0)
        self.assertFalse(UserOrgUnitAccess.objects.filter(user=self.member).exists())
        self.assertTrue(TestProcess.objects.filter(
            pk=project.pk, created_by=self.member,
        ).exists())
        removal_event = ActivityEvent.objects.get(
            company=self.other_company,
            verb=ActivityEvent.Verb.COMPANY_MEMBER_REMOVED,
        )
        self.assertTrue(removal_event.meta["account_deactivated"])
        self.assertEqual(removal_event.meta["remaining_company_memberships"], 0)
        self.client.logout()
        self.assertFalse(self.client.login(
            username=self.member.username, password="test-password",
        ))

    def test_platform_admin_can_remain_active_without_company(self):
        """Platform admin role is independent of company membership."""
        platform_admin = User.objects.create_user(
            username="platform-operator", email="operator@example.com",
            password="test-password", role=User.Role.ADMIN,
        )
        CompanyMember.objects.create(
            company=self.company, user=platform_admin,
        )
        url = reverse(
            "accounts:company_member_remove",
            args=[self.company.pk, platform_admin.pk],
        )
        self.assertEqual(self.client.post(url).status_code, 302)
        platform_admin.refresh_from_db()
        self.assertTrue(platform_admin.is_active)
        self.assertFalse(platform_admin.company_memberships.exists())
        event = ActivityEvent.objects.get(
            company=self.company,
            verb=ActivityEvent.Verb.COMPANY_MEMBER_REMOVED,
        )
        self.assertFalse(event.meta["account_deactivated"])

    def test_reinvite_after_deactivation_reuses_account_and_allows_activation(self):
        """A fresh invitation can restore access without losing audit history."""
        self.client.post(self.url)
        last_url = reverse(
            "accounts:company_member_remove",
            args=[self.other_company.pk, self.member.pk],
        )
        self.client.post(last_url)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)

        with patch("apps.accounts.views.send_invite_email") as send_email:
            response = self.client.post(
                reverse("accounts:company_invite_member", args=[self.company.pk]),
                {
                    "email": self.member.email,
                    "first_name": "Multi",
                    "last_name": "Company",
                    "invite_subject": "Welcome back",
                    "invite_message": "Your access has been restored.",
                    "invite_language": "en",
                },
            )
        self.assertEqual(response.status_code, 302)
        send_email.assert_called_once()
        self.assertEqual(User.objects.filter(email=self.member.email).count(), 1)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.assertTrue(CompanyMember.objects.filter(
            user=self.member, company=self.company,
        ).exists())
        invite = UserInvite.objects.get(
            user=self.member, company=self.company, revoked_at__isnull=True,
            accepted_at__isnull=True,
        )

        password = "NewSecurePassword2026!Long"
        response = self.client.post(
            reverse("accounts:accept_invite_uuid", args=[invite.pk]),
            {"new_password1": password, "new_password2": password},
        )
        self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)
        invite.refresh_from_db()
        self.assertIsNotNone(invite.accepted_at)
        self.client.logout()
        self.assertTrue(self.client.login(
            username=self.member.username, password=password,
        ))

    def test_orphan_invitation_cannot_reactivate_removed_user(self):
        self.client.post(self.url)
        last_url = reverse(
            "accounts:company_member_remove",
            args=[self.other_company.pk, self.member.pk],
        )
        self.client.post(last_url)
        # Even an erroneously unrevoked invitation must not activate
        # an account which no longer belongs to the invite's company.
        orphan = UserInvite.objects.create(
            company=self.other_company, user=self.member,
            created_by=self.admin,
        )
        invite_url = reverse("accounts:accept_invite_uuid", args=[orphan.pk])
        self.assertEqual(self.client.get(invite_url).status_code, 400)
        self.assertEqual(self.client.post(invite_url, {
            "new_password1": "NewSecurePassword2026!Long",
            "new_password2": "NewSecurePassword2026!Long",
        }).status_code, 400)
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)

    def test_projects_and_original_creator_are_preserved(self):
        project = TestProcess.objects.create(
            name="Existing recruitment",
            company=self.company,
            org_unit=self.unit,
            account_code="A",
            project_code="existing-1",
            created_by=self.member,
        )
        self.client.post(self.url)
        project.refresh_from_db()
        self.assertEqual(project.company, self.company)
        self.assertEqual(project.created_by, self.member)
        self.assertEqual(project.org_unit, self.unit)
        self.assertFalse(project.project_completion_notifications_enabled)

    def test_company_user_detail_shows_remove_control(self):
        response = self.client.get(reverse(
            "accounts:company_user_detail",
            args=[self.company.pk, self.member.pk],
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-member-removal-url=')

    def test_get_cannot_remove_a_member(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertTrue(CompanyMember.objects.filter(pk=self.membership.pk).exists())

    def test_non_admin_cannot_remove_a_member(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertTrue(CompanyMember.objects.filter(pk=self.membership.pk).exists())

    def test_last_company_admin_is_protected(self):
        self.membership.role = CompanyMember.ROLE_ADMIN
        self.membership.save(update_fields=["role"])
        response = self.client.post(self.url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CompanyMember.objects.filter(pk=self.membership.pk).exists())
        self.assertTrue(UserOrgUnitAccess.objects.filter(
            user=self.member, org_unit=self.unit,
        ).exists())

    def test_admin_cannot_remove_their_own_company_membership(self):
        self_membership = CompanyMember.objects.create(
            company=self.company, user=self.admin,
        )
        own_url = reverse(
            "accounts:company_member_remove", args=[self.company.pk, self.admin.pk]
        )
        self.assertEqual(self.client.post(own_url).status_code, 302)
        self.assertTrue(CompanyMember.objects.filter(pk=self_membership.pk).exists())

    def test_company_users_page_displays_remove_button_and_confirm_modal(self):
        response = self.client.get(
            reverse("accounts:company_users", args=[self.company.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-member-removal-url=')
        self.assertContains(response, 'id="removeCompanyMemberModal"')
        self.assertContains(response, "Kopplingar till andra företag påverkas inte.")

    def test_global_user_detail_lists_each_company_remove_action(self):
        response = self.client.get(
            reverse("accounts:admin_user_detail", args=[self.member.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, reverse(
                "accounts:company_member_remove", args=[self.company.pk, self.member.pk]
            ),
        )
        self.assertContains(
            response, reverse(
                "accounts:company_member_remove",
                args=[self.other_company.pk, self.member.pk],
            ),
        )

    def test_removed_pending_invite_cannot_be_activated(self):
        pending_user = User.objects.create_user(
            username="pending", email="pending@example.com",
            password=None, is_active=False,
        )
        CompanyMember.objects.create(company=self.company, user=pending_user)
        invite = UserInvite.objects.create(
            company=self.company, user=pending_user, created_by=self.admin,
        )
        pending_url = reverse(
            "accounts:company_member_remove", args=[self.company.pk, pending_user.pk]
        )
        self.assertEqual(self.client.post(pending_url).status_code, 302)
        self.assertEqual(
            self.client.get(reverse("accounts:accept_invite_uuid", args=[invite.pk])).status_code,
            400,
        )
