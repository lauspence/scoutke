from django import forms
from .models import (
    ClubShortlist,
    Comment,
    ContactRequest,
    ContentReport,
    Opportunity,
    OpportunityApplication,
    Post,
    ScoutReport,
    TalentSpot,
    TalentSpotClaim,
)

class PostForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("category") == Post.CATEGORY_TALENT:
            if not cleaned_data.get("prospect_name"):
                self.add_error("prospect_name", "Add a name, nickname, or shirt number for talent spots.")
            if not cleaned_data.get("location"):
                self.add_error("location", "Add the location where the talent was spotted.")
        return cleaned_data

    class Meta:
        model = Post
        fields = ["category", "prospect_name", "location", "content", "image", "video"]
        widgets = {
            "category": forms.Select(attrs={
                "class": "form-select form-select-sm",
            }),
            "prospect_name": forms.TextInput(attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Talent name, team, or shirt number if known",
            }),
            "location": forms.TextInput(attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Where did you see it? e.g. Kasarani, Kisumu, school tournament",
            }),
            "content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Share a highlight, match moment, scouting note, or football opinion..."
            }),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.TextInput(attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Add a comment..."
            })
        }


class TalentSpotForm(forms.ModelForm):
    class Meta:
        model = TalentSpot
        fields = [
            "prospect_name",
            "position",
            "age_estimate",
            "team_or_school",
            "location",
            "event_name",
            "notes",
            "evidence_image",
            "evidence_video",
        ]
        widgets = {
            "prospect_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Player name, nickname, or shirt number",
            }),
            "position": forms.Select(attrs={"class": "form-select"}),
            "age_estimate": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Estimated age",
                "min": 8,
            }),
            "team_or_school": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Team, school, or academy if known",
            }),
            "location": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Where was the talent seen?",
            }),
            "event_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Tournament, match, trial, or league",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "What stood out? Pace, passing, finishing, bravery, movement, attitude...",
            }),
            "evidence_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "evidence_video": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class ScoutReportForm(forms.ModelForm):
    class Meta:
        model = ScoutReport
        fields = [
            "technical",
            "physical",
            "tactical",
            "mentality",
            "potential",
            "summary",
            "recommendation",
        ]
        widgets = {
            "technical": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 10}),
            "physical": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 10}),
            "tactical": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 10}),
            "mentality": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 10}),
            "potential": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 10}),
            "summary": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "What did you see? Strengths, weaknesses, match context, and next step.",
            }),
            "recommendation": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        for field in ("technical", "physical", "tactical", "mentality", "potential"):
            value = cleaned_data.get(field)
            if value is not None and not 1 <= value <= 10:
                self.add_error(field, "Use a score from 1 to 10.")
        return cleaned_data


class ClubShortlistForm(forms.ModelForm):
    class Meta:
        model = ClubShortlist
        fields = ["status", "private_notes"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "private_notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Private recruitment notes for your club.",
            }),
        }


class TalentSpotClaimForm(forms.ModelForm):
    class Meta:
        model = TalentSpotClaim
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Explain why this spot is yours. Mention team, match, shirt number, or any proof scouts can check.",
            }),
        }


class ContactRequestForm(forms.ModelForm):
    class Meta:
        model = ContactRequest
        fields = ["message", "proposed_date"]
        widgets = {
            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Introduce your club and explain the opportunity or trial request.",
            }),
            "proposed_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
        }


class ContentReportForm(forms.ModelForm):
    class Meta:
        model = ContentReport
        fields = ["reason", "details"]
        widgets = {
            "reason": forms.Select(attrs={"class": "form-select"}),
            "details": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Add context for moderators. Do not include sensitive personal information.",
            }),
        }


class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = [
            "title",
            "opportunity_type",
            "location",
            "region",
            "deadline",
            "event_date",
            "age_min",
            "age_max",
            "positions",
            "description",
            "requirements",
            "contact_instructions",
            "is_active",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. U17 Nairobi trial day"}),
            "opportunity_type": forms.Select(attrs={"class": "form-select"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "Venue or town"}),
            "region": forms.TextInput(attrs={"class": "form-control", "placeholder": "County or region"}),
            "deadline": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "event_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "age_min": forms.NumberInput(attrs={"class": "form-control", "min": 8, "max": 40}),
            "age_max": forms.NumberInput(attrs={"class": "form-control", "min": 8, "max": 40}),
            "positions": forms.TextInput(attrs={"class": "form-control", "placeholder": "Any, GK, CB, winger, striker..."}),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Explain the opportunity, who should apply, and what will happen next.",
            }),
            "requirements": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Documents, kit, guardian consent, school level, or eligibility.",
            }),
            "contact_instructions": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional extra contact instructions for shortlisted players.",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        age_min = cleaned_data.get("age_min")
        age_max = cleaned_data.get("age_max")
        if age_min and age_max and age_min > age_max:
            self.add_error("age_max", "Maximum age must be higher than minimum age.")
        return cleaned_data


class OpportunityApplicationForm(forms.ModelForm):
    class Meta:
        model = OpportunityApplication
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Introduce yourself, mention your position, region, age, recent team, and why this opportunity fits you.",
            }),
        }
