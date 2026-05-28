from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User, GRADE_CHOICES


class RegisterForm(forms.ModelForm):
    """
    No password fields — system assigns a default password on approval.
    Students receive their default password by email when a teacher approves them.
    Teachers receive theirs when the admin approves them.
    """
    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'grade_level']
        widgets = {
            'username':    forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
            }),
            'first_name':  forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name',
            }),
            'last_name':   forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name',
            }),
            'email':       forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address (required)',
            }),
            'role':        forms.Select(attrs={'class': 'form-control'}),
            'grade_level': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required      = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required  = True

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError("Email address is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        if role == 'student' and not cleaned.get('grade_level'):
            raise forms.ValidationError("Students must select their grade level.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # Set an unusable password — will be replaced with generated password on approval
        user.set_unusable_password()
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your registered email address',
        }),
        label='Email Address'
    )


class ResetPasswordForm(forms.Form):
    password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password (min 8 chars)',
        })
    )
    password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        })
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        return cleaned


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'profile_image']
        widgets = {
            'first_name':    forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':     forms.TextInput(attrs={'class': 'form-control'}),
            'email':         forms.EmailInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class TeacherProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'profile_image']
        widgets = {
            'first_name':    forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':     forms.TextInput(attrs={'class': 'form-control'}),
            'email':         forms.EmailInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Current password',
        })
    )
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New password (min 8 chars)',
        })
    )
    confirm_password = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        })
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("New passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        return cleaned


class GoogleSignupForm(forms.Form):
    """After Google OAuth — user picks their role and grade level."""
    role = forms.ChoiceField(
        choices=[('student', 'Student'), ('teacher', 'Teacher')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    grade_level = forms.ChoiceField(
        choices=[('', '— Select grade level (students only) —'),
                 ('7','Grade 7'),('8','Grade 8'),('9','Grade 9'),
                 ('10','Grade 10'),('11','Grade 11'),('12','Grade 12')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('role') == 'student' and not cleaned.get('grade_level'):
            raise forms.ValidationError("Students must select their grade level.")
        return cleaned
