from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from apps.activity.models import ActivityEvent
from apps.activity.services import log_event

from .interpretation import create_candidate_result_snapshot
from .models import CandidateResultAccess
from .services import (
    create_candidate_result_access,
    rotate_candidate_result_access,
)


def _copy(locale: str) -> dict[str, str]:
    if locale == "sv":
        return {
            "subject": "Ditt assessmentresultat från Talena",
            "body": (
                "Hej,\n\n"
                "Tack för att du genomfört TQ:s test!\n\n"
                "Vi vill belysa att resultatet är del av helheten, inget facit.\n\n"
                "Om det är något du inte känner igen dig i, vill förtydliga "
                "eller berätta mer om, har du möjlighet att dela med dig av "
                "dina tankar genom att lämna kommentarer direkt i rapporten.\n\n"
                "Ta del av dina resultat här:\n"
                "{result_url}\n\n"
                "Din personliga verifieringskod:\n"
                "{verification_code}\n\n"
                "Vänliga hälsningar,\n"
                "Teamet på TQ"
            ),
        }
    return {
        "subject": "Your Talena assessment result",
        "body": (
            "Hi {first_name}!\n\n"
            "Thank you for completing the assessment.\n\n"
            "Your result is a basis for reflection and further "
            "conversation. It describes possible preferences and "
            "tendencies, not a grade or an absolute truth.\n\n"
            "View your result here:\n{result_url}\n\n"
            "Your personal verification code is:\n{verification_code}\n\n"
            "Best regards,\nTalena"
        ),
    }


def _html_body(
    locale: str,
    *,
    first_name: str,
    result_url: str,
    verification_code: str,
):
    if locale == "sv":
        return format_html(
            "<p>Hej,</p>"
            "<p>Tack för att du genomfört TQ:s test!</p>"
            "<p>Vi vill belysa att resultatet är del av helheten, inget facit.</p>"
            "<p>Om det är något du inte känner igen dig i, vill förtydliga "
            "eller berätta mer om, har du möjlighet att dela med dig av "
            "dina tankar genom att lämna kommentarer direkt i rapporten.</p>"
            "<p><strong>Ta del av dina resultat här:</strong><br>"
            "<a href=\"{result_url}\">{result_url}</a></p>"
            "<p><strong>Din personliga verifieringskod:</strong><br>"
            "{verification_code}</p>"
            "<p>Vänliga hälsningar,<br>Teamet på TQ</p>",
            result_url=result_url,
            verification_code=verification_code,
        )

    return format_html(
        "<p>Hi {first_name}!</p>"
        "<p>Thank you for completing the assessment.</p>"
        "<p>Your result is a basis for reflection and further conversation. "
        "It describes possible preferences and tendencies, not a grade or "
        "an absolute truth.</p>"
        "<p><strong>View your result here:</strong><br>"
        "<a href=\"{result_url}\">{result_url}</a></p>"
        "<p><strong>Your personal verification code is:</strong><br>"
        "{verification_code}</p>"
        "<p>Best regards,<br>Talena</p>",
        first_name=first_name,
        result_url=result_url,
        verification_code=verification_code,
    )


def _result_url(raw_token: str, base_url: str | None = None) -> str:
    path = reverse(
        "candidate_results:result",
        kwargs={"token": raw_token},
    )
    if base_url:
        return f"{base_url.rstrip('/')}{path}"
    return path


def _log_activity(invitation, *, actor, email_log_id, status, error=""):
    try:
        log_event(
            company=invitation.process.company,
            verb=(
                ActivityEvent.Verb.CANDIDATE_RESULT_EMAIL_SENT
                if status == "sent"
                else ActivityEvent.Verb.CANDIDATE_RESULT_EMAIL_FAILED
            ),
            actor=actor,
            actor_name="Talena" if actor is None else "",
            process=invitation.process,
            candidate=invitation.candidate,
            invitation=invitation,
            meta={
                "email_log_id": email_log_id,
                "error": error,
            },
        )
    except Exception:
        # Activity logging must never turn a delivered email into a failure.
        pass


def send_candidate_result_email(
    invitation,
    *,
    actor=None,
    base_url: str | None = None,
    replace_code: bool = False,
):
    """
    Create/reuse the snapshot and send one candidate result email.

    A resend rotates the token and verification code on the existing access
    row. It never creates a second active access record.
    """
    if not invitation.process.candidate_results_enabled:
        raise ValueError("Candidate results are not enabled for this process.")
    if invitation.status != "completed":
        raise ValueError("Candidate result email requires a completed invitation.")

    locale = (
        invitation.process.candidate_language or "sv"
    ).strip().lower()
    if locale not in {"sv", "en"}:
        locale = "sv"

    snapshot, _created = create_candidate_result_snapshot(
        invitation,
        language_code=locale,
    )

    access = (
        CandidateResultAccess.objects
        .filter(snapshot=snapshot)
        .first()
    )

    from apps.emails.models import EmailLog

    if access and replace_code:
        raw_token, raw_code = rotate_candidate_result_access(access)
    elif access:
        previous_log = (
            EmailLog.objects
            .filter(
                invitation=invitation,
                template_type="candidate_result",
                status="sent",
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if previous_log:
            return previous_log, access, None
        raw_token, raw_code = rotate_candidate_result_access(access)
    else:
        access, raw_token, raw_code = create_candidate_result_access(snapshot)

    copy = _copy(locale)
    subject = copy["subject"]
    first_name = invitation.candidate.first_name or ""
    result_url = _result_url(raw_token, base_url)
    body = copy["body"].format(
        first_name=first_name,
        result_url=result_url,
        verification_code=raw_code,
    )
    html_body = _html_body(
        locale,
        first_name=first_name,
        result_url=result_url,
        verification_code=raw_code,
    )

    email_log = EmailLog.objects.create(
        invitation=invitation,
        template_type="candidate_result",
        to_email=invitation.candidate.email,
        subject=subject,
        body_snapshot=body,
        status="queued",
    )

    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invitation.candidate.email],
    )
    message.attach_alternative(html_body, "text/html")

    try:
        message.send()
        email_log.mark_sent()
    except Exception as exc:
        email_log.mark_failed(str(exc))
        _log_activity(
            invitation,
            actor=actor,
            email_log_id=email_log.id,
            status="failed",
            error=str(exc),
        )
        raise

    _log_activity(
        invitation,
        actor=actor,
        email_log_id=email_log.id,
        status="sent",
    )
    return email_log, access, raw_code
