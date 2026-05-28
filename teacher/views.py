from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import logging
from accounts.decorators import role_required
logger = logging.getLogger("edulms")
from core.email_utils import (
    send_student_rejected,
    send_teacher_rejected,
    send_room_assigned, send_room_removed,
    send_new_assignment, send_assignment_graded,
)
from core.decorators import safe_view
from accounts.models import User
from courses.models import Room, RoomStudent, Lesson, Assignment, Submission, Quiz, Question, Material
from .forms import RoomForm, LessonForm, AssignmentForm, QuizForm, QuestionForm, GradeForm, MaterialForm


# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def dashboard(request):
    rooms            = Room.objects.filter(teacher=request.user)
    total_students   = RoomStudent.objects.filter(room__teacher=request.user).values('student').distinct().count()
    total_assignments = Assignment.objects.filter(room__teacher=request.user).count()
    pending_subs     = Submission.objects.filter(assignment__room__teacher=request.user, status='submitted').count()
    return render(request, 'teacher/dashboard.html', {
        'rooms': rooms,
        'total_students': total_students,
        'total_assignments': total_assignments,
        'pending_subs': pending_subs,
    })


# ─── ROOM CRUD ────────────────────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def create_room(request):
    form = RoomForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        room = form.save(commit=False)
        room.teacher = request.user
        room.save()
        messages.success(request, f"Room '{room}' created!")
        return redirect('teacher_dashboard')
    return render(request, 'teacher/room_form.html', {'form': form, 'title': 'Create Room'})


@safe_view
@role_required('teacher')
def edit_room(request, pk):
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    form = RoomForm(request.POST or None, request.FILES or None, instance=room)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Room updated!")
        return redirect('teacher_dashboard')
    return render(request, 'teacher/room_form.html', {'form': form, 'title': 'Edit Room', 'room': room})


@safe_view
@role_required('teacher')
def delete_room(request, pk):
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    if request.method == 'POST':
        room.delete()
        messages.success(request, "Room deleted.")
        return redirect('teacher_dashboard')
    return render(request, 'teacher/confirm_delete.html', {'obj': room, 'type': 'Room'})


# ─── ROOM OVERVIEW ───────────────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def room_overview(request, pk):
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    students  = RoomStudent.objects.filter(room=room).select_related('student')
    lessons   = room.lessons.all()
    materials = room.materials.all()
    assignments = room.assignments.all()
    quizzes   = room.quizzes.all()
    return render(request, 'teacher/room_overview.html', {
        'room': room, 'students': students,
        'lessons': lessons, 'materials': materials,
        'assignments': assignments, 'quizzes': quizzes,
    })


# ─── STUDENT ASSIGNMENT ───────────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def manage_students(request, pk):
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    assigned_ids = RoomStudent.objects.filter(room=room).values_list('student_id', flat=True)
    # Show only approved students that match the room's grade level
    eligible = User.objects.filter(
        role='student', is_approved=True, grade_level=room.grade_level
    ).exclude(id__in=assigned_ids).order_by('last_name','first_name')
    assigned = RoomStudent.objects.filter(room=room).select_related('student').order_by('student__last_name')
    return render(request, 'teacher/manage_students.html', {
        'room': room, 'eligible': eligible, 'assigned': assigned,
    })


@safe_view
@role_required('teacher')
def assign_student(request, pk, student_pk):
    room    = get_object_or_404(Room, pk=pk, teacher=request.user)
    student = get_object_or_404(User, pk=student_pk, role='student', is_approved=True)
    obj, created = RoomStudent.objects.get_or_create(room=room, student=student, defaults={'assigned_by': request.user})
    if created:
        try:
            send_room_assigned(student, room)
        except Exception as e:
            logger.error(f"Room assignment email failed for {student.email}: {e}")
    messages.success(request, f"{student.get_full_name() or student.username} added to {room}.")
    return redirect('manage_students', pk=pk)


@safe_view
@role_required('teacher')
def remove_student(request, pk, student_pk):
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    from accounts.models import User as U
    student = U.objects.filter(pk=student_pk).first()
    RoomStudent.objects.filter(room=room, student_id=student_pk).delete()
    if student:
        try:
            send_room_removed(student, room)
        except Exception as e:
            logger.error(f"Room removal email failed: {e}")
    messages.warning(request, "Student removed from room.")
    return redirect('manage_students', pk=pk)


# ─── LESSONS ─────────────────────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def manage_lessons(request, pk):
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    form = LessonForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        lesson = form.save(commit=False)
        lesson.room = room
        lesson.save()
        messages.success(request, "Lesson added!")
        return redirect('manage_lessons', pk=pk)
    return render(request, 'teacher/manage_lessons.html', {'room': room, 'form': form})


@safe_view
@role_required('teacher')
def delete_lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, room__teacher=request.user)
    room_pk = lesson.room.pk
    lesson.delete()
    return redirect('manage_lessons', pk=room_pk)


# ─── MATERIALS ───────────────────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def manage_materials(request, pk):
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    form = MaterialForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        mat = form.save(commit=False)
        mat.room = room
        mat.save()
        messages.success(request, "Material uploaded!")
        return redirect('manage_materials', pk=pk)
    return render(request, 'teacher/manage_materials.html', {'room': room, 'form': form})


@safe_view
@role_required('teacher')
def delete_material(request, pk):
    mat = get_object_or_404(Material, pk=pk, room__teacher=request.user)
    room_pk = mat.room.pk
    mat.delete()
    return redirect('manage_materials', pk=room_pk)


# ─── ASSIGNMENTS ─────────────────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def manage_assignments(request, pk):
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    form = AssignmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        a = form.save(commit=False)
        a.room = room
        a.save()
        try:
            send_new_assignment(a)
            messages.success(request, "Assignment created! Students notified by email.")
        except Exception as e:
            logger.error(f"Assignment email failed: {e}")
            messages.success(request, "Assignment created! (Email notification failed — check email settings.)")
        return redirect('manage_assignments', pk=pk)
    return render(request, 'teacher/manage_assignments.html', {'room': room, 'form': form})


@safe_view
@role_required('teacher')
def view_submissions(request, assignment_pk):
    assignment = get_object_or_404(Assignment, pk=assignment_pk, room__teacher=request.user)
    submissions = Submission.objects.filter(assignment=assignment).select_related('student','grade')
    return render(request, 'teacher/submissions.html', {
        'assignment': assignment, 'submissions': submissions
    })


@safe_view
@role_required('teacher')
def grade_submission(request, pk):
    from assessments.models import Grade
    submission = get_object_or_404(Submission, pk=pk, assignment__room__teacher=request.user)
    grade_obj, _ = Grade.objects.get_or_create(submission=submission)
    form = GradeForm(request.POST or None, instance=grade_obj)
    if request.method == 'POST' and form.is_valid():
        g = form.save(commit=False)
        g.submission = submission
        g.save()
        submission.status = 'graded'
        submission.save()
        try:
            send_assignment_graded(submission)
            messages.success(request, "Graded! Student notified by email.")
        except Exception as e:
            logger.error(f"Grade email failed: {e}")
            messages.success(request, "Graded! (Email notification failed — check email settings.)")
        return redirect('view_submissions', assignment_pk=submission.assignment.pk)
    return render(request, 'teacher/grade.html', {'submission': submission, 'form': form})


# ─── QUIZZES ─────────────────────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def manage_quiz(request, pk):
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    form = QuizForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        quiz = form.save(commit=False)
        quiz.room = room
        quiz.save()
        messages.success(request, "Quiz created!")
        return redirect('add_questions', quiz_pk=quiz.pk)
    return render(request, 'teacher/manage_quiz.html', {'room': room, 'form': form})


@safe_view
@role_required('teacher')
def add_questions(request, quiz_pk):
    quiz = get_object_or_404(Quiz, pk=quiz_pk, room__teacher=request.user)
    form = QuestionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        q = form.save(commit=False)
        q.quiz = quiz
        q.save()
        messages.success(request, "Question added!")
        return redirect('add_questions', quiz_pk=quiz_pk)
    return render(request, 'teacher/add_questions.html', {'quiz': quiz, 'form': form})


# ─── STUDENT APPROVAL ────────────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def pending_students(request):
    students = User.objects.filter(role='student', is_approved=False).order_by('date_joined')
    approved = User.objects.filter(role='student', is_approved=True).order_by('grade_level','last_name')
    return render(request, 'teacher/pending_students.html', {
        'students': students, 'approved': approved,
    })


@safe_view
@role_required('teacher')
def approve_student(request, pk):
    from accounts.models import PasswordResetToken
    from core.email_utils import send_student_setup_link
    from django.conf import settings
    student = get_object_or_404(User, pk=pk, role='student')
    student.is_approved = True
    student.set_unusable_password()   # no generated password — student sets their own
    student.save()

    # Build setup URL using SITE_BASE_URL from settings
    # Use SITE_BASE_URL from settings (set to your ngrok/production URL)
    base_url  = getattr(settings, 'SITE_BASE_URL', None) or request.build_absolute_uri('/').rstrip('/')
    token_obj = PasswordResetToken.generate(student, token_type='setup')
    setup_url = token_obj.get_setup_url(base_url)

    try:
        send_student_setup_link(student, setup_url)
        msg = (f"✅ {student.get_full_name() or student.username} approved! "
               f"Password setup link sent to {student.email}.")
        logger.info(f"Student setup link sent to {student.email}: {setup_url}")
    except Exception as e:
        logger.error(f"Setup email failed for {student.email}: {e}")
        msg = (f"✅ {student.get_full_name() or student.username} approved! "
               f"Email failed — share this link manually: {setup_url}")

    messages.success(request, msg)
    return redirect('pending_students')


@safe_view
@role_required('teacher')
def reject_student(request, pk):
    student = get_object_or_404(User, pk=pk, role='student')
    try:
        send_student_rejected(student)
    except Exception as e:
        logger.error(f"Failed to send rejection email to {student.email}: {e}")
    student.delete()
    messages.warning(request, "Student account rejected. Email notification sent.")
    return redirect('pending_students')



# ─── ANNOUNCEMENT VIEWS (FULL) ────────────────────────────────────────────────

@safe_view
@role_required('teacher')
def announcement_list(request):
    from courses.models import Announcement
    ann_type = request.GET.get('type', '')
    anns = Announcement.objects.all()
    if ann_type:
        anns = anns.filter(ann_type=ann_type)
    return render(request, 'teacher/announcements.html', {
        'announcements': anns,
        'ann_type': ann_type,
        'type_choices': Announcement.TYPE_CHOICES,
    })


@safe_view
@role_required('teacher')
def announcement_create(request):
    from courses.models import Announcement
    from teacher.forms import AnnouncementForm
    from core.email_utils import send_announcement
    form = AnnouncementForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        ann = form.save(commit=False)
        ann.author = request.user
        ann.save()
        if ann.send_email and ann.is_published():
            try:
                success, count, err = send_announcement(ann)
                if success:
                    messages.success(request, f"✅ Announcement posted and emailed to {count} recipient(s) — audience: {ann.audience_label()}.")
                elif err:
                    messages.warning(request, f"Announcement posted but email not sent: {err}")
                else:
                    messages.warning(request, "Announcement posted but email delivery failed. Check your email settings and logs/errors.log.")
            except Exception as e:
                logger.error(f"Announcement email error: {e}")
                messages.warning(request, f"Announcement posted but email failed: {e}")
        elif ann.send_email and not ann.is_published():
            messages.info(request, f"Announcement saved. Email will need to be sent manually after scheduled date: {ann.scheduled_at}.")
        else:
            messages.success(request, "Announcement posted (email not enabled).")
        return redirect('announcement_list')
    return render(request, 'teacher/announcement_form.html', {'form': form, 'action': 'Create'})


@safe_view
@role_required('teacher')
def announcement_edit(request, pk):
    from courses.models import Announcement
    from teacher.forms import AnnouncementForm
    ann = get_object_or_404(Announcement, pk=pk)
    form = AnnouncementForm(request.POST or None, request.FILES or None, instance=ann)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Announcement updated.")
        return redirect('announcement_list')
    return render(request, 'teacher/announcement_form.html', {'form': form, 'action': 'Edit', 'ann': ann})


@safe_view
@role_required('teacher')
def announcement_delete(request, pk):
    from courses.models import Announcement
    ann = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        ann.delete()
        messages.success(request, "Announcement deleted.")
        return redirect('announcement_list')
    return render(request, 'teacher/confirm_delete.html', {'obj': ann, 'type': 'Announcement'})



# ─── LIVE SESSIONS (Jitsi Meet) ──────────────────────────────────────────────

@safe_view
@role_required('teacher')
def live_sessions(request, pk):
    from courses.models import Room, LiveSession
    import secrets, string
    room = get_object_or_404(Room, pk=pk, teacher=request.user)
    sessions = LiveSession.objects.filter(room=room)

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        scheduled   = request.POST.get('scheduled_at', '')
        if title and scheduled:
            # Generate unique Jitsi room slug: edulms-roomslug-random
            slug = f"edulms-{room.pk}-{''.join(secrets.choice(string.ascii_lowercase+string.digits) for _ in range(8))}"
            LiveSession.objects.create(
                room=room, title=title, description=description,
                jitsi_room=slug, scheduled_at=scheduled,
                created_by=request.user, status='scheduled'
            )
            messages.success(request, f"✅ Live session '{title}' created.")
            return redirect('live_sessions', pk=pk)
        else:
            messages.error(request, "Title and scheduled time are required.")

    return render(request, 'teacher/live_sessions.html', {'room': room, 'sessions': sessions})


@safe_view
@role_required('teacher')
def live_session_start(request, pk, session_pk):
    from courses.models import LiveSession
    from django.utils import timezone
    session = get_object_or_404(LiveSession, pk=session_pk, room__teacher=request.user)
    session.status = 'live'
    session.started_at = timezone.now()
    session.save()
    messages.success(request, f"✅ Session '{session.title}' is now live.")
    return redirect('live_sessions', pk=pk)


@safe_view
@role_required('teacher')
def live_session_end(request, pk, session_pk):
    from courses.models import LiveSession
    from django.utils import timezone
    session = get_object_or_404(LiveSession, pk=session_pk, room__teacher=request.user)
    session.status = 'ended'
    session.ended_at = timezone.now()
    session.save()
    messages.success(request, f"Session '{session.title}' ended.")
    return redirect('live_sessions', pk=pk)


@safe_view
@role_required('teacher')
def live_session_delete(request, pk, session_pk):
    from courses.models import LiveSession
    session = get_object_or_404(LiveSession, pk=session_pk, room__teacher=request.user)
    if request.method == 'POST':
        session.delete()
        messages.success(request, "Session deleted.")
        return redirect('live_sessions', pk=pk)
    return render(request, 'teacher/confirm_delete.html', {
        'item': session.title, 'back_url': f'/teacher/room/{pk}/live/'
    })
