# apps/accounts/decorators.py
from functools import wraps
from django.http import HttpResponseForbidden
from apps.core.utils.auth import is_admin

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Not allowed")

        # Tillåt både "din admin" och Django superuser/staff om du vill
        if is_admin(request.user) or request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("Not allowed")

    return _wrapped