from django.shortcuts import render
from .models import MaintenanceSettings


def preview(request):
    settings = MaintenanceSettings.objects.first()

    if not settings:
        settings = MaintenanceSettings.objects.create()

    return render(request, 'maintenance/maintenance.html', {
        'settings': settings,
        'is_preview': True
    })