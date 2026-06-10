import os
import redis

# DB 2 só para a fila
QUEUE_REDIS_URL = os.environ.get('QUEUE_REDIS_URL', 'redis://127.0.0.1:6379/2')
r = redis.Redis.from_url(QUEUE_REDIS_URL, decode_responses=True)
QUEUE_KEY = 'fila:users'


def get_queue():
    return r.lrange(QUEUE_KEY, 0, -1)


def get_first():
    return r.lindex(QUEUE_KEY, 0)


def add_to_queue(username: str):
    if r.lpos(QUEUE_KEY, username) is None:
        r.rpush(QUEUE_KEY, username)


def remove_from_queue(username: str):
    r.lrem(QUEUE_KEY, 0, username)


def clear_queue():
    r.delete(QUEUE_KEY)


# ---------------------------------------------------------------------------
# Heartbeat do ControlConsumer (renovado a cada 5 s pelo frontend)
# ---------------------------------------------------------------------------

def mark_user_active(username: str, ttl: int = 10):
    """Marca o utilizador como activo na página de controlo (heartbeat)."""
    key = f"active:{username}"
    r.set(key, 1, ex=ttl)


def is_user_active(username: str) -> bool:
    """Verifica se o utilizador está activo na página de controlo."""
    key = f"active:{username}"
    return r.exists(key) == 1


# ---------------------------------------------------------------------------
# Confirmação de entrada — marcada no confirm_entry, dura toda a sessão.
# Usada pelo FilaConsumer.disconnect() para não remover da fila quem já
# confirmou entrada e está a aguardar (ou já está em) sessão de controlo.
# ---------------------------------------------------------------------------

def mark_entry_confirmed(username: str, session_duration: int):
    """
    Marca que o utilizador confirmou a entrada.
    TTL igual à duração da sessão mais uma margem de 60 s para absorver
    o tempo entre o confirm_entry e o ControlConsumer limpar a marcação.
    """
    key = f"confirmed:{username}"
    r.set(key, 1, ex=session_duration + 60)


def is_entry_confirmed(username: str) -> bool:
    """Verifica se o utilizador já confirmou entrada."""
    key = f"confirmed:{username}"
    return r.exists(key) == 1


def clear_entry_confirmed(username: str):
    """Remove a marcação de confirmação. Chamado quando a sessão termina."""
    r.delete(f"confirmed:{username}")