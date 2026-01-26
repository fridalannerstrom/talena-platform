from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from .forms import AccountForm

@login_required
def portal_settings(request):
    user = request.user

    if request.method == "POST":
        form = AccountForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your settings have been updated.")
            return redirect("portal:settings")
        messages.error(request, "Please correct the errors below.")
    else:
        form = AccountForm(instance=user)

    return render(request, "customer/portal/settings.html", {"form": form})


class PortalPasswordChangeView(PasswordChangeView):
    template_name = "customer/portal/password_change.html"
    success_url = reverse_lazy("portal:settings")

    def form_valid(self, form):
        messages.success(self.request, "You have successfully changed your password.")
        return super().form_valid(form)