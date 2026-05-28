"""
@safe_view decorator — wraps any view function with error catching.
Usage:
    @safe_view
    def my_view(request):
        ...
"""
from functools import wraps
from django.shortcuts import render
from .error_logger import log_error


def safe_view(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            log_error(request, e)
            return render(request, 'errors/500.html', status=500)
    return wrapper
