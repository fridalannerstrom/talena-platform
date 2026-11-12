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
                _("You do not have access to this project.")
            )

        company = get_company_for_user(request.user)
        if not company or process.company_id != company.id:
            return HttpResponseForbidden(
                _("You do not have access to this project.")
            )

        if not user_can_view_process(request.user, company, process):
            return HttpResponseForbidden(
                _("You do not have access to this project.")
            )

        return view_func(request, *args, **kwargs)

    return wrapped


def process_edit_access_required(view_func):
    """
    Guard process-changing endpoints.

    Editor can edit shared processes. Own can edit only processes created by
    that user. Viewer is read-only.

    The delete view separately handles assessment and billing protection.
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        process = _get_process_from_kwargs(kwargs)
        if process is None:
            return HttpResponseForbidden(
                _("You do not have permission to edit this project.")
            )

        # Keep tenant/Editor/Own checks here. The view performs the final
        # deletion safety check and returns the user to the project list with
        # feedback instead of exposing a plain HTTP 403 page.

        if is_admin(request.user):
            return view_func(request, *args, **kwargs)

        company = get_company_for_user(request.user)
        if not company or process.company_id != company.id:
            return HttpResponseForbidden(
                _("You do not have permission to edit this project.")
            )

        if not user_can_edit_process(request.user, company, process):
            return HttpResponseForbidden(
                _("You do not have permission to edit this project.")
            )

        return view_func(request, *args, **kwargs)

    return wrapped


def active_candidate_membership_required(view_func):
    """Block direct customer candidate/AI URLs after project soft-removal.

    History remains available internally for lawful billing and provider
    reconciliation, not through the active project candidate endpoints.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        candidate_id = kwargs.get("candidate_id")
        process = _get_process_from_kwargs(kwargs)
        if candidate_id is not None and process is not None and not process.is_historical:
            from django.http import Http404
            from apps.processes.models import TestInvitation

            if not TestInvitation.objects.filter(
                process=process,
                candidate_id=candidate_id,
                removed_from_process_at__isnull=True,
            ).exists():
                raise Http404("Candidate not active in project")
        return view_func(request, *args, **kwargs)

    return wrapped
