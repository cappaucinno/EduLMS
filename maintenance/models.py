from django.db import models


class MaintenanceSettings(models.Model):
    maintenance_mode = models.BooleanField(default=False)

    maintenance_title = models.CharField(
        max_length=255,
        default="System Maintenance"
    )

    maintenance_message = models.TextField(
        default="We are currently upgrading EduLMS to improve your experience. Please check back shortly."
    )

    maintenance_end_time = models.DateTimeField(
        null=True,
        blank=True
    )

    school_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    school_contact_email = models.EmailField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Maintenance Setting"
        verbose_name_plural = "Maintenance Settings"

    def __str__(self):
        return f"Maintenance Mode: {'ON' if self.maintenance_mode else 'OFF'}"