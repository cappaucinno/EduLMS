from django import forms
from courses.models import Room, Lesson, Assignment, Quiz, Question, Material, Announcement
from assessments.models import Grade


class RoomForm(forms.ModelForm):
    class Meta:
        model  = Room
        fields = ['name','subject','grade_level','description','thumbnail']
        widgets = {
            'name':        forms.TextInput(attrs={'class':'form-control'}),
            'subject':     forms.Select(attrs={'class':'form-control'}),
            'grade_level': forms.Select(attrs={'class':'form-control'}),
            'description': forms.Textarea(attrs={'class':'form-control','rows':3}),
            'thumbnail':   forms.FileInput(attrs={'class':'form-control'}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model  = Lesson
        fields = ['title','content','video_url','order']
        widgets = {
            'title':     forms.TextInput(attrs={'class':'form-control'}),
            'content':   forms.Textarea(attrs={'class':'form-control','rows':5}),
            'video_url': forms.URLInput(attrs={'class':'form-control'}),
            'order':     forms.NumberInput(attrs={'class':'form-control'}),
        }


class MaterialForm(forms.ModelForm):
    class Meta:
        model  = Material
        fields = ['title','description','file','link','order']
        widgets = {
            'title':       forms.TextInput(attrs={'class':'form-control'}),
            'description': forms.Textarea(attrs={'class':'form-control','rows':2}),
            'file':        forms.FileInput(attrs={'class':'form-control'}),
            'link':        forms.URLInput(attrs={'class':'form-control'}),
            'order':       forms.NumberInput(attrs={'class':'form-control'}),
        }


class AssignmentForm(forms.ModelForm):
    class Meta:
        model  = Assignment
        fields = ['title','description','due_date','max_score']
        widgets = {
            'title':       forms.TextInput(attrs={'class':'form-control'}),
            'description': forms.Textarea(attrs={'class':'form-control','rows':4}),
            'due_date':    forms.DateTimeInput(attrs={'class':'form-control','type':'datetime-local'}),
            'max_score':   forms.NumberInput(attrs={'class':'form-control'}),
        }


class QuizForm(forms.ModelForm):
    class Meta:
        model  = Quiz
        fields = ['title']
        widgets = {'title': forms.TextInput(attrs={'class':'form-control'})}


class QuestionForm(forms.ModelForm):
    class Meta:
        model  = Question
        fields = ['text','option_a','option_b','option_c','option_d','correct_answer']
        widgets = {
            'text':           forms.Textarea(attrs={'class':'form-control','rows':2}),
            'option_a':       forms.TextInput(attrs={'class':'form-control'}),
            'option_b':       forms.TextInput(attrs={'class':'form-control'}),
            'option_c':       forms.TextInput(attrs={'class':'form-control'}),
            'option_d':       forms.TextInput(attrs={'class':'form-control'}),
            'correct_answer': forms.Select(attrs={'class':'form-control'}),
        }


class GradeForm(forms.ModelForm):
    class Meta:
        model  = Grade
        fields = ['score','feedback']
        widgets = {
            'score':    forms.NumberInput(attrs={'class':'form-control'}),
            'feedback': forms.Textarea(attrs={'class':'form-control','rows':3}),
        }


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model  = Announcement
        fields = ['title','content','ann_type','audience','attachment','link','pinned','send_email','scheduled_at']
        widgets = {
            'title':        forms.TextInput(attrs={'class':'form-control','placeholder':'Announcement title'}),
            'content':      forms.Textarea(attrs={'class':'form-control','rows':6}),
            'ann_type':     forms.Select(attrs={'class':'form-control'}),
            'audience':     forms.Select(attrs={'class':'form-control'}),
            'attachment':   forms.FileInput(attrs={'class':'form-control'}),
            'link':         forms.URLInput(attrs={'class':'form-control','placeholder':'Optional external link'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class':'form-control','type':'datetime-local'}),
            'pinned':       forms.CheckboxInput(attrs={'class':'form-check-input'}),
            'send_email':   forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
