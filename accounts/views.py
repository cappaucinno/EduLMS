from core.decorators import safe_view
from core.email_utils import (
    send_student_registration_to_teachers,
    send_new_registration_to_admin,
    send_otp_email,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from .forms import RegisterForm, LoginForm
from .models import User, OTPVerification
import logging

logger = logging.getLogger('edulms')


@safe_view
def register_view(request):
    # Check if registration is open
    try:
        from core.models import SiteSettings
        s = SiteSettings.get()
        if not s.allow_student_registration and not s.allow_teacher_registration:
            msg = s.registration_message or "Registration is currently closed. Please check back later."
            messages.warning(request, msg)
            return redirect('/accounts/login/')
    except Exception:
        pass
    if request.user.is_authenticated:
        return redirect('/dashboard/')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data

        # Teachers → skip OTP, account pending admin approval
        if data.get('role') in ('teacher', 'admin'):
            user = form.save(commit=False)
            user.is_approved = False
            user.save()
            send_new_registration_to_admin(user)
            messages.info(request,
                "✅ Teacher account created! The Admin will review and approve your account. "
                "You will receive an email notification once approved.")
            return redirect('/accounts/login/')

        # Students → send OTP to verify email first
        email = data['email']

        form_payload = {
            'username':    data['username'],
            'first_name':  data['first_name'],
            'last_name':   data['last_name'],
            'email':       email,
            'role':        data['role'],
            'grade_level': data.get('grade_level', ''),
        }

        otp_obj = OTPVerification.generate(email=email, form_data=form_payload)
        name    = f"{data['first_name']} {data['last_name']}".strip() or data['username']

        email_sent = True
        try:
            send_otp_email(email=email, otp_code=otp_obj.otp_code, name=name)
            logger.info(f"OTP email sent to {email}")
        except Exception as e:
            email_sent = False
            logger.error(f"OTP email FAILED for {email}: {e}")

        if email_sent:
            messages.info(request,
                f"📧 A 6-digit verification code has been sent to {email}. "
                "Please check your inbox (and spam folder).")
        else:
            # Email failed but still let them proceed (console backend or misconfigured)
            messages.warning(request,
                f"⚠️ Could not send email to {email}. "
                "If you're testing locally, check the terminal console for the OTP code.")

        return redirect(f'/accounts/verify-otp/{otp_obj.pk}/')

    return render(request, 'accounts/register.html', {'form': form})


@safe_view
def verify_otp_view(request, pk):
    otp_obj = get_object_or_404(OTPVerification, pk=pk, is_used=False)

    if otp_obj.is_expired():
        otp_obj.delete()
        messages.error(request, "⏱️ Your verification code expired (10 min limit). Please register again.")
        return redirect('/accounts/register/')

    if otp_obj.attempts >= 5:
        otp_obj.delete()
        messages.error(request, "🔒 Too many incorrect attempts. Please register again.")
        return redirect('/accounts/register/')

    error = None
    if request.method == 'POST':
        entered = request.POST.get('otp_code', '').strip()

        if otp_obj.is_valid(entered):
            otp_obj.is_used = True
            otp_obj.save()

            d = otp_obj.form_data
            user = User(
                username    = d['username'],
                first_name  = d['first_name'],
                last_name   = d['last_name'],
                email       = d['email'],
                role        = d['role'],
                grade_level = d.get('grade_level') or None,
                is_approved = False,
            )
            # No password set at registration — assigned when teacher approves
            user.set_unusable_password()
            user.save()

            # Notify teachers about new student
            try:
                send_student_registration_to_teachers(user)
            except Exception as e:
                logger.error(f"Failed to notify teachers of new student {user.username}: {e}")

            messages.success(request,
                "✅ Email verified! Your account has been created and is pending "
                "teacher approval. You will receive an email when approved.")
            return redirect('/accounts/login/')

        else:
            otp_obj.attempts += 1
            otp_obj.save()
            remaining = max(0, 5 - otp_obj.attempts)
            error = f"❌ Incorrect code. {remaining} attempt(s) remaining."

    masked_email = _mask_email(otp_obj.form_data.get('email', ''))
    return render(request, 'accounts/verify_otp.html', {
        'otp_obj':      otp_obj,
        'masked_email': masked_email,
        'error':        error,
    })


@safe_view
def resend_otp_view(request, pk):
    otp_obj = get_object_or_404(OTPVerification, pk=pk, is_used=False)
    email   = otp_obj.form_data.get('email', '')
    name    = f"{otp_obj.form_data.get('first_name','')} {otp_obj.form_data.get('last_name','')}".strip()

    new_otp = OTPVerification.generate(email=email, form_data=otp_obj.form_data)
    try:
        send_otp_email(email=email, otp_code=new_otp.otp_code, name=name)
        messages.info(request, f"📧 A new verification code has been sent to {_mask_email(email)}.")
    except Exception as e:
        logger.error(f"Resend OTP failed for {email}: {e}")
        messages.warning(request,
            "⚠️ Could not send email. Check the terminal console for the OTP code if testing locally.")

    return redirect(f'/accounts/verify-otp/{new_otp.pk}/')


def _mask_email(email):
    if '@' not in email:
        return email
    local, domain = email.split('@', 1)
    return local[:2] + '***@' + domain


@safe_view
def login_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if not user.is_superuser and not user.is_approved:
            if user.role == 'teacher':
                messages.error(request,
                    "⏳ Your teacher account is pending Admin approval. "
                    "You will receive an email at your registered address when approved.")
            else:
                messages.error(request,
                    "⏳ Your account is pending Teacher approval. "
                    "You will receive an email at your registered address when approved.")
            return render(request, 'accounts/login.html', {'form': form})
        login(request, user)
        return redirect('/dashboard/')
    return render(request, 'accounts/login.html', {'form': form})


@safe_view
def logout_view(request):
    logout(request)
    return redirect('/accounts/login/')


@safe_view
def dashboard_redirect(request):
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')
    if request.user.is_superuser:
        return redirect('/superadmin/')
    role = request.user.role
    if role == 'teacher':
        return redirect('/teacher/dashboard/')
    elif role == 'student':
        return redirect('/student/dashboard/')
    else:
        return redirect('/admin/')


# ─── PASSWORD RECOVERY ────────────────────────────────────────────────────────

@safe_view
def forgot_password_view(request):
    from .forms import ForgotPasswordForm
    from .models import PasswordResetToken
    from core.email_utils import send_password_reset

    form = ForgotPasswordForm(request.POST or None)
    sent = False

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].strip().lower()
        # Always show success (don't reveal if email exists — security)
        try:
            user = User.objects.get(email__iexact=email, role='student')
            token_obj  = PasswordResetToken.generate(user)
            reset_url  = request.build_absolute_uri(
                f'/accounts/reset-password/{token_obj.token}/'
            )
            send_password_reset(user, reset_url)
            logger.info(f"Password reset link sent to {email}")
        except User.DoesNotExist:
            logger.info(f"Password reset requested for unknown email: {email}")
        except Exception as e:
            logger.error(f"Password reset email failed: {e}")

        sent = True

    return render(request, 'accounts/forgot_password.html', {'form': form, 'sent': sent})


@safe_view
def reset_password_view(request, token):
    from .forms import ResetPasswordForm
    from .models import PasswordResetToken

    try:
        token_obj = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        messages.error(request, "Invalid or expired password reset link.")
        return redirect('/accounts/forgot-password/')

    if not token_obj.is_valid():
        messages.error(request, "This reset link has expired or already been used. Please request a new one.")
        return redirect('/accounts/forgot-password/')

    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = token_obj.user
        user.set_password(form.cleaned_data['new_password'])
        user.save()
        token_obj.is_used = True
        token_obj.save()
        messages.success(request, "✅ Password changed successfully! You can now log in with your new password.")
        return redirect('/accounts/login/')

    return render(request, 'accounts/reset_password.html', {
        'form': form, 'token': token
    })


# ─── STUDENT PROFILE ──────────────────────────────────────────────────────────

@safe_view
def student_profile_view(request):
    from .forms import StudentProfileForm, ChangePasswordForm
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')

    profile_form  = StudentProfileForm(request.POST or None, instance=request.user)
    password_form = ChangePasswordForm(request.POST or None)
    active_tab    = 'profile'

    if request.method == 'POST':
        if 'save_profile' in request.POST:
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "✅ Profile updated successfully.")
                return redirect('/accounts/profile/')
            else:
                active_tab = 'profile'

        elif 'change_password' in request.POST:
            active_tab = 'password'
            if password_form.is_valid():
                if not request.user.check_password(password_form.cleaned_data['old_password']):
                    messages.error(request, "❌ Current password is incorrect.")
                else:
                    request.user.set_password(password_form.cleaned_data['new_password'])
                    request.user.save()
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "✅ Password changed successfully. You are still logged in.")
                    return redirect('/accounts/profile/')

    # Stats for profile
    from courses.models import RoomStudent, Submission, QuizAttempt
    from assessments.models import Grade

    enrolled_rooms    = RoomStudent.objects.filter(student=request.user).count()
    submissions_count = Submission.objects.filter(student=request.user).count()
    graded_count      = Grade.objects.filter(submission__student=request.user).count()
    quiz_attempts     = QuizAttempt.objects.filter(student=request.user).count()
    avg_score         = None
    grades = Grade.objects.filter(submission__student=request.user)
    if grades.exists():
        total = sum(g.score for g in grades)
        avg_score = round(total / grades.count(), 1)

    return render(request, 'accounts/student_profile.html', {
        'profile_form':   profile_form,
        'password_form':  password_form,
        'active_tab':     active_tab,
        'enrolled_rooms':    enrolled_rooms,
        'submissions_count': submissions_count,
        'graded_count':      graded_count,
        'quiz_attempts':     quiz_attempts,
        'avg_score':         avg_score,
    })


@safe_view
def teacher_profile_view(request):
    from .forms import TeacherProfileForm, ChangePasswordForm
    if not request.user.is_authenticated or request.user.role != 'teacher':
        return redirect('/accounts/login/')

    profile_form  = TeacherProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    password_form = ChangePasswordForm(request.POST or None)
    active_tab    = 'profile'

    if request.method == 'POST':
        if 'save_profile' in request.POST:
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "✅ Profile updated successfully.")
                return redirect('/accounts/teacher-profile/')
            active_tab = 'profile'

        elif 'change_password' in request.POST:
            active_tab = 'password'
            if password_form.is_valid():
                if not request.user.check_password(password_form.cleaned_data['old_password']):
                    messages.error(request, "❌ Current password is incorrect.")
                else:
                    request.user.set_password(password_form.cleaned_data['new_password'])
                    request.user.save()
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "✅ Password changed successfully.")
                    return redirect('/accounts/teacher-profile/')

    from courses.models import Room, RoomStudent, Assignment
    rooms_count   = Room.objects.filter(teacher=request.user).count()
    students_count = RoomStudent.objects.filter(room__teacher=request.user).values('student').distinct().count()
    assignments_count = Assignment.objects.filter(room__teacher=request.user).count()

    return render(request, 'accounts/teacher_profile.html', {
        'profile_form':       profile_form,
        'password_form':      password_form,
        'active_tab':         active_tab,
        'rooms_count':        rooms_count,
        'students_count':     students_count,
        'assignments_count':  assignments_count,
    })


# ─── PASSWORD SETUP (on first approval) ──────────────────────────────────────

@safe_view
def setup_password_view(request, token):
    """
    First-time password setup for newly approved teachers and students.
    Accessible at: /accounts/setup/password/<token>/
    Link is sent by email, valid 72 hours, single-use.
    """
    from .forms import ResetPasswordForm
    from .models import PasswordResetToken

    try:
        token_obj = PasswordResetToken.objects.get(
            token=token, token_type='setup', is_used=False
        )
    except PasswordResetToken.DoesNotExist:
        return render(request, 'accounts/setup_password_invalid.html', status=400)

    if not token_obj.is_valid():
        return render(request, 'accounts/setup_password_invalid.html', {
            'expired': True,
            'user': token_obj.user,
        }, status=400)

    user = token_obj.user
    form = ResetPasswordForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user.set_password(form.cleaned_data['password'])
        user.save()
        token_obj.is_used = True
        token_obj.save()

        # Auto-login after setup
        from django.contrib.auth import login
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        messages.success(request,
            f"✅ Password set! Welcome to EduLMS, {user.get_full_name() or user.first_name}.")
        return redirect('/dashboard/')

    return render(request, 'accounts/setup_password.html', {
        'form': form,
        'user_obj': user,
    })


# ─── GOOGLE OAUTH CALLBACK HANDLER ───────────────────────────────────────────

@safe_view
def google_signup_complete(request):
    """
    After Google OAuth, user must choose their role and grade level.
    allauth creates the socialaccount — we just need to set role.
    """
    from .forms import GoogleSignupForm
    if not request.user.is_authenticated:
        return redirect('/accounts/login/')
    user = request.user
    # If role already set, they're good
    if getattr(user, 'role', None) and user.role in ('student', 'teacher'):
        return redirect('/dashboard/')

    form = GoogleSignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user.role        = form.cleaned_data['role']
        user.grade_level = form.cleaned_data.get('grade_level') or None
        user.is_approved = False
        user.save()
        messages.info(request, "✅ Profile set up! Wait for approval before you can log in.")
        from core.email_utils import send_new_registration_to_admin
        try:
            send_new_registration_to_admin(user)
        except Exception:
            pass
        from django.contrib.auth import logout
        logout(request)
        return redirect('/accounts/login/')

    return render(request, 'accounts/google_signup_complete.html', {'form': form, 'user': user})
