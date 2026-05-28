import json
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from core.error_logger import log_error


# Paths that bypass maintenance mode entirely
MAINTENANCE_WHITELIST = (
    '/superadmin/',
    '/accounts/login/',
    '/accounts/logout/',
    '/admin/',
    '/static/',
    '/media/',
    '/api/auth/login/',
    '/api/auth/token/',
    '/maintenance/',
)


class MaintenanceModeMiddleware:
    """
    Intercepts all requests when maintenance mode is ON.
    - Superusers always pass through.
    - Whitelisted paths always pass through.
    - Everyone else sees the maintenance page (HTML or JSON for API).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check maintenance mode (cached via settings singleton)
        try:
            from core.models import SiteSettings
            settings_obj = SiteSettings.get()
        except Exception:
            return self.get_response(request)

        if settings_obj.is_in_maintenance():
            # Superusers always pass through
            if request.user.is_authenticated and request.user.is_superuser:
                return self.get_response(request)

            # Whitelisted paths pass through
            path = request.path
            for prefix in MAINTENANCE_WHITELIST:
                if path.startswith(prefix):
                    return self.get_response(request)

            # API requests get JSON
            accept = request.META.get('HTTP_ACCEPT', '')
            if 'application/json' in accept or path.startswith('/api/'):
                return HttpResponse(
                    json.dumps({
                        'error': 'maintenance',
                        'message': settings_obj.maintenance_message,
                        'title': settings_obj.maintenance_title,
                        'ends_at': settings_obj.maintenance_end_time.isoformat()
                                   if settings_obj.maintenance_end_time else None,
                    }),
                    content_type='application/json',
                    status=503,
                )

            # Everyone else → HTML maintenance page
            html = render_to_string('maintenance/maintenance.html', {
                'settings': settings_obj,
                'now': timezone.now(),
            })
            return HttpResponse(html, status=503)

        return self.get_response(request)


class SiteBannerMiddleware:
    """Injects site banner into template context via request attribute."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from core.models import SiteSettings
            s = SiteSettings.get()
            request.site_banner = s if s.banner_enabled and s.banner_message else None
            request.site_settings = s
        except Exception:
            request.site_banner = None
            request.site_settings = None
        return self.get_response(request)


class ErrorDetectionMiddleware:
    """
    Automatically catches any unhandled exception in any view,
    logs it to the ErrorLog table, then re-raises so Django
    can show the normal error page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        try:
            log_error(request, exception)
        except Exception:
            pass  # Never let the logger itself crash the app
        return None
