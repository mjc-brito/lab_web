from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .redis_queue import add_to_queue


@login_required
def queue_control_view(request):
    # Adiciona o usuário à fila caso ainda não esteja
    add_to_queue(request.user.username)
    return render(request, "core/queue_control.html")
