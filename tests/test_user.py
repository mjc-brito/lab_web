"""
Testes do modelo de utilizador personalizado (public.User).
Cobre: criação, campo student_number, permissões de staff.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:

    def test_criar_utilizador_com_student_number(self):
        """Utilizador criado correctamente com número de aluno."""
        u = User.objects.create_user(
            username="mat", password="x", student_number="12345"
        )
        assert u.student_number == "12345"
        assert u.is_active is True
        assert u.is_staff is False

    def test_student_number_obrigatorio_por_convencao(self):
        """O campo student_number existe no modelo."""
        u = User.objects.create_user(username="a", password="x", student_number="99")
        assert hasattr(u, "student_number")

    def test_professor_e_staff(self, professor):
        """Utilizador professor tem is_staff=True."""
        assert professor.is_staff is True

    def test_dois_utilizadores_numeros_diferentes(self, student, student2):
        """Dois alunos podem ter números de aluno diferentes."""
        assert student.student_number != student2.student_number

    def test_autenticacao_valida(self, client, student):
        """Login com credenciais correctas retorna sessão autenticada."""
        ok = client.login(username="aluno", password="senha123")
        assert ok is True

    def test_autenticacao_invalida(self, client, student):
        """Login com password errada falha."""
        ok = client.login(username="aluno", password="errada")
        assert ok is False