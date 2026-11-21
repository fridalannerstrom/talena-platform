"""Persistent per-user language and Talena-admin controls."""
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Company, CompanyMember

User = get_user_model()


class UserLanguagePreferenceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="language-admin", email="language-admin@example.com",
            password="AdminPassword-2026!",
        )
        self.member = User.objects.create_user(
            username="language-customer", email="language-customer@example.com",
            password="CustomerPassword-2026!",
        )
        self.company = Company.objects.create(name="Language Test AB")
        CompanyMember.objects.create(company=self.company, user=self.member)
        self.endpoint = reverse(
            "accounts:admin_user_language", args=[self.member.pk]
        )
        self.global_page = reverse(
            "accounts:admin_user_detail", args=[self.member.pk]
        )
        self.company_page = reverse(
            "accounts:company_user_detail",
            args=[self.company.pk, self.member.pk],
        )

    def test_legacy_user_without_preference_retains_browser_cookie(self):
        self.assertEqual(self.member.preferred_language, "")
        self.client.force_login(self.member)
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "sv"
        response = self.client.get(reverse("core:login"))
        self.assertEqual(response.wsgi_request.LANGUAGE_CODE, "sv")

    def test_admin_can_view_and_update_language_from_both_user_pages(self):
        self.client.force_login(self.admin)
        for page in (self.global_page, self.company_page):
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertContains(response, "Språk i Talena")
                self.assertContains(response, self.endpoint)
                self.assertContains(response, "Automatiskt (webbläsare)")

        response = self.client.post(
            self.endpoint,
            {"preferred_language": "sv", "next": self.company_page},
        )
        self.assertRedirects(response, self.company_page)
        self.member.refresh_from_db()
        self.assertEqual(self.member.preferred_language, "sv")
        self.assertContains(self.client.get(self.global_page), 'value="sv" selected')
        self.assertContains(self.client.get(self.company_page), 'value="sv" selected')

    def test_admin_preference_overrides_stale_cookie_on_next_customer_request(self):
        self.client.force_login(self.admin)
        self.client.post(self.endpoint, {"preferred_language": "sv"})
        self.client.force_login(self.member)
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        page = self.client.get(reverse("core:login"))
        self.assertEqual(page.wsgi_request.LANGUAGE_CODE, "sv")
        self.assertContains(page, "Glömt lösenord?")

    def test_customer_can_switch_language_and_it_persists_across_new_browser(self):
        self.member.preferred_language = "sv"
        self.member.save(update_fields=["preferred_language"])
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("core:login")},
        )
        self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.assertEqual(self.member.preferred_language, "en")

        another_browser = Client()
        another_browser.force_login(self.member)
        another_browser.cookies[settings.LANGUAGE_COOKIE_NAME] = "sv"
        page = another_browser.get(reverse("core:login"))
        self.assertEqual(page.wsgi_request.LANGUAGE_CODE, "en")
        self.assertContains(page, "Forgot password?")

    def test_anonymous_switch_does_not_create_a_stored_preference(self):
        self.client.post(
            reverse("set_language"),
            {"language": "sv", "next": reverse("core:login")},
        )
        self.member.refresh_from_db()
        self.assertEqual(self.member.preferred_language, "")

    def test_company_admin_is_not_platform_admin(self):
        CompanyMember.objects.filter(
            company=self.company, user=self.member
        ).update(role=CompanyMember.ROLE_ADMIN)
        self.client.force_login(self.member)
        response = self.client.post(self.endpoint, {"preferred_language": "sv"})
        self.assertEqual(response.status_code, 403)
        self.member.refresh_from_db()
        self.assertEqual(self.member.preferred_language, "")

    def test_invalid_language_is_rejected(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.endpoint, {"preferred_language": "no"}
        )
        self.assertEqual(response.status_code, 400)
        self.member.refresh_from_db()
        self.assertEqual(self.member.preferred_language, "")

    def test_admin_can_revert_to_browser_language(self):
        self.member.preferred_language = "sv"
        self.member.save(update_fields=["preferred_language"])
        self.client.force_login(self.admin)
        self.client.post(self.endpoint, {"preferred_language": ""})
        self.member.refresh_from_db()
        self.assertEqual(self.member.preferred_language, "")

    def test_admin_cannot_redirect_to_untrusted_host(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.endpoint,
            {"preferred_language": "sv", "next": "https://untrusted.example/"},
        )
        self.assertRedirects(response, self.global_page)

    def test_endpoint_is_post_only_and_csrf_protected(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.endpoint).status_code, 405)
        strict_client = Client(enforce_csrf_checks=True)
        strict_client.force_login(self.admin)
        self.assertEqual(
            strict_client.post(
                self.endpoint, {"preferred_language": "sv"}
            ).status_code,
            403,
        )
        self.member.refresh_from_db()
        self.assertEqual(self.member.preferred_language, "")

    def test_language_is_visible_in_both_user_lists(self):
        self.member.preferred_language = "en"
        self.member.save(update_fields=["preferred_language"])
        self.client.force_login(self.admin)
        for page in (
            reverse("accounts:admin_customers_list"),
            reverse("accounts:company_users", args=[self.company.pk]),
        ):
            response = self.client.get(page)
            self.assertContains(response, "Språk")
            self.assertContains(response, "English")

    def test_new_company_invitation_sets_language_on_new_account(self):
        self.client.force_login(self.admin)
        with patch("apps.accounts.views.send_invite_email") as mocked_email:
            response = self.client.post(
                reverse("accounts:company_invite_member", args=[self.company.pk]),
                {
                    "email": "new-swedish@example.com",
                    "first_name": "New",
                    "last_name": "Customer",
                    "invite_subject": "Welcome",
                    "invite_message": "Message",
                    "invite_language": "sv",
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mocked_email.called)
        invited = User.objects.get(email="new-swedish@example.com")
        self.assertEqual(invited.preferred_language, "sv")
