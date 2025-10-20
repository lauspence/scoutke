from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ScoutProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "profile_picture", "bio"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
        }
