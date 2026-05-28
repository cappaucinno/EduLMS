"""
EduLMS REST API Views
Base URL: /api/v1/

Auth endpoints (no auth required):
  POST /api/v1/auth/token/          → obtain JWT token pair
  POST /api/v1/auth/token/refresh/  → refresh access token
  POST /api/v1/auth/token/verify/   → verify token
  POST /api/v1/auth/logout/         → blacklist refresh token

User:
  GET  /api/v1/auth/me/             → current user profile
  PUT  /api/v1/auth/me/             → update profile (name, email)

Rooms:
  GET  /api/v1/rooms/               → list my rooms
  GET  /api/v1/rooms/<id>/          → room detail

Lessons:
  GET  /api/v1/rooms/<id>/lessons/  → list lessons in a room

Materials:
  GET  /api/v1/rooms/<id>/materials/

Assignments:
  GET  /api/v1/rooms/<id>/assignments/
  GET  /api/v1/assignments/<id>/
  POST /api/v1/assignments/<id>/submit/   (student)

Submissions:
  GET  /api/v1/submissions/               (teacher: all in my rooms; student: mine)
  GET  /api/v1/submissions/<id>/
  POST /api/v1/submissions/<id>/grade/    (teacher only)

Quizzes:
  GET  /api/v1/rooms/<id>/quizzes/
  GET  /api/v1/quizzes/<id>/
  POST /api/v1/quizzes/<id>/submit/       (student)

Grades:
  GET  /api/v1/grades/                    (student: my grades)

Announcements:
  GET  /api/v1/announcements/
  POST /api/v1/announcements/<id>/read/   (mark as read)

Live Sessions:
  GET  /api/v1/rooms/<id>/live/
  POST /api/v1/rooms/<id>/live/           (teacher: create session)

Dashboard:
  GET  /api/v1/dashboard/                 (role-aware summary)
"""
import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from accounts.models import User
from courses.models import (
    Room, RoomStudent, Lesson, Material, Assignment,
    Submission, Quiz, Question, QuizAttempt,
    Announcement, AnnouncementRead, LiveSession,
)
from assessments.models import Grade
from .serializers import (
    UserSerializer, RoomSerializer, LessonSerializer, MaterialSerializer,
    AssignmentSerializer, SubmissionSerializer, SubmissionCreateSerializer,
    QuizSerializer, QuizAttemptSerializer, QuizSubmitSerializer,
    GradeSerializer, AnnouncementSerializer, LiveSessionSerializer,
)
from .permissions import IsStudent, IsTeacher, IsTeacherOrAdmin, IsApproved

logger = logging.getLogger('edulms')


def api_error(message, code=400):
    return Response({'error': message}, status=code)


def api_ok(data=None, message=None, status_code=200):
    resp = {}
    if data    is not None: resp['data']    = data
    if message is not None: resp['message'] = message
    return Response(resp, status=status_code)


# ─── AUTH ────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def token_obtain(request):
    """
    POST /api/v1/auth/token/
    Body: {"username": "...", "password": "..."}
    Returns: {"access": "...", "refresh": "...", "user": {...}}
    """
    from django.contrib.auth import authenticate
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return api_error('Username and password are required.', 400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return api_error('Invalid credentials.', 401)

    if not user.is_approved and not user.is_superuser:
        return api_error('Your account is pending approval.', 403)

    refresh = RefreshToken.for_user(user)
    return Response({
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
        'user':    UserSerializer(user, context={'request': request}).data,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """POST /api/v1/auth/token/refresh/ — {"refresh": "..."}"""
    from rest_framework_simplejwt.views import TokenRefreshView
    from rest_framework_simplejwt.serializers import TokenRefreshSerializer
    serializer = TokenRefreshSerializer(data=request.data)
    try:
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)
    except TokenError as e:
        return api_error(str(e), 401)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """POST /api/v1/auth/logout/ — {"refresh": "..."} — blacklists token"""
    try:
        RefreshToken(request.data.get('refresh', '')).blacklist()
        return api_ok(message='Logged out successfully.')
    except TokenError:
        return api_error('Invalid or already expired token.', 400)


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated, IsApproved])
def me(request):
    """GET/PUT /api/v1/auth/me/ — current user profile"""
    user = request.user
    if request.method == 'GET':
        return Response(UserSerializer(user, context={'request': request}).data)

    allowed = ['first_name', 'last_name', 'email']
    for field in allowed:
        if field in request.data:
            setattr(user, field, request.data[field])
    user.save()
    return Response(UserSerializer(user, context={'request': request}).data)


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def dashboard(request):
    """GET /api/v1/dashboard/ — role-aware summary stats"""
    user = request.user

    if user.role == 'student':
        enrolled = RoomStudent.objects.filter(student=user).select_related('room')
        rooms    = [rs.room for rs in enrolled]
        grades   = Grade.objects.filter(submission__student=user)
        attempts = QuizAttempt.objects.filter(student=user)
        pending  = Submission.objects.filter(student=user, status='submitted').count()
        avg = None
        if grades.exists():
            avg = round(sum(g.score for g in grades) / grades.count(), 1)
        return api_ok({
            'role':               'student',
            'enrolled_rooms':     len(rooms),
            'graded_assignments': grades.count(),
            'quiz_attempts':      attempts.count(),
            'pending_submissions':pending,
            'avg_score':          avg,
            'rooms': RoomSerializer(rooms, many=True, context={'request':request}).data,
        })

    elif user.role == 'teacher':
        rooms    = Room.objects.filter(teacher=user)
        students = RoomStudent.objects.filter(room__teacher=user).values('student').distinct().count()
        pending  = Submission.objects.filter(
            assignment__room__teacher=user, status='submitted'
        ).count()
        unread_errors = 0
        try:
            from core.models import ErrorLog
            unread_errors = ErrorLog.objects.filter(resolved=False).count()
        except Exception:
            pass
        return api_ok({
            'role':             'teacher',
            'total_rooms':      rooms.count(),
            'total_students':   students,
            'pending_to_grade': pending,
            'unread_errors':    unread_errors,
            'rooms': RoomSerializer(rooms, many=True, context={'request':request}).data,
        })

    else:  # admin
        return api_ok({
            'role':            'admin',
            'total_users':     User.objects.exclude(is_superuser=True).count(),
            'total_rooms':     Room.objects.count(),
            'pending_teachers':User.objects.filter(role='teacher', is_approved=False).count(),
            'pending_students':User.objects.filter(role='student', is_approved=False).count(),
        })


# ─── ROOMS ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def room_list(request):
    """GET /api/v1/rooms/ — rooms for current user (role-aware)"""
    user = request.user
    if user.role == 'student':
        rooms = [rs.room for rs in RoomStudent.objects.filter(student=user).select_related('room')]
    elif user.role == 'teacher':
        rooms = Room.objects.filter(teacher=user)
    else:
        rooms = Room.objects.all()
    return Response(RoomSerializer(rooms, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def room_detail(request, pk):
    """GET /api/v1/rooms/<pk>/"""
    user = request.user
    try:
        room = Room.objects.get(pk=pk)
    except Room.DoesNotExist:
        return api_error('Room not found.', 404)

    # Access check
    if user.role == 'student':
        if not RoomStudent.objects.filter(room=room, student=user).exists():
            return api_error('You are not enrolled in this room.', 403)
    elif user.role == 'teacher' and room.teacher != user:
        return api_error('You do not own this room.', 403)

    return Response(RoomSerializer(room, context={'request': request}).data)


# ─── LESSONS ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def lesson_list(request, pk):
    """GET /api/v1/rooms/<pk>/lessons/"""
    lessons = Lesson.objects.filter(room__pk=pk).order_by('order')
    return Response(LessonSerializer(lessons, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def lesson_detail(request, pk, lesson_pk):
    """GET /api/v1/rooms/<pk>/lessons/<lesson_pk>/"""
    try:
        lesson = Lesson.objects.get(pk=lesson_pk, room__pk=pk)
    except Lesson.DoesNotExist:
        return api_error('Lesson not found.', 404)
    return Response(LessonSerializer(lesson, context={'request': request}).data)


# ─── MATERIALS ───────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def material_list(request, pk):
    """GET /api/v1/rooms/<pk>/materials/"""
    materials = Material.objects.filter(room__pk=pk).order_by('order')
    return Response(MaterialSerializer(materials, many=True, context={'request': request}).data)


# ─── ASSIGNMENTS ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def assignment_list(request, pk):
    """GET /api/v1/rooms/<pk>/assignments/"""
    assignments = Assignment.objects.filter(room__pk=pk).order_by('-created_at')
    return Response(AssignmentSerializer(assignments, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def assignment_detail(request, assignment_pk):
    """GET /api/v1/assignments/<pk>/"""
    try:
        a = Assignment.objects.get(pk=assignment_pk)
    except Assignment.DoesNotExist:
        return api_error('Assignment not found.', 404)
    return Response(AssignmentSerializer(a, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApproved, IsStudent])
def assignment_submit(request, assignment_pk):
    """
    POST /api/v1/assignments/<pk>/submit/
    Multipart: file + notes
    """
    try:
        assignment = Assignment.objects.get(pk=assignment_pk)
    except Assignment.DoesNotExist:
        return api_error('Assignment not found.', 404)

    if not RoomStudent.objects.filter(room=assignment.room, student=request.user).exists():
        return api_error('You are not enrolled in this room.', 403)

    if Submission.objects.filter(assignment=assignment, student=request.user).exists():
        return api_error('You have already submitted this assignment.', 409)

    serializer = SubmissionCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    sub = serializer.save(student=request.user, status='submitted')

    # Notify teacher
    try:
        from core.email_utils import send_new_assignment
    except Exception:
        pass

    return Response(
        SubmissionSerializer(sub, context={'request': request}).data,
        status=201
    )


# ─── SUBMISSIONS ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def submission_list(request):
    """GET /api/v1/submissions/ — teacher: all in rooms; student: mine"""
    user = request.user
    if user.role == 'student':
        subs = Submission.objects.filter(student=user).select_related(
            'assignment__room', 'student'
        ).order_by('-submitted_at')
    elif user.role == 'teacher':
        subs = Submission.objects.filter(
            assignment__room__teacher=user
        ).select_related('assignment__room','student').order_by('-submitted_at')
    else:
        subs = Submission.objects.all().order_by('-submitted_at')

    page = request.query_params.get('page', 1)
    return Response(SubmissionSerializer(subs[:40], many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApproved, IsTeacher])
def submission_grade(request, submission_pk):
    """
    POST /api/v1/submissions/<pk>/grade/
    Body: {"score": 85, "feedback": "Good work"}
    """
    try:
        sub = Submission.objects.get(pk=submission_pk, assignment__room__teacher=request.user)
    except Submission.DoesNotExist:
        return api_error('Submission not found.', 404)

    score    = request.data.get('score')
    feedback = request.data.get('feedback', '')
    if score is None:
        return api_error('score is required.', 400)

    grade, created = Grade.objects.update_or_create(
        submission=sub,
        defaults={'score': float(score), 'feedback': feedback, 'graded_at': timezone.now()}
    )
    sub.status = 'graded'
    sub.save()

    try:
        from core.email_utils import send_assignment_graded
        send_assignment_graded(sub)
    except Exception as e:
        logger.warning(f"Grade email failed: {e}")

    return api_ok({
        'id':        grade.id,
        'score':     grade.score,
        'feedback':  grade.feedback,
        'graded_at': str(grade.graded_at),
    }, message='Graded successfully.')


# ─── QUIZZES ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def quiz_list(request, pk):
    """GET /api/v1/rooms/<pk>/quizzes/"""
    quizzes = Quiz.objects.filter(room__pk=pk)
    return Response(QuizSerializer(quizzes, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def quiz_detail(request, quiz_pk):
    """GET /api/v1/quizzes/<pk>/ — includes questions (correct answer hidden for students)"""
    try:
        quiz = Quiz.objects.prefetch_related('questions').get(pk=quiz_pk)
    except Quiz.DoesNotExist:
        return api_error('Quiz not found.', 404)

    data = QuizSerializer(quiz, context={'request': request}).data

    # Hide correct_answer from students
    if request.user.role == 'student':
        for q in data.get('questions', []):
            q.pop('correct_answer', None)

    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApproved, IsStudent])
def quiz_submit(request, quiz_pk):
    """
    POST /api/v1/quizzes/<pk>/submit/
    Body: {"answers": {"1": "A", "2": "C", ...}}
    Returns score and per-question result.
    """
    try:
        quiz = Quiz.objects.prefetch_related('questions').get(pk=quiz_pk)
    except Quiz.DoesNotExist:
        return api_error('Quiz not found.', 404)

    if not RoomStudent.objects.filter(room=quiz.room, student=request.user).exists():
        return api_error('You are not enrolled in this room.', 403)

    if QuizAttempt.objects.filter(quiz=quiz, student=request.user).exists():
        return api_error('You have already attempted this quiz.', 409)

    serializer = QuizSubmitSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    answers = serializer.validated_data['answers']
    questions = quiz.questions.all()
    results = []
    correct = 0

    for q in questions:
        given   = answers.get(str(q.pk), '').upper()
        is_ok   = given == q.correct_answer.upper()
        if is_ok:
            correct += 1
        results.append({
            'question_id': q.pk,
            'given':       given,
            'correct':     q.correct_answer,
            'is_correct':  is_ok,
        })

    total   = questions.count()
    percent = round((correct / total * 100), 1) if total else 0

    attempt = QuizAttempt.objects.create(
        quiz=quiz, student=request.user, score=percent
    )

    return api_ok({
        'attempt_id':   attempt.pk,
        'score':        percent,
        'correct':      correct,
        'total':        total,
        'results':      results,
    }, message=f'Quiz submitted. Score: {percent}%')


# ─── GRADES ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved, IsStudent])
def grade_list(request):
    """GET /api/v1/grades/ — student's own grades"""
    grades = Grade.objects.filter(submission__student=request.user).select_related(
        'submission__assignment__room'
    ).order_by('-graded_at')
    return Response(GradeSerializer(grades, many=True, context={'request': request}).data)


# ─── ANNOUNCEMENTS ───────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved])
def announcement_list(request):
    """GET /api/v1/announcements/ — audience-filtered announcements"""
    user = request.user
    from django.db.models import Q
    qs = Announcement.objects.filter(
        Q(audience='all') |
        Q(audience='students', ) if user.role == 'student' else Q() |
        Q(audience='teachers')   if user.role == 'teacher' else Q() |
        Q(audience=f'grade_{user.grade_level}') if user.grade_level else Q()
    ).order_by('-pinned', '-created_at')

    # Simpler reliable filter
    valid = ['all', f'grade_{user.grade_level}',
             'students' if user.role=='student' else '',
             'teachers' if user.role=='teacher' else '']
    qs = Announcement.objects.filter(audience__in=[v for v in valid if v]).order_by('-pinned','-created_at')

    return Response(AnnouncementSerializer(qs, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApproved])
def announcement_mark_read(request, ann_pk):
    """POST /api/v1/announcements/<pk>/read/"""
    try:
        ann = Announcement.objects.get(pk=ann_pk)
    except Announcement.DoesNotExist:
        return api_error('Announcement not found.', 404)
    AnnouncementRead.objects.update_or_create(
        announcement=ann, user=request.user,
        defaults={'is_read': True, 'read_at': timezone.now()}
    )
    return api_ok(message='Marked as read.')


# ─── LIVE SESSIONS ───────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsApproved])
def live_session_list(request, pk):
    """
    GET  /api/v1/rooms/<pk>/live/ — list sessions
    POST /api/v1/rooms/<pk>/live/ — create session (teacher only)
    """
    try:
        room = Room.objects.get(pk=pk)
    except Room.DoesNotExist:
        return api_error('Room not found.', 404)

    if request.method == 'GET':
        sessions = LiveSession.objects.filter(room=room)
        return Response(LiveSessionSerializer(sessions, many=True, context={'request': request}).data)

    # POST — teacher only
    if request.user.role != 'teacher' or room.teacher != request.user:
        return api_error('Only the room teacher can create sessions.', 403)

    import secrets, string
    slug = f"edulms-{room.pk}-{''.join(secrets.choice(string.ascii_lowercase+string.digits) for _ in range(8))}"
    session = LiveSession.objects.create(
        room=room,
        title=request.data.get('title', 'Live Class'),
        description=request.data.get('description', ''),
        jitsi_room=slug,
        scheduled_at=request.data.get('scheduled_at', timezone.now()),
        created_by=request.user,
        status='scheduled',
    )
    return Response(
        LiveSessionSerializer(session, context={'request': request}).data,
        status=201
    )


# ─── STUDENTS IN ROOM (teacher) ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApproved, IsTeacher])
def room_students(request, pk):
    """GET /api/v1/rooms/<pk>/students/"""
    try:
        room = Room.objects.get(pk=pk, teacher=request.user)
    except Room.DoesNotExist:
        return api_error('Room not found.', 404)
    from .serializers import PublicUserSerializer
    students = [rs.student for rs in RoomStudent.objects.filter(room=room).select_related('student')]
    return Response(PublicUserSerializer(students, many=True).data)
