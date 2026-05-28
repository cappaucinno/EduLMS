from django.urls import path
from . import views

urlpatterns = [
    path('register/',                         views.register_view,        name='register'),
    path('verify-otp/<int:pk>/',              views.verify_otp_view,      name='verify_otp'),
    path('resend-otp/<int:pk>/',              views.resend_otp_view,      name='resend_otp'),
    path('login/',                            views.login_view,           name='login'),
    path('logout/',                           views.logout_view,          name='logout'),
    # Password recovery (forgot password)
    path('forgot-password/',                  views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/',       views.reset_password_view,  name='reset_password'),
    # First-time password SETUP (sent on approval)
    path('setup/password/<str:token>/',       views.setup_password_view,  name='setup_password'),
    # Profiles
    path('profile/',                          views.student_profile_view, name='student_profile'),
    path('google-signup/',   views.google_signup_complete, name='google_signup_complete'),
    path('teacher-profile/',                  views.teacher_profile_view, name='teacher_profile'),
]
