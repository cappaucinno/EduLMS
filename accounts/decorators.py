from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from functools import wraps


def role_required(*roles):
    """Restrict view access to specific roles."""
    def decorator(view_func):
        @wraps(view_func)
        def inner(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('/accounts/login/')
            if request.user.role in roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden(
                "<h2>403 - Access Denied</h2>"
                f"<p>Your role (<strong>{request.user.role}</strong>) cannot access this page.</p>"
                "<a href='/dashboard/'>Go to Dashboard</a>"
            )
        return inner
    return decorator
