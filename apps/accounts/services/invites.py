from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_invite_email(request, user, invite_link, company=None):
    subject = "Du är inbjuden till Talena"

    context = {
        "user": user,
        "company": company,
        "invite_link": invite_link,
    }

    # Om du vill köra template:
    text_body = render_to_string("emails/invite.txt", context)
    html_body = render_to_string("emails/invite.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()