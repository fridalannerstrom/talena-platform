from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from apps.accounts.utils.org_access import (
    get_company_for_user,
    user_can_edit_process,
    user_can_view_process,
)
from apps.core.utils.auth import is_admin
from apps.processes.models import TestProcess
from apps.processes.services.process_locking import can_delete_process_safely


def _get_process_from_kwargs(kwargs):
    process_id = kwargs.get("process_id") or kwargs.get("pk")
    if process_id is None:
        return None
    return get_object_or_404(TestProcess, pk=process_id)


def process_view_access_required(view_func):
    """
    Guard process/candidate endpoints with the same Viewer/Editor/Own rules
    used by process lists and process detail pages.

    Talena admins keep global access. Customer users must belong to the
    process company and have effective access to the process org unit.
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if is_admin(request.user):
            return view_func(request, *args, **kwargs)

        process = _get_process_from_kwargs(kwargs)
        if process is None:
            return HttpResponseForbidden(
                _("You do not have access to this process.")
            )

        company = get_company_for_user(request.user)
        if not company or process.company_id != company.id:
            return HttpResponseForbidden(
                _("You do not have access to this process.")
            )

        if not user_can_view_process(request.user, company, process):
            return HttpResponseForbidden(
                _("You do not have access to this process.")
            )

        return view_func(request, *args, **kwargs)

    return wrapped


def process_edit_access_required(view_func):
    """
    Guard process-changing endpoints.

    Editor can edit shared processes. Own can edit only processes created by
    that user. Viewer is read-only.

    Deletion has an additional data-integrity guard: a process with an already
    ordered SOVA assessment must not be deleted, even when invitation email
    delivery failed and the invitation currently has status ``failed``.
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        process = _get_process_from_kwargs(kwargs)
        if process is None:
            return HttpResponseForbidden(
                _("You do not have permission to edit this process.")
            )

        if (
            view_func.__name__ == "process_delete"
            and not can_delete_process_safely(process)
        ):
            return HttpResponseForbidden(
                _(
                    "This process cannot be deleted after assessments "
                    "have been ordered."
                )
            )

        if is_admin(request.user):
            return view_func(request, *args, **kwargs)

        company = get_company_for_user(request.user)
        if not company or process.company_id != company.id:
            return HttpResponseForbidden(
                _("You do not have permission to edit this process.")
            )

        if not user_can_edit_process(request.user, company, process):
            return HttpResponseForbidden(
                _("You do not have permission to edit this process.")
            )

        return view_func(request, *args, **kwargs)

    return wrapped
