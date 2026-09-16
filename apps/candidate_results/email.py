from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone

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
                "Hej {first_name}!\n\n"
                "Tack för att du har genomfört assessmenten i "
                "{process_name}.\n\n"
                "Ditt resultat är ett reflektionsunderlag inför den "
                "fortsatta dialogen. Det beskriver möjliga preferenser "
                "och tendenser, inte ett betyg eller en absolut sanning.\n\n"
                "Visa ditt resultat här:\n{result_url}\n\n"
                "Din personliga verifieringskod är:\n{verification_code}\n\n"
                "Vänliga hälsningar,\nTalena"
            ),
        }
    return {
        "subject": "Your Talena assessment result",
        "body": (
            "Hi {first_name}!\n\n"
            "Thank you for completing the assessment in "
            "{process_name}.\n\n"
            "Your result is a basis for reflection and further "
            "conversation. It describes possible preferences and "
            "tendencies, not a grade or an absolute truth.\n\n"
            "View your result here:\n{result_url}\n\n"
            "Your personal verification code is:\n{verification_code}\n\n"
            "Best regards,\nTalena"
        ),
    }


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

    if access and replace_code:
        raw_token, raw_code = rotate_candidate_result_access(access)
    elif access:
        raise ValueError(
            "An active candidate result access record already exists; "
            "use replace_code=True to resend safely."
        )
    else:
        access, raw_token, raw_code = create_candidate_result_access(snapshot)

    copy = _copy(locale)
    subject = copy["subject"]
    body = copy["body"].format(
        first_name=invitation.candidate.first_name or "",
        process_name=invitation.process.name or "Talena",
        result_url=_result_url(raw_token, base_url),
        verification_code=raw_code,
    )

    from apps.emails.models import EmailLog

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
