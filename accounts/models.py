from django.contrib.auth.models import AbstractUser
from django.db import models


GRADE_CHOICES = (
    ('7',  'Grade 7'),
    ('8',  'Grade 8'),
    ('9',  'Grade 9'),
    ('10', 'Grade 10'),
    ('11', 'Grade 11'),
    ('12', 'Grade 12'),
)


class User(AbstractUser):
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    is_approved = models.BooleanField(
        default=False,
        help_text='Teachers/Admins are auto-approved. Students require teacher approval.'
    )
    # Only relevant for students — their grade level
    grade_level = models.CharField(
        max_length=2, choices=GRADE_CHOICES, blank=True, null=True,
        help_text='Grade level (students only)'
    )

    profile_image = models.ImageField(
        upload_to='profile_images/',
        blank=True, null=True,
        help_text='Profile photo'
    )

    def is_admin(self):    return self.role == 'admin'
    def is_teacher(self):  return self.role == 'teacher'
    def is_student(self):  return self.role == 'student'

    def get_grade_display_label(self):
        return dict(GRADE_CHOICES).get(self.grade_level, '—')

    def __str__(self):
        if self.role == 'student' and self.grade_level:
            return f"{self.get_full_name() or self.username} (Grade {self.grade_level})"
        return f"{self.get_full_name() or self.username} ({self.role})"


import random
import string
from django.utils import timezone
from datetime import timedelta


class OTPVerification(models.Model):
    """Temporary OTP record for student email verification during registration."""
    # Store form data as JSON until OTP verified
    email       = models.EmailField()
    otp_code    = models.CharField(max_length=6)
    form_data   = models.JSONField()          # serialised registration data
    created_at  = models.DateTimeField(auto_now_add=True)
    attempts    = models.IntegerField(default=0)
    is_used     = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.email} ({self.otp_code})"

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def is_valid(self, code):
        return (
            not self.is_used
            and not self.is_expired()
            and self.attempts < 5
            and self.otp_code == code.strip()
        )

    @classmethod
    def generate(cls, email, form_data):
        """Delete old OTPs for this email and create a fresh one."""
        cls.objects.filter(email=email).delete()
        code = ''.join(random.choices(string.digits, k=6))
        return cls.objects.create(
            email=email,
            otp_code=code,
            form_data=form_data,
        )


class PasswordResetToken(models.Model):
    """
    Secure token for:
      - 'setup'  : first-time password setup (sent on account approval)
      - 'reset'  : forgot-password recovery
    """
    TOKEN_TYPE_CHOICES = (
        ('setup', 'Password Setup'),
        ('reset', 'Password Reset'),
    )
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token       = models.CharField(max_length=128, unique=True)
    token_type  = models.CharField(max_length=10, choices=TOKEN_TYPE_CHOICES, default='reset')
    created_at  = models.DateTimeField(auto_now_add=True)
    is_used     = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        # Setup links: 72 hours | Reset links: 1 hour
        limit = timedelta(hours=72 if self.token_type == 'setup' else 1)
        return timezone.now() > self.created_at + limit

    def is_valid(self):
        return not self.is_used and not self.is_expired()

    @classmethod
    def generate(cls, user, token_type='reset'):
        import secrets
        # Invalidate old tokens of same type for this user
        cls.objects.filter(user=user, token_type=token_type, is_used=False).update(is_used=True)
        token = secrets.token_urlsafe(64)
        return cls.objects.create(user=user, token=token, token_type=token_type)

    def get_setup_url(self, base_url=None):
        from django.conf import settings
        base = (base_url or getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000')).rstrip('/')
        return f"{base}/accounts/setup/password/{self.token}/"

    def __str__(self):
        return f"{self.token_type} token for {self.user.username}"
