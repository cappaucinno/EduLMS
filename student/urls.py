from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',                              views.dashboard,          name='student_dashboard'),
    path('room/<int:pk>/',                          views.room_detail,        name='room_detail'),
    path('room/<int:room_pk>/lesson/<int:lesson_pk>/', views.view_lesson,    name='view_lesson'),
    path('assignment/<int:assignment_pk>/submit/',  views.submit_assignment,  name='submit_assignment'),
    path('quiz/<int:quiz_pk>/take/',                views.take_quiz,          name='take_quiz'),
    path('announcements/',  views.announcements,      name='student_announcements'),
    path('announcement/<int:pk>/read/', views.mark_announcement_read, name='mark_ann_read'),
    path('log-tab-violation/',              views.log_tab_violation,       name='log_tab_violation'),
    path('grades/',                                 views.my_grades,          name='my_grades'),

    path('room/<int:pk>/live/', views.student_live_sessions, name='student_live_sessions'),
]