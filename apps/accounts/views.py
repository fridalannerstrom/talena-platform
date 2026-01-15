from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from apps.core.utils.auth import is_admin

from .forms import InviteUserForm
from .services.invites import send_invite_email

from django.shortcuts import render, get_object_or_404

from apps.processes.models import TestProcess 

User = get_user_model()


@login_required
def post_login_redirect(request):
    if is_admin(request.user):
        return redirect("admin_dashboard")
    return redirect("customer_dashboard")


@login_required
def invite_user(request):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    if request.method != "POST":
        return redirect("admin_dashboard")

    form = InviteUserForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Could not create invite. Check the form fields.")
        return redirect("admin_dashboard")

    user = form.save(commit=False)
    user.set_unusable_password()
    user.is_active = False
    user.save()

    send_invite_email(request, user)
    messages.success(request, f"Invite sent to {user.email}.")

    return redirect("admin_dashboard")


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
            return redirect("post_login_redirect")
    else:
        form = SetPasswordForm(user)

    return render(request, "accounts/accept_invite.html", {"form": form, "user": user})



@login_required
def admin_user_detail(request, pk):
    if not is_admin(request.user):
        return HttpResponseForbidden("No access.")

    user_obj = get_object_or_404(User, pk=pk)

    # Processer som användaren skapat (ditt befintliga mönster)
    processes = (
        TestProcess.objects
        .filter(created_by=user_obj)
        .order_by("-created_at")  # justera om du har annat fält
    )

    # Pågående vs klara (om du har statusfält)
    active_processes = processes.filter(is_completed=False) if hasattr(TestProcess, "is_completed") else processes
    pending_invite = not user_obj.is_active

    return render(request, "admin/accounts/user_detail.html", {
        "u": user_obj,
        "processes": processes,
        "active_processes": active_processes,
        "pending_invite": pending_invite,
    })