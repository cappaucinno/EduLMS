"""
EduLMS API Serializers
All data shapes for the REST API.
"""
from rest_framework import serializers
from accounts.models import User
from courses.models import (
    Room, RoomStudent, Lesson, Material, Assignment,
    Submission, Quiz, Question, QuizAttempt,
    Announcement, AnnouncementRead, LiveSession,
)
from assessments.models import Grade


# ─── AUTH / USER ─────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    full_name     = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id','username','email','first_name','last_name','full_name',
                  'role','grade_level','is_approved','date_joined','profile_image']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_profile_image(self, obj):
        request = self.context.get('request')
        if obj.profile_image and request:
            return request.build_absolute_uri(obj.profile_image.url)
        return None


class PublicUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id','username','full_name','role','grade_level']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


# ─── ROOMS ───────────────────────────────────────────────────────────────────

class RoomSerializer(serializers.ModelSerializer):
    teacher      = PublicUserSerializer(read_only=True)
    student_count = serializers.SerializerMethodField()
    thumbnail    = serializers.SerializerMethodField()

    class Meta:
        model  = Room
        fields = ['id','name','subject','grade_level','description',
                  'teacher','student_count','thumbnail','created_at']

    def get_student_count(self, obj):
        return obj.roomstudent_set.count()

    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if getattr(obj, 'thumbnail', None) and obj.thumbnail and request:
            return request.build_absolute_uri(obj.thumbnail.url)
        return None


# ─── LESSONS & MATERIALS ─────────────────────────────────────────────────────

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Lesson
        fields = ['id','room','title','content','video_url','order','created_at']


class MaterialSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model  = Material
        fields = ['id','room','title','file','link','order','created_at']

    def get_file(self, obj):
        request = self.context.get('request')
        if getattr(obj, 'file', None) and obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


# ─── ASSIGNMENTS ─────────────────────────────────────────────────────────────

class AssignmentSerializer(serializers.ModelSerializer):
    room_name    = serializers.CharField(source='room.name',         read_only=True)
    room_subject = serializers.CharField(source='room.subject',      read_only=True)
    is_overdue   = serializers.SerializerMethodField()

    class Meta:
        model  = Assignment
        fields = ['id','room','room_name','room_subject','title','description',
                  'due_date','max_score','is_overdue','created_at']

    def get_is_overdue(self, obj):
        from django.utils import timezone
        return obj.due_date < timezone.now() if obj.due_date else False


class SubmissionSerializer(serializers.ModelSerializer):
    student   = PublicUserSerializer(read_only=True)
    grade     = serializers.SerializerMethodField()
    file      = serializers.SerializerMethodField()

    class Meta:
        model  = Submission
        fields = ['id','assignment','student','file','notes',
                  'status','submitted_at','grade']

    def get_grade(self, obj):
        try:
            g = obj.grade
            return {'score': g.score, 'feedback': g.feedback, 'graded_at': g.graded_at}
        except Exception:
            return None

    def get_file(self, obj):
        request = self.context.get('request')
        if getattr(obj, 'file', None) and obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Submission
        fields = ['assignment','file','notes']


# ─── QUIZ ────────────────────────────────────────────────────────────────────

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Question
        fields = ['id','text','option_a','option_b','option_c','option_d']


class QuizSerializer(serializers.ModelSerializer):
    questions     = QuestionSerializer(many=True, read_only=True)
    question_count = serializers.SerializerMethodField()
    attempted     = serializers.SerializerMethodField()

    class Meta:
        model  = Quiz
        fields = ['id','room','title','question_count','attempted','questions','created_at']

    def get_question_count(self, obj):
        return obj.questions.count()

    def get_attempted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.quizattempt_set.filter(student=request.user).exists()
        return False


class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model  = QuizAttempt
        fields = ['id','quiz','student','score','attempted_at']


class QuizSubmitSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.CharField(),
        help_text='{"question_id": "A"|"B"|"C"|"D"}'
    )


# ─── GRADES ──────────────────────────────────────────────────────────────────

class GradeSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source='submission.assignment.title', read_only=True)
    room_name        = serializers.CharField(source='submission.assignment.room.name', read_only=True)
    subject          = serializers.CharField(source='submission.assignment.room.subject', read_only=True)
    max_score        = serializers.IntegerField(source='submission.assignment.max_score', read_only=True)

    class Meta:
        model  = Grade
        fields = ['id','submission','assignment_title','room_name','subject',
                  'score','max_score','feedback','graded_at']


# ─── ANNOUNCEMENTS ───────────────────────────────────────────────────────────

class AnnouncementSerializer(serializers.ModelSerializer):
    author       = PublicUserSerializer(read_only=True)
    is_read      = serializers.SerializerMethodField()
    attachment   = serializers.SerializerMethodField()

    class Meta:
        model  = Announcement
        fields = ['id','title','content','ann_type','audience','author',
                  'pinned','link','attachment','is_read',
                  'scheduled_at','created_at']

    def get_is_read(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return AnnouncementRead.objects.filter(
                announcement=obj, user=request.user, is_read=True
            ).exists()
        return False

    def get_attachment(self, obj):
        request = self.context.get('request')
        if getattr(obj, 'attachment', None) and obj.attachment and request:
            return request.build_absolute_uri(obj.attachment.url)
        return None


# ─── LIVE SESSIONS ───────────────────────────────────────────────────────────

class LiveSessionSerializer(serializers.ModelSerializer):
    jitsi_url    = serializers.SerializerMethodField()
    created_by   = PublicUserSerializer(read_only=True)

    class Meta:
        model  = LiveSession
        fields = ['id','room','title','description','jitsi_url','jitsi_room',
                  'scheduled_at','started_at','ended_at','status','created_by']

    def get_jitsi_url(self, obj):
        return obj.get_jitsi_url()
