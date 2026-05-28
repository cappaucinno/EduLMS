"""
EduLMS REST API
==============
Full API for mobile and third-party apps.

Authentication
--------------
All endpoints require a Bearer JWT token (except /api/auth/login/ and /api/auth/register/).

Get a token:
    POST /api/auth/login/
    { "username": "...", "password": "..." }
    → { "access": "...", "refresh": "...", "user": {...} }

Refresh a token:
    POST /api/auth/token/refresh/
    { "refresh": "..." }

Include in requests:
    Authorization: Bearer <access_token>

Endpoints
---------
AUTH
    POST   /api/auth/login/
    POST   /api/auth/register/
    POST   /api/auth/token/refresh/
    GET    /api/auth/me/
    PATCH  /api/auth/me/

ROOMS
    GET    /api/rooms/                → list my rooms
    GET    /api/rooms/<id>/           → room detail

LESSONS
    GET    /api/rooms/<id>/lessons/   → lessons in room

MATERIALS
    GET    /api/rooms/<id>/materials/ → materials in room

ASSIGNMENTS
    GET    /api/rooms/<id>/assignments/
    GET    /api/assignments/<id>/
    POST   /api/assignments/<id>/submit/   (student)

QUIZZES
    GET    /api/rooms/<id>/quizzes/
    GET    /api/quizzes/<id>/
    POST   /api/quizzes/<id>/submit/   (student)

GRADES
    GET    /api/grades/               → student's grades

ANNOUNCEMENTS
    GET    /api/announcements/
    POST   /api/announcements/<id>/read/

LIVE SESSIONS
    GET    /api/rooms/<id>/live/
    POST   /api/rooms/<id>/live/       (teacher)

NOTIFICATIONS
    GET    /api/notifications/

SUPERADMIN (admin only)
    GET    /api/admin/users/
    POST   /api/admin/users/<id>/approve/
    GET    /api/admin/stats/
"""

import logging
from django.utils import timezone
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import PasswordResetToken
from courses.models import (
    Room, RoomStudent, Lesson, Material, Assignment,
    Submission, Quiz, Question, QuizAttempt,
    Announcement, AnnouncementRead, LiveSession,
)
from assessments.models import Grade

logger = logging.getLogger('edulms')
User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def user_json(user):
    return {
        'id':           user.pk,
        'username':     user.username,
        'first_name':   user.first_name,
        'last_name':    user.last_name,
        'full_name':    user.get_full_name() or user.username,
        'email':        user.email,
        'role':         user.role,
        'grade_level':  user.grade_level,
        'is_approved':  user.is_approved,
        'avatar_url':   user.profile_image.url if user.profile_image else None,
        'date_joined':  user.date_joined.isoformat(),
    }


def room_json(room, request_user=None):
    enrolled = (
        RoomStudent.objects.filter(room=room, student=request_user).exists()
        if request_user and request_user.role == 'student' else True
    )
    return {
        'id':          room.pk,
        'name':        room.name,
        'subject':     room.subject,
        'grade_level': room.grade_level,
        'description': room.description or '',
        'teacher':     user_json(room.teacher),
        'student_count': RoomStudent.objects.filter(room=room).count(),
        'thumbnail_url': room.thumbnail.url if hasattr(room, 'thumbnail') and room.thumbnail else None,
        'is_enrolled': enrolled,
    }


def paginate(queryset, request, serializer_fn):
    paginator = PageNumberPagination()
    paginator.page_size = int(request.GET.get('page_size', 20))
    page = paginator.paginate_queryset(queryset, request)
    data = [serializer_fn(obj) for obj in page] if page else []
    return paginator.get_paginated_response(data)


def error(msg, code=400):
    return Response({'error': msg}, status=code)


def require_role(*roles):
    """Returns error if user role not in roles."""
    def decorator(fn):
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles and not request.user.is_superuser:
                return error('Permission denied.', 403)
            return fn(request, *args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """
    POST /api/auth/login/
    Body: { "username": "...", "password": "..." }
    Returns JWT tokens + user info.
    """
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return error('Username and password are required.')

    user = authenticate(username=username, password=password)
    if not user:
        # Try by email
        try:
            u = User.objects.get(email__iexact=username)
            user = authenticate(username=u.username, password=password)
        except User.DoesNotExist:
            pass

    if not user:
        return error('Invalid username or password.', 401)

    if not user.is_approved and not user.is_superuser:
        return error('Your account is pending approval. You will receive an email once approved.', 403)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
        'token_type': 'Bearer',
        'user': user_json(user),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    """
    POST /api/auth/register/
    Body: { "username", "first_name", "last_name", "email", "grade_level" }
    No password — student sets it after approval via email link.
    """
    data = request.data
    required = ['username', 'first_name', 'last_name', 'email', 'role']
    for f in required:
        if not data.get(f):
            return error(f'{f} is required.')

    if data['role'] not in ('student', 'teacher'):
        return error('Role must be student or teacher.')

    if data['role'] == 'student' and not data.get('grade_level'):
        return error('grade_level is required for students.')

    if User.objects.filter(username__iexact=data['username']).exists():
        return error('Username already taken.')

    if User.objects.filter(email__iexact=data['email']).exists():
        return error('An account with this email already exists.')

    user = User(
        username    = data['username'],
        first_name  = data.get('first_name', ''),
        last_name   = data.get('last_name', ''),
        email       = data['email'].lower(),
        role        = data['role'],
        grade_level = data.get('grade_level') or None,
        is_approved = False,
    )
    user.set_unusable_password()
    user.save()

    try:
        from core.email_utils import send_new_registration_to_admin
        send_new_registration_to_admin(user)
    except Exception as e:
        logger.warning(f"API register: admin notification failed: {e}")

    return Response({
        'message': 'Registration successful. Wait for approval — you will receive an email with a password setup link.',
        'user': {'id': user.pk, 'username': user.username, 'email': user.email},
    }, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_token_refresh(request):
    """
    POST /api/auth/token/refresh/
    Body: { "refresh": "..." }
    """
    from rest_framework_simplejwt.views import TokenRefreshView
    return TokenRefreshView.as_view()(request._request)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def api_me(request):
    """
    GET  /api/auth/me/   → current user info
    PATCH /api/auth/me/  → update first_name, last_name, email
    """
    user = request.user
    if request.method == 'PATCH':
        for field in ('first_name', 'last_name', 'email'):
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return Response({'message': 'Profile updated.', 'user': user_json(user)})

    return Response({'user': user_json(user)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_change_password(request):
    """
    POST /api/auth/change-password/
    Body: { "old_password": "...", "new_password": "..." }
    """
    user = request.user
    old_pw = request.data.get('old_password', '')
    new_pw = request.data.get('new_password', '')

    if not old_pw or not new_pw:
        return error('old_password and new_password are required.')
    if len(new_pw) < 8:
        return error('New password must be at least 8 characters.')
    if not user.check_password(old_pw):
        return error('Current password is incorrect.', 400)

    user.set_password(new_pw)
    user.save()
    return Response({'message': 'Password changed successfully.'})


# ═══════════════════════════════════════════════════════════════════════════════
# ROOMS
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_rooms(request):
    """GET /api/rooms/ — list rooms for current user."""
    user = request.user
    if user.role == 'teacher':
        rooms = Room.objects.filter(teacher=user).order_by('grade_level', 'subject')
    elif user.role == 'student':
        room_ids = RoomStudent.objects.filter(student=user).values_list('room_id', flat=True)
        rooms = Room.objects.filter(pk__in=room_ids).order_by('grade_level', 'subject')
    else:
        rooms = Room.objects.all().order_by('grade_level', 'subject')

    return Response({'rooms': [room_json(r, user) for r in rooms]})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_room_detail(request, pk):
    """GET /api/rooms/<id>/ — room detail."""
    user = request.user
    room = get_object_or_404(Room, pk=pk)
    if user.role == 'student':
        get_object_or_404(RoomStudent, room=room, student=user)
    elif user.role == 'teacher' and room.teacher != user:
        return error('Permission denied.', 403)
    return Response({'room': room_json(room, user)})


# ═══════════════════════════════════════════════════════════════════════════════
# LESSONS
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_lessons(request, pk):
    """GET /api/rooms/<id>/lessons/"""
    room = get_object_or_404(Room, pk=pk)
    _check_room_access(request.user, room)
    lessons = Lesson.objects.filter(room=room).order_by('order', 'pk')
    return Response({'lessons': [
        {
            'id':        l.pk,
            'title':     l.title,
            'content':   l.content,
            'video_url': l.video_url or '',
            'order':     l.order,
        }
        for l in lessons
    ]})


# ═══════════════════════════════════════════════════════════════════════════════
# MATERIALS
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_materials(request, pk):
    """GET /api/rooms/<id>/materials/"""
    room = get_object_or_404(Room, pk=pk)
    _check_room_access(request.user, room)
    mats = Material.objects.filter(room=room).order_by('order', 'pk')
    return Response({'materials': [
        {
            'id':       m.pk,
            'title':    m.title,
            'file_url': m.file.url if m.file else None,
            'link':     m.link or '',
            'order':    m.order,
        }
        for m in mats
    ]})


# ═══════════════════════════════════════════════════════════════════════════════
# ASSIGNMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_assignments(request, pk):
    """GET /api/rooms/<id>/assignments/"""
    room = get_object_or_404(Room, pk=pk)
    _check_room_access(request.user, room)
    assignments = Assignment.objects.filter(room=room).order_by('-due_date')
    user = request.user
    data = []
    for a in assignments:
        sub = None
        if user.role == 'student':
            try:
                s = Submission.objects.get(assignment=a, student=user)
                sub = {
                    'id': s.pk, 'status': s.status,
                    'submitted_at': s.submitted_at.isoformat() if s.submitted_at else None,
                    'grade': None,
                }
                try:
                    g = Grade.objects.get(submission=s)
                    sub['grade'] = {'score': g.score, 'max': a.max_score, 'feedback': g.feedback or ''}
                except Grade.DoesNotExist:
                    pass
            except Submission.DoesNotExist:
                pass
        data.append({
            'id':          a.pk,
            'title':       a.title,
            'description': a.description or '',
            'due_date':    a.due_date.isoformat() if a.due_date else None,
            'max_score':   a.max_score,
            'submission':  sub,
        })
    return Response({'assignments': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_assignment_detail(request, pk):
    """GET /api/assignments/<id>/"""
    a = get_object_or_404(Assignment, pk=pk)
    _check_room_access(request.user, a.room)
    return Response({'assignment': {
        'id':          a.pk,
        'title':       a.title,
        'description': a.description or '',
        'due_date':    a.due_date.isoformat() if a.due_date else None,
        'max_score':   a.max_score,
        'room':        {'id': a.room.pk, 'name': a.room.name},
    }})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_submit_assignment(request, pk):
    """
    POST /api/assignments/<id>/submit/
    Student submits assignment (multipart/form-data with 'file' + optional 'notes').
    """
    if request.user.role != 'student':
        return error('Only students can submit assignments.', 403)
    a = get_object_or_404(Assignment, pk=pk)
    get_object_or_404(RoomStudent, room=a.room, student=request.user)

    if Submission.objects.filter(assignment=a, student=request.user).exists():
        return error('You have already submitted this assignment.', 409)

    if a.due_date and timezone.now() > a.due_date:
        return error('This assignment is past its due date.', 400)

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return error('A file is required.')

    sub = Submission.objects.create(
        assignment  = a,
        student     = request.user,
        file        = uploaded_file,
        notes       = request.data.get('notes', ''),
        status      = 'submitted',
        submitted_at = timezone.now(),
    )
    return Response({
        'message': 'Assignment submitted successfully.',
        'submission_id': sub.pk,
        'submitted_at': sub.submitted_at.isoformat(),
    }, status=201)


# ═══════════════════════════════════════════════════════════════════════════════
# QUIZZES
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_quizzes(request, pk):
    """GET /api/rooms/<id>/quizzes/"""
    room = get_object_or_404(Room, pk=pk)
    _check_room_access(request.user, room)
    quizzes = Quiz.objects.filter(room=room).order_by('-pk')
    user = request.user
    data = []
    for q in quizzes:
        attempt = None
        if user.role == 'student':
            try:
                a = QuizAttempt.objects.get(quiz=q, student=user)
                attempt = {'score': a.score, 'attempted_at': a.attempted_at.isoformat()}
            except QuizAttempt.DoesNotExist:
                pass
        data.append({
            'id':             q.pk,
            'title':          q.title,
            'question_count': q.questions.count(),
            'attempted':      attempt is not None,
            'attempt':        attempt,
        })
    return Response({'quizzes': data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_quiz_detail(request, pk):
    """GET /api/quizzes/<id>/ — returns questions (options only, no correct_answer for students)."""
    q = get_object_or_404(Quiz, pk=pk)
    _check_room_access(request.user, q.room)
    user = request.user

    if user.role == 'student' and QuizAttempt.objects.filter(quiz=q, student=user).exists():
        return error('You have already attempted this quiz.', 409)

    questions = []
    for qs in q.questions.all().order_by('pk'):
        qdata = {
            'id':       qs.pk,
            'text':     qs.text,
            'option_a': qs.option_a,
            'option_b': qs.option_b,
            'option_c': qs.option_c,
            'option_d': qs.option_d,
        }
        # Only teachers/admins see correct answer
        if user.role in ('teacher',) or user.is_superuser:
            qdata['correct_answer'] = qs.correct_answer
        questions.append(qdata)

    return Response({'quiz': {
        'id':        q.pk,
        'title':     q.title,
        'room':      {'id': q.room.pk, 'name': q.room.name},
        'questions': questions,
    }})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_submit_quiz(request, pk):
    """
    POST /api/quizzes/<id>/submit/
    Body: { "answers": {"<question_id>": "a"|"b"|"c"|"d", ...} }
    """
    if request.user.role != 'student':
        return error('Only students can submit quizzes.', 403)

    q = get_object_or_404(Quiz, pk=pk)
    get_object_or_404(RoomStudent, room=q.room, student=request.user)

    if QuizAttempt.objects.filter(quiz=q, student=request.user).exists():
        return error('You have already attempted this quiz.', 409)

    answers = request.data.get('answers', {})
    if not answers:
        return error('Answers are required.')

    questions = list(q.questions.all())
    if not questions:
        return error('This quiz has no questions yet.')

    score = 0
    results = []
    for qs in questions:
        given = answers.get(str(qs.pk), '').lower()
        correct = (given == qs.correct_answer.lower())
        if correct:
            score += 1
        results.append({
            'question_id': qs.pk,
            'given':       given,
            'correct':     qs.correct_answer.lower(),
            'is_correct':  correct,
        })

    pct = round((score / len(questions)) * 100, 1)
    QuizAttempt.objects.create(quiz=q, student=request.user, score=pct)

    return Response({
        'message':  'Quiz submitted.',
        'score':    pct,
        'correct':  score,
        'total':    len(questions),
        'results':  results,
    }, status=201)


# ═══════════════════════════════════════════════════════════════════════════════
# GRADES
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_grades(request):
    """GET /api/grades/ — student's assignment grades and quiz attempts."""
    user = request.user
    if user.role != 'student':
        return error('Only students can view this endpoint.', 403)

    grades = Grade.objects.filter(submission__student=user).select_related(
        'submission__assignment__room'
    ).order_by('-graded_at')

    attempts = QuizAttempt.objects.filter(student=user).select_related(
        'quiz__room'
    ).order_by('-attempted_at')

    return Response({
        'assignment_grades': [
            {
                'id':           g.pk,
                'assignment':   g.submission.assignment.title,
                'room':         g.submission.assignment.room.name,
                'subject':      g.submission.assignment.room.subject,
                'score':        g.score,
                'max_score':    g.submission.assignment.max_score,
                'percentage':   round((g.score / g.submission.assignment.max_score) * 100, 1) if g.submission.assignment.max_score else 0,
                'feedback':     g.feedback or '',
                'graded_at':    g.graded_at.isoformat(),
            }
            for g in grades
        ],
        'quiz_attempts': [
            {
                'id':          a.pk,
                'quiz':        a.quiz.title,
                'room':        a.quiz.room.name,
                'score':       a.score,
                'attempted_at': a.attempted_at.isoformat(),
            }
            for a in attempts
        ],
        'summary': {
            'total_graded':   grades.count(),
            'average_grade':  round(sum(g.score for g in grades) / grades.count(), 1) if grades.count() else None,
            'total_quizzes':  attempts.count(),
            'average_quiz':   round(sum(a.score for a in attempts) / attempts.count(), 1) if attempts.count() else None,
        }
    })


# ═══════════════════════════════════════════════════════════════════════════════
# ANNOUNCEMENTS
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_announcements_list(request):
    """GET /api/announcements/?page=1&type=urgent&unread=1"""
    user  = request.user
    grade = user.grade_level or ''
    audiences = ['all']
    if user.role == 'student':
        audiences += ['students', f'grade_{grade}']
    elif user.role == 'teacher':
        audiences += ['teachers']
    else:
        audiences = [c[0] for c in Announcement.AUDIENCE_CHOICES]

    qs = Announcement.objects.filter(audience__in=audiences).filter(
        scheduled_at__isnull=True
    ) | Announcement.objects.filter(
        audience__in=audiences, scheduled_at__lte=timezone.now()
    )
    qs = qs.select_related('author').order_by('-pinned', '-created_at')

    # Filters
    if request.GET.get('type'):
        qs = qs.filter(ann_type=request.GET['type'])
    if request.GET.get('unread') == '1':
        read_ids = AnnouncementRead.objects.filter(user=user, is_read=True).values_list('announcement_id', flat=True)
        qs = qs.exclude(pk__in=read_ids)

    read_ids = set(AnnouncementRead.objects.filter(user=user, is_read=True).values_list('announcement_id', flat=True))
    return paginate(qs, request, lambda a: {
        'id':             a.pk,
        'title':          a.title,
        'content':        a.content,
        'ann_type':       a.ann_type,
        'audience':       a.audience,
        'author':         a.author.get_full_name() if a.author else '',
        'pinned':         a.pinned,
        'is_read':        a.pk in read_ids,
        'attachment_url': a.attachment.url if a.attachment else None,
        'link':           a.link or '',
        'created_at':     a.created_at.isoformat(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_announcement_read(request, pk):
    """POST /api/announcements/<id>/read/"""
    a = get_object_or_404(Announcement, pk=pk)
    obj, _ = AnnouncementRead.objects.get_or_create(user=request.user, announcement=a)
    obj.is_read = True
    obj.read_at = timezone.now()
    obj.save()
    return Response({'message': 'Marked as read.'})


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE SESSIONS (JITSI)
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_live_sessions(request, pk):
    """
    GET  /api/rooms/<id>/live/  → list live sessions
    POST /api/rooms/<id>/live/  → create (teachers only)
    """
    room = get_object_or_404(Room, pk=pk)
    _check_room_access(request.user, room)

    if request.method == 'POST':
        if request.user.role != 'teacher' or room.teacher != request.user:
            return error('Only the room teacher can create sessions.', 403)
        import secrets, string
        title     = request.data.get('title', '').strip()
        scheduled = request.data.get('scheduled_at', '')
        if not title or not scheduled:
            return error('title and scheduled_at are required.')
        slug = f"edulms-{room.pk}-{''.join(secrets.choice(string.ascii_lowercase+string.digits) for _ in range(8))}"
        s = LiveSession.objects.create(
            room=room, title=title,
            description=request.data.get('description', ''),
            jitsi_room=slug, scheduled_at=scheduled,
            created_by=request.user,
        )
        return Response({'message': 'Session created.', 'session': _session_json(s)}, status=201)

    sessions = LiveSession.objects.filter(room=room).order_by('-scheduled_at')
    return Response({'live_sessions': [_session_json(s) for s in sessions]})


def _session_json(s):
    return {
        'id':           s.pk,
        'title':        s.title,
        'description':  s.description or '',
        'status':       s.status,
        'jitsi_room':   s.jitsi_room,
        'jitsi_url':    s.get_jitsi_url(),
        'scheduled_at': s.scheduled_at.isoformat() if s.scheduled_at else None,
        'started_at':   s.started_at.isoformat() if s.started_at else None,
        'ended_at':     s.ended_at.isoformat() if s.ended_at else None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS / DASHBOARD SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_notifications(request):
    """GET /api/notifications/ — unread counts and recent activity."""
    user = request.user
    read_ids = AnnouncementRead.objects.filter(user=user, is_read=True).values_list('announcement_id', flat=True)
    audiences = ['all']
    if user.role == 'student':
        audiences += ['students', f'grade_{user.grade_level or ""}']
    elif user.role == 'teacher':
        audiences += ['teachers']
    unread_anns = Announcement.objects.filter(
        audience__in=audiences
    ).exclude(pk__in=read_ids).count()

    data = {'unread_announcements': unread_anns, 'items': []}
    if user.role == 'student':
        pending = Assignment.objects.filter(
            room__roomstudent__student=user,
            due_date__gt=timezone.now()
        ).exclude(
            submission__student=user
        ).count()
        data['pending_assignments'] = pending
        live = LiveSession.objects.filter(
            room__roomstudent__student=user, status='live'
        ).count()
        data['live_sessions'] = live
    elif user.role == 'teacher':
        pending_subs = Submission.objects.filter(
            assignment__room__teacher=user, status='submitted'
        ).count()
        data['pending_grading'] = pending_subs
        pending_students = User.objects.filter(role='student', is_approved=False).count()
        data['pending_approvals'] = pending_students

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard(request):
    """GET /api/dashboard/ — full dashboard summary for the current user."""
    user = request.user
    if user.role == 'student':
        rooms = RoomStudent.objects.filter(student=user).select_related('room')
        grades = Grade.objects.filter(submission__student=user)
        attempts = QuizAttempt.objects.filter(student=user)
        return Response({
            'role': 'student',
            'rooms_count':     rooms.count(),
            'grades_count':    grades.count(),
            'quiz_count':      attempts.count(),
            'average_grade':   round(sum(g.score for g in grades) / grades.count(), 1) if grades.count() else None,
            'rooms': [room_json(rs.room, user) for rs in rooms[:6]],
        })
    elif user.role == 'teacher':
        rooms = Room.objects.filter(teacher=user)
        students = RoomStudent.objects.filter(room__teacher=user).values('student').distinct().count()
        pending_subs = Submission.objects.filter(assignment__room__teacher=user, status='submitted').count()
        return Response({
            'role': 'teacher',
            'rooms_count':     rooms.count(),
            'students_count':  students,
            'pending_grading': pending_subs,
            'rooms': [room_json(r) for r in rooms[:6]],
        })
    else:
        return Response({
            'role':           'admin',
            'total_users':    User.objects.exclude(is_superuser=True).count(),
            'total_students': User.objects.filter(role='student').count(),
            'total_teachers': User.objects.filter(role='teacher').count(),
            'pending':        User.objects.filter(is_approved=False).count(),
            'total_rooms':    Room.objects.count(),
        })


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_admin_users(request):
    """GET /api/admin/users/?role=student&status=pending&q=search"""
    if not request.user.is_superuser and request.user.role not in ('admin',):
        return error('Admin access required.', 403)
    qs = User.objects.exclude(is_superuser=True).order_by('is_approved', 'role', '-date_joined')
    if request.GET.get('role'):
        qs = qs.filter(role=request.GET['role'])
    if request.GET.get('status') == 'pending':
        qs = qs.filter(is_approved=False)
    elif request.GET.get('status') == 'approved':
        qs = qs.filter(is_approved=True)
    if request.GET.get('q'):
        q = request.GET['q']
        qs = qs.filter(username__icontains=q) | User.objects.filter(email__icontains=q) | User.objects.filter(first_name__icontains=q)
    return paginate(qs, request, user_json)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_admin_approve(request, pk):
    """POST /api/admin/users/<id>/approve/"""
    if not request.user.is_superuser:
        return error('Admin access required.', 403)
    from django.conf import settings as s
    from core.email_utils import send_teacher_setup_link, send_student_setup_link
    user = get_object_or_404(User, pk=pk)
    user.is_approved = True
    user.set_unusable_password()
    user.save()
    base_url = getattr(s, 'SITE_BASE_URL', 'http://127.0.0.1:8000')
    token_obj = PasswordResetToken.generate(user, token_type='setup')
    setup_url = token_obj.get_setup_url(base_url)
    try:
        if user.role == 'teacher':
            send_teacher_setup_link(user, setup_url)
        else:
            send_student_setup_link(user, setup_url)
        email_sent = True
    except Exception as e:
        logger.error(f"API approve: email failed for {user.email}: {e}")
        email_sent = False
    return Response({
        'message':    f'{user.username} approved.',
        'email_sent': email_sent,
        'setup_url':  setup_url,
        'user':       user_json(user),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_admin_stats(request):
    """GET /api/admin/stats/"""
    if not request.user.is_superuser:
        return error('Admin access required.', 403)
    from core.models import ErrorLog
    from courses.models import Assignment, Submission
    week_ago = timezone.now() - timezone.timedelta(days=7)
    return Response({
        'users': {
            'total':    User.objects.exclude(is_superuser=True).count(),
            'students': User.objects.filter(role='student').count(),
            'teachers': User.objects.filter(role='teacher').count(),
            'pending':  User.objects.filter(is_approved=False).count(),
            'new_this_week': User.objects.filter(date_joined__gte=week_ago).count(),
        },
        'rooms':         Room.objects.count(),
        'assignments':   Assignment.objects.count(),
        'submissions':   Submission.objects.count(),
        'announcements': Announcement.objects.count(),
        'errors': {
            'active':   ErrorLog.objects.filter(resolved=False).count(),
            'resolved': ErrorLog.objects.filter(resolved=True).count(),
        },
    })


# ═══════════════════════════════════════════════════════════════════════════════
# UTIL
# ═══════════════════════════════════════════════════════════════════════════════

def _check_room_access(user, room):
    """Raise 403 if user doesn't have access to this room."""
    if user.is_superuser:
        return
    if user.role == 'teacher' and room.teacher != user:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied('You are not the teacher of this room.')
    if user.role == 'student':
        if not RoomStudent.objects.filter(room=room, student=user).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You are not enrolled in this room.')
