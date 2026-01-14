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

    return render(request, "core/dashboards/customer_dashboard.html", {
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

    return render(request, "core/dashboards/admin_dashboard.html", {
        "form": form,
        "accounts": accounts,
        "error": error,
        "ping": "DASHBOARD VIEW HIT",
    })


@login_required
def sova_projects(request):
    from .integrations.sova import SovaClient
    import os

    debug = {}
    try:
        client = SovaClient()
        debug["base_url"] = client.base_url
        debug["has_user"] = bool(os.getenv("SOVA_USERNAME"))
        debug["has_pass"] = bool(os.getenv("SOVA_PASSWORD"))

        accounts = client.get_accounts_with_projects()
        debug["accounts_len"] = len(accounts)
        for a in accounts:
            a["projects_len"] = len(a.get("projects", []))

        return render(request, "core/sova_projects.html", {
            "accounts": accounts,
            "debug": debug,
            "error": None
        })
    except Exception as e:
        debug["exception"] = str(e)
        return render(request, "core/sova_projects.html", {
            "accounts": [],
            "debug": debug,
            "error": str(e)
        })


@login_required
def sova_project_detail(request, account_code, project_code):
    client = SovaClient()
    error = None
    project = None

    try:
        projects = client.get_projects_for_account(account_code)
        project = next((p for p in projects if (p.get("code") or "") == project_code), None)
        if not project:
            error = f"Project '{project_code}' not found in account '{account_code}'."
    except Exception as e:
        error = str(e)

    return render(request, "admin/projects/sova_project_detail.html", {
        "account_code": account_code,
        "project_code": project_code,
        "project": project,
        "error": error,
    })