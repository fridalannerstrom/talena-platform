from datetime import timedelta
from pathlib import Path

from django.conf import settings
import uuid

from django.core import mail
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.forms import (
    CompanyInviteMemberForm, InviteUserForm,
    DEFAULT_INVITE_SUBJECT, DEFAULT_INVITE_SUBJECT_SV,
    DEFAULT_INVITE_MESSAGE, DEFAULT_INVITE_MESSAGE_SV,
)
from apps.accounts.services.invites import account_invitation_copy
from apps.accounts.models import Company, UserInvite


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class InvitationEmailTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="invite-admin@example.com",
            email="invite-admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)

    def test_company_invite_sends_edited_copy_with_activation_link(self):
        company = Company.objects.create(name="Example company")
        response = self.client.post(
            reverse("accounts:company_invite_member", args=[company.pk]),
            {
                "email": "new-user@example.com",
                "first_name": "New",
                "last_name": "User",
                "invite_subject": "Welcome aboard",
                "invite_message": "A personal welcome <script>alert(1)</script>.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        invitation = UserInvite.objects.get(company=company)
        sent = mail.outbox[0]
        self.assertEqual(sent.subject, "Welcome aboard")
        self.assertIn("A personal welcome <script>", sent.body)
        self.assertIn(str(invitation.id), sent.body)
        self.assertNotIn("<script>", sent.alternatives[0][0])
        self.assertIn("&lt;script&gt;", sent.alternatives[0][0])

    def test_customer_create_sends_edited_copy_with_activation_link(self):
        response = self.client.post(
            reverse("accounts:admin_customers_create"),
            {
                "email": "new-customer@example.com",
                "first_name": "New",
                "last_name": "Customer",
                "invite_subject": "Your Talena account",
                "invite_message": "A message chosen by the admin.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(mail.outbox[0].subject, "Your Talena account")
        self.assertIn("A message chosen by the admin.", mail.outbox[0].body)
        self.assertIn("/invite/accept/", mail.outbox[0].body)


    def test_account_invitation_contains_separate_login_link_and_modern_branding(self):
        company = Company.objects.create(name="Talent preview client")
        response = self.client.post(
            reverse("accounts:company_invite_member", args=[company.pk]),
            {"email": "english@example.com", "first_name": "Alex",
             "invite_subject": "Welcome to Talena", "invite_message": "Hello Alex",
             "invite_language": "en"},
        )
        self.assertEqual(response.status_code, 302)
        sent = mail.outbox[-1]
        body_html = sent.alternatives[0][0]
        login_url = "http://testserver" + reverse("core:login")
        self.assertIn(login_url, sent.body)
        self.assertIn(login_url, body_html)
        self.assertIn("Sign in to Talena", body_html)
        self.assertIn("Activate my account", body_html)
        self.assertIn("#ff6f61", body_html)
        self.assertNotIn("#6f4ee8", body_html)
        self.assertIn("for initial setup only", sent.body)

    def test_swedish_account_invitation_changes_default_copy_but_keeps_custom_copy(self):
        company = Company.objects.create(name="Svenskt företag")
        self.client.post(reverse("accounts:company_invite_member", args=[company.pk]), {
            "email": "swedish@example.com", "first_name": "Alex",
            "invite_language": "sv", "invite_subject": "Welcome to Talena",
            "invite_message": "You've received a Talena account, bringing assessment processes, results and AI-supported insights together in one clear workflow.",
        })
        sent = mail.outbox[-1]
        self.assertEqual(sent.subject, "Välkommen till Talena")
        self.assertIn("Logga in på Talena", sent.alternatives[0][0])
        self.assertIn("Aktivera mitt konto", sent.alternatives[0][0])
        self.assertIn("Skapa ditt lösenord", sent.body)

    def test_links_follow_the_environment_host(self):
        company = Company.objects.create(name="Preview host")
        with override_settings(ALLOWED_HOSTS=["testserver", "stage.talena.io"]):
            self.client.post(
                reverse("accounts:company_invite_member", args=[company.pk]),
                {"email": "env@example.com", "invite_subject": "Welcome",
                 "invite_message": "Test", "invite_language": "en"},
                HTTP_HOST="stage.talena.io",
            )
        sent = mail.outbox[-1]
        self.assertIn("http://stage.talena.io" + reverse("core:login"), sent.body)
        self.assertIn("http://stage.talena.io", sent.alternatives[0][0])

    def test_admin_only_preview_never_sends_or_creates_a_user(self):
        company = Company.objects.create(name="Preview Company")
        preview = reverse("accounts:company_account_invitation_preview", args=[company.pk])
        before_users = get_user_model().objects.count()
        response = self.client.post(preview, {
            "invite_subject": "Custom preview subject",
            "invite_message": "A personal welcome <script>alert(1)</script>",
            "invite_language": "sv",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Custom preview subject", response.content.decode())
        self.assertIn("Logga in på Talena", response.content.decode())
        self.assertNotIn("<script>alert(1)</script>", response.content.decode())
        self.assertIn("sandbox=\"\"", response.content.decode())
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(get_user_model().objects.count(), before_users)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(self.client.get(preview).status_code, 405)

    def test_non_admin_cannot_preview_email(self):
        company = Company.objects.create(name="Private Company")
        non_admin = get_user_model().objects.create_user(
            username="preview-customer@example.com", email="preview-customer@example.com",
            password="password-12345"
        )
        self.client.force_login(non_admin)
        response = self.client.post(
            reverse("accounts:company_account_invitation_preview", args=[company.pk]),
            {"invite_language": "sv"},
        )
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_revoked_accepted_and_expired_uuid_invites_show_recovery(self):
        company = Company.objects.create(name="Invitation states")
        user = get_user_model().objects.create_user(
            username="invited-state@example.com", email="invited-state@example.com",
            password=None, is_active=False,
        )
        missing_url = reverse("accounts:accept_invite_uuid", args=[uuid.uuid4()])
        response = self.client.get(missing_url)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Sign in to Talena", status_code=400)
        self.assertContains(response, "Contact support", status_code=400)

        invite = UserInvite.objects.create(company=company, user=user, created_by=self.admin)
        url = reverse("accounts:accept_invite_uuid", args=[invite.id])
        self.assertEqual(self.client.get(url).status_code, 200)

        with override_settings(TALENA_ACCOUNT_INVITE_EXPIRY_DAYS=14):
            UserInvite.objects.filter(pk=invite.pk).update(
                created_at=timezone.now() - timedelta(days=15)
            )
            self.assertEqual(self.client.get(url).status_code, 400)
        invite.refresh_from_db()
        invite.created_at = timezone.now()
        invite.revoked_at = timezone.now()
        invite.save(update_fields=["created_at", "revoked_at"])
        self.assertEqual(self.client.get(url).status_code, 400)
        invite.revoked_at = None
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["revoked_at", "accepted_at"])
        self.assertEqual(self.client.get(url).status_code, 400)

    def test_malformed_invite_path_uses_the_same_safe_recovery_page(self):
        response = self.client.get("/tq-admin/invite/not-a-real-token/")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Sign in to Talena", status_code=400)

    def test_used_invite_can_sign_in_without_reusing_token(self):
        company = Company.objects.create(name="Activation journey")
        user = get_user_model().objects.create_user(
            username="onboarding@example.com", email="onboarding@example.com",
            password=None, is_active=False,
        )
        invite = UserInvite.objects.create(company=company, user=user, created_by=self.admin)
        url = reverse("accounts:accept_invite_uuid", args=[invite.id])
        self.client.logout()
        activated = self.client.post(url, {
            "new_password1": "ExamplePassword-123!",
            "new_password2": "ExamplePassword-123!",
        })
        self.assertEqual(activated.status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 400)
        login_response = self.client.post(reverse("core:login"), {
            "username": user.email,
            "password": "ExamplePassword-123!",
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))

    def test_default_copy_switches_in_both_directions_on_server(self):
        self.assertEqual(
            account_invitation_copy(
                subject=DEFAULT_INVITE_SUBJECT,
                message=DEFAULT_INVITE_MESSAGE,
                language="sv",
            ),
            (DEFAULT_INVITE_SUBJECT_SV, DEFAULT_INVITE_MESSAGE_SV),
        )
        self.assertEqual(
            account_invitation_copy(
                subject=DEFAULT_INVITE_SUBJECT_SV,
                message=DEFAULT_INVITE_MESSAGE_SV,
                language="en",
            ),
            (DEFAULT_INVITE_SUBJECT, DEFAULT_INVITE_MESSAGE),
        )
        self.assertEqual(
            account_invitation_copy(
                subject="Anpassad ämnesrad", message="Mitt personliga mejl",
                language="en",
            ),
            ("Anpassad ämnesrad", "Mitt personliga mejl"),
        )

    def test_both_invitation_forms_expose_exact_bilingual_defaults(self):
        for form_class in (CompanyInviteMemberForm, InviteUserForm):
            with self.subTest(form=form_class):
                form = form_class()
                for field_name, expected_en, expected_sv in (
                    ("invite_subject", DEFAULT_INVITE_SUBJECT, DEFAULT_INVITE_SUBJECT_SV),
                    ("invite_message", DEFAULT_INVITE_MESSAGE, DEFAULT_INVITE_MESSAGE_SV),
                ):
                    widget = form.fields[field_name].widget
                    self.assertEqual(widget.attrs["data-invite-default-en"], expected_en)
                    self.assertEqual(widget.attrs["data-invite-default-sv"], expected_sv)

        base = Path(settings.BASE_DIR)
        for template in (
            "templates/admin/accounts/companies/_invite_user_modal.html",
            "templates/admin/accounts/customer/customers_create.html",
        ):
            with self.subTest(template=template):
                html = (base / template).read_text(encoding="utf-8")
                self.assertIn("account-invite-language.js", html)

    def test_email_and_preview_use_uploaded_talena_v8_png_logo(self):
        logo = Path(settings.BASE_DIR) / "static/images/talena-logo-v8.png"
        self.assertTrue(logo.is_file())
        with logo.open("rb") as image:
            self.assertEqual(image.read(8), b"\x89PNG\r\n\x1a\n")

        company = Company.objects.create(name="Brand check")
        self.client.post(reverse("accounts:company_invite_member", args=[company.pk]), {
            "email": "brandcheck@example.com",
            "invite_subject": DEFAULT_INVITE_SUBJECT,
            "invite_message": DEFAULT_INVITE_MESSAGE,
            "invite_language": "sv",
        })
        sent_html = mail.outbox[-1].alternatives[0][0]
        self.assertIn("talena-logo-v8.png", sent_html)
        self.assertNotIn("talena-logo-email.png", sent_html)
        preview = self.client.post(
            reverse("accounts:company_account_invitation_preview", args=[company.pk]),
            {"invite_subject": DEFAULT_INVITE_SUBJECT,
             "invite_message": DEFAULT_INVITE_MESSAGE, "invite_language": "sv"},
        )
        self.assertContains(preview, "talena-logo-v8.png")

    def test_subject_rejects_line_breaks(self):
        form = CompanyInviteMemberForm({
            "email": "new-user@example.com",
            "invite_subject": "Welcome\nBcc: extra@example.com",
            "invite_message": "A message.",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("invite_subject", form.errors)
