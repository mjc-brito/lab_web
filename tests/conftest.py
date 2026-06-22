import pytest
import fakeredis
import core.redis_queue as redis_queue
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Substitui o Redis real por um Redis em memória em todos os testes."""
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_queue, "r", fake)
    yield


@pytest.fixture
def student(db):
    """Utilizador aluno básico."""
    return User.objects.create_user(
        username="aluno", password="senha123", student_number="12345"
    )


@pytest.fixture
def student2(db):
    """Segundo utilizador aluno para testes multi-utilizador."""
    return User.objects.create_user(
        username="aluno2", password="senha123", student_number="67890"
    )


@pytest.fixture
def professor(db):
    """Utilizador professor (staff)."""
    return User.objects.create_user(
        username="prof", password="senha123",
        student_number="00000", is_staff=True
    )