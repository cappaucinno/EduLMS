from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.conf import settings
from .models import User, OTPVerification, PasswordResetToken
import logging

logger = logging.getLogger('edulms')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ['username', 'get_full_name', 'role', 'grade_level',
                     'is_approved', 'approval_status', 'is_active', 'date_joined']
    list_filter   = ['role', 'is_approved', 'is_active', 'grade_level']
    list_editable = ['is_approved']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering      = ['is_approved', 'role', '-date_joined']
    list_per_page = 30

    fieldsets = UserAdmin.fieldsets + (
        ('Role & Approval', {'fields': ('role', 'grade_level', 'is_approved')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Approval', {'fields': ('role', 'grade_level', 'is_approved')}),
    )

    actions = ['approve_and_send_setup', 'revoke_selected']

    @admin.action(description='✅ Approve & send password setup link')
    def approve_and_send_setup(self, request, queryset):
        from core.email_utils import send_teacher_setup_link, send_student_setup_link
        base_url = getattr(settings, 'SITE_BASE_URL', request.build_absolute_uri('/').rstrip('/'))
        count = 0
        failed = []

        for user in queryset.filter(is_approved=False):
            user.is_approved = True
            user.set_unusable_password()
            user.save()

            token_obj = PasswordResetToken.generate(user, token_type='setup')
            setup_url = token_obj.get_setup_url(base_url)

            try:
                if user.role == 'teacher':
                    send_teacher_setup_link(user, setup_url)
                else:
                    send_student_setup_link(user, setup_url)
                count += 1
                logger.info(f"Setup link sent to {user.email}: {setup_url}")
            except Exception as e:
                failed.append(user.username)
                logger.error(f"Setup email failed for {user.email}: {e}")

        msg = f'{count} account(s) approved and password setup link emailed.'
        if failed:
            msg += f' Failed to email: {", ".join(failed)} — check email settings.'
        self.message_user(request, msg)

    @admin.action(description='❌ Revoke approval')
    def revoke_selected(self, request, queryset):
        updated = queryset.exclude(is_superuser=True).update(is_approved=False)
        self.message_user(request, f'{updated} account(s) approval revoked.')

    def approval_status(self, obj):
        if obj.is_superuser:
            return format_html('<span style="color:#888;font-size:12px;">superuser</span>')
        if obj.is_approved:
            return format_html('<span style="background:#d4edda;color:#155724;padding:2px 8px;border-radius:4px;font-size:11px;">Approved</span>')
        return format_html('<span style="background:#fff3cd;color:#856404;padding:2px 8px;border-radius:4px;font-size:11px;">⏳ Pending</span>')
    approval_status.short_description = 'Status'


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display  = ['email', 'otp_code', 'attempts', 'is_used', 'is_expired_display', 'created_at']
    list_filter   = ['is_used']
    readonly_fields = ['email', 'otp_code', 'form_data', 'created_at', 'attempts', 'is_used']
    ordering = ['-created_at']

    def is_expired_display(self, obj):
        return obj.is_expired()
    is_expired_display.boolean = True
    is_expired_display.short_description = 'Expired?'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display  = ['user', 'token_type', 'is_used', 'is_valid_display', 'created_at']
    list_filter   = ['token_type', 'is_used']
    readonly_fields = ['user', 'token', 'token_type', 'created_at', 'is_used']
    ordering = ['-created_at']

    def is_valid_display(self, obj):
        return obj.is_valid()
    is_valid_display.boolean = True
    is_valid_display.short_description = 'Valid?'
