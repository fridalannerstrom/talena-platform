from django.core import mail
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.forms import CompanyInviteMemberForm
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

    def test_subject_rejects_line_breaks(self):
        form = CompanyInviteMemberForm({
            "email": "new-user@example.com",
            "invite_subject": "Welcome\nBcc: extra@example.com",
            "invite_message": "A message.",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("invite_subject", form.errors)
