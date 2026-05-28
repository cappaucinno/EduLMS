from django.db import models
from django.conf import settings


class ErrorLog(models.Model):
    SEVERITY_CHOICES = (
        ('low',      'Low'),
        ('medium',   'Medium'),
        ('high',     'High'),
        ('critical', 'Critical'),
    )

    error_type  = models.CharField(max_length=200)
    message     = models.TextField()
    traceback   = models.TextField(blank=True)
    url         = models.CharField(max_length=500, blank=True)
    method      = models.CharField(max_length=10, blank=True)
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='errors'
    )
    user_role   = models.CharField(max_length=20, default='anonymous')
    post_data   = models.TextField(blank=True, default='{}')
    extra       = models.TextField(blank=True, default='{}')
    severity    = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    resolved    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name      = 'Error Log'
        verbose_name_plural = 'Error Logs'

    def __str__(self):
        return f"[{self.error_type}] {self.message[:60]} — {self.created_at:%Y-%m-%d %H:%M}"


class SiteSettings(models.Model):
    """
    Singleton model — only one row ever exists (pk=1).
    Controls maintenance mode, site-wide announcements, etc.
    """
    # ── Maintenance ───────────────────────────────────────────────────────────
    maintenance_mode      = models.BooleanField(default=False)
    maintenance_title     = models.CharField(max_length=200, default="We'll be right back!")
    maintenance_message   = models.TextField(
        default="EduLMS is currently undergoing scheduled maintenance. "
                "We'll be back shortly. Thank you for your patience."
    )
    maintenance_end_time  = models.DateTimeField(
        null=True, blank=True,
        help_text="Expected time maintenance ends (shown to users). Leave blank to hide."
    )
    maintenance_started   = models.DateTimeField(null=True, blank=True)

    # ── Site banner ───────────────────────────────────────────────────────────
    banner_enabled        = models.BooleanField(default=False)
    banner_message        = models.CharField(max_length=300, blank=True)
    banner_type           = models.CharField(
        max_length=10,
        choices=[('info','Info'),('warning','Warning'),('success','Success'),('danger','Danger')],
        default='info'
    )
    banner_link           = models.URLField(blank=True)
    banner_dismissible    = models.BooleanField(default=True)

    # ── Registration control ──────────────────────────────────────────────────
    allow_student_registration = models.BooleanField(default=True)
    allow_teacher_registration = models.BooleanField(default=True)
    registration_message       = models.CharField(max_length=300, blank=True,
        help_text="Shown when registration is closed.")

    # ── Contact / School ──────────────────────────────────────────────────────
    school_name           = models.CharField(max_length=200, blank=True)
    school_contact_email  = models.EmailField(blank=True)
    school_contact_phone  = models.CharField(max_length=30, blank=True)
    school_website        = models.URLField(blank=True)
    school_address        = models.TextField(blank=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='settings_updates'
    )

    class Meta:
        verbose_name = verbose_name_plural = 'Site Settings'

    def __str__(self):
        status = '🔴 MAINTENANCE' if self.maintenance_mode else '🟢 Online'
        return f"Site Settings [{status}]"

    @classmethod
    def get(cls):
        """Always returns the single settings object, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def is_in_maintenance(self):
        """True only if maintenance_mode is on and end_time hasn't passed yet."""
        if not self.maintenance_mode:
            return False
        if self.maintenance_end_time:
            from django.utils import timezone
            if timezone.now() > self.maintenance_end_time:
                # Auto-disable when end time passes
                self.maintenance_mode = False
                self.save(update_fields=['maintenance_mode'])
                return False
        return True
