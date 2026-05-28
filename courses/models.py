from django.db import models
from accounts.models import User, GRADE_CHOICES

SUBJECT_CHOICES = (
    ('English',       'English'),
    ('Filipino',      'Filipino'),
    ('Mathematics',   'Mathematics'),
    ('Science',       'Science'),
    ('AP',            'Araling Panlipunan'),
    ('TLE',           'Technology & Livelihood Education'),
    ('MAPEH',         'MAPEH'),
    ('ESP',           'Edukasyon sa Pagpapakatao'),
    ('ICT',           'ICT'),
    ('Research',      'Research'),
    ('Other',         'Other'),
)


class Room(models.Model):
    """A Room = one Subject in one Grade Level, managed by one Teacher."""
    name        = models.CharField(max_length=200, help_text='e.g. "Grade 8 - Mathematics"')
    subject     = models.CharField(max_length=50, choices=SUBJECT_CHOICES)
    grade_level = models.CharField(max_length=2, choices=GRADE_CHOICES)
    description = models.TextField(blank=True)
    teacher     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rooms_taught')
    created_at  = models.DateTimeField(auto_now_add=True)
    thumbnail   = models.ImageField(upload_to='room_thumbnails/', blank=True, null=True)

    class Meta:
        ordering = ['grade_level', 'subject']

    def __str__(self):
        return f"Grade {self.grade_level} — {self.subject}"

    def student_count(self):
        return self.assignments_to.count()


class RoomStudent(models.Model):
    """Teacher-assigned link between a student and a room. No self-enrollment."""
    room       = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='assignments_to')
    student    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='assignments_made'
    )

    class Meta:
        unique_together = ('room', 'student')

    def __str__(self):
        return f"{self.student} → {self.room}"


class Material(models.Model):
    """Downloadable file/link attached to a room."""
    room        = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='materials')
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file        = models.FileField(upload_to='materials/', blank=True, null=True)
    link        = models.URLField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    order       = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.room} — {self.title}"


class Lesson(models.Model):
    room       = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='lessons')
    title      = models.CharField(max_length=200)
    content    = models.TextField()
    video_url  = models.URLField(blank=True)
    order      = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.room} — {self.title}"


class Assignment(models.Model):
    room       = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='assignments')
    title      = models.CharField(max_length=200)
    description = models.TextField()
    due_date   = models.DateTimeField()
    max_score  = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.room} — {self.title}"


class Submission(models.Model):
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('graded',    'Graded'),
    )
    student     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    assignment  = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    file        = models.FileField(upload_to='submissions/', blank=True, null=True)
    notes       = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')

    class Meta:
        unique_together = ('student', 'assignment')

    def __str__(self):
        return f"{self.student.username} → {self.assignment.title}"


class Quiz(models.Model):
    room       = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='quizzes')
    title      = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.room} — {self.title}"


class Question(models.Model):
    quiz          = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text          = models.TextField()
    option_a      = models.CharField(max_length=200)
    option_b      = models.CharField(max_length=200)
    option_c      = models.CharField(max_length=200)
    option_d      = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=1, choices=[('A','A'),('B','B'),('C','C'),('D','D')])

    def __str__(self):
        return self.text[:60]


class QuizAttempt(models.Model):
    student     = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz        = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score       = models.FloatField(default=0)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'quiz')



class Announcement(models.Model):
    TYPE_CHOICES = (
        ('notice',  'Notice'),
        ('event',   'Event'),
        ('exam',    'Exam'),
        ('holiday', 'Holiday'),
        ('urgent',  'Urgent'),
    )
    AUDIENCE_CHOICES = (
        ('all',      'Everyone (Students & Teachers)'),
        ('students', 'All Students'),
        ('teachers', 'All Teachers'),
        ('grade_7',  'Grade 7 Students'),
        ('grade_8',  'Grade 8 Students'),
        ('grade_9',  'Grade 9 Students'),
        ('grade_10', 'Grade 10 Students'),
        ('grade_11', 'Grade 11 Students'),
        ('grade_12', 'Grade 12 Students'),
    )

    title          = models.CharField(max_length=255)
    content        = models.TextField()
    ann_type       = models.CharField(max_length=10, choices=TYPE_CHOICES, default='notice')
    audience       = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all')
    author         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='announcements')
    pinned         = models.BooleanField(default=False)
    send_email     = models.BooleanField(default=True)
    attachment     = models.FileField(upload_to='announcement_files/', blank=True, null=True)
    link           = models.URLField(blank=True)
    scheduled_at   = models.DateTimeField(null=True, blank=True, help_text='Leave blank to publish now')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pinned', '-created_at']

    def __str__(self):
        return self.title

    def audience_label(self):
        return dict(self.AUDIENCE_CHOICES).get(self.audience, self.audience)

    def type_color(self):
        return {
            'notice': 'primary', 'event': 'success',
            'exam': 'warning', 'holiday': 'info', 'urgent': 'danger'
        }.get(self.ann_type, 'secondary')

    def is_published(self):
        from django.utils import timezone
        if self.scheduled_at and self.scheduled_at > timezone.now():
            return False
        return True

    def read_count(self):
        return self.reads.filter(is_read=True).count()


class AnnouncementRead(models.Model):
    """Tracks read status per user per announcement."""
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ann_reads')
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='reads')
    is_read      = models.BooleanField(default=False)
    read_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'announcement')

    def __str__(self):
        return f"{self.user.username} — {self.announcement.title} ({'read' if self.is_read else 'unread'})"


class TabViolation(models.Model):
    """Logs when a student switches tabs during a quiz or activity."""
    student     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tab_violations')
    quiz        = models.ForeignKey(Quiz, on_delete=models.CASCADE, null=True, blank=True, related_name='tab_violations')
    page_url    = models.CharField(max_length=500)
    occurred_at = models.DateTimeField(auto_now_add=True)
    count       = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-occurred_at']

    def __str__(self):
        return f"{self.student.username} — tab switch on {self.page_url}"


class LiveSession(models.Model):
    """Jitsi Meet live class session for a room."""
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('live',      'Live Now'),
        ('ended',     'Ended'),
    )
    room         = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='live_sessions')
    title        = models.CharField(max_length=200)
    description  = models.TextField(blank=True)
    jitsi_room   = models.CharField(max_length=120, unique=True)   # slug used in Jitsi URL
    scheduled_at = models.DateTimeField()
    started_at   = models.DateTimeField(null=True, blank=True)
    ended_at     = models.DateTimeField(null=True, blank=True)
    status       = models.CharField(max_length=12, choices=STATUS_CHOICES, default='scheduled')
    created_by   = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.room.name} — {self.title}"

    def get_jitsi_url(self):
        from django.conf import settings as s
        domain = getattr(s, 'JITSI_DOMAIN', 'meet.jit.si')
        return f"https://{domain}/{self.jitsi_room}"
