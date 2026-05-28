from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User


@receiver(post_save, sender=User)
def auto_approve_superuser(sender, instance, **kwargs):
    """Superusers are always approved with admin role."""
    if instance.is_superuser and (not instance.is_approved or instance.role != 'admin'):
        User.objects.filter(pk=instance.pk).update(role='admin', is_approved=True)
