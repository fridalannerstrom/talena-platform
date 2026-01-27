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
        proc_qs = proc_qs.filter(created_by=request.user)

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
        cand_qs = cand_qs.filter(invitations__process__created_by=request.user)

    cand_qs = cand_qs.distinct().order_by("first_name", "last_name")[:limit_each]

    for c in cand_qs:
        inv_qs = TestInvitation.objects.filter(candidate=c).select_related("process")
        if not admin:
            inv_qs = inv_qs.filter(process__created_by=request.user)

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
