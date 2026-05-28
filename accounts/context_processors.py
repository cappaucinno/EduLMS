from .models import User
from django.utils import timezone


def pending_approvals(request):
    pending_students = 0
    pending_teachers = 0
    unread_announcements = 0
    unread_ann_ids = []

    if request.user.is_authenticated:
        if request.user.role == 'teacher':
            pending_students = User.objects.filter(role='student', is_approved=False).count()

        if request.user.is_superuser or request.user.role == 'admin':
            pending_teachers = User.objects.filter(role='teacher', is_approved=False).count()
            pending_students = User.objects.filter(role='student', is_approved=False).count()

        # Unread announcements for this user
        try:
            from courses.models import Announcement, AnnouncementRead
            role = request.user.role
            grade = request.user.grade_level or ''

            audience_filter = ['all']
            if role == 'student':
                audience_filter += ['students', f'grade_{grade}']
            elif role == 'teacher':
                audience_filter += ['teachers']

            visible_ids = Announcement.objects.filter(
                audience__in=audience_filter
            ).filter(
                scheduled_at__isnull=True
            ).values_list('id', flat=True) | Announcement.objects.filter(
                audience__in=audience_filter,
                scheduled_at__lte=timezone.now()
            ).values_list('id', flat=True)

            read_ids = AnnouncementRead.objects.filter(
                user=request.user, is_read=True
            ).values_list('announcement_id', flat=True)

            unread_ids_qs = set(visible_ids) - set(read_ids)
            unread_announcements = len(unread_ids_qs)
            unread_ann_ids = list(unread_ids_qs)
        except Exception:
            pass

    sa_error_count = 0
    pending_total = 0
    if request.user.is_authenticated and request.user.is_superuser:
        from core.models import ErrorLog
        sa_error_count = ErrorLog.objects.filter(resolved=False).count()
        pending_total = (
            User.objects.filter(role='teacher', is_approved=False).count() +
            User.objects.filter(role='student', is_approved=False).count()
        )

    # Site settings (maintenance, banner)
    try:
        from core.models import SiteSettings
        site = SiteSettings.get()
    except Exception:
        site = None

    return {
        'pending_approvals':   pending_students,
        'pending_teachers':    pending_teachers,
        'unread_count':        unread_announcements,
        'unread_ann_ids':      unread_ann_ids,
        'sa_error_count':      sa_error_count,
        'pending_total':       pending_total,
        'site':                site,
    }
