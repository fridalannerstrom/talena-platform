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


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

from apps.processes.models import TestInvitation
from apps.core.integrations.sova import SovaClient


@csrf_exempt
def sova_ingest(request):
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    # ✅ Enkel auth: shared secret i header
    secret = request.headers.get("X-Talena-Webhook-Secret")
    if not secret or secret != getattr(settings, "SOVA_WEBHOOK_SHARED_SECRET", ""):
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "invalid json"}, status=400)

    meta = payload.get("meta_data") or {}
    status = (payload.get("status") or "").lower()

    process_id = meta.get("talena_process_id")
    candidate_id = meta.get("talena_candidate_id")
    request_id = meta.get("talena_request_id")  # du skickar denna i payload 👍

    # ✅ Hitta invitation: request_id är bäst (unika)
    invitation = None
    if request_id:
        invitation = TestInvitation.objects.filter(request_id=request_id).first()
    if not invitation and process_id and candidate_id:
        invitation = TestInvitation.objects.filter(process_id=process_id, candidate_id=candidate_id).first()

    if not invitation:
        return JsonResponse({"status": "ignored", "reason": "invitation not found"}, status=200)

    # ✅ Spara rå webhook payload (om du har ett fält för det)
    # invitation.webhook_payload = payload

    if status in ("started", "in_progress"):
        if invitation.status not in ("completed",):
            invitation.status = "started"
            invitation.save(update_fields=["status"])

    if status == "completed":
        invitation.status = "completed"
        invitation.completed_at = timezone.now()

        # 1) om SOVA skickar score i webhooken: plocka här (exempel)
        # invitation.overall_score = payload.get("overall_score")

        # 2) annars: hämta score via API (som du redan gjort)
        if invitation.sova_project_id and invitation.request_id:
            client = SovaClient()
            data = client.get_project_candidates(invitation.sova_project_id)
            items = data.get("candidates") if isinstance(data, dict) else data
            items = items or []
            match = next((c for c in items if c.get("request_id") == invitation.request_id), None)
            if match:
                invitation.overall_score = match.get("overall_score")
                invitation.project_results = match.get("project_results")

        invitation.save(update_fields=["status", "completed_at", "overall_score", "project_results"])

    return JsonResponse({"status": "ok"})