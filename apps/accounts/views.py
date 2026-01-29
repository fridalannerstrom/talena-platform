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

from .forms import InviteUserForm, AccountForm, UserAccountAccessForm
from .services.invites import send_invite_email
from .decorators import admin_required
from apps.portal.forms import AccountForm as PortalAccountForm, ProfileImageForm
from .models import Account, UserAccountAccess
from .utils.permissions import get_user_accessible_accounts

from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from .models import Company, CompanyMember, Account
from .forms import CompanyMemberAddForm, CompanyMemberRoleForm

User = get_user_model()


# ============================================================================
# BEFINTLIGA VIEWS (dina ursprungliga)
# ============================================================================

@login_required
def admin_user_detail(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    user_obj = get_object_or_404(User, pk=pk)

    # Processer som användaren skapat (ditt befintliga mönster)
    processes = (
        TestProcess.objects
        .filter(created_by=user_obj)
        .order_by("-created_at")
    )

    # Pågående vs klara (om du har statusfält)
    active_processes = processes.filter(is_completed=False) if hasattr(TestProcess, "is_completed") else processes
    pending_invite = not user_obj.is_active

    # Hämta användarens account-koppling
    try:
        user_account = UserAccountAccess.objects.select_related('account').get(user=user_obj)
    except UserAccountAccess.DoesNotExist:
        user_account = None

    return render(request, "admin/accounts/user_detail.html", {
        "u": user_obj,
        "processes": processes,
        "active_processes": active_processes,
        "pending_invite": pending_invite,
        "user_account": user_account,
    })


@login_required
def admin_customers_list(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    customers = (
        User.objects
        .filter(is_superuser=False, is_staff=False)
        .select_related('account_access__account')  # Optimering
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


# ============================================================================
# NYA VIEWS FÖR ACCOUNT HIERARCHY
# ============================================================================

@login_required
def account_hierarchy(request):
    """Visar hierarkisk vy av alla accounts"""
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    # Hämta alla root accounts (de utan parent)
    root_accounts = Account.objects.filter(parent=None).prefetch_related('children')

    # Bygg index
    by_parent = {}
    for a in root_accounts:
        by_parent.setdefault(a.parent_id, []).append(a)

    # Valfritt: sortera snyggt
    for k in by_parent:
        by_parent[k].sort(key=lambda x: (x.name or "").lower())

    nodes = []

    def walk(parent_id=None, level=0):
        for a in by_parent.get(parent_id, []):
            nodes.append({
                "id": a.id,
                "parent_id": a.parent_id,
                "level": level,
                "name": a.name,
                "account_code": a.account_code,
                "has_children": a.children.exists(),
                "full_path": getattr(a, "full_path", ""),
            })
            walk(a.id, level + 1)

    walk(None, 0)
    
    return render(request, "admin/accounts/hierarchy/hierarchy.html", {
        "root_accounts": root_accounts,
    })


@login_required
def account_create(request, parent_id=None):
    """Skapa nytt account (med eller utan parent)"""
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    parent = None
    if parent_id:
        parent = get_object_or_404(Account, id=parent_id)
    
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            if parent:
                account.parent = parent
            account.save()
            messages.success(request, f'Account "{account.name}" skapad!')
            return redirect("accounts:account_hierarchy")
        messages.error(request, "Kunde inte skapa account. Kontrollera fälten.")
    else:
        # Om vi har en parent, pre-fyll parent-fältet
        initial = {}
        if parent:
            initial['parent'] = parent
        form = AccountForm(initial=initial)
    
    return render(request, "admin/accounts/hierarchy/account_form.html", {
        "form": form,
        "parent": parent,
        "is_edit": False,
    })


@login_required
def account_edit(request, pk):
    """Redigera ett befintligt account"""
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    account = get_object_or_404(Account, pk=pk)
    
    if request.method == "POST":
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, f'Account "{account.name}" uppdaterad!')
            return redirect("accounts:account_hierarchy")
        messages.error(request, "Kunde inte uppdatera account.")
    else:
        form = AccountForm(instance=account)
    
    return render(request, "admin/accounts/hierarchy/account_form.html", {
        "form": form,
        "account": account,
        "is_edit": True,
    })


@login_required
def account_delete(request, pk):
    """Ta bort ett account (och alla dess barn!)"""
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    account = get_object_or_404(Account, pk=pk)
    
    if request.method == "POST":
        account_name = account.name
        account.delete()
        messages.success(request, f'Account "{account_name}" borttagen!')
        return redirect("accounts:account_hierarchy")
    
    # Räkna hur många underkonton som kommer försvinna
    descendants_count = len(account.get_descendants())
    
    return render(request, "admin/accounts/hierarchy/account_confirm_delete.html", {
        "account": account,
        "descendants_count": descendants_count,
    })


@login_required
def account_users(request, pk):
    """Visa och hantera användare för ett specifikt account"""
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    account = get_object_or_404(Account, pk=pk)
    
    # Hämta alla users kopplade till detta account
    user_accesses = UserAccountAccess.objects.filter(
        account=account
    ).select_related('user')
    
    # Form för att lägga till ny user
    if request.method == "POST":
        form = UserAccountAccessForm(request.POST)
        if form.is_valid():
            access = form.save(commit=False)
            access.account = account
            access.save()
            messages.success(request, f'Användare "{access.user.email}" tillagd!')
            return redirect("accounts:account_users", pk=account.pk)
        messages.error(request, "Kunde inte lägga till användare.")
    else:
        form = UserAccountAccessForm()
        # Pre-fyll account-fältet
        form.initial['account'] = account
    
    return render(request, "admin/accounts/hierarchy/account_users.html", {
        "account": account,
        "user_accesses": user_accesses,
        "form": form,
    })


@login_required
def account_user_remove(request, pk, user_id):
    """Ta bort en användare från ett account"""
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    account = get_object_or_404(Account, pk=pk)
    user_access = get_object_or_404(UserAccountAccess, account=account, user_id=user_id)
    
    if request.method == "POST":
        user_email = user_access.user.email
        user_access.delete()
        messages.success(request, f'Användare "{user_email}" borttagen från account!')
        return redirect("accounts:account_users", pk=account.pk)
    
    return render(request, "admin/accounts/hierarchy/account_user_confirm_remove.html", {
        "account": account,
        "user_access": user_access,
    })




@login_required
@admin_required
def company_list(request):
    companies = (
        Company.objects
        .annotate(
            member_count=Count("memberships", distinct=True),
            account_count=Count("accounts", distinct=True),
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

    # Members
    memberships = (
        CompanyMember.objects
        .filter(company=company)
        .select_related("user")
        .order_by("user__email")
    )

    add_form = CompanyMemberAddForm()
    if request.method == "POST" and request.POST.get("action") == "add_members":
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

    # Accounts (enkelt overview: root accounts)
    root_accounts = (
        Account.objects
        .filter(company=company, parent__isnull=True)
        .prefetch_related("children")
        .order_by("name")
    )

    return render(request, "admin/accounts/companies/company_detail.html", {
        "company": company,
        "memberships": memberships,
        "add_form": add_form,
        "root_accounts": root_accounts,
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