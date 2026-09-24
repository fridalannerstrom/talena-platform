from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core.utils.auth import is_admin
from apps.processes.models import PinnedProject
from apps.processes.services.access import get_accessible_processes_for_user

MAX_PINNED_PROJECTS = 5


def pinned_projects(request):
    """Expose only the current user's accessible, active shortcuts."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or is_admin(user):
        return {"pinned_projects": (), "pinned_project_ids": ()}

    accessible, _ = get_accessible_processes_for_user(user)
    pins = list(
        PinnedProject.objects
        .filter(user=user, process__in=accessible)
        .select_related("process")
        .order_by("-created_at", "-pk")[:MAX_PINNED_PROJECTS]
    )
    return {
        "pinned_projects": [pin.process for pin in pins],
        "pinned_project_ids": [pin.process_id for pin in pins],
    }


@login_required
@require_POST
def toggle_pinned_project(request, pk):
    accessible, _ = get_accessible_processes_for_user(request.user)
    process = get_object_or_404(accessible, pk=pk)

    # Lock per user so simultaneous tabs cannot exceed the shortcut limit.
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        existing = PinnedProject.objects.filter(user=request.user, process=process)
        if existing.exists():
            existing.delete()
        elif PinnedProject.objects.filter(user=request.user).count() >= MAX_PINNED_PROJECTS:
            messages.warning(request, _("You can pin up to five projects. Unpin one first."))
        else:
            PinnedProject.objects.create(user=request.user, process=process)

    fallback = reverse("processes:process_list")
    next_url = request.POST.get("next", "")
    if not next_url.startswith("/") or not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = fallback
    return redirect(next_url)
