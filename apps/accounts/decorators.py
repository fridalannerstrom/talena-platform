from django.http import HttpResponseForbidden

def admin_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Not allowed")
        if getattr(request.user, "role", None) != "admin":
            return HttpResponseForbidden("Not allowed")
        return view_func(request, *args, **kwargs)
    return _wrapped