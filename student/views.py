from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import role_required
from core.decorators import safe_view
from courses.models import Room, RoomStudent, Lesson, Assignment, Submission, Quiz, QuizAttempt, Material
from assessments.models import Grade
from .forms import SubmissionForm


def _get_room_or_403(request, pk):
    """Return room only if this student is assigned to it."""
    room = get_object_or_404(Room, pk=pk)
    if not RoomStudent.objects.filter(room=room, student=request.user).exists():
        return None
    return room


@safe_view
@role_required('student')
def dashboard(request):
    assignments = RoomStudent.objects.filter(student=request.user).select_related('room__teacher')
    grades = Grade.objects.filter(submission__student=request.user).select_related(
        'submission__assignment__room'
    )
    attempts = QuizAttempt.objects.filter(student=request.user).select_related('quiz__room')
    return render(request, 'student/dashboard.html', {
        'assignments': assignments,
        'grades': grades,
        'attempts': attempts,
    })


@safe_view
@role_required('student')
def room_detail(request, pk):
    room = _get_room_or_403(request, pk)
    if not room:
        messages.error(request, "You are not assigned to this room.")
        return redirect('student_dashboard')
    lessons     = room.lessons.all()
    materials   = room.materials.all()
    assignments = room.assignments.all()
    quizzes     = room.quizzes.all()
    submitted_ids = list(Submission.objects.filter(
        student=request.user, assignment__room=room
    ).values_list('assignment_id', flat=True))
    attempted_quiz_ids = list(QuizAttempt.objects.filter(
        student=request.user, quiz__room=room
    ).values_list('quiz_id', flat=True))
    return render(request, 'student/room_detail.html', {
        'room': room,
        'lessons': lessons,
        'materials': materials,
        'assignments': assignments,
        'quizzes': quizzes,
        'submitted_ids': submitted_ids,
        'attempted_quiz_ids': attempted_quiz_ids,
    })


@safe_view
@role_required('student')
def view_lesson(request, room_pk, lesson_pk):
    room = _get_room_or_403(request, room_pk)
    if not room:
        messages.error(request, "You are not assigned to this room.")
        return redirect('student_dashboard')
    lesson = get_object_or_404(Lesson, pk=lesson_pk, room=room)
    return render(request, 'student/lesson_view.html', {'room': room, 'lesson': lesson})


@safe_view
@role_required('student')
def submit_assignment(request, assignment_pk):
    assignment = get_object_or_404(Assignment, pk=assignment_pk)
    room = _get_room_or_403(request, assignment.room.pk)
    if not room:
        messages.error(request, "You are not assigned to this room.")
        return redirect('student_dashboard')
    existing = Submission.objects.filter(student=request.user, assignment=assignment).first()
    if existing:
        messages.warning(request, "You already submitted this assignment.")
        return redirect('room_detail', pk=room.pk)
    form = SubmissionForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        sub = form.save(commit=False)
        sub.student    = request.user
        sub.assignment = assignment
        sub.save()
        messages.success(request, "Assignment submitted!")
        return redirect('room_detail', pk=room.pk)
    return render(request, 'student/submit_assignment.html', {'assignment': assignment, 'form': form})


@safe_view
@role_required('student')
def take_quiz(request, quiz_pk):
    quiz = get_object_or_404(Quiz, pk=quiz_pk)
    room = _get_room_or_403(request, quiz.room.pk)
    if not room:
        messages.error(request, "You are not assigned to this room.")
        return redirect('student_dashboard')
    if QuizAttempt.objects.filter(student=request.user, quiz=quiz).exists():
        messages.warning(request, "You already attempted this quiz.")
        return redirect('room_detail', pk=room.pk)
    questions = quiz.questions.all()
    if request.method == 'POST':
        score = sum(
            1 for q in questions
            if request.POST.get(f'q_{q.pk}', '').upper() == q.correct_answer
        )
        total   = questions.count()
        percent = round((score / total) * 100, 1) if total else 0
        QuizAttempt.objects.create(student=request.user, quiz=quiz, score=percent)
        messages.success(request, f"Quiz submitted! Score: {score}/{total} ({percent}%)")
        return redirect('room_detail', pk=room.pk)
    return render(request, 'student/quiz.html', {'quiz': quiz, 'questions': questions})


@safe_view
@role_required('student')
def my_grades(request):
    grades = Grade.objects.filter(submission__student=request.user).select_related(
        'submission__assignment__room'
    )
    attempts = QuizAttempt.objects.filter(student=request.user).select_related('quiz__room')
    return render(request, 'student/grades.html', {'grades': grades, 'attempts': attempts})


@safe_view
@role_required('student')
def announcements(request):
    from courses.models import Announcement, AnnouncementRead
    from django.utils import timezone
    grade = request.user.grade_level or ''
    anns = Announcement.objects.filter(
        audience__in=['all', 'students', f'grade_{grade}'],
        scheduled_at__isnull=True,
    ) | Announcement.objects.filter(
        audience__in=['all', 'students', f'grade_{grade}'],
        scheduled_at__lte=timezone.now(),
    )
    anns = anns.order_by('-pinned', '-created_at').select_related('author')
    return render(request, 'student/announcements.html', {'announcements': anns})


@safe_view
def mark_announcement_read(request, pk):
    """AJAX endpoint — mark announcement as read for current user."""
    from django.http import JsonResponse
    from django.utils import timezone
    from courses.models import Announcement, AnnouncementRead
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=401)
    ann = get_object_or_404(Announcement, pk=pk)
    obj, _ = AnnouncementRead.objects.get_or_create(
        user=request.user, announcement=ann
    )
    if not obj.is_read:
        obj.is_read = True
        obj.read_at = timezone.now()
        obj.save()
    return JsonResponse({'status': 'ok', 'ann_id': pk})


@safe_view
def log_tab_violation(request):
    """AJAX endpoint — student switched tabs, log the violation."""
    from django.http import JsonResponse
    from courses.models import TabViolation, Quiz
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'unauthenticated'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'method'}, status=405)

    import json
    data     = json.loads(request.body or '{}')
    page_url = data.get('url', '')[:500]
    quiz_id  = data.get('quiz_id')

    quiz = None
    if quiz_id:
        try:
            quiz = Quiz.objects.get(pk=quiz_id)
        except Quiz.DoesNotExist:
            pass

    # Increment existing or create new
    viol, created = TabViolation.objects.get_or_create(
        student=request.user,
        quiz=quiz,
        page_url=page_url,
    )
    if not created:
        viol.count += 1
        viol.save()

    return JsonResponse({'status': 'logged', 'count': viol.count})


# ─── LIVE SESSIONS (Jitsi) ──────────────────────────────────────────────────

@safe_view
@role_required('student')
def student_live_sessions(request, pk):
    from courses.models import Room, RoomStudent, LiveSession
    room = get_object_or_404(Room, pk=pk)
    get_object_or_404(RoomStudent, room=room, student=request.user)
    sessions = LiveSession.objects.filter(room=room)
    return render(request, 'student/live_sessions.html', {
        'room': room, 'sessions': sessions
    })
