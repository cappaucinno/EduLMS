"""
EduLMS Email Utility
All outgoing emails go through _send() which handles logging and errors.
"""
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('edulms')


def _school():
    return getattr(settings, 'SCHOOL_NAME', 'EduLMS')


def _from():
    return settings.DEFAULT_FROM_EMAIL


def _send(subject, template, context, recipient_list, fail_silently=True):
    """Renders HTML + plain text and sends. Returns True on success."""
    if not recipient_list:
        logger.warning(f"_send skipped '{subject}': no recipients")
        return False
    recipient_list = [e for e in recipient_list if e and '@' in e]
    if not recipient_list:
        logger.warning(f"_send skipped '{subject}': all recipients had empty emails")
        return False

    context.setdefault('school_name', _school())
    context.setdefault('year', timezone.now().year)

    try:
        html_body  = render_to_string(f'emails/{template}.html', context)
        plain_body = render_to_string(f'emails/{template}.txt',  context)
        msg = EmailMultiAlternatives(
            subject    = f"[{_school()}] {subject}",
            body       = plain_body,
            from_email = _from(),
            to         = recipient_list,
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=fail_silently)
        logger.info(f"Email sent: '{subject}' → {recipient_list}")
        return True
    except Exception as e:
        logger.error(f"Email FAILED: '{subject}' → {e}")
        if not fail_silently:
            raise
        return False


# ─── APPROVAL / REJECTION ────────────────────────────────────────────────────

def send_student_approved(student):
    return _send("Your student account has been approved",
                 "student_approved", {'user': student}, [student.email])


def send_student_rejected(student):
    return _send("Update on your account registration",
                 "student_rejected", {'user': student}, [student.email])


def send_teacher_approved(teacher):
    return _send("Your teacher account has been approved",
                 "teacher_approved", {'user': teacher}, [teacher.email])


def send_teacher_rejected(teacher):
    return _send("Update on your teacher account registration",
                 "teacher_rejected", {'user': teacher}, [teacher.email])


def send_new_registration_to_admin(user):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admins = list(User.objects.filter(is_superuser=True).values_list('email', flat=True))
    admins = [e for e in admins if e]
    if not admins:
        logger.warning("No admin emails found to notify of new registration")
        return False
    return _send(
        f"New {user.role} account pending approval: {user.get_full_name() or user.username}",
        "new_registration_admin",
        {'new_user': user},
        admins,
    )


def send_student_registration_to_teachers(student):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    teachers = list(User.objects.filter(role='teacher', is_approved=True).values_list('email', flat=True))
    teachers = [e for e in teachers if e]
    if not teachers:
        logger.info("No approved teachers with email to notify of new student")
        return False
    return _send(
        f"New student pending approval: {student.get_full_name() or student.username} (Grade {student.grade_level})",
        "new_student_admin",
        {'student': student},
        teachers,
    )


# ─── OTP ─────────────────────────────────────────────────────────────────────

def send_otp_email(email, otp_code, name=''):
    return _send(
        "Your EduLMS verification code",
        "otp_verify",
        {'otp_code': otp_code, 'name': name},
        [email],
        fail_silently=False,  # Must raise so register view can show error
    )


# ─── ROOM ASSIGNMENT ─────────────────────────────────────────────────────────

def send_room_assigned(student, room):
    return _send(
        f"You have been added to: {room.name}",
        "room_assigned",
        {'user': student, 'room': room},
        [student.email],
    )


def send_room_removed(student, room):
    return _send(
        f"You have been removed from: {room.name}",
        "room_removed",
        {'user': student, 'room': room},
        [student.email],
    )


# ─── ASSIGNMENT NOTIFICATIONS ────────────────────────────────────────────────

def send_new_assignment(assignment):
    from courses.models import RoomStudent
    students = RoomStudent.objects.filter(room=assignment.room).select_related('student')
    emails = [rs.student.email for rs in students if rs.student.email]
    if not emails:
        logger.info(f"No student emails for assignment notification in {assignment.room}")
        return False
    return _send(
        f"New assignment in {assignment.room.name}: {assignment.title}",
        "new_assignment",
        {'assignment': assignment},
        emails,
    )


def send_assignment_graded(submission):
    return _send(
        f"Your assignment has been graded: {submission.assignment.title}",
        "assignment_graded",
        {'submission': submission},
        [submission.student.email],
    )


# ─── ANNOUNCEMENTS ───────────────────────────────────────────────────────────

def send_announcement(announcement):
    """
    Sends announcement email to correct audience.
    Returns (success: bool, recipient_count: int, error: str|None)
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    audience    = announcement.audience
    recipients  = []

    if audience == 'all':
        recipients = list(User.objects.filter(
            is_approved=True, role__in=['student','teacher']
        ).exclude(email='').values_list('email', flat=True))

    elif audience == 'students':
        recipients = list(User.objects.filter(
            is_approved=True, role='student'
        ).exclude(email='').values_list('email', flat=True))

    elif audience == 'teachers':
        recipients = list(User.objects.filter(
            is_approved=True, role='teacher'
        ).exclude(email='').values_list('email', flat=True))

    elif audience.startswith('grade_'):
        grade = audience.replace('grade_', '')
        recipients = list(User.objects.filter(
            is_approved=True, role='student', grade_level=grade
        ).exclude(email='').values_list('email', flat=True))

    recipients = list(set(recipients))  # deduplicate

    if not recipients:
        logger.warning(f"Announcement '{announcement.title}': no recipients with email for audience '{audience}'")
        return False, 0, "No recipients found with email addresses."

    success = _send(
        subject       = announcement.title,
        template      = "announcement",
        context       = {'announcement': announcement},
        recipient_list = recipients,
    )
    return success, len(recipients), None


# ─── PASSWORD RECOVERY ───────────────────────────────────────────────────────

def send_password_reset(user, reset_url):
    """Student receives a password reset link."""
    return _send(
        "Password reset request",
        "password_reset",
        {'user': user, 'reset_url': reset_url},
        [user.email],
        fail_silently=False,
    )


# ─── PASSWORD SETUP (on account approval) ────────────────────────────────────

def send_teacher_setup_link(teacher, setup_url):
    """Teacher gets a password setup link when Admin approves their account."""
    return _send(
        "Set up your EduLMS teacher account password",
        "teacher_setup_password",
        {'user': teacher, 'setup_url': setup_url},
        [teacher.email],
        fail_silently=False,
    )


def send_student_setup_link(student, setup_url):
    """Student gets a password setup link when Teacher approves their account."""
    return _send(
        "Set up your EduLMS student account password",
        "student_setup_password",
        {'user': student, 'setup_url': setup_url},
        [student.email],
        fail_silently=False,
    )
