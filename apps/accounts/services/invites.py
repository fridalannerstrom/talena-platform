from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static


def send_invite_email(request, user, invite_link, company=None):
    subject = "Välkommen till Talena"

    logo_url = request.build_absolute_uri(static("images/talena-logo-email.png"))

    context = {
        "user": user,
        "company": company,
        "company_name": company.name if company else "din organisation",
        "invite_link": invite_link,
        "invited_by": request.user.get_full_name() or request.user.email,
        "logo_url": logo_url,
    }

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