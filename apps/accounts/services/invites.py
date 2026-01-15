from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail

def build_invite_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("accounts:accept_invite", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)

def send_invite_email(request, user):
    link = build_invite_link(request, user)

    subject = "Welcome to Talena, set your password"
    message = (
        "Hi!\n\n"
        "You have been invited to Talena.\n"
        "Set your password using the link below:\n\n"
        f"{link}\n\n"
        "If you didn’t expect this email, you can ignore it.\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
        fail_silently=False,
    )