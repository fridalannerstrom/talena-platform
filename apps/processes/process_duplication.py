"""Duplicate project settings without copying candidates or orders (ticket #328).

Sova account_code/project_code refer to shared assessment templates. The unique
Sova order/project IDs belong to invitations and are never copied here.
"""
from copy import deepcopy

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import get_language
from django.views.decorators.http import require_http_methods

from apps.accounts.models import CompanyMember
from apps.accounts.utils.org_access import user_can_edit_process
from apps.activity.models import ActivityEvent
from apps.activity.services import log_event

from .models import ProcessRoleContext, TestProcess
from .process_settings_models import ProcessAutomationSettings



def localize(sv, en):
    return sv if (get_language() or "").startswith("sv") else en


class DuplicateProcessForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        strip=True,
        widget=forms.TextInput(attrs={"class": "form-control", "autofocus": "autofocus"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].label = localize("Namn på kopian", "Name of the copy")


def has_saved_sova_template(source):
    """Ensure a reusable shared Sova template is configured locally.

    Talena reuses Sova's project *code* for new assessment orders. Looking up
    Sova here is unnecessary and would stop otherwise-valid duplication when
    local credentials or Sova's API are unavailable. No unique Sova project or
    assessment-order ID is stored on TestProcess or copied.
    """
    return bool(
        (source.account_code or "").strip()
        and (source.project_code or "").strip()
    )


def copy_process_settings(source, *, name, created_by):
    """Explicitly allowlist project settings. No candidate-linked objects."""
    with transaction.atomic():
        duplicate = TestProcess.objects.create(
            name=name,
            provider="sova",
            company=source.company,
            org_unit=source.org_unit,
            account_code=source.account_code,
            project_code=source.project_code,  # shared template, not unique order ID
            project_name_snapshot=source.project_name_snapshot,
            job_title=source.job_title,
            job_location=source.job_location,
            notes=source.notes,
            purpose=source.purpose,
            selected_tests=deepcopy(source.selected_tests),
            candidate_language=source.candidate_language,
            candidate_results_enabled=source.candidate_results_enabled,
            created_by=created_by,
            source="talena",
            sova_sync_enabled=source.sova_sync_enabled,
            sova_account_name=source.sova_account_name,
            sova_project_name=source.sova_project_name,
            # New UUID token, active state, creator and timestamps use defaults.
        )
        duplicate.labels.set(source.labels.filter(company=source.company))

        try:
            context = source.role_context
        except ProcessRoleContext.DoesNotExist:
            context = None

        if context is not None:
            ProcessRoleContext.objects.create(
                process=duplicate,
                context_text=context.context_text,
                role_title=context.role_title,
                job_advertisement=context.job_advertisement,
                requirements_profile=context.requirements_profile,
                competency_profile=context.competency_profile,
                must_haves=context.must_haves,
                nice_to_haves=context.nice_to_haves,
                priorities=context.priorities,
                purpose_data=deepcopy(context.purpose_data),
                # Do not copy the legacy interview_notes field.
            )

        try:
            automation = source.automation_settings
        except ProcessAutomationSettings.DoesNotExist:
            automation = None

        if automation is not None:
            ProcessAutomationSettings.objects.create(
                process=duplicate,
                automatic_invitation_enabled=automation.automatic_invitation_enabled,
            )

        log_event(
            company=source.company,
            verb=ActivityEvent.Verb.PROCESS_CREATED,
            actor=created_by,
            process=duplicate,
            meta={
                "process_name": duplicate.name,
                "duplicated_from_process_id": source.pk,
                "selected_tests": duplicate.selected_tests,
                "sova_template": {
                    "account_code": duplicate.account_code,
                    "project_code": duplicate.project_code,
                },
            },
        )
    return duplicate


@login_required
@require_http_methods(["GET", "POST"])
def process_duplicate(request, pk):
    source = get_object_or_404(
        TestProcess.objects.select_related("company", "org_unit").prefetch_related("labels"),
        pk=pk, is_historical=False, source="talena", provider="sova",
    )
    # Access check applies to GET and POST, even if a URL is guessed.
    if (
        not source.company_id
        or not CompanyMember.objects.filter(
            company_id=source.company_id, user=request.user,
        ).exists()
        or not user_can_edit_process(request.user, source.company, source)
    ):
        return HttpResponseForbidden(
            localize("Du får inte duplicera detta projekt.", "You cannot duplicate this project.")
        )

    if not source.org_unit_id or source.org_unit.company_id != source.company_id:
        messages.error(request, localize(
            "Projektet saknar ett giltigt konto och kan inte dupliceras.",
            "The project has no valid account and cannot be duplicated.",
        ))
        return redirect("processes:process_list")

    suggested_name = localize(f"{source.name} (kopia)", f"{source.name} (copy)")
    form = DuplicateProcessForm(
        request.POST if request.method == "POST" else None,
        initial={"name": suggested_name},
    )
    if request.method == "POST" and form.is_valid():
        if not has_saved_sova_template(source):
            form.add_error(None, localize(
                "Projektet saknar en sparad Sova-mall och kan inte dupliceras.",
                "This project has no saved Sova template and cannot be duplicated.",
            ))
        else:
            duplicate = copy_process_settings(
                source, name=form.cleaned_data["name"], created_by=request.user,
            )
            messages.success(request, localize(
                "Projektet har duplicerats utan kandidater.",
                "Project duplicated without candidates.",
            ))
            return redirect("processes:process_detail", pk=duplicate.pk)
    return render(
        request, "customer/processes/process_duplicate.html",
        {"form": form, "source": source},
    )
