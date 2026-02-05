from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect

from .forms import AccountForm, ProfileImageForm


@login_required
def portal_settings(request):
    user = request.user
    profile = user.profile

    # Initiera alltid formulären (så render aldrig kraschar)
    account_form = AccountForm(instance=user)
    image_form = ProfileImageForm(instance=profile)
    password_form = PasswordChangeForm(user=user)

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "avatar":
            image_form = ProfileImageForm(request.POST, request.FILES, instance=profile)
            if image_form.is_valid():
                image_form.save()
                messages.success(request, "Profile photo updated.")
                return redirect("portal:settings")
            messages.error(request, "Could not upload image. Please try again.")

        elif form_type == "remove_avatar":
            if profile.image:
                profile.image.delete(save=False)
                profile.image = None
                profile.save(update_fields=["image"])
            messages.success(request, "Profile photo removed.")
            return redirect("portal:settings")

        elif form_type == "profile":
            account_form = AccountForm(request.POST, instance=user)
            image_form = ProfileImageForm(request.POST, request.FILES, instance=profile)
            if account_form.is_valid() and image_form.is_valid():
                account_form.save()
                image_form.save()
                messages.success(request, "Settings updated.")
                return redirect("portal:settings")
            messages.error(request, "Please correct the errors below.")

        elif form_type == "password":
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully.")
                return redirect("portal:settings")
            messages.error(request, "Please correct the password errors below.")

        else:
            messages.error(request, "Unknown form submission.")

    return render(
        request,
        "customer/portal/settings.html",
        {
            "account_form": account_form,
            "image_form": image_form,
            "password_form": password_form,
        },
    )
