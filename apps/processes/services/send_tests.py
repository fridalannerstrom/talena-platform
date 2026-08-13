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
    Skickar tester i SOVA + mailar kandidaten med samma mall som kundflödet.
    Används av både kund och admin.

    context: "customer" eller "admin" (sparas i meta_data).
    """
    from apps.core.integrations.sova import SovaClient  # justera import
    client = SovaClient()

    sent_count = 0
    skipped_count = 0

    # (Valfritt) project_id lookup en gång (om du använder inv.sova_project_id)
    sova_project_id = None
    try:
        accounts = client.get_accounts_with_projects()
        for a in accounts:
            if (a.get("code") or "").strip() == (process.account_code or "").strip():
                for p in (a.get("projects") or []):
                    if (p.get("code") or "").strip() == (process.project_code or "").strip():
                        sova_project_id = p.get("id")
                        break
                break
    except Exception:
        sova_project_id = None

    for inv in invitations:
        candidate = inv.candidate

        lang = (
            getattr(
                process,
                "candidate_language",
                "sv",
            )
            or "sv"
        ).strip().lower()

        if lang not in {"sv", "en"}:
            lang = "sv"

        if inv.status in ("sent", "started", "completed"):
            skipped_count += 1
            continue

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

        try:
            resp = client.order_assessment(process.project_code, payload)
            test_url = (resp or {}).get("url")

            if not test_url:
                # du kan välja att fortsätta utan mail här, men det är bättre att faila tydligt
                raise ValueError("SOVA returnerade ingen url")

            # --- Email template (samma som kund) ---
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

            default_template = (
                get_default_invitation_template(lang)
            )

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

            sender_full_name = actor_user.get_full_name().strip() or actor_user.first_name or actor_user.email

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

            customer_user = actor_user
            customer_display_name = (
                customer_user.get_full_name().strip()
                or customer_user.first_name
                or customer_user.email
            )

            from_email = settings.DEFAULT_FROM_EMAIL

            msg = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[candidate.email],
                reply_to=[customer_user.email],
            )

            try:
                msg.send()
                email_log.mark_sent()
            except Exception as e:
                email_log.mark_failed(str(e))
                raise
            
            # --- Update invitation ---

            sent_at = timezone.now()

            inv.status = "sent"
            inv.invited_at = sent_at
            inv.invited_by = actor_user
            inv.sova_payload = resp
            inv.request_id = request_id
            inv.assessment_url = test_url

            update_fields = [
                "status",
                "invited_at",
                "invited_by",
                "sova_payload",
                "request_id",
                "assessment_url",
            ]

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
                }
            )

            # om du har fältet på modellen
            if hasattr(inv, "sova_project_id") and sova_project_id is not None:
                inv.sova_project_id = sova_project_id
                update_fields.append("sova_project_id")

            inv.save(update_fields=update_fields)

            register_sent_assessments(
                invitation=inv,
                sent_by=actor_user,
                sent_at=sent_at,
                sova_request_id=request_id,
            )

            sent_count += 1

        except Exception as e:
            # Låt viewn hantera messages per kandidat om du vill,
            # men här returnerar vi fel-lista istället (enklare att återanvända).
            # Vi lägger felet på invitation-objektet temporärt:
            inv._send_error = str(e)

    return {
        "sent_count": sent_count,
        "skipped_count": skipped_count,
        "errors": [
            {"invitation_id": inv.id, "email": inv.candidate.email, "error": getattr(inv, "_send_error", None)}
            for inv in invitations
            if getattr(inv, "_send_error", None)
        ]
    }
