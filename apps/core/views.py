from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.core.integrations.sova import SovaClient
from apps.core.utils.auth import is_admin
from apps.accounts.forms import InviteUserForm
from django.shortcuts import redirect


def home(request):
    return JsonResponse({"app": "Talena", "status": "alive"})


def health(request):
    return JsonResponse({"status": "ok"})

def root_redirect(request):
    return redirect("accounts:login")


@login_required
def customer_dashboard(request):
    if is_admin(request.user):
        return HttpResponseForbidden("Admins should use the admin dashboard.")

    accounts = []
    error = None
    try:
        accounts = SovaClient().get_accounts_with_projects()
    except Exception as e:
        error = str(e)

    return render(request, "customer/core/layouts/customer_dashboard.html", {
        "accounts": accounts,
        "error": error,
        "ping": "DASHBOARD VIEW HIT",
    })


@login_required
def admin_dashboard(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    accounts = []
    error = None
    try:
        accounts = SovaClient().get_accounts_with_projects()
    except Exception as e:
        error = str(e)

    # Fix: form måste definieras här
    form = InviteUserForm()

    return render(request, "admin/core/layouts/admin_dashboard.html", {
        "form": form,
        "accounts": accounts,
        "error": error,
        "ping": "DASHBOARD VIEW HIT",
    })
