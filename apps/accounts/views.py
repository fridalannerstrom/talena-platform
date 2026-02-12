from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.db.models import Count
from django.views.decorators.http import require_POST
from apps.core.integrations.sova import SovaClient
from apps.projects.models import ProjectMeta

from apps.core.utils.auth import is_admin
from apps.processes.models import TestProcess, TestInvitation, Candidate

from .forms import InviteUserForm, OrgUnitForm, UserOrgUnitAccessForm
from .services.invites import send_invite_email
from .decorators import admin_required
from apps.portal.forms import AccountForm as PortalAccountForm, ProfileImageForm
from .utils.permissions import get_user_accessible_accounts

from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from .models import Company, CompanyMember, OrgUnit, UserOrgUnitAccess
from .forms import CompanyMemberAddForm, CompanyForm, CompanyInviteMemberForm, OrgUnitAccessAddForm

from django.db import transaction

from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from .models import UserInvite
from django.utils import timezone

import json
from django.http import JsonResponse
from django.db.models import Count, Q, Max

from django.db.models.functions import Coalesce

from django import template
from django.utils import timezone
from apps.processes.forms import TestProcessCreateForm


User = get_user_model()

def build_invite_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("accounts:accept_invite", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)

def build_invite_uuid_link(request, invite):
    path = reverse("accounts:accept_invite_uuid", kwargs={"invite_id": invite.id})
    return request.build_absolute_uri(path)


from django.db.models import Count, Q

@login_required
def admin_user_detail(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    user_obj = get_object_or_404(User, pk=pk)
    pending_invite = not user_obj.is_active

    invite_link = None
    open_invite_modal = False

    company = Company.objects.filter(memberships__user=user_obj).first()

    # --- POST actions (din befintliga kod) ---
    if request.method == "POST":
        action = request.POST.get("action")
        if action in ("resend_invite_email", "generate_invite_link"):
            if not pending_invite:
                messages.info(request, "Användaren är redan aktiv. Ingen invite behövs.")
                return redirect("accounts:admin_user_detail", pk=user_obj.pk)

            if not company:
                messages.error(request, "Användaren är inte kopplad till något företag.")
                return redirect("accounts:admin_user_detail", pk=user_obj.pk)

            with transaction.atomic():
                UserInvite.objects.filter(
                    user=user_obj,
                    company=company,
                    accepted_at__isnull=True,
                    revoked_at__isnull=True,
                ).update(revoked_at=timezone.now())

                invite = UserInvite.objects.create(
                    user=user_obj,
                    company=company,
                    created_by=request.user,
                )

                invite_link = build_invite_uuid_link(request, invite)

                if user_obj.has_usable_password():
                    user_obj.set_unusable_password()
                if user_obj.is_active:
                    user_obj.is_active = False
                user_obj.save(update_fields=["password", "is_active"])

            if action == "resend_invite_email":
                send_invite_email(request, user_obj, invite_link=invite_link, company=company)
                messages.success(request, f"Inbjudan skickad till {user_obj.email}.")
                return redirect("accounts:admin_user_detail", pk=user_obj.pk)

            open_invite_modal = True
            messages.success(request, "Ny invite-länk genererad.")

    # --- DATA: processer + KPI ---
    processes = (
        TestProcess.objects
        .filter(created_by=user_obj)
        .annotate(invitations_count=Count("invitations", distinct=True))  # <-- ändra related_name om behövs
        .order_by("-created_at")
    )

    processes_count = processes.count()

    invitations_qs = TestInvitation.objects.filter(process__created_by=user_obj)
    invitations_created = invitations_qs.count()
    invitations_completed = invitations_qs.filter(status="completed").count()

    active_processes = processes
    if hasattr(TestProcess, "is_completed"):
        active_processes = processes.filter(is_completed=False)

    orgunit_accesses = (
        UserOrgUnitAccess.objects
        .filter(user=user_obj)
        .select_related("org_unit", "org_unit__company")
        .order_by("org_unit__company__name", "org_unit__name")
    )

    memberships = (
        CompanyMember.objects
        .filter(user=user_obj)
        .select_related("company")
        .order_by("company__name")
    )

    return render(request, "admin/accounts/customer/customer_detail.html", {
        # ✅ använd samma namn som templaten använder
        "user_obj": user_obj,
        "u": user_obj,  # valfritt bakåtkompatibelt om du råkar använda u någonstans

        "company": company,
        "memberships": memberships,

        "processes": processes,
        "active_processes": active_processes,

        # KPI
        "processes_count": processes_count,
        "invitations_created": invitations_created,
        "invitations_completed": invitations_completed,

        "pending_invite": pending_invite,
        "invite_link": invite_link,
        "open_invite_modal": open_invite_modal,

        "orgunit_accesses": orgunit_accesses,
    })


@login_required
def admin_customers_list(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    customers = (
        User.objects
        .filter(is_superuser=False, is_staff=False)
        .prefetch_related("company_memberships__company")
        .order_by("-date_joined")
    )
    return render(request, "admin/accounts/customer/customers_list.html", {"customers": customers})


@login_required
def admin_customers_create(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    if request.method == "POST":
        form = InviteUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_unusable_password()
            user.is_active = False
            user.save()

            send_invite_email(request, user)
            messages.success(request, f"Invite sent to {user.email}.")
            return redirect("accounts:admin_customers_list")

        messages.error(request, "Could not create invite. Check the form fields.")
    else:
        form = InviteUserForm()

    return render(request, "admin/accounts/customer/customers_create.html", {"form": form})


def accept_invite(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, "accounts/invite_invalid.html", status=400)

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            user.is_active = True
            user.save(update_fields=["is_active"])

            login(request, user)
            messages.success(request, "Password set. Welcome to Talena!")
            return redirect("core:post_login_redirect")
    else:
        form = SetPasswordForm(user)

    return render(request, "accounts/accept_invite.html", {"form": form, "user": user})


@login_required
def admin_process_detail(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    process = get_object_or_404(TestProcess, pk=pk)

    invitations = (
        TestInvitation.objects
        .filter(process=process)
        .select_related("candidate")
        .order_by("-created_at")
    )

    # Snabb statistik (nice för admin-UI)
    status_counts = {}
    for inv in invitations:
        status_counts[inv.status] = status_counts.get(inv.status, 0) + 1

    total_sent = invitations.count()

    return render(request, "admin/accounts/customer/process_detail.html", {
        "process": process,
        "invitations": invitations,
        "status_counts": status_counts,
        "total_sent": total_sent, 
    })


@login_required
def admin_candidate_detail(request, process_pk, candidate_pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    process = get_object_or_404(TestProcess, pk=process_pk)
    candidate = get_object_or_404(Candidate, pk=candidate_pk)

    invitation = get_object_or_404(
        TestInvitation,
        process=process,
        candidate=candidate,
    )

    # (valfritt) samma dummy-data som kunden använder
    dummy_profile = {"labels": '["Drive","Structure","Collaboration","Stability"]', "values": "[6,8,7,5]"}
    dummy_abilities = {"labels": '["Verbal","Numerical","Logical"]', "values": "[7,6,8]"}

    return render(request, "admin/accounts/customer/candidate_detail.html", {
        "process": process,
        "candidate": candidate,
        "invitation": invitation,
        "dummy_profile": dummy_profile,
        "dummy_abilities": dummy_abilities,
    })



from django.db.models import Count, Q

@login_required
@admin_required
def company_list(request):
    q = (request.GET.get("q") or "").strip()
    sort = request.GET.get("sort") or "name"

    qs = (
        Company.objects
        .annotate(
            member_count=Count("memberships", distinct=True),
            orgunit_count=Count("org_units", distinct=True),
            last_activity=Max("memberships__user__last_login"),
            pending_invites=Count("memberships", filter=Q(memberships__user__is_active=False), distinct=True),
        )
    )

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(org_number__icontains=q)
        )

    sort_map = {
        "name": "name",
        "-name": "-name",
        "members": "-member_count",
        "units": "-orgunit_count",
        "newest": "-created_at",  # om du har created_at
        "oldest": "created_at",
        "pending": "-pending_invites",
        "activity": "-last_activity",
    }
    qs = qs.order_by(sort_map.get(sort, "name"))

    return render(request, "admin/accounts/companies/company_list.html", {
        "companies": qs,
        "q": q,
        "sort": sort,
    })



@login_required
@admin_required
def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)

    # ------------------------------------------------------------
    # KPI:er (samma logik som stats, men för overview)
    # ------------------------------------------------------------
    users_count = CompanyMember.objects.filter(company=company).count()

    orgunits_qs = OrgUnit.objects.filter(company=company)
    accounts_total = orgunits_qs.count()
    accounts_root = orgunits_qs.filter(parent__isnull=True).count()
    accounts_sub = accounts_total - accounts_root

    processes_qs = TestProcess.objects.filter(company=company)
    processes_count = processes_qs.count()

    invitations_qs = TestInvitation.objects.filter(process__company=company)
    invitations_count = invitations_qs.count()

    candidates_count = invitations_qs.values("candidate_id").distinct().count()

    invite_form = CompanyInviteMemberForm() 

    invitation_status = (
        invitations_qs
        .values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # ------------------------------------------------------------
    # Listor för overview (liten “preview”)
    # ------------------------------------------------------------
    memberships = (
        CompanyMember.objects
        .filter(company=company)
        .select_related("user")
        .order_by("user__email")
    )

    recent_memberships = memberships[:6]  # lagom för en overview-preview

    # Modaler / actions (om du vill kunna bjuda in härifrån)
    invite_form = CompanyInviteMemberForm()

    # ------------------------------------------------------------
    # POST (endast invite här, resten finns på egna sidor)
    # ------------------------------------------------------------
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "invite_member":
            invite_form = CompanyInviteMemberForm(request.POST)
            if invite_form.is_valid():
                email = invite_form.cleaned_data["email"]
                first_name = invite_form.cleaned_data.get("first_name", "")
                last_name = invite_form.cleaned_data.get("last_name", "")

                with transaction.atomic():
                    user, created_user = User.objects.get_or_create(
                        email=email,
                        defaults={
                            "username": email,
                            "first_name": first_name,
                            "last_name": last_name,
                            "is_active": False,
                        }
                    )

                    if not created_user:
                        changed = False
                        if first_name and not user.first_name:
                            user.first_name = first_name
                            changed = True
                        if last_name and not user.last_name:
                            user.last_name = last_name
                            changed = True
                        if changed:
                            user.save(update_fields=["first_name", "last_name"])

                    CompanyMember.objects.get_or_create(company=company, user=user)

                    # Om redan aktiv, skicka inget
                    if user.is_active:
                        messages.info(request, f"{email} har redan ett aktivt konto. Ingen inbjudan skickades.")
                        return redirect("accounts:company_detail", pk=company.pk)

                    # Se till att användaren är pending
                    if user.has_usable_password():
                        user.set_unusable_password()
                    user.is_active = False
                    user.save(update_fields=["is_active", "password"])

                    # Revoka gamla invites
                    UserInvite.objects.filter(
                        user=user,
                        company=company,
                        accepted_at__isnull=True,
                        revoked_at__isnull=True,
                    ).update(revoked_at=timezone.now())

                    # Skapa ny invite
                    invite = UserInvite.objects.create(
                        user=user,
                        company=company,
                        created_by=request.user,
                    )

                    invite_link = build_invite_uuid_link(request, invite)
                    send_invite_email(
                        request,
                        user,
                        invite_link=invite_link,
                        company=company,
                    )

                messages.success(request, f"Inbjudan skickades till {email}.")
                return redirect("accounts:company_detail", pk=company.pk)

            messages.error(request, "Kunde inte bjuda in användare. Kontrollera fälten.")

    # Kandidater (unika via invitations i företaget)
    candidate_rows = (
        TestInvitation.objects
        .filter(process__company=company)
        .select_related("candidate", "process")
        .order_by("candidate__name")
    )

    invitations_created = (
        invitations_qs
        .filter(status="created")
        .count()
    )

    # ------------------------------------------------------------
    # Render
    # ------------------------------------------------------------
    return render(request, "admin/accounts/companies/company_detail.html", {
        "company": company,
        "active_tab": "overview",
        "show_invite_button": True,

        # KPI
        "users_count": users_count,
        "accounts_total": accounts_total,
        "accounts_root": accounts_root,
        "accounts_sub": accounts_sub,
        "processes_count": processes_count,
        "candidates_count": candidates_count,
        "invitations_count": invitations_count,
        "invitation_status": invitation_status,
        "candidate_rows": candidate_rows,
        "invitations_created": invitations_created,

        # Preview-data
        "memberships": memberships,
        "recent_memberships": recent_memberships,

        # Modal/form
        "invite_form": invite_form,
    })



@login_required
@admin_required
@require_POST
def company_member_remove(request, company_pk, user_pk):
    company = get_object_or_404(Company, pk=company_pk)
    membership = get_object_or_404(CompanyMember, company=company, user_id=user_pk)
    email = membership.user.email
    membership.delete()
    messages.success(request, f"{email} togs bort från {company.name}.")
    return redirect("accounts:company_detail", pk=company.pk)


@login_required
@admin_required
@require_POST
def company_member_update_role(request, company_pk, user_pk):
    company = get_object_or_404(Company, pk=company_pk)
    membership = get_object_or_404(CompanyMember, company=company, user_id=user_pk)

    form = CompanyMemberRoleForm(request.POST)
    if form.is_valid():
        membership.role = form.cleaned_data["role"]
        membership.save(update_fields=["role"])
        messages.success(request, "Rollen uppdaterades.")
    else:
        messages.error(request, "Kunde inte uppdatera rollen.")

    return redirect("accounts:company_detail", pk=company.pk)




@login_required
@admin_required
def company_create(request):
    if request.method == "POST":
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save()
            messages.success(request, f"Företag '{company.name}' skapat.")
            return redirect("accounts:company_detail", pk=company.pk)
    else:
        form = CompanyForm()

    return render(request, "admin/accounts/companies/company_form.html", {
        "form": form,
        "is_create": True,
    })


def accept_invite_uuid(request, invite_id):
    invite = get_object_or_404(UserInvite, id=invite_id)

    # Ogiltig om revoked eller redan accepterad
    if invite.revoked_at is not None or invite.accepted_at is not None:
        return render(request, "accounts/invite_invalid.html", status=400)

    user = invite.user

    # Om användaren redan är aktiv: låt den logga in istället
    if user.is_active:
        messages.info(request, "Kontot är redan aktiverat. Logga in.")
        return redirect("login")

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            user.is_active = True
            user.save(update_fields=["is_active"])

            invite.accepted_at = timezone.now()
            invite.save(update_fields=["accepted_at"])

            login(request, user)
            return redirect("core:post_login_redirect")
    else:
        form = SetPasswordForm(user)

    return render(request, "accounts/accept_invite.html", {"form": form, "user": user})


@login_required
@admin_required
@require_POST
def orgunit_move(request, company_pk):
    """
    Tar emot JSON:
      { "unit_id": 123, "new_parent_id": 456 }   -> flytta under annan
      { "unit_id": 123, "new_parent_id": null }  -> gör root
    """
    company = get_object_or_404(Company, pk=company_pk)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON."}, status=400)

    unit_id = payload.get("unit_id")
    new_parent_id = payload.get("new_parent_id", None)

    if not unit_id:
        return JsonResponse({"ok": False, "error": "unit_id is required."}, status=400)

    unit = get_object_or_404(OrgUnit, pk=unit_id, company=company)

    new_parent = None
    if new_parent_id:
        new_parent = get_object_or_404(OrgUnit, pk=new_parent_id, company=company)

        # skydd: förhindra loop (lägga under sig själv eller sin egen subtree)
        cur = new_parent
        while cur:
            if cur.pk == unit.pk:
                return JsonResponse({"ok": False, "error": "Cannot move unit under itself/descendant."}, status=400)
            cur = cur.parent

    with transaction.atomic():
        unit.parent = new_parent
        unit.save(update_fields=["parent"])

    return JsonResponse({
        "ok": True,
        "unit_id": unit.pk,
        "new_parent_id": new_parent.pk if new_parent else None,
    })

@login_required
@admin_required
def company_account_structure(request, pk):
    company = get_object_or_404(Company, pk=pk)

    orgunit_form = OrgUnitForm(company=company)

    # Tree
    all_units = (
        OrgUnit.objects
        .filter(company=company)
        .select_related("parent")
        .order_by("name")
    )
    children_map = {}
    for u in all_units:
        children_map.setdefault(u.parent_id, []).append(u)
    root_units = children_map.get(None, [])

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_orgunit":
            orgunit_form = OrgUnitForm(request.POST, company=company)
            if orgunit_form.is_valid():
                unit = orgunit_form.save(commit=False)
                unit.company = company
                unit.save()
                messages.success(request, f"Enhet '{unit.name}' skapad.")
                return redirect("accounts:company_account_structure", pk=company.pk)
            messages.error(request, "Kunde inte skapa enhet. Kontrollera fälten.")

    return render(request, "admin/accounts/companies/company_account_structure.html", {
        "company": company,
        "orgunit_form": orgunit_form,
        "root_units": root_units,
        "children_map": children_map,
    })


@login_required
@admin_required
def company_user_access(request, pk):
    company = get_object_or_404(Company, pk=pk)

    # alla users i bolaget
    users = (
        User.objects
        .filter(company_memberships__company=company)
        .distinct()
        .order_by("email")
    )

    # vilken user är vald?
    selected_user_id = request.GET.get("user")
    selected_user = None

    if selected_user_id:
        selected_user = get_object_or_404(User, pk=selected_user_id)

        # säkerhet: måste vara medlem i företaget
        if not CompanyMember.objects.filter(company=company, user=selected_user).exists():
            return HttpResponseForbidden("No access.")

    # accounts/orgunits för checkbox-lista
    all_units = (
        OrgUnit.objects
        .filter(company=company)
        .select_related("parent")
        .order_by("name")
    )
    children_map = {}
    for u in all_units:
        children_map.setdefault(u.parent_id, []).append(u)
    root_units = children_map.get(None, [])

    # prechecked för vald user
    checked_ids = set()
    if selected_user:
        checked_ids = set(
            UserOrgUnitAccess.objects
            .filter(user=selected_user, org_unit__company=company)
            .values_list("org_unit_id", flat=True)
        )

    return render(request, "admin/accounts/companies/company_user_access.html", {
        "company": company,
        "users": users,
        "selected_user": selected_user,
        "root_units": root_units,
        "children_map": children_map,
        "checked_ids": checked_ids,
    })


@login_required
@admin_required
def company_user_access_state(request, company_pk):
    company = get_object_or_404(Company, pk=company_pk)
    user_id = request.GET.get("user_id")
    if not user_id:
        return JsonResponse({"ok": False, "error": "user_id required"}, status=400)

    user = get_object_or_404(User, pk=user_id)

    if not CompanyMember.objects.filter(company=company, user=user).exists():
        return JsonResponse({"ok": False, "error": "User not in company"}, status=403)

    checked_ids = list(
        UserOrgUnitAccess.objects
        .filter(user=user, org_unit__company=company)
        .values_list("org_unit_id", flat=True)
    )
    return JsonResponse({"ok": True, "checked_ids": checked_ids})


@login_required
@admin_required
@require_POST
def company_user_access_set(request, company_pk):
    company = get_object_or_404(Company, pk=company_pk)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    user_id = payload.get("user_id")
    unit_ids = payload.get("unit_ids", [])
    mode = payload.get("mode")  # expected: "replace" (new UI)
    grant = payload.get("grant")  # legacy true/false (optional)

    if not user_id or not isinstance(unit_ids, list):
        return JsonResponse({"ok": False, "error": "user_id and unit_ids required"}, status=400)

    user = get_object_or_404(User, pk=user_id)

    # Safety: user must belong to this company
    if not CompanyMember.objects.filter(company=company, user=user).exists():
        return JsonResponse({"ok": False, "error": "User not in company"}, status=403)

    # Only units in this company
    units = list(OrgUnit.objects.filter(company=company, id__in=unit_ids))

    # Validate: ensure all provided unit_ids exist for this company
    requested_ids = {int(x) for x in unit_ids if str(x).isdigit()}
    found_ids = {u.id for u in units}
    missing = sorted(list(requested_ids - found_ids))
    if missing:
        return JsonResponse({"ok": False, "error": f"Invalid unit_ids for company: {missing}"}, status=400)

    with transaction.atomic():
        # ✅ New behavior: replace all access with provided list
        if mode == "replace":
            # Delete all accesses for this user within the company
            UserOrgUnitAccess.objects.filter(
                user=user,
                org_unit__company=company
            ).delete()

            # Re-create access rows for selected units
            # (bulk_create is faster and fine here)
            objs = [UserOrgUnitAccess(user=user, org_unit=u) for u in units]
            if objs:
                UserOrgUnitAccess.objects.bulk_create(objs)

            return JsonResponse({
                "ok": True,
                "action": "replaced",
                "count": len(objs),
            })

        # --- Legacy behavior (optional fallback) ---
        if grant is True:
            created = 0
            for unit in units:
                _, was_created = UserOrgUnitAccess.objects.get_or_create(user=user, org_unit=unit)
                created += 1 if was_created else 0
            return JsonResponse({"ok": True, "action": "granted", "created": created})

        if grant is False:
            deleted, _ = UserOrgUnitAccess.objects.filter(user=user, org_unit__in=units).delete()
            return JsonResponse({"ok": True, "action": "removed", "deleted": deleted})

        return JsonResponse({"ok": False, "error": "Provide mode='replace' or grant=true/false"}, status=400)




@login_required
@admin_required
def company_users(request, pk):
    company = get_object_or_404(Company, pk=pk)

    memberships = (
        CompanyMember.objects
        .filter(company=company)
        .select_related("user")
        .order_by("user__email")
    )

    invite_form = CompanyInviteMemberForm()  # ✅ behövs för modalen

    return render(request, "admin/accounts/companies/company_users.html", {
        "company": company,
        "memberships": memberships,
        "active_tab": "users",
        "show_invite_button": True,  # så knappen syns uppe i headern
        "invite_form": invite_form,  # ✅
    })


@login_required
@admin_required
def company_stats(request, pk):
    company = get_object_or_404(Company, pk=pk)

    # --- Users / Accounts ---
    users_count = CompanyMember.objects.filter(company=company).count()

    orgunits_qs = OrgUnit.objects.filter(company=company)
    accounts_total = orgunits_qs.count()
    accounts_root = orgunits_qs.filter(parent__isnull=True).count()
    accounts_sub = accounts_total - accounts_root

    # Users per account (OrgUnit)
    users_per_unit = (
        UserOrgUnitAccess.objects
        .filter(org_unit__company=company)
        .values("org_unit_id", "org_unit__name", "org_unit__unit_code")
        .annotate(user_count=Count("user", distinct=True))
        .order_by("-user_count", "org_unit__name")
    )

    # --- Process / candidates / invitations ---
    # Välj EN av varianterna nedan beroende på din datamodell.

    # VARIANT A: Om TestProcess har FK -> company
    processes_qs = TestProcess.objects.filter(company=company)
    processes_count = processes_qs.count()

    # Invitations
    invitations_qs = TestInvitation.objects.filter(process__company=company)
    invitations_count = invitations_qs.count()
    invite_form = CompanyInviteMemberForm()

    # Candidates (distinct candidates invited in this company)
    candidates_count = invitations_qs.values("candidate_id").distinct().count()

    # (Valfritt) status breakdown, snyggt för “Skickade tester”
    invitation_status = (
        invitations_qs
        .values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    invitations_created = (
        invitations_qs
        .filter(status="created")
        .count()
    )

    return render(request, "admin/accounts/companies/company_stats.html", {
        "company": company,
        "active_tab": "stats",
        "show_invite_button": True,

        "users_count": users_count,
        "accounts_total": accounts_total,
        "accounts_root": accounts_root,
        "accounts_sub": accounts_sub,

        "processes_count": processes_count,
        "candidates_count": candidates_count,
        "invitations_count": invitations_count,
        "invitation_status": invitation_status,
        "invitations_created": invitations_created,
        "invite_form": invite_form,

        "users_per_unit": users_per_unit,
    })



@login_required
def admin_process_create_for_user(request, user_pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    user_obj = get_object_or_404(User, pk=user_pk)

    next_url = request.GET.get("next") or reverse(
        "accounts:admin_user_detail",
        kwargs={"pk": user_obj.pk}
    )

    client = SovaClient()
    error = None

    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    choices = []
    template_cards = []
    project_id_map = {}

    for a in accounts:
        acc = (a.get("code") or "").strip()
        for p in (a.get("projects") or []):
            proj_code = (p.get("code") or "").strip()
            sova_name = (p.get("name") or proj_code).strip()

            value = f"{acc}|{proj_code}"
            project_id_map[value] = p.get("id")

            meta = meta_map.get((acc, proj_code))
            title = (getattr(meta, "intern_name", None) or sova_name)

            choices.append((value, title))
            template_cards.append({
                "value": value,
                "title": title,
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
                "sova_project_id": p.get("id"),
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    if request.method == "POST":
        form = TestProcessCreateForm(request.POST)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            obj = form.save(commit=False)

            value = form.cleaned_data["sova_template"]
            acc, proj = value.split("|", 1)

            # ✅ company kopplad till KUNDEN (user_obj), inte admin
            company_id = (
                CompanyMember.objects
                .filter(user=user_obj)
                .values_list("company_id", flat=True)
                .first()
            )
            if not company_id:
                form.add_error(None, "Kunden är inte kopplad till något företag.")
                return render(request, "admin/accounts/customer/process_create.html", {
                    "user_obj": user_obj,
                    "form": form,
                    "error": error,
                    "template_cards": template_cards,
                    "next_url": next_url,
                    "templates_count": len(template_cards),
                    "accounts_count": len(accounts),
                })

            obj.company_id = company_id

            # ✅ samma SOVA-fält som kund
            obj.provider = "sova"
            obj.account_code = acc
            obj.project_code = proj
            obj.sova_project_id = project_id_map.get(value)

            meta = meta_map.get((acc, proj))
            obj.project_name_snapshot = (getattr(meta, "intern_name", None) or "")
            if not obj.project_name_snapshot:
                match = next((t for t in template_cards if t["value"] == value), None)
                obj.project_name_snapshot = (match["sova_name"] if match else proj)

            # ✅ viktigaste skillnaden: created_by = kunden
            obj.created_by = user_obj
            obj.save()

            messages.success(request, "Testprocess skapad.")
            return redirect(f"{reverse('accounts:admin_user_detail', kwargs={'pk': user_obj.pk})}?next={next_url}")

        messages.error(request, "Kunde inte skapa testprocess. Kontrollera fälten.")
    else:
        form = TestProcessCreateForm()
        form.fields["sova_template"].choices = choices

    return render(request, "admin/accounts/customer/process_create.html", {
        "user_obj": user_obj,
        "form": form,
        "error": error,
        "template_cards": template_cards,
        "next_url": next_url,
        "templates_count": len(template_cards),
        "accounts_count": len(accounts),
    })


@login_required
def admin_process_update(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    obj = get_object_or_404(TestProcess, pk=pk)

    # 🔙 stabil "next" för bra back-flow
    next_url = request.GET.get("next") or reverse(
        "accounts:admin_process_detail", kwargs={"pk": obj.pk}
    )

    old_acc = (obj.account_code or "").strip()
    old_proj = (obj.project_code or "").strip()
    locked = obj.is_template_locked()

    client = SovaClient()
    error = None

    # 1) Hämta accounts + projects från SOVA
    try:
        accounts = client.get_accounts_with_projects()
    except Exception as e:
        accounts = []
        error = str(e)

    # 2) Hämta meta för intern_name
    metas = ProjectMeta.objects.filter(provider="sova")
    meta_map = {(m.account_code, m.project_code): m for m in metas}

    # 3) Bygg choices + cards (med subtitle/icon om du vill)
    choices = []
    template_cards = []

    for a in accounts:
        acc = (a.get("code") or "").strip()
        for p in (a.get("projects") or []):
            proj_code = (p.get("code") or "").strip()
            sova_name = (p.get("name") or proj_code).strip()

            meta = meta_map.get((acc, proj_code))
            title = (getattr(meta, "intern_name", None) or sova_name)

            value = f"{acc}|{proj_code}"
            choices.append((value, title))

            template_cards.append({
                "value": value,
                "title": title,
                "subtitle": f"{acc} · {proj_code}",
                "icon": "layers",
                "account_code": acc,
                "project_code": proj_code,
                "sova_name": sova_name,
            })

    template_cards.sort(key=lambda x: (x["title"] or "").lower())

    if request.method == "POST":
        form = TestProcessCreateForm(request.POST, instance=obj)
        form.fields["sova_template"].choices = choices

        if form.is_valid():
            updated = form.save(commit=False)

            value = form.cleaned_data["sova_template"]
            acc, proj = value.split("|", 1)

            if locked and ((acc.strip() != old_acc) or (proj.strip() != old_proj)):
                messages.error(
                    request,
                    "Du kan inte ändra testpaket efter att tester har skickats i processen."
                )
                return redirect(f"{reverse('accounts:admin_process_update', kwargs={'pk': obj.pk})}?next={next_url}")

            updated.provider = "sova"
            updated.account_code = acc
            updated.project_code = proj

            meta = meta_map.get((acc, proj))
            if meta and getattr(meta, "intern_name", None):
                updated.project_name_snapshot = meta.intern_name
            else:
                match = next((t for t in template_cards if t["value"] == value), None)
                updated.project_name_snapshot = (match["sova_name"] if match else proj)

            updated.save()
            messages.success(request, "Process uppdaterad.")

            # tillbaka dit du kom ifrån (process detail eller user)
            return redirect(next_url)

        messages.error(request, "Kunde inte spara. Kontrollera fälten.")

    else:
        form = TestProcessCreateForm(instance=obj)
        form.fields["sova_template"].choices = choices
        form.initial["sova_template"] = f"{obj.account_code}|{obj.project_code}"

    return render(request, "admin/accounts/customer/process_edit.html", {
        "form": form,
        "process": obj,
        "error": error,
        "template_cards": template_cards,
        "template_locked": locked,
        "next_url": next_url,
    })