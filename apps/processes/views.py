from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from apps.core.integrations.sova import SovaClient
from .forms import TestProcessCreateForm
from .models import TestProcess

@login_required
def process_list(request):
    # sen kan du filtrera per kund/tenant, men nu: bara per användare
    processes = TestProcess.objects.filter(created_by=request.user)
    return render(request, "customer/processes/process_list.html", {"processes": processes})

@login_required
def process_create(request):
    client = SovaClient()
    error = None

    # 1) Hämta accounts + projects från SOVA
    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    # 2) Bygg dropdown choices
    # value: "ACCOUNT_CODE::PROJECT_CODE::PROJECT_NAME"
    choices = []
    for a in accounts:
        acc = a.get("code")
        for p in a.get("projects", []) or []:
            proj_code = p.get("code")
            proj_name = p.get("name") or proj_code
            label = f"{proj_name}  ({acc} / {proj_code})"
            value = f"{acc}::{proj_code}::{proj_name}"
            choices.append((value, label))

    if request.method == "POST":
        form = TestProcessCreateForm(request.POST)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            obj = form.save(commit=False)

            # plocka ut valda mallens delar
            value = form.cleaned_data["sova_template"]
            acc, proj, proj_name = value.split("::", 2)

            obj.provider = "sova"
            obj.account_code = acc
            obj.project_code = proj
            obj.project_name_snapshot = proj_name
            obj.created_by = request.user

            obj.save()
            return redirect("process_list")
    else:
        form = TestProcessCreateForm()
        form.fields["sova_template"].choices = choices

    return render(request, "customer/processes/process_create.html", {
        "form": form,
        "error": error,
        "accounts_count": len(accounts),
        "choices_count": len(choices),
    })