"""
EduLMS REST API URL Configuration
All endpoints prefixed with /api/v1/
"""
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [

    # ── AUTH ──────────────────────────────────────────────────────────────────
    path('auth/token/',            views.token_obtain,          name='token_obtain'),
    path('auth/token/refresh/',    views.token_refresh,         name='token_refresh'),
    path('auth/logout/',           views.logout,                name='logout'),
    path('auth/me/',               views.me,                    name='me'),

    # ── DASHBOARD ─────────────────────────────────────────────────────────────
    path('dashboard/',             views.dashboard,             name='dashboard'),

    # ── ROOMS ─────────────────────────────────────────────────────────────────
    path('rooms/',                 views.room_list,             name='room_list'),
    path('rooms/<int:pk>/',        views.room_detail,           name='room_detail'),
    path('rooms/<int:pk>/students/', views.room_students,       name='room_students'),

    # ── LESSONS ───────────────────────────────────────────────────────────────
    path('rooms/<int:pk>/lessons/',              views.lesson_list,    name='lesson_list'),
    path('rooms/<int:pk>/lessons/<int:lesson_pk>/', views.lesson_detail, name='lesson_detail'),

    # ── MATERIALS ─────────────────────────────────────────────────────────────
    path('rooms/<int:pk>/materials/',            views.material_list,  name='material_list'),

    # ── ASSIGNMENTS ───────────────────────────────────────────────────────────
    path('rooms/<int:pk>/assignments/',              views.assignment_list,   name='assignment_list'),
    path('assignments/<int:assignment_pk>/',          views.assignment_detail, name='assignment_detail'),
    path('assignments/<int:assignment_pk>/submit/',   views.assignment_submit, name='assignment_submit'),

    # ── SUBMISSIONS ───────────────────────────────────────────────────────────
    path('submissions/',                              views.submission_list,   name='submission_list'),
    path('submissions/<int:submission_pk>/grade/',    views.submission_grade,  name='submission_grade'),

    # ── QUIZZES ───────────────────────────────────────────────────────────────
    path('rooms/<int:pk>/quizzes/',                  views.quiz_list,    name='quiz_list'),
    path('quizzes/<int:quiz_pk>/',                   views.quiz_detail,  name='quiz_detail'),
    path('quizzes/<int:quiz_pk>/submit/',             views.quiz_submit,  name='quiz_submit'),

    # ── GRADES ────────────────────────────────────────────────────────────────
    path('grades/',                                  views.grade_list,   name='grade_list'),

    # ── ANNOUNCEMENTS ─────────────────────────────────────────────────────────
    path('announcements/',                           views.announcement_list,       name='announcement_list'),
    path('announcements/<int:ann_pk>/read/',         views.announcement_mark_read,  name='announcement_read'),

    # ── LIVE SESSIONS ─────────────────────────────────────────────────────────
    path('rooms/<int:pk>/live/',                     views.live_session_list, name='live_session_list'),
]
