from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

@login_required
def post_login_redirect(request):
    user = request.user
    if getattr(user, "role", None) == "admin" or user.is_staff or user.is_superuser:
        return redirect("admin_dashboard")
    return redirect("customer_dashboard")
