from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class CustomUserrCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'student_number', 'password1', 'password2']
class LoginForm(AuthenticationForm):
    pass