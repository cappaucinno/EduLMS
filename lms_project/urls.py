from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from core.api_views import announcements_api
from django.views.generic import TemplateView
from django.urls import path, include

# ─── Custom Error Handlers ────────────────────────────────────────────────────
handler400 = 'core.views.error_400'
handler403 = 'core.views.error_403'
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'


def home(request):
    return redirect('/dashboard/') if request.user.is_authenticated else redirect('/accounts/login/')


urlpatterns = [
    path('admin/',     admin.site.urls),
    path('',           home),
    path('accounts/',  include('accounts.urls')),
    path('auth/',       include('allauth.urls')),  # Google OAuth
    path('teacher/',   include('teacher.urls')),
    path('student/',   include('student.urls')),
    path('dashboard/', include('accounts.dashboard_urls')),
    path('system/',    include('core.urls')),
    path('api/',       include('core.api_urls')),  # REST API
    path('api/v1/',      include('api.urls', namespace='api')),
    path('superadmin/',  include('superadmin.urls')),
    path('api/announcements/', announcements_api, name='announcements_api'),
    path('docs/document/',     TemplateView.as_view(template_name='docs/document.html'),     name='doc_document'),
    path('docs/changelog/',    TemplateView.as_view(template_name='docs/changelog.html'),    name='doc_changelog'),
    path('docs/presentation/', TemplateView.as_view(template_name='docs/presentation.html'), name='doc_presentation'),
    path('docs/instruction/',  TemplateView.as_view(template_name='docs/instruction.html'),  name='doc_instruction'),

    path('maintenance/', include('maintenance.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
