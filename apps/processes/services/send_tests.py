# apps/processes/services/send_tests.py
import uuid
from django.conf import settings
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives

from apps.emails.models import EmailTemplate, EmailLog
from apps.emails.utils import render_placeholders  # justera import om din ligger annorlunda


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
            "language": "sv",
            "job_title": process.job_title or process.name,
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
            lang = "sv"
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

            subject_tpl = template.subject if template else "{process_name}: Ditt test"
            body_tpl = template.body if template else (
                "Hej {first_name}!\n\n"
                "Klicka på länken för att starta testet:\n"
                "{assessment_url}\n\n"
                "Vänliga hälsningar,\n"
                "Talena"
            )

            ctx = {
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "email": candidate.email,
                "process_name": process.name,
                "job_title": process.job_title,
                "job_location": process.job_location,
                "assessment_url": test_url,
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

            customer_user = process.created_by
            customer_display_name = (
                customer_user.get_full_name()
                or customer_user.first_name
                or customer_user.email
            )

            from_email = f"{customer_display_name} via Talena <no-reply@talena.se>"

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
            inv.status = "sent"
            inv.invited_at = timezone.now()
            inv.sova_payload = resp
            inv.request_id = request_id
            inv.assessment_url = test_url

            update_fields = ["status", "invited_at", "sova_payload", "request_id", "assessment_url"]

            # om du har fältet på modellen
            if hasattr(inv, "sova_project_id") and sova_project_id is not None:
                inv.sova_project_id = sova_project_id
                update_fields.append("sova_project_id")

            inv.save(update_fields=update_fields)

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
