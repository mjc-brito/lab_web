"""
Testes das views HTTP (páginas públicas e protegidas).
Cobre: home, about, login, register, fila (acesso autenticado),
       redireccionamento de não autenticados.
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.redis_queue import clear_queue, add_to_queue

User = get_user_model()


@pytest.mark.django_db
class TestPaginasPublicas:

    def test_home_acessivel_sem_login(self, client):
        r = client.get(reverse("home"))
        assert r.status_code == 200

    def test_about_acessivel_sem_login(self, client):
        r = client.get(reverse("about"))
        assert r.status_code == 200

    def test_login_page_acessivel(self, client):
        r = client.get(reverse("login"))
        assert r.status_code == 200

    def test_register_page_acessivel(self, client):
        r = client.get(reverse("register"))
        assert r.status_code == 200

    def test_login_correcto_redireciona(self, client, student):
        r = client.post(reverse("login"), {
            "username": "aluno", "password": "senha123"
        })
        # Django redireciona após login com sucesso
        assert r.status_code == 302

    def test_login_incorrecto_fica_na_pagina(self, client, student):
        r = client.post(reverse("login"), {
            "username": "aluno", "password": "errada"
        })
        assert r.status_code == 200  # permanece na página de login


@pytest.mark.django_db
class TestPaginasProtegidas:

    def test_fila_requer_autenticacao(self, client):
        """Utilizador não autenticado é redireccionado para login."""
        r = client.get(reverse("queue_control"))
        assert r.status_code == 302
        assert "/login/" in r.url

    def test_fila_acessivel_autenticado(self, client, student):
        clear_queue()
        client.login(username="aluno", password="senha123")
        r = client.get(reverse("queue_control"))
        assert r.status_code == 200


@pytest.mark.django_db
class TestLabSettings:

    def test_lab_settings_criados_automaticamente(self):
        """LabSettings cria registo padrão se não existir."""
        from core.models import LabSettings
        duration = LabSettings.get_duration()
        assert duration == 20 * 60  # 20 minutos em segundos

    def test_lab_settings_entry_timeout(self):
        """Timeout de entrada padrão é 1 minuto."""
        from core.models import LabSettings
        timeout = LabSettings.get_entry_timeout()
        assert timeout == 1 * 60  # 1 minuto em segundos

    def test_lab_settings_configuravel(self, db):
        """Alteração no admin reflecte nos classmethods."""
        from core.models import LabSettings
        obj, _ = LabSettings.objects.get_or_create(pk=1)
        obj.session_duration_minutes = 10
        obj.entry_timeout_minutes = 2
        obj.save()
        assert LabSettings.get_duration() == 600
        assert LabSettings.get_entry_timeout() == 120