from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from apps.accounts.forms import CreateCustomerUserForm
from .integrations.sova import SovaClient
from apps.core.integrations.sova import SovaClient

def home(request):
    return JsonResponse({"app": "Talena", "status": "alive"})

def health(request):
    return JsonResponse({"status": "ok"})


def _is_admin(user):
    return getattr(user, "role", None) == "admin" or user.is_staff or user.is_superuser


@login_required
def customer_dashboard(request):
    if _is_admin(request.user):
        # Admin ska inte hamna här (valfritt)
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
    if not _is_admin(request.user):
        return HttpResponseForbidden("No access.")
    
    accounts = []
    error = None

    try:
        accounts = SovaClient().get_accounts_with_projects()
    except Exception as e:
        error = str(e)

    if request.method == "POST":
        form = CreateCustomerUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("admin_dashboard")
    else:
        form = CreateCustomerUserForm()

    return render(request, "admin/core/layouts/admin_dashboard.html", {
        "form": form,
        "accounts": accounts,
        "error": error,
        "ping": "DASHBOARD VIEW HIT",
    })
