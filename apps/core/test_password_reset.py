"""Password recovery must be secure, bilingual and compatible with Talena SMTP."""
import re
from urllib.parse import urlsplit

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reset-user@example.com",
            email="reset-user@example.com",
            password="Original-Secure-Password-123!",
        )
        self.reset_url = reverse("core:password_reset")

    def _request_link(self, **kwargs):
        response = self.client.post(
            self.reset_url,
            {"email": self.user.email},
            **kwargs,
        )
        self.assertRedirects(response, reverse("core:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        match = re.search(
            r"https?://[^\s]+/password-reset/confirm/[^\s]+",
            mail.outbox[0].body,
        )
        self.assertIsNotNone(match)
        return match.group(0).strip()

    def test_login_links_to_password_recovery(self):
        response = self.client.get(reverse("core:login"))
        self.assertContains(response, 'href="' + self.reset_url + '"')

    def test_recovery_and_confirmation_pages_render(self):
        self.assertContains(self.client.get(self.reset_url), "Forgot your password?")
        self.assertContains(
            self.client.get(reverse("core:password_reset_done")),
            "Check your email",
        )

    def test_active_user_receives_bilingual_multipart_message(self):
        link = self._request_link(HTTP_ACCEPT_LANGUAGE="sv")
        self.assertTrue(link.startswith("http://testserver/"))
        message = mail.outbox[0]
        self.assertIn("Återställ ditt lösenord", message.subject)
        self.assertIn("Återställ", message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(message.alternatives[0][1], "text/html")
        self.assertIn("Välj nytt lösenord", message.alternatives[0][0])

    def test_recovery_uses_the_request_environment_and_https(self):
        with override_settings(ALLOWED_HOSTS=["testserver", "stage.talena.io"]):
            link = self._request_link(
                HTTP_HOST="stage.talena.io",
                HTTP_ACCEPT_LANGUAGE="en",
                secure=True,
            )
        self.assertTrue(link.startswith("https://stage.talena.io/"))
        self.assertIn("Reset your Talena password", mail.outbox[0].subject)

    def test_unknown_inactive_and_unusable_password_do_not_reveal_accounts(self):
        inactive = get_user_model().objects.create_user(
            username="inactive@example.com",
            email="inactive@example.com",
            password="Another-Secure-Password-123!",
            is_active=False,
        )
        unusable = get_user_model().objects.create_user(
            username="unusable@example.com",
            email="unusable@example.com",
            password=None,
        )
        self.assertFalse(inactive.is_active)
        self.assertFalse(unusable.has_usable_password())
        for address in ("unknown@example.com", inactive.email, unusable.email):
            with self.subTest(address=address):
                response = self.client.post(self.reset_url, {"email": address})
                self.assertRedirects(response, reverse("core:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_token_sets_new_password_and_cannot_be_reused(self):
        link = self._request_link()
        original_path = urlsplit(link).path
        redirect_response = self.client.get(original_path)
        self.assertEqual(redirect_response.status_code, 302)
        self.assertIn("/set-password/", redirect_response.url)
        confirmation_url = redirect_response.url
        self.assertContains(self.client.get(confirmation_url), "New password")
        response = self.client.post(
            confirmation_url,
            {
                "new_password1": "Brand-New-Secure-Password-123!",
                "new_password2": "Brand-New-Secure-Password-123!",
            },
        )
        self.assertRedirects(response, reverse("core:password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brand-New-Secure-Password-123!"))
        self.assertFalse(self.user.check_password("Original-Secure-Password-123!"))
        self.assertContains(
            self.client.get(original_path), "This link is no longer valid"
        )
        login = self.client.post(
            reverse("core:login"),
            {"username": self.user.username, "password": "Brand-New-Secure-Password-123!"},
        )
        self.assertEqual(login.status_code, 302)

    def test_password_validation_still_applies(self):
        link = self._request_link()
        confirmation_url = self.client.get(urlsplit(link).path).url
        response = self.client.post(
            confirmation_url,
            {"new_password1": "123", "new_password2": "123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Original-Secure-Password-123!"))

    def test_bad_token_shows_recovery_not_password_form(self):
        response = self.client.get(
            reverse(
                "core:password_reset_confirm",
                kwargs={"uidb64": "bad", "token": "invalid-token"},
            )
        )
        self.assertContains(response, "This link is no longer valid")
        self.assertNotContains(response, 'name="new_password1"')

    def test_reset_form_referrer_policy_allows_same_origin_csrf(self):
        # Chromium can send Origin: null for form POSTs under no-referrer.
        # Keep referrers on our own origin but never send them off-site.
        response = self.client.get(self.reset_url)
        self.assertContains(response, '<meta name="referrer" content="same-origin">')
        self.assertNotContains(response, '<meta name="referrer" content="no-referrer">')

    def test_csrf_protection_stays_enabled(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        initial = client.get(self.reset_url)
        self.assertEqual(initial.status_code, 200)
        token = client.cookies["csrftoken"].value
        sent = client.post(
            self.reset_url,
            {"email": self.user.email, "csrfmiddlewaretoken": token},
            HTTP_ORIGIN="http://testserver",
        )
        self.assertRedirects(sent, reverse("core:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        refused = client.post(
            self.reset_url,
            {"email": self.user.email, "csrfmiddlewaretoken": token},
            HTTP_ORIGIN="null",
        )
        self.assertEqual(refused.status_code, 403)
        self.assertEqual(len(mail.outbox), 1)

    def test_swedish_recovery_form(self):
        response = self.client.get(self.reset_url, HTTP_ACCEPT_LANGUAGE="sv")
        self.assertContains(response, "Glömt lösenord?")
        self.assertContains(response, "Skicka återställningslänk")
