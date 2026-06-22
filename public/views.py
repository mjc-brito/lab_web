from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import CustomUserrCreationForm, LoginForm
from django.contrib import messages

# Create your views here.
from datetime import datetime

def home(request):
    return render(request, 'public/home.html', {'year': datetime.now().year})

def register_view(request):
    if request.method == "POST":
        form = CustomUserrCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            messages.success(request, "Registro enviado com sucesso. Aguarde aprovação.")
            return redirect('home')
        else:
            messages.error(request, "Corrija os erros abaixo.")
    else:
        form = CustomUserrCreationForm()
    return render(request, 'public/register.html', {'form': form})
    
def custom_login_view(request):
    from django.contrib.auth.views import LoginView
    return LoginView.as_view(
        template_name='public/login.html',
        authentication_form=LoginForm
    )(request)


def about(request):
    from core.models import LabSettings
    obj = LabSettings.objects.first()
    return render(request, 'public/about.html', {
        'session_duration': obj.session_duration_minutes if obj else 20,
        'entry_timeout': obj.entry_timeout_minutes if obj else 1,
    })