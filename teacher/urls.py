from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',                              views.dashboard,          name='teacher_dashboard'),
    # Room CRUD
    path('room/create/',                            views.create_room,        name='create_room'),
    path('room/<int:pk>/edit/',                     views.edit_room,          name='edit_room'),
    path('room/<int:pk>/delete/',                   views.delete_room,        name='delete_room'),
    path('room/<int:pk>/',                          views.room_overview,      name='room_overview'),
    # Students in room
    path('room/<int:pk>/students/',                 views.manage_students,    name='manage_students'),
    path('room/<int:pk>/students/<int:student_pk>/assign/',  views.assign_student, name='assign_student'),
    path('room/<int:pk>/students/<int:student_pk>/remove/',  views.remove_student, name='remove_student'),
    # Content
    path('room/<int:pk>/lessons/',                  views.manage_lessons,     name='manage_lessons'),
    path('lesson/<int:pk>/delete/',                 views.delete_lesson,      name='delete_lesson'),
    path('room/<int:pk>/materials/',                views.manage_materials,   name='manage_materials'),
    path('material/<int:pk>/delete/',               views.delete_material,    name='delete_material'),
    path('room/<int:pk>/assignments/',              views.manage_assignments, name='manage_assignments'),
    path('assignment/<int:assignment_pk>/submissions/', views.view_submissions, name='view_submissions'),
    path('submission/<int:pk>/grade/',              views.grade_submission,   name='grade_submission'),
    path('room/<int:pk>/quiz/',                     views.manage_quiz,        name='manage_quiz'),
    path('quiz/<int:quiz_pk>/questions/',           views.add_questions,      name='add_questions'),
    # Announcements
    path('announcements/',                    views.announcement_list,   name='announcement_list'),
    path('announcements/create/',             views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/edit/',      views.announcement_edit,   name='announcement_edit'),
    path('announcements/<int:pk>/delete/',    views.announcement_delete, name='announcement_delete'),
    # Approvals
    path('students/pending/',                       views.pending_students,   name='pending_students'),
    path('students/<int:pk>/approve/',              views.approve_student,    name='approve_student'),
    path('students/<int:pk>/reject/',               views.reject_student,     name='reject_student'),
]
