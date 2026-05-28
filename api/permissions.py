"""EduLMS API custom permissions."""
from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'teacher'


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.role == 'admin'
        )


class IsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in ('teacher', 'admin') or request.user.is_superuser
        )


class IsApproved(BasePermission):
    message = 'Your account is pending approval.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_approved or request.user.is_superuser
        )
