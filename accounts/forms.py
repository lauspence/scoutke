from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, UserSettings, VerificationRequest


class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'role','profile_picture', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        }


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )

    class Meta:
        model = User
        fields = ['username', 'password']

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'bio', 'profile_picture']  # role stays fixed usually
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell people about your football journey.',
            }),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'bio', 'profile_picture']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell scouts, clubs, and fans a little about your football story.',
            }),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = [
            "layout_density",
            "notify_in_app",
            "notify_email",
            "notify_contact",
            "notify_reports",
            "notify_social",
            "profile_visibility",
            "show_email",
            "allow_contact",
            "show_stats",
            "default_feed",
            "autoplay_video",
            "show_media",
            "compact_cards",
            "player_available",
            "player_trials",
            "scout_regional_alerts",
            "scout_shortlist_alerts",
            "club_trial_ready",
            "club_contact_alerts",
        ]
        widgets = {
            "layout_density": forms.Select(attrs={"class": "form-select settings-control"}),
            "profile_visibility": forms.Select(attrs={"class": "form-select settings-control"}),
            "default_feed": forms.Select(attrs={"class": "form-select settings-control"}),
        }


class VerificationRequestForm(forms.ModelForm):
    class Meta:
        model = VerificationRequest
        fields = ["organization_name", "role_context", "evidence"]
        widgets = {
            "organization_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Club, academy, agency, or scouting network",
            }),
            "role_context": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Your official role and region",
            }),
            "evidence": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Add links, references, registration details, or public proof staff can review.",
            }),
        }


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'profile_picture']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'profile_picture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

