"""
Teste de integração ponta-a-ponta (fluxo HTTP completo).
Cobre: registo → login → acesso à fila → página de controlo acessível.
Não usa WebSockets aqui — esse fluxo está em test_ws_queue.py.
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_fluxo_completo_login_e_acesso_fila(client):
    """
    Utilizador faz login e consegue aceder à página da fila.
    Verifica que o fluxo base funciona de ponta a ponta via HTTP.
    """
    from core.redis_queue import clear_queue
    clear_queue()

    # 1. Criar utilizador
    User.objects.create_user(
        username="e2e_aluno", password="senha123", student_number="11111"
    )

    # 2. Login
    r = client.post(reverse("login"), {
        "username": "e2e_aluno",
        "password": "senha123",
    })
    assert r.status_code == 302  # redireciona após login com sucesso

    # 3. Acesso à fila — deve ser permitido
    r = client.get(reverse("queue_control"))
    assert r.status_code == 200


@pytest.mark.django_db
def test_acesso_sem_login_redireciona_para_login(client):
    """
    Utilizador não autenticado a tentar aceder à fila
    é redireccionado para a página de login.
    """
    r = client.get(reverse("queue_control"))
    assert r.status_code == 302
    assert "login" in r.url


@pytest.mark.django_db
def test_registo_cria_utilizador(client):
    """POST em /register/ cria utilizador na base de dados."""
    r = client.post(reverse("register"), {
        "username": "novo_aluno",
        "password1": "TestPass123!",
        "password2": "TestPass123!",
        "student_number": "22222",
    })
    # redireciona ou mostra sucesso
    assert r.status_code in (200, 302)
    assert User.objects.filter(username="novo_aluno").exists()


@pytest.mark.django_db
def test_paginas_publicas_retornam_200(client):
    """Todas as páginas públicas devem ser acessíveis sem autenticação."""
    paginas = ["home", "about", "login", "register"]
    for nome in paginas:
        r = client.get(reverse(nome))
        assert r.status_code == 200, f"Página '{nome}' devolveu {r.status_code}"