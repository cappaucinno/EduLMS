from django.contrib import admin
from .models import ErrorLog


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display  = ['created_at', 'error_type', 'short_message', 'url', 'user_role', 'severity', 'resolved']
    list_filter   = ['error_type', 'severity', 'resolved', 'user_role', 'created_at']
    search_fields = ['error_type', 'message', 'url', 'traceback']
    readonly_fields = [
        'error_type', 'message', 'traceback', 'url',
        'method', 'user', 'user_role', 'post_data', 'extra', 'created_at'
    ]
    list_editable = ['resolved', 'severity']
    ordering      = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page = 30

    actions = ['mark_resolved', 'mark_critical']

    @admin.action(description='Mark selected as Resolved')
    def mark_resolved(self, request, queryset):
        queryset.update(resolved=True)

    @admin.action(description='Mark selected as Critical')
    def mark_critical(self, request, queryset):
        queryset.update(severity='critical')

    def short_message(self, obj):
        return obj.message[:80] + ('…' if len(obj.message) > 80 else '')
    short_message.short_description = 'Message'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
