from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import translation


def send_invite_email(request, user, invite_link, company=None):
    """
    Send Talena account invitations in English.

    The account recipient has not chosen a Talena language yet,
    so account invitations always use English.
    """

    logo_url = request.build_absolute_uri(
        static("images/talena-logo-email.png")
    )

    context = {
        "user": user,
        "company": company,
        "company_name": (
            company.name
            if company
            else "your organisation"
        ),
        "invite_link": invite_link,
        "invited_by": (
            request.user.get_full_name()
            or request.user.email
        ),
        "logo_url": logo_url,
    }

    # Account invitations should always be sent in English,
    # regardless of the language selected by the administrator.
    with translation.override("en"):
        subject = "Welcome to Talena"

        text_body = render_to_string(
            "emails/invite.txt",
            context,
        )

        html_body = render_to_string(
            "emails/invite.html",
            context,
        )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            None,
        ),
        to=[user.email],
    )

    msg.attach_alternative(
        html_body,
        "text/html",
    )

    msg.send()