import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from accounts.models import User, PasswordResetToken
from courses.models import Room, RoomStudent, Assignment, Submission, Announcement
from assessments.models import Grade
from core.models import ErrorLog, SiteSettings

logger = logging.getLogger('edulms')


def superadmin_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            return redirect('/accounts/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@superadmin_required
def dashboard(request):
    s = SiteSettings.get()
    total_users      = User.objects.exclude(is_superuser=True).count()
    total_students   = User.objects.filter(role='student').count()
    total_teachers   = User.objects.filter(role='teacher').count()
    pending_teachers = User.objects.filter(role='teacher', is_approved=False).count()
    pending_students = User.objects.filter(role='student', is_approved=False).count()
    total_rooms      = Room.objects.count()
    total_assignments  = Assignment.objects.count()
    total_submissions  = Submission.objects.count()
    total_announcements = Announcement.objects.count()
    recent_errors    = ErrorLog.objects.filter(resolved=False).count()
    week_ago = timezone.now() - timezone.timedelta(days=7)
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()
    new_subs_week  = Submission.objects.filter(submitted_at__gte=week_ago).count()
    recent_users   = User.objects.exclude(is_superuser=True).order_by('-date_joined')[:8]
    return render(request, 'superadmin/dashboard.html', {
        'total_users': total_users, 'total_students': total_students,
        'total_teachers': total_teachers, 'pending_teachers': pending_teachers,
        'pending_students': pending_students, 'total_rooms': total_rooms,
        'total_assignments': total_assignments, 'total_submissions': total_submissions,
        'total_announcements': total_announcements, 'recent_errors': recent_errors,
        'new_users_week': new_users_week, 'new_subs_week': new_subs_week,
        'recent_users': recent_users, 'site': s,
    })


# ─── USER MANAGEMENT ─────────────────────────────────────────────────────────

@superadmin_required
def user_list(request):
    role   = request.GET.get('role', '')
    status = request.GET.get('status', '')
    search = request.GET.get('q', '')
    users = User.objects.exclude(is_superuser=True).order_by('is_approved', 'role', '-date_joined')
    if role:
        users = users.filter(role=role)
    if status == 'pending':
        users = users.filter(is_approved=False)
    elif status == 'approved':
        users = users.filter(is_approved=True)
    if search:
        from django.db.models import Q
        users = users.filter(
            Q(username__icontains=search) | Q(email__icontains=search) |
            Q(first_name__icontains=search) | Q(last_name__icontains=search)
        )
    return render(request, 'superadmin/user_list.html', {
        'users': users, 'role': role, 'status': status, 'search': search
    })


@superadmin_required
def approve_user(request, pk):
    from django.conf import settings
    from core.email_utils import send_teacher_setup_link, send_student_setup_link
    user = get_object_or_404(User, pk=pk)
    user.is_approved = True
    user.set_unusable_password()
    user.save()
    base_url  = getattr(settings, 'SITE_BASE_URL', None) or request.build_absolute_uri('/').rstrip('/')
    token_obj = PasswordResetToken.generate(user, token_type='setup')
    setup_url = token_obj.get_setup_url(base_url)
    try:
        if user.role == 'teacher':
            send_teacher_setup_link(user, setup_url)
        else:
            send_student_setup_link(user, setup_url)
        messages.success(request, f"✅ {user} approved. Setup link sent to {user.email}.")
    except Exception as e:
        logger.error(f"Setup email failed for {user.email}: {e}")
        messages.warning(request, f"✅ {user} approved. Email failed — share link: {setup_url}")
    return redirect('superadmin_users')


@superadmin_required
def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        name = str(user)
        user.delete()
        messages.success(request, f"User '{name}' deleted.")
        return redirect('superadmin_users')
    return render(request, 'superadmin/confirm_delete.html', {'obj': user})


@superadmin_required
def resend_setup(request, pk):
    from django.conf import settings
    from core.email_utils import send_teacher_setup_link, send_student_setup_link
    user = get_object_or_404(User, pk=pk, is_approved=True)
    base_url  = getattr(settings, 'SITE_BASE_URL', None) or request.build_absolute_uri('/').rstrip('/')
    token_obj = PasswordResetToken.generate(user, token_type='setup')
    setup_url = token_obj.get_setup_url(base_url)
    try:
        if user.role == 'teacher':
            send_teacher_setup_link(user, setup_url)
        else:
            send_student_setup_link(user, setup_url)
        messages.success(request, f"Setup link resent to {user.email}.")
    except Exception as e:
        messages.warning(request, f"Email failed. Manual link: {setup_url}")
    return redirect('superadmin_users')


# ─── ROOMS ───────────────────────────────────────────────────────────────────

@superadmin_required
def room_list(request):
    rooms = Room.objects.all().select_related('teacher').order_by('grade_level', 'subject')
    # Add student count annotation
    for room in rooms:
        room.student_count = RoomStudent.objects.filter(room=room).count()
    return render(request, 'superadmin/room_list.html', {'rooms': rooms})


# ─── ERRORS ──────────────────────────────────────────────────────────────────

@superadmin_required
def error_list(request):
    errors   = ErrorLog.objects.filter(resolved=False).order_by('-created_at')[:50]
    resolved = ErrorLog.objects.filter(resolved=True).count()
    return render(request, 'superadmin/error_list.html', {'errors': errors, 'resolved': resolved})


@superadmin_required
def error_resolve(request, pk):
    err = get_object_or_404(ErrorLog, pk=pk)
    err.resolved = True
    err.save()
    messages.success(request, f"Error #{pk} resolved.")
    return redirect('superadmin_errors')


# ─── MAINTENANCE MODE ─────────────────────────────────────────────────────────

@superadmin_required
def maintenance(request):
    site = SiteSettings.get()
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'enable_maintenance':
            site.maintenance_mode    = True
            site.maintenance_title   = request.POST.get('title', site.maintenance_title)
            site.maintenance_message = request.POST.get('message', site.maintenance_message)
            site.maintenance_started = timezone.now()
            end_time = request.POST.get('end_time', '').strip()
            if end_time:
                from django.utils.dateparse import parse_datetime
                site.maintenance_end_time = parse_datetime(end_time)
            else:
                site.maintenance_end_time = None
            site.updated_by = request.user
            site.save()
            messages.warning(request, "🔴 Maintenance mode ENABLED. Only superadmins can access the site.")

        elif action == 'disable_maintenance':
            site.maintenance_mode    = False
            site.maintenance_end_time = None
            site.updated_by = request.user
            site.save()
            messages.success(request, "🟢 Maintenance mode DISABLED. Site is live again.")

        elif action == 'save_banner':
            site.banner_enabled     = 'banner_enabled' in request.POST
            site.banner_message     = request.POST.get('banner_message', '')[:300]
            site.banner_type        = request.POST.get('banner_type', 'info')
            site.banner_link        = request.POST.get('banner_link', '')
            site.banner_dismissible = 'banner_dismissible' in request.POST
            site.updated_by = request.user
            site.save()
            messages.success(request, "✅ Site banner updated.")

        elif action == 'save_registration':
            site.allow_student_registration = 'allow_students' in request.POST
            site.allow_teacher_registration = 'allow_teachers' in request.POST
            site.registration_message       = request.POST.get('registration_message', '')
            site.updated_by = request.user
            site.save()
            messages.success(request, "✅ Registration settings updated.")

        elif action == 'save_contact':
            site.school_name          = request.POST.get('school_name', '')
            site.school_contact_email = request.POST.get('contact_email', '')
            site.school_contact_phone = request.POST.get('contact_phone', '')
            site.school_website       = request.POST.get('school_website', '')
            site.school_address       = request.POST.get('school_address', '')
            site.updated_by = request.user
            site.save()
            messages.success(request, "✅ School contact info updated.")

        elif action == 'clear_banner':
            site.banner_enabled = False
            site.banner_message = ''
            site.updated_by = request.user
            site.save()
            messages.success(request, "✅ Site banner cleared.")

        return redirect('superadmin_maintenance')

    return render(request, 'superadmin/maintenance.html', {'site': site, 'now': timezone.now()})


# ─── SITE SETTINGS ───────────────────────────────────────────────────────────

@superadmin_required
def site_settings(request):
    from django.conf import settings
    ctx = {
        'site_base_url':  getattr(settings, 'SITE_BASE_URL', ''),
        'school_name':    getattr(settings, 'SCHOOL_NAME', ''),
        'email_backend':  settings.EMAIL_BACKEND,
        'email_user':     settings.EMAIL_HOST_USER,
        'debug':          settings.DEBUG,
        'jitsi_domain':   getattr(settings, 'JITSI_DOMAIN', 'meet.jit.si'),
        'site':           SiteSettings.get(),
    }
    return render(request, 'superadmin/site_settings.html', ctx)


# ─── API DOCS ────────────────────────────────────────────────────────────────

@superadmin_required
def api_docs(request):
    return render(request, 'superadmin/api_docs.html', {})
