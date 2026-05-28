from django.http import JsonResponse
from django.utils import timezone
from courses.models import Announcement, AnnouncementRead
from accounts.decorators import role_required


def announcements_api(request):
    """Returns announcements for the logged-in user as JSON."""
    if not request.user.is_authenticated:
        return JsonResponse({'announcements': []})

    role  = request.user.role
    grade = request.user.grade_level or ''

    audience_filter = ['all']
    if role == 'student':
        audience_filter += ['students', f'grade_{grade}']
    elif role == 'teacher':
        audience_filter += ['teachers', 'students']
    else:
        audience_filter = [c[0] for c in Announcement.AUDIENCE_CHOICES]

    anns = Announcement.objects.filter(
        audience__in=audience_filter
    ).filter(
        scheduled_at__isnull=True
    ).select_related('author') | Announcement.objects.filter(
        audience__in=audience_filter,
        scheduled_at__lte=timezone.now()
    ).select_related('author')

    anns = anns.order_by('-pinned', '-created_at')[:50]

    data = []
    for a in anns:
        data.append({
            'id':             a.pk,
            'title':          a.title,
            'content':        a.content,
            'ann_type':       a.ann_type,
            'audience':       a.audience_label(),
            'author':         a.author.get_full_name() or a.author.username if a.author else 'System',
            'pinned':         a.pinned,
            'attachment_url': a.attachment.url if a.attachment else '',
            'link':           a.link,
            'created_at':     a.created_at.strftime('%b %d, %Y %H:%M'),
        })

    return JsonResponse({'announcements': data})
