from django.db import models
from courses.models import Submission


class Grade(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='grade')
    score      = models.FloatField()
    feedback   = models.TextField(blank=True)
    graded_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Grade {self.score} — {self.submission}"
