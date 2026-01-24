from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

def send_invite_email(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    path = reverse("accounts:accept_invite", kwargs={"uidb64": uidb64, "token": token})
    invite_url = request.build_absolute_uri(path)

    subject = "Set your password for Talena"
    message = (
        f"Hi {user.first_name or ''},\n\n"
        f"You’ve been invited to Talena.\n"
        f"Set your password here:\n{invite_url}\n\n"
        f"If you didn’t expect this email, you can ignore it."
    )

    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])