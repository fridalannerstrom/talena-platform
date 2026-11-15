"""Project creator completion notifications (#466).

The authenticated Sova ingest callback calls this after it marks an invitation
completed. Delivery is independent of the candidate result-sharing feature.
"""
import logging
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from apps.emails.models import EmailLog
from apps.processes.models import TestInvitation
from apps.processes.services.assessment_usage import (
    AssessmentUsage,
    classify_activity_status,
    classify_sova_activity,
)

logger = logging.getLogger(__name__)


def _has_observed_incomplete_assessments(invitation):
    """Do not send when Sova explicitly reports an assigned test unfinished.

    An overall completed status is authoritative if individual statuses are
    absent. Unknown/non-assessment activities are not treated as tests.
    """
    selected = set(invitation.process.selected_tests or [])
    for activity in invitation.sova_activities or []:
        if not isinstance(activity, dict):
            continue
        assessment = classify_sova_activity(
            activity.get("activity") or activity.get("name") or ""
        )
        if not assessment or (selected and assessment not in selected):
            continue
        status = classify_activity_status(activity.get("status"))
        if status == AssessmentUsage.Status.STARTED:
            return True
        raw = str(activity.get("status") or "").strip().lower().replace("_", " ")
        if raw in {"sent", "created", "pending", "not started", "incomplete", "invited"}:
            return True
    return False


def send_project_completion_email(invitation, *, base_url):
    """Send once per invitation/project, retrying only if previous send failed.

    A database row lock serialises concurrent duplicate callbacks. The SMTP
    operation and sent-at marker share one transaction, so concurrent callbacks
    cannot both decide to send. Delivery errors are retained in EmailLog and
    may be retried by a future completed callback.
    """
    with transaction.atomic():
        locked = (
            TestInvitation.objects.select_for_update()
            .select_related("process__created_by", "candidate")
            .get(pk=invitation.pk)
        )
        project = locked.process
        owner = project.created_by
        if (
            locked.status != "completed"
            or locked.removed_from_process_at is not None
            or project.is_historical
            or not project.project_completion_notifications_enabled
            or locked.project_completion_email_sent_at is not None
            or not owner.is_active
            or not owner.email
            or _has_observed_incomplete_assessments(locked)
        ):
            return None

        language = "en" if project.candidate_language == "en" else "sv"
        subject = (
            "Candidate has completed their tests"
            if language == "en"
            else "Kandidaten har slutfört sina tester"
        )
        candidate_name = str(locked.candidate)
        candidate_url = urljoin(
            base_url,
            reverse(
                "processes:process_candidate_detail",
                kwargs={
                    "process_id": project.pk,
                    "candidate_id": locked.candidate_id,
                },
            ),
        )
        context = {
            "language": language,
            "recipient_name": owner.first_name,
            "candidate_name": candidate_name,
            "project_name": project.name,
            "candidate_url": candidate_url,
            "logo_url": urljoin(base_url, static("images/talena-logo-v8.png")),
        }
        text_body = render_to_string("emails/project_completion.txt", context)
        html_body = render_to_string("emails/project_completion.html", context)
        email_log = EmailLog.objects.create(
            invitation=locked,
            template_type="project_completion",
            to_email=owner.email,
            subject=subject,
            body_snapshot=text_body,
            status="queued",
        )
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[owner.email],
        )
        message.attach_alternative(html_body, "text/html")
        try:
            if message.send() != 1:
                raise RuntimeError("Email backend did not accept the message")
        except Exception as exc:
            # Do not store raw exception details, which can contain PII.
            email_log.mark_failed(type(exc).__name__)
            logger.warning(
                "Project completion email failed for invitation %s (%s)",
                locked.pk,
                type(exc).__name__,
            )
            return email_log

        email_log.mark_sent()
        locked.project_completion_email_sent_at = timezone.now()
        locked.save(update_fields=["project_completion_email_sent_at"])
        return email_log
