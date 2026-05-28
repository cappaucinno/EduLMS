"""
EduLMS Error Detection & Logging System
Captures all errors with full context: user, URL, traceback, timestamp.
Stores in SQLite error log table + writes to errors.log file.
"""
import traceback
import logging
import json
from datetime import datetime

logger = logging.getLogger('edulms')


def log_error(request, exception, extra=None):
    """
    Call this anywhere to log an error with full context.
    Usage: log_error(request, exception)
    """
    from core.models import ErrorLog

    tb     = traceback.format_exc()
    method = getattr(request, 'method', 'N/A')
    path   = getattr(request, 'path', 'N/A')
    user   = None
    role   = 'anonymous'

    if hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user
        role = request.user.role

    post_data = {}
    if hasattr(request, 'POST'):
        # Scrub sensitive fields
        post_data = {
            k: ('***' if k.lower() in ('password', 'password2', 'token') else v)
            for k, v in request.POST.items()
        }

    ErrorLog.objects.create(
        error_type  = type(exception).__name__,
        message     = str(exception),
        traceback   = tb,
        url         = path,
        method      = method,
        user        = user,
        user_role   = role,
        post_data   = json.dumps(post_data),
        extra       = json.dumps(extra or {}),
    )

    # Also write to file log
    logger.error(
        f"[{type(exception).__name__}] {exception} | "
        f"URL={path} | User={user} | Role={role}",
        exc_info=True,
    )
