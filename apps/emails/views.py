from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from apps.processes.models import TestProcess
from .models import EmailTemplate
from .forms import EmailTemplateForm

from urllib.parse import urlparse
from django.http import HttpResponseRedirect

from apps.accounts.decorators import admin_required
from apps.accounts.models import Company


@login_required
def edit_process_invitation_template(request, process_id):
    process = get_object_or_404(
        TestProcess,
        pk=process_id,
        created_by=request.user,
    )

    tpl, _ = EmailTemplate.objects.get_or_create(
        process=process,
        template_type="invitation",
        language="sv",
        defaults=get_default_invitation_template(),
    )

    if request.method == "POST":
        form = EmailTemplateForm(request.POST, instance=tpl)
        if form.is_valid():
            form.save()
            messages.success(request, "Invitation email template updated.")
            return redirect("processes:process_detail", pk=process.id)
    else:
        form = EmailTemplateForm(instance=tpl)

    return render(request, "emails/edit_invitation_template.html", {
        "process": process,
        "form": form,
        "placeholders": get_email_template_placeholders(),
    })

def get_default_invitation_template():
    return {
        "subject": "Invitation to assessment process",
        "body": (
            "Hi {first_name},\n\n"
            "You have been invited to complete assessments for {process_name}.\n\n"
            "Click the link below to start:\n"
            "{assessment_url}\n\n"
            "Best regards,\n"
            "{sender_full_name}"
        ),
    }


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

    tpl, _ = EmailTemplate.objects.get_or_create(
        process=process,
        template_type="invitation",
        language="sv",
        defaults=get_default_invitation_template(),
    )

    if request.method == "POST":
        form = EmailTemplateForm(request.POST, instance=tpl)

        if form.is_valid():
            form.save()
            messages.success(request, "Invitation email template updated.")
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