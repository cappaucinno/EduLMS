from django.shortcuts import render
from core.error_logger import log_error
from core.decorators import safe_view


def error_400(request, exception=None):
    return render(request, 'errors/400.html', status=400)


def error_403(request, exception=None):
    return render(request, 'errors/403.html', status=403)


def error_404(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def error_500(request):
    return render(request, 'errors/500.html', status=500)


def maintenance_preview(request):
    """Preview the maintenance page (superadmin only)."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    from core.models import SiteSettings
    from django.utils import timezone
    site = SiteSettings.get()
    # Temporarily override for preview
    preview = type('PreviewSettings', (), {
        'maintenance_title': site.maintenance_title or "We'll be right back!",
        'maintenance_message': site.maintenance_message or "EduLMS is undergoing maintenance.",
        'maintenance_end_time': site.maintenance_end_time,
        'school_name': site.school_name,
        'school_contact_email': site.school_contact_email,
    })()
    return render(request, 'maintenance.html', {
        'settings': preview,
        'now': timezone.now(),
        'is_preview': True,
    })
