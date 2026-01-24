from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from apps.processes.models import TestProcess
from .models import EmailTemplate
from .forms import EmailTemplateForm

from urllib.parse import urlparse
from django.http import HttpResponseRedirect


@login_required
def edit_process_invitation_template(request, process_id):
    process = get_object_or_404(TestProcess, pk=process_id, created_by=request.user)

    tpl, _ = EmailTemplate.objects.get_or_create(
        process=process,
        template_type="invitation",
        language="sv",
        defaults={
            "subject": "{process_name}: Ditt test för {job_title}",
            "body": (
                "Hej {first_name}!\n\n"
                "Klicka på länken för att starta testet:\n"
                "{assessment_url}\n\n"
                "Vänliga hälsningar,\n"
                "Talena"
            ),
        },
    )

    if request.method == "POST":
        form = EmailTemplateForm(request.POST, instance=tpl)
        if form.is_valid():
            form.save()
            messages.success(request, "Invitation email template updated.")
            return redirect("processes:process_detail", pk=process.id)
    else:
        form = EmailTemplateForm(instance=tpl)

    placeholders = [
        "{first_name}", "{last_name}", "{email}",
        "{process_name}", "{job_title}", "{job_location}",
        "{assessment_url}",
    ]

    return render(request, "emails/edit_invitation_template.html", {
        "process": process,
        "form": form,
        "placeholders": placeholders,
    })