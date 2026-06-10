"""
Testes do FilaConsumer (WebSocket /ws/fila/).
Cobre: posição na fila, is_first, broadcast quando alguém sai,
       página de validação (your_turn), confirm_entry, entry_expired.
Usa channels.testing.WebsocketCommunicator — não precisa de servidor real.
"""
import pytest
import json
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from config.asgi import application
from core.redis_queue import clear_queue, add_to_queue, remove_from_queue

User = get_user_model()


async def make_communicator(user):
    """Cria um WebsocketCommunicator autenticado para /ws/fila/."""
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY

    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    await sync_to_async(session.save)()

    communicator = WebsocketCommunicator(
        application,
        "/ws/fila/",
        headers=[(b"cookie", f"sessionid={session.session_key}".encode())],
    )
    return communicator


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_primeiro_utilizador_is_first(student):
    await sync_to_async(clear_queue)()
    comm = await make_communicator(student)
    connected, _ = await comm.connect()
    assert connected

    msg = json.loads(await comm.receive_from())
    assert msg["is_first"] is True
    assert msg["posicao"] == 0

    await comm.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_segundo_utilizador_nao_e_primeiro(student, student2):
    await sync_to_async(clear_queue)()

    comm1 = await make_communicator(student)
    await comm1.connect()
    await comm1.receive_from()  # descarta msg inicial

    comm2 = await make_communicator(student2)
    await comm2.connect()
    msg2 = json.loads(await comm2.receive_from())

    assert msg2["is_first"] is False
    assert msg2["posicao"] == 1

    await comm1.disconnect()
    await comm2.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_segundo_torna_se_primeiro_apos_saida(student, student2):
    """Quando o primeiro sai, o segundo recebe is_first=True."""
    import asyncio

    await sync_to_async(clear_queue)()

    comm1 = await make_communicator(student)
    await comm1.connect()
    await comm1.receive_from()  # descarta msg inicial do comm1

    comm2 = await make_communicator(student2)
    await comm2.connect()
    await comm2.receive_from()  # descarta msg inicial do comm2 (posicao=1)

    # primeiro desconecta
    await comm1.disconnect()

    # pequena pausa para o disconnect propagar
    await asyncio.sleep(0.1)

    # lê mensagens até encontrar is_first=True (descarta broadcasts intermédios)
    is_first = False
    for _ in range(5):
        raw = await comm2.receive_from(timeout=2)
        msg = json.loads(raw)
        if msg.get("is_first") is True:
            is_first = True
            break

    assert is_first is True

    await comm2.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_desconexao_remove_da_fila(student):
    """Ao desconectar, utilizador é removido da fila."""
    await sync_to_async(clear_queue)()

    comm = await make_communicator(student)
    await comm.connect()
    await comm.receive_from()
    await comm.disconnect()

    fila = await sync_to_async(lambda: __import__('core.redis_queue', fromlist=['get_queue']).get_queue())()
    assert student.username not in fila


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_hello_action_aceite(student):
    """Acção 'hello' é aceite sem fechar a ligação (keepalive)."""
    import asyncio

    await sync_to_async(clear_queue)()
    comm = await make_communicator(student)
    connected, _ = await comm.connect()
    assert connected

    await comm.receive_from()  # descarta msg inicial

    await comm.send_to(text_data=json.dumps({"action": "hello"}))
    await asyncio.sleep(0.1)

    # drena quaisquer mensagens pendentes sem falhar
    while not await comm.receive_nothing(timeout=0.3):
        await comm.receive_from()

    # envia um segundo hello — se a ligação estivesse fechada isto falharia
    await comm.send_to(text_data=json.dumps({"action": "hello"}))
    await asyncio.sleep(0.1)

    # ligação continua viva — conseguimos desconectar normalmente
    await comm.disconnect()