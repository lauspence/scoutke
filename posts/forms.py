from django import forms
from .models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["content", "image", "video"]
        widgets = {
            "content": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Share your latest highlight..."
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
