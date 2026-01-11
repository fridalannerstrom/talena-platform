from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from apps.accounts.forms import CreateCustomerUserForm

def home(request):
    return JsonResponse({"app": "Talena", "status": "alive"})

def health(request):
    return JsonResponse({"status": "ok"})


def _is_admin(user):
    return getattr(user, "role", None) == "admin" or user.is_staff or user.is_superuser


@login_required
def customer_dashboard(request):
    if _is_admin(request.user):
        # Admin ska inte hamna här (valfritt)
        return HttpResponseForbidden("Admins should use the admin dashboard.")
    return render(request, "core/dashboards/customer_dashboard.html")

@login_required
def admin_dashboard(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden("No access.")

    if request.method == "POST":
        form = CreateCustomerUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("admin_dashboard")
    else:
        form = CreateCustomerUserForm()

    return render(request, "core/dashboards/admin_dashboard.html", {"form": form})