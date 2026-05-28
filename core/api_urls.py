"""
EduLMS API URLs
All routes are under /api/
"""
from django.urls import path
from core.api import (
    # Auth
    api_login, api_register, api_token_refresh,
    api_me, api_change_password,
    # Rooms
    api_rooms, api_room_detail,
    # Content
    api_lessons, api_materials,
    # Assignments
    api_assignments, api_assignment_detail, api_submit_assignment,
    # Quizzes
    api_quizzes, api_quiz_detail, api_submit_quiz,
    # Grades
    api_grades,
    # Announcements
    api_announcements_list, api_announcement_read,
    # Live sessions
    api_live_sessions,
    # Dashboard / Notifications
    api_notifications, api_dashboard,
    # Admin
    api_admin_users, api_admin_approve, api_admin_stats,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # ── AUTH ──────────────────────────────────────────────────────────────────
    path('auth/login/',           api_login,           name='api_login'),
    path('auth/register/',        api_register,        name='api_register'),
    path('auth/token/refresh/',   TokenRefreshView.as_view(), name='api_token_refresh'),
    path('auth/me/',              api_me,              name='api_me'),
    path('auth/change-password/', api_change_password, name='api_change_password'),

    # ── ROOMS ─────────────────────────────────────────────────────────────────
    path('rooms/',                api_rooms,       name='api_rooms'),
    path('rooms/<int:pk>/',       api_room_detail, name='api_room_detail'),

    # ── ROOM CONTENT ──────────────────────────────────────────────────────────
    path('rooms/<int:pk>/lessons/',     api_lessons,      name='api_lessons'),
    path('rooms/<int:pk>/materials/',   api_materials,    name='api_materials'),
    path('rooms/<int:pk>/assignments/', api_assignments,  name='api_assignments'),
    path('rooms/<int:pk>/quizzes/',     api_quizzes,      name='api_quizzes'),
    path('rooms/<int:pk>/live/',        api_live_sessions,name='api_live_sessions'),

    # ── ASSIGNMENTS ───────────────────────────────────────────────────────────
    path('assignments/<int:pk>/',         api_assignment_detail,  name='api_assignment_detail'),
    path('assignments/<int:pk>/submit/',  api_submit_assignment,  name='api_submit_assignment'),

    # ── QUIZZES ───────────────────────────────────────────────────────────────
    path('quizzes/<int:pk>/',         api_quiz_detail,  name='api_quiz_detail'),
    path('quizzes/<int:pk>/submit/',  api_submit_quiz,  name='api_submit_quiz'),

    # ── GRADES ────────────────────────────────────────────────────────────────
    path('grades/',  api_grades,  name='api_grades'),

    # ── ANNOUNCEMENTS ─────────────────────────────────────────────────────────
    path('announcements/',              api_announcements_list, name='api_announcements'),
    path('announcements/<int:pk>/read/',api_announcement_read,  name='api_announcement_read'),

    # ── DASHBOARD & NOTIFICATIONS ─────────────────────────────────────────────
    path('dashboard/',     api_dashboard,     name='api_dashboard'),
    path('notifications/', api_notifications, name='api_notifications'),

    # ── ADMIN ─────────────────────────────────────────────────────────────────
    path('admin/users/',                api_admin_users,   name='api_admin_users'),
    path('admin/users/<int:pk>/approve/', api_admin_approve, name='api_admin_approve'),
    path('admin/stats/',                api_admin_stats,   name='api_admin_stats'),
]
