from django import forms
from django.contrib.auth import get_user_model

from .models import Post, Comment


User = get_user_model()


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        fields = (
            'title',
            'text',
            'pub_date',
            'location',
            'category',
            'image',
        )
        widgets = {
            'pub_date': forms.DateInput(attrs={'type': 'date'}),
        }


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = (
            'text',
        )


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = {
            'first_name',
            'last_name',
            'email'
        }
        widgets = {
            'email': forms.EmailInput(),
        }
