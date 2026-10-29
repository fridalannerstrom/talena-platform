"""Company report branding editor and private media delivery."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_GET

from apps.accounts.decorators import admin_required
from apps.accounts.models import Company, CompanyBranding, CompanyMember
from apps.core.utils.auth import is_admin

from .branding_forms import CompanyBrandingForm
from .report_branding import (
    get_report_branding,
    normalize_brand_image,
)


def _cleanup_asset_paths(files):
    """Delete replaced/reset media only after a successful DB transaction."""
    for storage, name in files:
        if name:
            storage.delete(name)


@login_required
@admin_required
@require_http_methods(["GET", "POST"])
def company_branding_settings(request, company_pk):
    company = get_object_or_404(Company, pk=company_pk)
    branding = CompanyBranding.objects.filter(company=company).first()

    if request.method == "POST" and request.POST.get("action") == "reset":
        if branding:
            old_files = [
                (field.storage, field.name)
                for field in (branding.logo, branding.cover_image) if field.name
            ]
            with transaction.atomic():
                branding.delete()
                transaction.on_commit(lambda: _cleanup_asset_paths(old_files))
        messages.success(request, "Talena's default report branding has been restored.")
        return redirect("accounts:company_branding_settings", company_pk=company.pk)

    if request.method == "POST":
        form = CompanyBrandingForm(
            request.POST, request.FILES,
            instance=branding or CompanyBranding(company=company),
        )
        if form.is_valid():
            files = {}
            for field, kind in (("logo", "logo"), ("cover_image", "cover")):
                if field in request.FILES and not form.cleaned_data.get("remove_" + field):
                    try:
                        files[field] = normalize_brand_image(request.FILES[field], kind)
                    except ValueError as exc:
                        form.add_error(field, str(exc))

            if not form.errors:
                instance = form.save(commit=False)
                instance.company = company
                replaced = []
                for field in ("logo", "cover_image"):
                    old = getattr(branding, field) if branding else None
                    if form.cleaned_data.get("remove_" + field):
                        setattr(instance, field, "")
                        if old and old.name:
                            replaced.append((old.storage, old.name))
                    elif field in files:
                        setattr(instance, field, files[field])
                        if old and old.name:
                            replaced.append((old.storage, old.name))

                # A single stable row per company. Never overwrite another
                # tenant's file, and keep the old image on validation failure.
                with transaction.atomic():
                    instance.save()
                    transaction.on_commit(lambda: _cleanup_asset_paths(replaced))
                messages.success(request, "Report branding saved.")
                return redirect("accounts:company_branding_settings", company_pk=company.pk)
    else:
        form = CompanyBrandingForm(instance=branding or CompanyBranding(company=company))

    profile = get_report_branding(company)
    return render(request, "admin/accounts/companies/company_branding.html", {
        "company": company,
        "form": form,
        "branding": branding,
        "profile": profile,
        "palette": profile["palette"],
        "active": "branding",
        "show_invite_button": False,
    })


@login_required
@require_GET
def company_branding_asset(request, company_pk, kind):
    """Secure same-origin preview URL, reusable by authorized report UIs.

    Do not redirect to raw Azure blobs (private or public), and do not allow
    customer X to request customer Y's report assets by guessing its ID.
    """
    if kind not in {"logo", "cover"}:
        raise Http404
    company = get_object_or_404(Company, pk=company_pk)
    permitted = (
        request.user.is_superuser
        or request.user.is_staff
        or is_admin(request.user)
        or CompanyMember.objects.filter(user=request.user, company=company).exists()
    )
    if not permitted:
        raise Http404

    branding = CompanyBranding.objects.filter(company=company).first()
    field = (branding.logo if kind == "logo" else branding.cover_image) if branding else None
    if not field or not field.name:
        raise Http404
    # Every uploaded image has been normalized to PNG/JPEG on save.
    content_type = "image/png" if field.name.lower().endswith(".png") else "image/jpeg"
    try:
        opened = field.open("rb")
    except (OSError, FileNotFoundError) as exc:
        raise Http404 from exc
    response = FileResponse(opened, content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Disposition"] = f'inline; filename="company-{kind}.{"png" if kind == "logo" else "jpg"}"'
    return response
