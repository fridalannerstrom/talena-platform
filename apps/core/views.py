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

    # --- Customers (admins only) ---
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
                "label": f"{display}",
                "url": reverse("accounts:admin_user_detail", kwargs={"pk": u.id}),
            })

    # --- Processes (scoped) ---
    proc_qs = TestProcess.objects.filter(
        tokens_to_q(tokens, ["name", "project_name_snapshot", "project_code", "job_title"])
    )
    if not admin:
        # Filtrera baserat på account-access istället för created_by
        proc_qs = filter_by_user_accounts(proc_qs, request.user, 'account')

    proc_qs = proc_qs.order_by("-created_at")[:limit_each]

    for p in proc_qs:
        url = (
            reverse("accounts:admin_process_detail", kwargs={"pk": p.id})
            if admin
            else reverse("processes:process_detail", kwargs={"pk": p.id})
        )
        results.append({
            "type": "process",
            "label": f"{p.name}",
            "url": url,
        })

    # --- Candidates (scoped) ---
    cand_qs = Candidate.objects.filter(
        tokens_to_q(tokens, ["first_name", "last_name", "email"])
    )

    if not admin:
        # Filtrera baserat på account-access
        from apps.accounts.utils.permissions import get_user_accessible_accounts
        accessible_accounts = get_user_accessible_accounts(request.user)
        cand_qs = cand_qs.filter(invitations__process__account__in=accessible_accounts)

    cand_qs = cand_qs.distinct().order_by("first_name", "last_name")[:limit_each]

    for c in cand_qs:
        inv_qs = TestInvitation.objects.filter(candidate=c).select_related("process")
        if not admin:
            # Filtrera invitations baserat på account
            inv_qs = inv_qs.filter(process__account__in=accessible_accounts)

        latest_inv = inv_qs.order_by("-created_at").first()

        full_name = f"{c.first_name} {c.last_name}".strip() or c.email

        if latest_inv:
            p = latest_inv.process
            url = (
                reverse("accounts:admin_candidate_detail", kwargs={"process_pk": p.id, "candidate_pk": c.id})
                if admin
                else reverse("processes:process_candidate_detail", kwargs={"process_id": p.id, "candidate_id": c.id})
            )
        else:
            url = "#"

        results.append({
            "type": "candidate",
            "label": f"{full_name}",
            "url": url,
        })

    # Sortera lite trevligt
    order = {"customer": 0, "candidate": 1, "process": 2}
    results.sort(key=lambda r: order.get(r["type"], 99))
    results = results[:12]

    return JsonResponse({"results": results})
