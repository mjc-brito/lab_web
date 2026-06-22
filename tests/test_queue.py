"""
Testes da fila Redis (core.redis_queue).
Cobre: adicionar, remover, sem duplicados, ordem FIFO, get_first, clear.
"""
import pytest
import core.redis_queue as rq


# Nota: mock_redis em conftest.py é autouse=True,
# pelo que todos os testes usam Redis em memória automaticamente.

def test_fila_vazia_inicial():
    rq.clear_queue()
    assert rq.get_queue() == []


def test_adicionar_utilizador():
    rq.clear_queue()
    rq.add_to_queue("alice")
    assert rq.get_queue() == ["alice"]


def test_ordem_fifo():
    """Primeiro a entrar é o primeiro na fila."""
    rq.clear_queue()
    rq.add_to_queue("alice")
    rq.add_to_queue("bob")
    rq.add_to_queue("carol")
    assert rq.get_queue() == ["alice", "bob", "carol"]


def test_sem_duplicados():
    """O mesmo utilizador não pode estar duas vezes na fila."""
    rq.clear_queue()
    rq.add_to_queue("alice")
    rq.add_to_queue("alice")
    assert rq.get_queue() == ["alice"]


def test_remover_primeiro():
    rq.clear_queue()
    rq.add_to_queue("alice")
    rq.add_to_queue("bob")
    rq.remove_from_queue("alice")
    assert rq.get_queue() == ["bob"]


def test_remover_do_meio():
    rq.clear_queue()
    rq.add_to_queue("alice")
    rq.add_to_queue("bob")
    rq.add_to_queue("carol")
    rq.remove_from_queue("bob")
    assert rq.get_queue() == ["alice", "carol"]


def test_remover_nao_existente_nao_lanca_erro():
    """Remover utilizador que não existe não deve lançar excepção."""
    rq.clear_queue()
    rq.add_to_queue("alice")
    rq.remove_from_queue("ninguem")
    assert rq.get_queue() == ["alice"]


def test_get_first_retorna_primeiro():
    rq.clear_queue()
    rq.add_to_queue("alice")
    rq.add_to_queue("bob")
    assert rq.get_first() == "alice"


def test_get_first_fila_vazia_retorna_none():
    rq.clear_queue()
    assert rq.get_first() is None


def test_clear_queue():
    rq.clear_queue()
    rq.add_to_queue("alice")
    rq.add_to_queue("bob")
    rq.clear_queue()
    assert rq.get_queue() == []


def test_proximo_apos_remocao_do_primeiro():
    """Após o primeiro sair, o segundo passa a ser o primeiro."""
    rq.clear_queue()
    rq.add_to_queue("alice")
    rq.add_to_queue("bob")
    rq.remove_from_queue("alice")
    assert rq.get_first() == "bob"


def test_re_adicionar_apos_remocao_vai_para_o_fim():
    """Utilizador removido e re-adicionado vai para o fim da fila."""
    rq.clear_queue()
    rq.add_to_queue("alice")
    rq.add_to_queue("bob")
    rq.remove_from_queue("alice")
    rq.add_to_queue("alice")
    assert rq.get_queue() == ["bob", "alice"]