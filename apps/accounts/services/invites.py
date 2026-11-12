"""Talena account invitation email rendering and delivery.

The preview and the actual email share precisely the same templates and URL
context. No account token is ever needed to render a preview.
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse

from apps.accounts.forms import (
    DEFAULT_INVITE_MESSAGE,
    DEFAULT_INVITE_SUBJECT,
    DEFAULT_INVITE_MESSAGE_SV,
    DEFAULT_INVITE_SUBJECT_SV,
)


def account_invitation_language(language):
    """Only supported UI languages may select invitation copy."""
    return "sv" if str(language).lower().startswith("sv") else "en"


def account_invitation_copy(*, subject=None, message=None, language="en"):
    language = account_invitation_language(language)
    # Keep preview and delivery consistent even when the form was initially
    # filled in another language. Only replace untouched standard text.
    default_subject = (
        DEFAULT_INVITE_SUBJECT_SV if language == "sv" else DEFAULT_INVITE_SUBJECT
    )
    default_message = (
        DEFAULT_INVITE_MESSAGE_SV if language == "sv" else DEFAULT_INVITE_MESSAGE
    )
    if subject is None or subject in (DEFAULT_INVITE_SUBJECT, DEFAULT_INVITE_SUBJECT_SV):
        subject = default_subject
    if message is None or message in (DEFAULT_INVITE_MESSAGE, DEFAULT_INVITE_MESSAGE_SV):
        message = default_message
    return subject, message


def account_invitation_context(
    request, user, invite_link, company=None, *, message=None, language="en"
):
    """Use the request host for both links (dev, stage and production)."""
    return {
        "user": user,
        "company": company,
        "company_name": company.name if company else (
            "din organisation" if language == "sv" else "your organisation"
        ),
        "invite_link": invite_link,
        "login_url": request.build_absolute_uri(reverse("core:login")),
        "invited_by": request.user.get_full_name() or request.user.email,
        "logo_url": request.build_absolute_uri(static("images/talena-logo-v8.png")),
        "invite_message": message,
        "language": account_invitation_language(language),
    }


def render_account_invitation(request, user, invite_link, company=None, *,
                              subject=None, message=None, language="en"):
    """Return subject, plain text and HTML for delivery or admin-only preview."""
    lang = account_invitation_language(language)
    resolved_subject, resolved_message = account_invitation_copy(
        subject=subject, message=message, language=lang,
    )
    context = account_invitation_context(
        request, user, invite_link, company,
        message=resolved_message, language=lang,
    )
    return (
        resolved_subject,
        render_to_string("emails/invite.txt", context, request=request),
        render_to_string("emails/invite.html", context, request=request),
    )


def send_invite_email(request, user, invite_link, company=None, *,
                      subject=None, message=None, language="en"):
    """Send the account activation link and the separate normal login link."""
    subject, text_body, html_body = render_account_invitation(
        request, user, invite_link, company,
        subject=subject, message=message, language=language,
    )
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
