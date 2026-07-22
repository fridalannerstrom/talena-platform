from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from apps.core.utils.auth import is_admin as is_admin_user

from .forms import AccountForm, ProfileImageForm


@login_required
def portal_settings(request):
    user = request.user
    profile = user.profile

    is_admin = is_admin_user(user)

    if is_admin:
        template_name = "admin/portal/settings.html"
    else:
        template_name = "customer/portal/settings.html"

    account_form = AccountForm(
        instance=user
    )

    image_form = ProfileImageForm(
        instance=profile
    )

    password_form = PasswordChangeForm(
        user=user
    )

    if request.method == "POST":
        form_type = request.POST.get(
            "form_type"
        )

        if form_type == "avatar":
            image_form = ProfileImageForm(
                request.POST,
                request.FILES,
                instance=profile,
            )

            if image_form.is_valid():
                image_form.save()

                messages.success(
                    request,
                    _("Profile photo updated."),
                )

                return redirect(
                    "portal:settings"
                )

            messages.error(
                request,
                _(
                    "Could not upload image. "
                    "Please try again."
                ),
            )

        elif form_type == "remove_avatar":
            if profile.image:
                profile.image.delete(
                    save=False
                )

                profile.image = None

                profile.save(
                    update_fields=["image"]
                )

            messages.success(
                request,
                _("Profile photo removed."),
            )

            return redirect(
                "portal:settings"
            )

        elif form_type == "profile":
            account_form = AccountForm(
                request.POST,
                instance=user,
            )

            image_form = ProfileImageForm(
                request.POST,
                request.FILES,
                instance=profile,
            )

            if (
                account_form.is_valid()
                and image_form.is_valid()
            ):
                account_form.save()
                image_form.save()

                messages.success(
                    request,
                    _("Settings updated."),
                )

                return redirect(
                    "portal:settings"
                )

            messages.error(
                request,
                _("Please correct the errors below."),
            )

        elif form_type == "password":
            password_form = PasswordChangeForm(
                user=user,
                data=request.POST,
            )

            if password_form.is_valid():
                password_form.save()

                update_session_auth_hash(
                    request,
                    user,
                )

                messages.success(
                    request,
                    _("Password updated successfully."),
                )

                return redirect(
                    "portal:settings"
                )

            messages.error(
                request,
                _(
                    "Please correct the password "
                    "errors below."
                ),
            )

        else:
            messages.error(
                request,
                _("Unknown form submission."),
            )

    return render(
        request,
        template_name,
        {
            "account_form": account_form,
            "image_form": image_form,
            "password_form": password_form,
            "is_admin": is_admin,
        },
    )