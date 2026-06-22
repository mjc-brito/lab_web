import json
import os
import sys
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .redis_queue import (
    get_queue, get_first, add_to_queue, remove_from_queue,
    mark_user_active,
    mark_entry_confirmed, is_entry_confirmed, clear_entry_confirmed,
)


class FilaConsumer(AsyncWebsocketConsumer):
    group_name = "queue"

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await sync_to_async(add_to_queue)(self.user.username)
        await self.accept()

        self._entry_timer = None
        self._awaiting_entry = False

        await self._send_position()
        await self._broadcast_queue()

    async def receive(self, text_data):
        data = json.loads(text_data or "{}")

        if data.get("action") == "refresh":
            await self._send_position()

        elif data.get("action") == "confirm_entry":
            if self._awaiting_entry:
                if self._entry_timer:
                    self._entry_timer.cancel()
                self._awaiting_entry = False

                # Marca confirmação ANTES de enviar entry_confirmed e de fechar
                # o wsQueue. Assim quando o FilaConsumer.disconnect() correr
                # (provocado pelo wsQueue.close() no frontend) a chave já
                # existe no Redis e o utilizador não é removido da fila.
                from .models import LabSettings
                duration = await sync_to_async(LabSettings.get_duration)()
                await sync_to_async(mark_entry_confirmed)(
                    self.user.username, duration
                )

                await self.send(text_data=json.dumps({"type": "entry_confirmed"}))

        elif data.get("action") == "leave":
            await sync_to_async(remove_from_queue)(self.user.username)
            await self._broadcast_queue()
            await self._send_position()

        elif data.get("action") == "hello":
            await sync_to_async(mark_user_active)(self.user.username)

    async def disconnect(self, close_code):
        await self._cancel_entry_timer()
        if self.user and self.user.is_authenticated:
            # Só remove da fila se o utilizador NÃO tiver confirmado entrada.
            # Se tiver confirmado, está a caminho (ou já dentro) do
            # ControlConsumer — não deve perder o lugar.
            if not await sync_to_async(is_entry_confirmed)(self.user.username):
                await sync_to_async(remove_from_queue)(self.user.username)
                await self._broadcast_queue()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def _broadcast_queue(self):
        fila = await sync_to_async(get_queue)()
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "queue_update", "fila": fila}
        )

    async def _send_position(self):
        fila = await sync_to_async(get_queue)()
        user = self.user.username
        pos = fila.index(user) if user in fila else None
        is_first = (fila[0] == user) if fila and user in fila else False
        await self.send(text_data=json.dumps({
            "posicao": pos,
            "is_first": is_first,
            "fila": fila,
        }))

    async def queue_update(self, event):
        fila = event["fila"]
        user = self.user.username
        pos = fila.index(user) if user in fila else None
        is_first = (fila[0] == user) if fila and user in fila else False
        await self.send(text_data=json.dumps({
            "posicao": pos,
            "is_first": is_first,
            "fila": fila,
        }))
        if is_first and not self._awaiting_entry:
            await self._start_entry_countdown()

    # --- countdown de validação ---

    async def _start_entry_countdown(self):
        from .models import LabSettings
        timeout = await sync_to_async(LabSettings.get_entry_timeout)()
        self._awaiting_entry = True

        await self.send(text_data=json.dumps({
            "type": "your_turn",
            "timeout_seconds": timeout,
        }))

        self._entry_timer = asyncio.create_task(
            self._entry_timeout_task(timeout)
        )

    async def _entry_timeout_task(self, timeout: int):
        await asyncio.sleep(timeout)
        if self._awaiting_entry:
            self._awaiting_entry = False
            await self.send(text_data=json.dumps({"type": "entry_expired"}))
            await sync_to_async(remove_from_queue)(self.user.username)
            await sync_to_async(add_to_queue)(self.user.username)
            await self._broadcast_queue()
            await self._send_position()

    async def _cancel_entry_timer(self):
        if self._entry_timer and not self._entry_timer.done():
            self._entry_timer.cancel()
        self._awaiting_entry = False


class ControlConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        first = await sync_to_async(get_first)()
        if self.user.username != first:
            await self.close()
            return

        await self.accept()

        self._sandbox = None
        self._sandbox_lock = asyncio.Lock()
        self._session_expired = False

        from .models import LabSettings
        duration = await sync_to_async(LabSettings.get_duration)()

        await self.send(text_data=json.dumps({
            "type": "session_info",
            "duration_seconds": duration,
        }))

        await self._start_sandbox()
        self._timer_task = asyncio.create_task(self._session_timer(duration))

    async def disconnect(self, close_code):
        if hasattr(self, "_timer_task"):
            self._timer_task.cancel()
        await self._stop_sandbox()
        if hasattr(self, "user") and self.user.is_authenticated:
            await sync_to_async(clear_entry_confirmed)(self.user.username)
            await sync_to_async(remove_from_queue)(self.user.username)
            if getattr(self, "_session_expired", False):
                # timer expirou — recoloca no fim para poder tentar de novo
                await sync_to_async(add_to_queue)(self.user.username)
            # fechar browser / mudar página — sai da fila completamente, não recoloca
            fila = await sync_to_async(get_queue)()
            await self.channel_layer.group_send(
                "queue",
                {"type": "queue_update", "fila": fila}
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "run_code":
            await self._sandbox_send({"action": "exec", "code": data.get("code", "")})
        elif action == "get_var":
            await self._sandbox_send({"action": "get_var", "name": data.get("name", "")})
        elif action == "save_vars":
            await self._sandbox_send({"action": "save_vars", "names": data.get("names", [])})
        elif action == "save_all":
            await self._sandbox_send({"action": "save_all"})
        elif action == "clear_vars":
            await self._sandbox_send({"action": "clear"})

    # --- Sandbox lifecycle ---

    async def _start_sandbox(self):
        """Lança o processo filho sandbox_worker.py."""
        worker_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "sandbox_worker.py"
        )
        self._sandbox = await asyncio.create_subprocess_exec(
            sys.executable, worker_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10 * 1024 * 1024,
        )
        await asyncio.wait_for(
            self._sandbox.stdout.readline(), timeout=5.0
        )
        self._read_task = asyncio.create_task(self._read_sandbox_output())

    async def _stop_sandbox(self):
        """Termina o processo filho de forma limpa."""
        if self._sandbox and self._sandbox.returncode is None:
            try:
                self._sandbox.stdin.close()
                await asyncio.wait_for(self._sandbox.wait(), timeout=3.0)
            except Exception:
                self._sandbox.kill()
        if hasattr(self, "_read_task"):
            self._read_task.cancel()

    async def _sandbox_send(self, cmd: dict):
        """Envia um comando JSON ao processo filho."""
        if not self._sandbox or self._sandbox.returncode is not None:
            await self.send(text_data=json.dumps({
                "type": "stderr",
                "message": "Sandbox não está disponível.\n"
            }))
            return
        async with self._sandbox_lock:
            line = json.dumps(cmd) + "\n"
            self._sandbox.stdin.write(line.encode())
            await self._sandbox.stdin.drain()

    async def _read_sandbox_output(self):
        """Lê continuamente o stdout do processo filho."""
        try:
            while True:
                line = await self._sandbox.stdout.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.decode())
                    await self._dispatch_sandbox_msg(msg)
                except json.JSONDecodeError:
                    pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.send(text_data=json.dumps({
                "type": "stderr",
                "message": f"Erro interno da sandbox: {e}\n"
            }))

    async def _dispatch_sandbox_msg(self, msg: dict):
        """Transforma a resposta do worker numa mensagem WebSocket para o cliente."""
        t = msg.get("type")

        if t == "exec_result":
            if msg.get("stdout"):
                await self.send(text_data=json.dumps({
                    "type": "stdout",
                    "message": msg["stdout"]
                }))
            if msg.get("error"):
                await self.send(text_data=json.dumps({
                    "type": "stderr",
                    "message": msg["error"]
                }))
            elif msg.get("stderr"):
                await self.send(text_data=json.dumps({
                    "type": "stderr",
                    "message": msg["stderr"]
                }))
            if "vars" in msg:
                await self.send(text_data=json.dumps({
                    "type": "vars_update",
                    "vars": msg["vars"]
                }))

        elif t == "var_result":
            if msg.get("error"):
                await self.send(text_data=json.dumps({
                    "type": "stderr",
                    "message": msg["error"] + "\n"
                }))
            else:
                await self.send(text_data=json.dumps({
                    "type": "stdout",
                    "message": f"{msg['name']} = {msg['value']}\n"
                }))

        elif t == "save_result":
            await self.send(text_data=json.dumps({
                "type": "download",
                "filename": msg["filename"],
                "data_b64": msg["data_b64"]
            }))

        elif t == "cleared":
            await self.send(text_data=json.dumps({
                "type": "vars_update",
                "vars": {}
            }))

        elif t == "error":
            await self.send(text_data=json.dumps({
                "type": "stderr",
                "message": msg.get("error", "Erro desconhecido") + "\n"
            }))

    # --- Timer de sessão ---

    async def _session_timer(self, duration: int):
        await asyncio.sleep(duration)
        self._session_expired = True  # marca ANTES de fechar
        await self.send(text_data=json.dumps({
            "type": "stderr",
            "message": "\n⏰ Tempo de sessão esgotado.\n"
        }))
        await self.send(text_data=json.dumps({"type": "session_expired"}))
        await self.close()
        # disconnect() corre a seguir e trata da fila