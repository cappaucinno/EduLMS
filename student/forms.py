from django import forms
from courses.models import Submission

class SubmissionForm(forms.ModelForm):
    class Meta:
        model  = Submission
        fields = ['file', 'notes']
        widgets = {
            'file':  forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                           'placeholder': 'Optional notes for your teacher...'}),
        }
