from django.shortcuts import render
from apps.core.integrations.sova import SovaClient
import os
from django.contrib.auth.decorators import login_required
from .models import ProjectMeta

@login_required
def projectmeta_list(request):
    items = ProjectMeta.objects.order_by("account_code", "project_code") 
    return render(request, "projects/projectmeta_list.html", {"items": items})


@login_required
def sova_projects(request):

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

        return render(request, "admin/projects/sova_projects.html", {
            "accounts": accounts,
            "debug": debug,
            "error": None
        })
    except Exception as e:
        debug["exception"] = str(e)
        return render(request, "admin/projects/sova_projects.html", {
            "accounts": [],
            "debug": debug,
            "error": str(e)
        })


@login_required
def sova_project_detail(request, account_code, project_code):
    client = SovaClient()
    error = None
    project = None

    # 1) Hämta Talena metadata (från DB)
    # Viktigt: matcha samma nycklar som du sparar i admin
    meta = ProjectMeta.objects.filter(
        provider="sova",
        account_code=account_code.strip(),
        project_code=project_code.strip(),
    ).first()

    # 2) Hämta projektet från SOVA
    try:
        projects = client.get_projects_for_account(account_code)
        project = next(
            (
                p for p in projects
                if (p.get("code") or "").strip().lower() == project_code.strip().lower()
            ),
            None
        )
        if not project:
            error = f"Project '{project_code}' not found in account '{account_code}'."
    except Exception as e:
        error = str(e)

    return render(request, "admin/projects/sova_project_detail.html", {
        "account_code": account_code,
        "project_code": project_code,
        "project": project,
        "meta": meta,          # <-- NYCKELN HÄR
        "error": error,
    })
