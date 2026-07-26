from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils.translation import override

from apps.processes.models import TestProcess
from .models import EmailTemplate
from .forms import EmailTemplateForm

from urllib.parse import urlparse
from django.http import HttpResponseRedirect

from apps.accounts.decorators import admin_required
from apps.accounts.models import Company

from django.http import HttpResponseForbidden
from apps.projects.models import ProjectMeta
from apps.processes.services.process_recommendations import PROCESS_PURPOSES
from apps.accounts.utils.org_access import get_company_for_user
from apps.accounts.utils.org_access import user_can_edit_process

from apps.processes.purpose_context_config import get_purpose_context_config


# Talena invitation email template i18n batch 1
LEGACY_DEFAULT_INVITATION_TEMPLATES = (
    {
        "subject": "Invitation to assessment process",
        "body": (
            "Hi {first_name},\n\n"
            "You have been invited to complete assessments for "
            "{process_name}.\n\n"
            "Click the link below to start:\n"
            "{assessment_url}\n\n"
            "Best regards,\n"
            "{sender_full_name}"
        ),
    },
    {
        "subject": "Inbjudan till testprocess",
        "body": (
            "Hej {first_name},\n\n"
            "Du har blivit inbjuden att genomföra tester för "
            "{process_name}.\n\n"
            "Klicka på länken nedan för att börja:\n"
            "{assessment_url}\n\n"
            "Vänliga hälsningar,\n"
            "{sender_full_name}"
        ),
    },
)

def get_default_invitation_template(
    language_code="sv",
):
    with override(language_code):
        return {
            "subject": _(
                "Invitation to assessment process"
            ),
            "body": _(
                "Hi {first_name},\n\n"
                "You have been invited to complete assessments.\n\n"
                "Click the link below to start:\n"
                "{assessment_url}\n\n"
                "Best regards,\n"
                "{sender_full_name}"
            ),
        }


def upgrade_legacy_default_invitation_template(
    template,
):
    is_legacy_default = any(
        template.subject == legacy["subject"]
        and template.body == legacy["body"]
        for legacy in LEGACY_DEFAULT_INVITATION_TEMPLATES
    )

    if not is_legacy_default:
        return False

    defaults = get_default_invitation_template(
        template.language or "sv"
    )

    template.subject = defaults["subject"]
    template.body = defaults["body"]

    template.save(
        update_fields=[
            "subject",
            "body",
            "updated_at",
        ]
    )

    return True


@login_required
def edit_process_invitation_template(request, process_id):
    process = get_object_or_404(
        TestProcess.objects.select_related("company", "created_by", "org_unit"),
        pk=process_id,
    )

    company = get_company_for_user(request.user)

    if not company or process.company_id != company.id:
        return HttpResponseForbidden(
            _("No access.")
        )

    if not user_can_edit_process(request.user, company, process):
        return HttpResponseForbidden(
            _(
                "You do not have permission to edit "
                "this email template."
            )
        )

    tpl, _created = EmailTemplate.objects.get_or_create(
        process=process,
        template_type="invitation",
        language="sv",
        defaults=get_default_invitation_template(
            "sv"
        ),
    )

    if not _created:
        upgrade_legacy_default_invitation_template(
            tpl
        )

    if request.method == "POST":
        form = EmailTemplateForm(request.POST, instance=tpl)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                _("Invitation email template updated."),
            )

            # Stanna kvar i samma tab efter save
            return redirect("emails:edit_process_invitation_template", process_id=process.id)
    else:
        form = EmailTemplateForm(instance=tpl)

    purpose_lookup = {
        item["key"]: item
        for item in PROCESS_PURPOSES
    }

    process_purpose = purpose_lookup.get(process.purpose)

    meta = ProjectMeta.objects.filter(
        provider="sova",
        account_code=process.account_code,
        project_code=process.project_code,
    ).first()

    context_config = get_purpose_context_config(process.purpose)

    return render(request, "emails/edit_invitation_template.html", {
        "process": process,
        "form": form,
        "placeholders": get_email_template_placeholders(),

        # Needed by process_base / _process_header.html
        "active": "email_templates",
        "meta": meta,
        "can_edit": True,
        "process_purpose": process_purpose,
        "self_reg_url": request.build_absolute_uri(process.get_self_registration_url()),
        "context_config": context_config,
    })

def get_email_template_placeholders():
    return [
        "{first_name}",
        "{last_name}",
        "{email}",
        "{process_name}",
        "{assessment_url}",
        "{sender_first_name}",
        "{sender_last_name}",
        "{sender_full_name}",
    ]

@login_required
@admin_required
def admin_edit_company_process_invitation_template(request, company_pk, process_pk):
    company = get_object_or_404(Company, pk=company_pk)

    process = get_object_or_404(
        TestProcess.objects.select_related("company", "created_by", "org_unit"),
        pk=process_pk,
        company=company,
    )

    tpl, _created = EmailTemplate.objects.get_or_create(
        process=process,
        template_type="invitation",
        language="sv",
        defaults=get_default_invitation_template(
            "sv"
        ),
    )

    if not _created:
        upgrade_legacy_default_invitation_template(
            tpl
        )

    if request.method == "POST":
        form = EmailTemplateForm(request.POST, instance=tpl)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                _("Invitation email template updated."),
            )
            return redirect(
                "accounts:company_process_detail",
                company_pk=company.pk,
                process_pk=process.pk,
            )
    else:
        form = EmailTemplateForm(instance=tpl)

    return render(request, "emails/admin_edit_invitation_template.html", {
        "company": company,
        "process": process,
        "form": form,
        "placeholders": get_email_template_placeholders(),
        "active": "processes",
        "show_invite_button": True,
    })