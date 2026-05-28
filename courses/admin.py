from django.contrib import admin
from .models import (
    Room, RoomStudent, Lesson, Material, Assignment, Submission,
    Quiz, Question, QuizAttempt, Announcement, AnnouncementRead, TabViolation
)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display  = ['name', 'subject', 'grade_level', 'teacher', 'student_count', 'created_at']
    list_filter   = ['grade_level', 'subject', 'teacher']
    search_fields = ['name', 'subject']


@admin.register(RoomStudent)
class RoomStudentAdmin(admin.ModelAdmin):
    list_display = ['student', 'room', 'assigned_by', 'assigned_at']
    list_filter  = ['room__grade_level', 'room__subject']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display  = ['title', 'ann_type', 'audience', 'author', 'pinned', 'send_email', 'read_count', 'created_at']
    list_filter   = ['ann_type', 'audience', 'pinned']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['pin_announcements']

    @admin.action(description='📌 Pin selected announcements')
    def pin_announcements(self, request, queryset):
        queryset.update(pinned=True)

    def read_count(self, obj):
        return obj.read_count()
    read_count.short_description = 'Reads'


@admin.register(AnnouncementRead)
class AnnouncementReadAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'is_read', 'read_at']
    list_filter  = ['is_read']


@admin.register(TabViolation)
class TabViolationAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'page_url', 'count', 'occurred_at']
    list_filter  = ['occurred_at']
    search_fields = ['student__username']


admin.site.register(Lesson)
admin.site.register(Material)
admin.site.register(Assignment)
admin.site.register(Submission)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(QuizAttempt)
