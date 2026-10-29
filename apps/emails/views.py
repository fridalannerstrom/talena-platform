from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils.translation import gettext as _

from apps.processes.models import TestProcess
from .models import EmailTemplate, CompanyInvitationTemplate
from .forms import EmailTemplateForm, CompanyInvitationTemplateForm
from .utils import (
    get_default_invitation_template,
    upgrade_legacy_default_invitation_template,
    INVITATION_PLACEHOLDERS,
    render_placeholders,
)

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

    language = (
        process.candidate_language
        or "sv"
    )

    tpl, _created = EmailTemplate.objects.get_or_create(
        process=process,
        template_type="invitation",
        language=language,
        defaults=get_default_invitation_template(
            language
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
        "{company_name}",
        "{job_title}",
        "{job_location}",
        "{process_name}",
        "{assessments}",
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

    language = (
        process.candidate_language
        or "sv"
    )

    tpl, _created = EmailTemplate.objects.get_or_create(
        process=process,
        template_type="invitation",
        language=language,
        defaults=get_default_invitation_template(
            language
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


@login_required
@admin_required
def admin_edit_company_invitation_template(request, company_pk):
    """Company-wide default for new invitations, administered only by TQ admins."""
    company = get_object_or_404(Company, pk=company_pk)
    language = request.GET.get("language", "sv")
    if language not in {"sv", "en"}:
        language = "sv"

    template = CompanyInvitationTemplate.objects.filter(
        company=company, language=language,
    ).first()

    if request.method == "POST":
        form = CompanyInvitationTemplateForm(request.POST, instance=template)
        if form.is_valid():
            saved = form.save(commit=False)
            saved.company = company
            saved.language = language
            saved.save()
            messages.success(request, _("Company invitation template saved."))
            return HttpResponseRedirect(f"{request.path}?language={language}")
    else:
        initial = get_default_invitation_template(language)
        form = CompanyInvitationTemplateForm(
            instance=template,
            initial=initial if template is None else None,
        )

    example = {
        "first_name": "Anna",
        "last_name": "Example",
        "email": "anna@example.test",
        "company_name": company.name,
        "process_name": "Sample recruitment process",
        "assessments": "Personality, Logical Reasoning",
        "assessment_url": "https://example.test/assessment",
        "job_title": "Example role",
        "job_location": "Stockholm",
        "sender_first_name": "Talena",
        "sender_last_name": "Admin",
        "sender_full_name": "Talena Admin",
    }

    return render(request, "emails/admin_edit_company_invitation_template.html", {
        "company": company,
        "form": form,
        "template_saved": template is not None,
        "language": language,
        "placeholders": ["{" + key + "}" for key in INVITATION_PLACEHOLDERS],
        "preview_values": example,
        "initial_preview_subject": render_placeholders(form["subject"].value() or "", example),
        "initial_preview_body": render_placeholders(form["body"].value() or "", example),
        "active": "email_templates",
        "show_invite_button": False,
    })
