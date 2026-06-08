# players/forms.py
from django import forms
from .models import PlayerProfile


class PlayerProfileForm(forms.ModelForm):
    class Meta:
        model = PlayerProfile
        fields = [
            # Personal
            "full_name", "age", "nationality", "region",

            # Physical
            "height_cm", "weight_kg", "preferred_foot",

            # Football
            "position", "current_club", "jersey_number",

            # Media
            "profile_picture", "highlight_video",

            # Bio
            "bio",
        ]
        widgets = {
            # Personal
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control", "min": 10}),
            "nationality": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.Select(attrs={"class": "form-control"}),  # Uses REGION_CHOICES from model.

            # Physical
            "height_cm": forms.NumberInput(attrs={"class": "form-control"}),
            "weight_kg": forms.NumberInput(attrs={"class": "form-control"}),
            "preferred_foot": forms.Select(attrs={"class": "form-control"}),  # Uses choices from model.

            # Football
            "position": forms.Select(attrs={"class": "form-control"}),  # Uses POSITION_CHOICES from model.
            "current_club": forms.TextInput(attrs={"class": "form-control"}),
            "jersey_number": forms.TextInput(attrs={"class": "form-control"}),

            # Media
            "profile_picture": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "highlight_video": forms.URLInput(attrs={"class": "form-control"}),

            # Bio
            "bio": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }
