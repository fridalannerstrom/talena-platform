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
from .forms import CompanyMemberAddForm, CompanyForm, CompanyInviteMemberForm

from django.db import transaction

from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from .models import UserInvite
from django.utils import timezone

import json
from django.http import JsonResponse




User = get_user_model()


def build_invite_link(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("accounts:accept_invite", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)

def build_invite_uuid_link(request, invite):
    path = reverse("accounts:accept_invite_uuid", kwargs={"invite_id": invite.id})
    return request.build_absolute_uri(path)



@login_required
def admin_user_detail(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    user_obj = get_object_or_404(User, pk=pk)
    pending_invite = not user_obj.is_active

    invite_link = None
    open_invite_modal = False

    # Hitta company för usern (om du tillåter bara 1 företag per user)
    company = Company.objects.filter(memberships__user=user_obj).first()

    if request.method == "POST" and request.POST.get("action") == "generate_invite_link":
        if not pending_invite:
            messages.info(request, "Användaren är redan aktiv. Ingen invite behövs.")
        elif not company:
            messages.error(request, "Användaren är inte kopplad till något företag. Koppla användaren först.")
        else:
            # Revoka tidigare aktiva invites
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

            # Bygg ny länk (UUID)
            invite_link = request.build_absolute_uri(
                reverse("accounts:accept_invite_uuid", kwargs={"invite_id": invite.id})
            )
            open_invite_modal = True
            messages.success(request, "Ny invite-länk genererad.")

    # Processer som användaren skapat
    processes = (
        TestProcess.objects
        .filter(created_by=user_obj)
        .order_by("-created_at")
    )
    active_processes = processes.filter(is_completed=False) if hasattr(TestProcess, "is_completed") else processes

    # Hämta user_account
    try:
        user_account = UserAccountAccess.objects.select_related("account").get(user=user_obj)
    except UserAccountAccess.DoesNotExist:
        user_account = None

    return render(request, "admin/accounts/user_detail.html", {
        "u": user_obj,
        "company": company,  # valfritt att visa i UI
        "processes": processes,
        "active_processes": active_processes,
        "pending_invite": pending_invite,
        "user_account": user_account,
        "invite_link": invite_link,                # ✅ bara efter POST
        "open_invite_modal": open_invite_modal,    # ✅ öppna modal efter POST
    })

@login_required
def admin_customers_list(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    customers = (
        User.objects
        .filter(is_superuser=False, is_staff=False)
        .prefetch_related("account_accesses__account")
        .order_by("-date_joined")
    )
    return render(request, "admin/accounts/customers_list.html", {"customers": customers})


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

    return render(request, "admin/accounts/customers_create.html", {"form": form})


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

    return render(request, "admin/accounts/process_detail.html", {
        "process": process,
        "invitations": invitations,
        "status_counts": status_counts,
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

    return render(request, "admin/accounts/candidate_detail.html", {
        "process": process,
        "candidate": candidate,
        "invitation": invitation,
        "dummy_profile": dummy_profile,
        "dummy_abilities": dummy_abilities,
    })


@login_required
@admin_required
def admin_profile(request):
    user = request.user
    profile = user.profile

    if request.method == "POST":
        account_form = PortalAccountForm(request.POST, instance=user)
        image_form = ProfileImageForm(request.POST, request.FILES, instance=profile)

        if account_form.is_valid() and image_form.is_valid():
            account_form.save()
            image_form.save()
            messages.success(request, "Admin profile updated.")
            return redirect("accounts:admin_profile")
        messages.error(request, "Please correct the errors below.")
    else:
        account_form = PortalAccountForm(instance=user)
        image_form = ProfileImageForm(instance=profile)

    return render(
        request,
        "admin/accounts/admin/profile.html",
        {"account_form": account_form, "image_form": image_form},
    )


class AdminPasswordChangeView(PasswordChangeView):
    template_name = "admin/accounts/admin/password_change.html"
    success_url = reverse_lazy("accounts:admin_profile")

    def form_valid(self, form):
        messages.success(self.request, "Du har bytt lösenord.")
        return super().form_valid(form)



@login_required
@admin_required
def company_list(request):
    companies = (
        Company.objects
        .annotate(
            member_count=Count("memberships", distinct=True),
            orgunit_count=Count("org_units", distinct=True),
        )
        .order_by("name")
    )
    return render(request, "admin/accounts/companies/company_list.html", {
        "companies": companies,
    })


@login_required
@admin_required
def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)

    # Forms (default)
    add_form = CompanyMemberAddForm()
    invite_form = CompanyInviteMemberForm()
    orgunit_form = OrgUnitForm(company=company)

    # Selected unit (för högersidan)
    selected_unit_id = request.GET.get("org_unit")
    selected_unit = None
    selected_unit_members = []

    if selected_unit_id:
        try:
            selected_unit = OrgUnit.objects.get(pk=selected_unit_id, company=company)
            selected_unit_members = (
                UserOrgUnitAccess.objects
                .filter(org_unit=selected_unit)
                .select_related("user")
                .order_by("user__email")
            )
        except OrgUnit.DoesNotExist:
            selected_unit = None
            selected_unit_members = []

    # Org tree (vänstersidan) – byggs ALLTID (GET och POST)
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

    # Memberships (overview-tabellen)
    memberships = (
        CompanyMember.objects
        .filter(company=company)
        .select_related("user")
        .order_by("user__email")
    )

    # (valfritt) Customers – byt till company membership istället för account_accesses
    customers = (
        User.objects
        .filter(
            is_staff=False,
            is_superuser=False,
            company_memberships__company=company,
        )
        .distinct()
        .order_by("email")
    )

    # POST actions
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_orgunit":
            orgunit_form = OrgUnitForm(request.POST, company=company)
            if orgunit_form.is_valid():
                unit = orgunit_form.save(commit=False)
                unit.company = company
                unit.save()
                messages.success(request, f"Enhet '{unit.name}' skapad.")
                return redirect(
                    f"{reverse('accounts:company_detail', kwargs={'pk': company.pk})}?tab=accounts&org_unit={unit.pk}"
                )
            messages.error(request, "Kunde inte skapa enhet. Kontrollera fälten.")

        elif action == "add_members":
            add_form = CompanyMemberAddForm(request.POST)
            if add_form.is_valid():
                users = add_form.cleaned_data["users"]
                role = add_form.cleaned_data["role"]

                created = 0
                updated = 0
                for u in users:
                    obj, was_created = CompanyMember.objects.update_or_create(
                        company=company,
                        user=u,
                        defaults={"role": role},
                    )
                    created += 1 if was_created else 0
                    updated += 0 if was_created else 1

                if created:
                    messages.success(request, f"{created} användare lades till.")
                if updated:
                    messages.info(request, f"{updated} användare fanns redan och fick rollen uppdaterad.")

                return redirect("accounts:company_detail", pk=company.pk)

            messages.error(request, "Kunde inte lägga till användare. Kontrollera formuläret.")

        elif action == "invite_member":
            invite_form = CompanyInviteMemberForm(request.POST)
            if invite_form.is_valid():
                email = invite_form.cleaned_data["email"]
                first_name = invite_form.cleaned_data.get("first_name", "")
                last_name = invite_form.cleaned_data.get("last_name", "")

                with transaction.atomic():
                    user, created_user = User.objects.get_or_create(
                        email=email,
                        defaults={
                            "username": email,  # om du fortfarande använder username
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

                    # Koppla till företag
                    CompanyMember.objects.get_or_create(company=company, user=user)

                    invite_link = None
                    open_invite_modal = False

                    if not user.is_active:
                        if user.has_usable_password():
                            user.set_unusable_password()
                        user.save()

                        invite_link = build_invite_link(request, user)
                        open_invite_modal = True

                messages.success(request, f"Inbjudan skapad för {email}.")

                # Rendera samma sida men med invite_link så modalen kan visa länken
                return render(request, "admin/accounts/companies/company_detail.html", {
                    "company": company,
                    "memberships": memberships,
                    "add_form": add_form,
                    "invite_form": CompanyInviteMemberForm(),
                    "customers": customers,

                    "orgunit_form": orgunit_form,
                    "root_units": root_units,
                    "children_map": children_map,
                    "selected_unit": selected_unit,
                    "selected_unit_members": selected_unit_members,

                    "invite_link": invite_link,
                    "invite_email": email,
                    "open_invite_modal": open_invite_modal,
                    "active_tab": request.GET.get("tab", "overview"),
                })

            messages.error(request, "Kunde inte bjuda in användare. Kontrollera fälten.")

    # Default render (GET eller POST med valideringsfel)
    return render(request, "admin/accounts/companies/company_detail.html", {
        "company": company,
        "memberships": memberships,
        "add_form": add_form,
        "invite_form": invite_form,
        "customers": customers,

        "orgunit_form": orgunit_form,
        "root_units": root_units,
        "children_map": children_map,
        "selected_unit": selected_unit,
        "selected_unit_members": selected_unit_members,

        "active_tab": request.GET.get("tab", "overview"),
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