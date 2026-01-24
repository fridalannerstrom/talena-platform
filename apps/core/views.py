from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from apps.core.integrations.sova import SovaClient
from apps.core.utils.auth import is_admin

def home(request):
    return JsonResponse({"app": "Talena", "status": "alive"})


def health(request):
    return JsonResponse({"status": "ok"})

def root_redirect(request):
    return redirect("core:login")


@login_required
def post_login_redirect(request):
    if is_admin(request.user):
        return redirect("core:admin_dashboard")
    return redirect("core:customer_dashboard")


def _get_sova_accounts():
    try:
        return SovaClient().get_accounts_with_projects(), None
    except Exception as e:
        return [], str(e)

@login_required
def customer_dashboard(request):
    if is_admin(request.user):
        return HttpResponseForbidden("Admins should use the admin dashboard.")

    accounts, error = _get_sova_accounts()
    return render(request, "customer/core/layouts/customer_dashboard.html", {
        "accounts": accounts,
        "error": error,
    })

@login_required
def admin_dashboard(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    accounts, error = _get_sova_accounts()
    return render(request, "admin/core/layouts/admin_dashboard.html", {
        "accounts": accounts,
        "error": error,
    })