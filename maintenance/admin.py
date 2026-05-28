from django.contrib import admin
from .models import MaintenanceSettings


@admin.register(MaintenanceSettings)
class MaintenanceSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'maintenance_mode',
        'maintenance_title',
        'maintenance_end_time',
        'updated_at',
    )

    search_fields = ('maintenance_title',)