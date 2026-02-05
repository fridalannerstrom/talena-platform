from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from apps.core.integrations.sova import SovaClient
from apps.core.utils.auth import is_admin

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.processes.models import Candidate, TestProcess, TestInvitation
from apps.accounts.utils.permissions import filter_by_user_accounts

from apps.accounts.models import CompanyMember

from apps.accounts.utils.permissions import get_user_accessible_orgunits

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from apps.core.utils.auth import is_admin
from apps.accounts.models import Company, OrgUnit
from apps.accounts.utils.permissions import get_user_accessible_orgunits
from apps.processes.models import TestProcess, Candidate, TestInvitation

User = get_user_model()


def tokens_to_q(tokens, fields):
    """
    Bygger en Q där ALLA tokens måste matcha,
    och varje token kan matcha i valfritt av fälten (OR).
    """
    q_obj = Q()
    for t in tokens:
        part = Q()
        for f in fields:
            part |= Q(**{f"{f}__icontains": t})
        q_obj &= part
    return q_obj


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
    # (om du har detta logik kvar)
    if request.user.is_staff or request.user.is_superuser:
        return HttpResponseForbidden("Admins should use the admin dashboard.")

    # 1) Hämta SOVA-accounts (din befintliga funktion)
    accounts, error = _get_sova_accounts()  # behåll som du har

    # 2) Hämta userns company
    company_id = (
        CompanyMember.objects
        .filter(user=request.user)
        .values_list("company_id", flat=True)
        .first()
    )

    # 3) Processer som tillhör company (och ev. fallback på created_by)
    if company_id:
        accessible_processes = TestProcess.objects.filter(company_id=company_id)
    else:
        # om användaren inte är kopplad till company än
        accessible_processes = TestProcess.objects.filter(created_by=request.user)

    total_processes = accessible_processes.count()

    return render(request, "customer/core/layouts/customer_dashboard.html", {
        "accounts": accounts,            # från SOVA API
        "error": error,                 # från SOVA API
        "total_processes": total_processes,
        "processes": accessible_processes[:5],  # valfritt: visa senaste 5
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



from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from apps.core.utils.auth import is_admin
from apps.accounts.models import Company, OrgUnit
from apps.accounts.utils.permissions import get_user_accessible_orgunits
from apps.processes.models import TestProcess, Candidate, TestInvitation

# tokens_to_q(...) antar jag att du redan har i samma fil
# och att den returnerar ett Q-objekt

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.core.utils.auth import is_admin
from apps.accounts.models import Company, OrgUnit
from apps.accounts.utils.permissions import get_user_accessible_orgunits
from apps.processes.models import TestProcess, Candidate, TestInvitation

User = get_user_model()

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.core.utils.auth import is_admin
from apps.accounts.models import Company, OrgUnit
from apps.processes.models import TestProcess, Candidate, TestInvitation

User = get_user_model()

@login_required
@require_GET
def global_search(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    tokens = [t for t in q.split() if t]
    limit_each = 5
    results = []
    admin = is_admin(request.user)

    # -----------------------------
    # ADMIN: Customers
    # -----------------------------
    if admin:
        users_qs = (
            User.objects
            .filter(tokens_to_q(tokens, ["email", "first_name", "last_name"]))
            .order_by("first_name", "last_name")[:limit_each]
        )
        for u in users_qs:
            display = (f"{u.first_name} {u.last_name}").strip() or u.email
            results.append({
                "type": "customer",
                "label": display,
                "url": reverse("accounts:admin_user_detail", kwargs={"pk": u.id}),
            })

    # -----------------------------
    # ADMIN: Companies
    # -----------------------------
    if admin:
        companies_qs = (
            Company.objects
            .filter(tokens_to_q(tokens, ["name", "org_number"]))
            .order_by("name")[:limit_each]
        )
        for co in companies_qs:
            results.append({
                "type": "company",
                "label": co.name,
                "url": reverse("accounts:company_detail", kwargs={"pk": co.id}),
            })

    # -----------------------------
    # ADMIN: OrgUnits
    # -----------------------------
    if admin:
        org_qs = (
            OrgUnit.objects
            .select_related("company", "parent")
            .filter(tokens_to_q(tokens, ["name", "unit_code", "company__name"]))
            .order_by("company__name", "name")[:limit_each]
        )
        for ou in org_qs:
            url = f"{reverse('accounts:company_detail', kwargs={'pk': ou.company_id})}?tab=accounts&org_unit={ou.id}"
            results.append({
                "type": "org_unit",
                "label": f"{ou.name} ({ou.unit_code}) – {ou.company.name}",
                "url": url,
            })

    # -----------------------------
    # PROCESSES (ADMIN = alla, CUSTOMER = created_by=user)
    # -----------------------------
    proc_qs = TestProcess.objects.filter(
        tokens_to_q(tokens, ["name", "project_name_snapshot", "project_code", "account_code", "job_title"])
    )
    if not admin:
        proc_qs = proc_qs.filter(created_by=request.user)

    proc_qs = proc_qs.order_by("-created_at")[:limit_each]

    for p in proc_qs:
        url = (
            reverse("accounts:admin_process_detail", kwargs={"pk": p.id})
            if admin
            else reverse("processes:process_detail", kwargs={"pk": p.id})
        )
        results.append({"type": "process", "label": p.name, "url": url})

    # -----------------------------
    # CANDIDATES (ADMIN = alla, CUSTOMER = candidates i user’s processer)
    # -----------------------------
    cand_qs = Candidate.objects.filter(
        tokens_to_q(tokens, ["first_name", "last_name", "email"])
    )

    if not admin:
        cand_qs = cand_qs.filter(invitations__process__created_by=request.user)

    cand_qs = cand_qs.distinct().order_by("first_name", "last_name")[:limit_each]

    for c in cand_qs:
        full_name = f"{c.first_name} {c.last_name}".strip() or c.email

        inv_qs = TestInvitation.objects.filter(candidate=c).select_related("process").order_by("-created_at")
        if not admin:
            inv_qs = inv_qs.filter(process__created_by=request.user)

        latest_inv = inv_qs.first()

        if latest_inv:
            p = latest_inv.process
            url = (
                reverse("accounts:admin_candidate_detail", kwargs={"process_pk": p.id, "candidate_pk": c.id})
                if admin
                else reverse("processes:process_candidate_detail", kwargs={"process_id": p.id, "candidate_id": c.id})
            )
        else:
            url = "#"

        results.append({"type": "candidate", "label": full_name, "url": url})

    # -----------------------------
    # Sort + limit
    # -----------------------------
    order = {"customer": 0, "company": 1, "org_unit": 2, "process": 3, "candidate": 4}
    results.sort(key=lambda r: order.get(r["type"], 99))
    results = results[:12]

    return JsonResponse({"results": results})
