"""Talena platform-admin controls for a user's global interface language."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required


@login_required
@admin_required
@require_POST
def set_user_language(request, user_pk):
    """Only Talena administrators may update other users' UI preference."""
    target_user = get_object_or_404(get_user_model(), pk=user_pk)
    language = request.POST.get("preferred_language")

    if language not in ("", "sv", "en"):
        return HttpResponseBadRequest("Invalid language")

    if target_user.preferred_language != language:
        target_user.preferred_language = language
        target_user.save(update_fields=["preferred_language"])
        messages.success(request, "Användarens språk har uppdaterats.")
    else:
        messages.info(request, "Språkinställningen är redan sparad.")

    # The admin can arrive from a company user or a global user page.
    # Only same-origin redirects are allowed; never redirect to an external host.
    back = request.POST.get("next", "")
    if back and url_has_allowed_host_and_scheme(
        back,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(back)
    return redirect(reverse("accounts:admin_user_detail", args=[target_user.pk]))
