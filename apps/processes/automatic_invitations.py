from __future__ import annotations

import logging
from collections import defaultdict
from contextvars import ContextVar
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.views.decorators.http import require_GET

from apps.accounts.utils.org_access import (
    get_company_for_user,
    user_can_edit_process,
)

from .models import TestInvitation, TestProcess
from .process_settings_models import ProcessAutomationSettings


logger = logging.getLogger(__name__)

_PROCESS_SETTING_OVERRIDE: ContextVar[bool | None] = ContextVar(
    "talena_process_automatic_invitation_setting_override",
    default=None,
)
_AUTO_INVITATION_ACTOR = ContextVar(
    "talena_automatic_invitation_actor",
    default=None,
)
_PENDING_INVITATION_IDS: ContextVar[list[int] | None] = ContextVar(
    "talena_pending_automatic_invitation_ids",
    default=None,
)
_AUTO_INVITATION_CONTEXT: ContextVar[str] = ContextVar(
    "talena_automatic_invitation_context",
    default="customer_auto",
)


def automatic_invitation_enabled(process: TestProcess) -> bool:
    """Return the saved process setting. Missing settings preserve legacy OFF behaviour."""

    try:
        settings_obj = process.automation_settings
    except ProcessAutomationSettings.DoesNotExist:
        return False

    return bool(settings_obj.automatic_invitation_enabled)


def set_automatic_invitation_enabled(process: TestProcess, enabled: bool) -> None:
    ProcessAutomationSettings.objects.update_or_create(
        process=process,
        defaults={
            "automatic_invitation_enabled": bool(enabled),
        },
    )


def capture_process_automatic_invitation_setting(view_func):
    """
    Capture the checkbox used by process creation/settings without coupling the
    large process views to this feature. The setting is persisted when the
    process itself is successfully saved.

    The UI sends a separate presence marker. If that marker is missing, the
    existing value is deliberately left untouched so a failed/missing JS asset
    can never silently turn an enabled setting off.
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.method != "POST":
            return view_func(request, *args, **kwargs)

        if "automatic_invitation_setting_present" not in request.POST:
            return view_func(request, *args, **kwargs)

        enabled = "automatic_invitation_enabled" in request.POST
        token = _PROCESS_SETTING_OVERRIDE.set(enabled)

        try:
            return view_func(request, *args, **kwargs)
        finally:
            _PROCESS_SETTING_OVERRIDE.reset(token)

    return wrapped


def capture_automatic_candidate_invitations(
    view_func=None,
    *,
    context: str = "customer_auto",
):
    """
    Collect newly created invited candidates during one add action and send
    their assessments after the view completes successfully.

    A list is used deliberately so a current or future multi-candidate add
    action follows exactly the same process setting and is sent as one batch.
    """

    def decorator(func):
        @wraps(func)
        def wrapped(request, *args, **kwargs):
            if request.method != "POST":
                return func(request, *args, **kwargs)

            actor_token = _AUTO_INVITATION_ACTOR.set(request.user)
            pending_token = _PENDING_INVITATION_IDS.set([])
            context_token = _AUTO_INVITATION_CONTEXT.set(context)

            try:
                response = func(request, *args, **kwargs)

                if getattr(response, "status_code", 500) < 400:
                    _flush_pending_automatic_invitations()

                return response
            finally:
                _AUTO_INVITATION_CONTEXT.reset(context_token)
                _PENDING_INVITATION_IDS.reset(pending_token)
                _AUTO_INVITATION_ACTOR.reset(actor_token)

        return wrapped

    if view_func is not None:
        return decorator(view_func)

    return decorator


def _flush_pending_automatic_invitations() -> None:
    invitation_ids = _PENDING_INVITATION_IDS.get() or []
    actor = _AUTO_INVITATION_ACTOR.get()

    if not invitation_ids or actor is None:
        return

    # Preserve creation order while removing accidental duplicates.
    unique_ids = list(dict.fromkeys(invitation_ids))

    invitations = list(
        TestInvitation.objects
        .filter(pk__in=unique_ids)
        .select_related("process", "candidate", "process__company")
        .order_by("pk")
    )

    grouped: dict[int, list[TestInvitation]] = defaultdict(list)
    processes = {}

    for invitation in invitations:
        process = invitation.process

        if invitation.source != "invited":
            continue

        if not automatic_invitation_enabled(process):
            continue

        grouped[process.pk].append(invitation)
        processes[process.pk] = process

    if not grouped:
        return

    # Import lazily so this feature does not create a circular dependency at
    # Django app startup and so tests can patch the existing send service.
    from apps.processes.services.send_tests import send_assessments_and_emails

    for process_id, process_invitations in grouped.items():
        process = processes[process_id]

        try:
            result = send_assessments_and_emails(
                process=process,
                invitations=process_invitations,
                actor_user=actor,
                context=_AUTO_INVITATION_CONTEXT.get(),
            )
        except Exception:
            # Candidate creation must not be rolled back because an external
            # invitation provider is unavailable. The normal manual retry path
            # remains available to the user.
            logger.exception(
                "Automatic invitation sending failed for process %s",
                process_id,
            )
            continue

        if result.get("errors"):
            logger.warning(
                "Automatic invitation completed with errors for process %s: %s",
                process_id,
                result.get("errors"),
            )


@receiver(post_save, sender=TestProcess)
def _persist_process_automatic_invitation_setting(
    sender,
    instance: TestProcess,
    **kwargs,
):
    enabled = _PROCESS_SETTING_OVERRIDE.get()

    if enabled is None:
        return

    set_automatic_invitation_enabled(instance, enabled)


@receiver(post_save, sender=TestInvitation)
def _queue_new_automatic_invitation(
    sender,
    instance: TestInvitation,
    created: bool,
    **kwargs,
):
    if not created or instance.source != "invited":
        return

    actor = _AUTO_INVITATION_ACTOR.get()
    pending = _PENDING_INVITATION_IDS.get()

    if actor is None or pending is None:
        return

    if not automatic_invitation_enabled(instance.process):
        return

    pending.append(instance.pk)


@login_required
@require_GET
def process_automatic_invitation_setting(request, pk):
    """Small read endpoint used to initialise the process Settings toggle."""

    process = get_object_or_404(TestProcess, pk=pk)
    company = get_company_for_user(request.user)

    if (
        not company
        or process.company_id != company.id
        or not user_can_edit_process(request.user, company, process)
    ):
        return HttpResponseForbidden("No access.")

    return JsonResponse(
        {
            "enabled": automatic_invitation_enabled(process),
        }
    )
