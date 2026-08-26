# apps/processes/services/send_tests.py
import uuid
from django.conf import settings
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives

from apps.emails.models import EmailTemplate, EmailLog
from apps.emails.utils import (
    render_placeholders,
    get_default_invitation_template,
    format_assessment_names,
)
from apps.activity.models import ActivityEvent
from apps.activity.services import log_event

from apps.processes.services.assessment_usage import (
    register_sent_assessments,
)


def send_assessments_and_emails(*, process, invitations, actor_user, context="customer"):
    """
    Order assessments in SOVA and email the candidate.

    The flow is deliberately retry-safe:
    - As soon as SOVA returns an assessment URL, the SOVA order is persisted.
    - Assessment usage is registered at order time (the helper is idempotent).
    - If email delivery fails, the invitation becomes ``failed`` but keeps the
      existing SOVA URL/request id.
    - A later retry reuses that existing SOVA order instead of creating a
      duplicate assessment.

    Used by both customer and admin flows.
    ``context`` is stored in activity metadata.
    """
    from apps.core.integrations.sova import SovaClient

    client = SovaClient()

    sent_count = 0
    skipped_count = 0

    # Resolve the SOVA project id once when available. Failure here must not
    # prevent ordering because the project code is still sufficient for SOVA.
    sova_project_id = None
    try:
        accounts = client.get_accounts_with_projects()
        for account in accounts:
            if (account.get("code") or "").strip() != (process.account_code or "").strip():
                continue

            for project in account.get("projects") or []:
                if (project.get("code") or "").strip() == (process.project_code or "").strip():
                    sova_project_id = project.get("id")
                    break
            break
    except Exception:
        sova_project_id = None

    for inv in invitations:
        candidate = inv.candidate

        lang = (
            getattr(process, "candidate_language", "sv")
            or "sv"
        ).strip().lower()

        if lang not in {"sv", "en"}:
            lang = "sv"

        if inv.status in ("sent", "started", "completed"):
            skipped_count += 1
            continue

        try:
            # ---------------------------------------------------------
            # 1. Reuse an already-created SOVA order when possible.
            # ---------------------------------------------------------
            # The assessment URL is our strongest signal that SOVA already
            # accepted the order. This is especially important after an email
            # failure: retrying must never create another SOVA assessment.
            existing_test_url = (getattr(inv, "assessment_url", None) or "").strip()

            if existing_test_url:
                test_url = existing_test_url
                request_id = (
                    getattr(inv, "request_id", None)
                    or getattr(inv, "sova_request_id", None)
                    or f"talena-{process.id}-{candidate.id}-{uuid.uuid4().hex}"
                )
                resp = getattr(inv, "sova_payload", None) or {}

                reuse_update_fields = []

                if not getattr(inv, "request_id", None):
                    inv.request_id = request_id
                    reuse_update_fields.append("request_id")

                if (
                    hasattr(inv, "sova_project_id")
                    and getattr(inv, "sova_project_id", None) is None
                    and sova_project_id is not None
                ):
                    inv.sova_project_id = sova_project_id
                    reuse_update_fields.append("sova_project_id")

                if reuse_update_fields:
                    inv.save(update_fields=reuse_update_fields)

                usage_sent_at = (
                    getattr(inv, "invited_at", None)
                    or timezone.now()
                )

            else:
                request_id = f"talena-{process.id}-{candidate.id}-{uuid.uuid4().hex}"

                payload = {
                    "request_id": request_id,
                    "candidate_id": str(candidate.id),
                    "first_name": candidate.first_name,
                    "last_name": candidate.last_name,
                    "email": candidate.email,
                    "language": lang,
                    "job_title": process.job_title or "Assessment",
                    "job_number": f"talena-{process.id}",
                    "meta_data": {
                        "talena_process_id": str(process.id),
                        "talena_candidate_id": str(candidate.id),
                        "talena_user_id": str(actor_user.id),
                        "talena_request_id": request_id,
                        "talena_context": context,
                    },
                }

                resp = client.order_assessment(process.project_code, payload)
                test_url = (resp or {}).get("url")

                if not test_url:
                    raise ValueError("SOVA returned no assessment URL")

                # Persist the successful SOVA order BEFORE email delivery.
                # If email fails, a retry can safely reuse this exact order.
                inv.sova_payload = resp
                inv.request_id = request_id
                inv.assessment_url = test_url

                order_update_fields = [
                    "sova_payload",
                    "request_id",
                    "assessment_url",
                ]

                if (
                    hasattr(inv, "sova_project_id")
                    and sova_project_id is not None
                ):
                    inv.sova_project_id = sova_project_id
                    order_update_fields.append("sova_project_id")

                inv.save(update_fields=order_update_fields)
                usage_sent_at = timezone.now()

            # A SOVA order is billable/trackable even if the invitation email
            # subsequently fails. This helper is safe to call repeatedly.
            register_sent_assessments(
                invitation=inv,
                sent_by=actor_user,
                sent_at=usage_sent_at,
                sova_request_id=request_id,
            )

            # ---------------------------------------------------------
            # 2. Build and send invitation email.
            # ---------------------------------------------------------
            template = (
                EmailTemplate.objects
                .filter(
                    process=process,
                    template_type="invitation",
                    language=lang,
                    is_active=True,
                )
                .first()
            )

            default_template = get_default_invitation_template(lang)

            subject_tpl = (
                template.subject
                if template
                else default_template["subject"]
            )

            body_tpl = (
                template.body
                if template
                else default_template["body"]
            )

            sender_full_name = (
                actor_user.get_full_name().strip()
                or actor_user.first_name
                or actor_user.email
            )

            ctx = {
                "first_name": candidate.first_name or "",
                "last_name": candidate.last_name or "",
                "email": candidate.email or "",
                "process_name": process.name or "",
                "assessments": format_assessment_names(process.selected_tests),
                "job_title": process.job_title or "",
                "job_location": process.job_location or "",
                "assessment_url": test_url or "",
                "sender_first_name": actor_user.first_name or "",
                "sender_last_name": actor_user.last_name or "",
                "sender_full_name": sender_full_name,
            }

            subject = render_placeholders(subject_tpl, ctx)
            body = render_placeholders(body_tpl, ctx)

            email_log = EmailLog.objects.create(
                invitation=inv,
                template_type="invitation",
                to_email=candidate.email,
                subject=subject,
                body_snapshot=body,
                status="queued",
            )

            msg = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[candidate.email],
                reply_to=[actor_user.email],
            )

            try:
                msg.send()
                email_log.mark_sent()
            except Exception as exc:
                email_log.mark_failed(str(exc))
                raise

            # ---------------------------------------------------------
            # 3. Mark the Talena invitation as sent only after email.
            # ---------------------------------------------------------
            sent_at = timezone.now()

            inv.status = "sent"
            inv.invited_at = sent_at
            inv.invited_by = actor_user
            inv.save(
                update_fields=[
                    "status",
                    "invited_at",
                    "invited_by",
                ]
            )

            # Logging is useful but must never turn a successfully delivered
            # assessment into a failed/retryable invitation.
            try:
                log_event(
                    company=process.company,
                    verb=ActivityEvent.Verb.INVITE_SENT,
                    actor=actor_user,
                    process=process,
                    candidate=inv.candidate,
                    invitation=inv,
                    meta={
                        "context": context,
                        "email_log_id": email_log.id,
                    },
                )
            except Exception:
                pass

            sent_count += 1

        except Exception as exc:
            # Keep the persisted SOVA order, but expose that delivery failed.
            # A later retry will reuse assessment_url/request_id above.
            if inv.status not in ("sent", "started", "completed"):
                try:
                    inv.status = "failed"
                    inv.save(update_fields=["status"])
                except Exception:
                    pass

            inv._send_error = str(exc)

    return {
        "sent_count": sent_count,
        "skipped_count": skipped_count,
        "errors": [
            {
                "invitation_id": inv.id,
                "email": inv.candidate.email,
                "error": getattr(inv, "_send_error", None),
            }
            for inv in invitations
            if getattr(inv, "_send_error", None)
        ],
    }
