"""
core/hardware.py

Abstracção da comunicação com o Arduino Due via USB/serial.

Quando USE_REAL_HARDWARE=1 (variável de ambiente), as funções hw_apply_input
e hw_read_output comunicam com o Arduino através de pyserial.
Caso contrário, é usado um modelo de primeira ordem simulado em software,
útil para desenvolvimento e testes sem hardware ligado.

Protocolo serial (9600 baud, terminador \n):
    Leitura  : enviar "R\n"         → receber "<float>\n"  (valor 0.0-1.0)
    Actuação : enviar "W <float>\n" → receber "OK\n"
    Saúde    : enviar "?\n"         → receber "READY\n"
"""

import os
import threading
import time

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

SERIAL_PORT    = os.environ.get("ARDUINO_PORT", "/dev/ttyACM0")
SERIAL_BAUD    = int(os.environ.get("ARDUINO_BAUD", "9600"))
SERIAL_TIMEOUT = float(os.environ.get("ARDUINO_TIMEOUT", "1.0"))
USE_REAL_HARDWARE = os.environ.get("USE_REAL_HARDWARE", "0") == "1"

# ---------------------------------------------------------------------------
# Gestão da ligação serial (singleton por processo)
# ---------------------------------------------------------------------------

_serial_lock = threading.Lock()
_serial_conn = None   # instância serial.Serial


def _get_connection():
    """
    Devolve a ligação serial, abrindo-a se necessário.
    Deve ser chamada com _serial_lock já adquirido pelo chamador.
    """
    global _serial_conn
    if _serial_conn is None or not _serial_conn.is_open:
        import serial  # importação tardia -- não falha quando USE_REAL_HARDWARE=0
        _serial_conn = serial.Serial(
            port=SERIAL_PORT,
            baudrate=SERIAL_BAUD,
            timeout=SERIAL_TIMEOUT,
        )
        # O Arduino Due faz reset ao abrir a porta serial; aguarda arranque.
        time.sleep(2.0)
        _serial_conn.reset_input_buffer()
        _serial_conn.reset_output_buffer()
    return _serial_conn


def _send_command(command: str) -> str:
    """
    Envia um comando ao Arduino e aguarda resposta numa única linha.
    Adquire o lock uma única vez para toda a operação (escrita + leitura),
    evitando deadlock com _get_connection().
    Lança serial.SerialException ou IOError em caso de falha.
    """
    with _serial_lock:
        conn = _get_connection()
        conn.write((command + "\n").encode("utf-8"))
        conn.flush()
        raw = conn.readline()

    if not raw:
        raise IOError(f"Sem resposta do Arduino ao comando '{command}'.")

    return raw.decode("utf-8", errors="replace").strip()


def close_connection():
    """Fecha a ligação serial, se estiver aberta."""
    global _serial_conn
    with _serial_lock:
        if _serial_conn is not None and _serial_conn.is_open:
            _serial_conn.close()
        _serial_conn = None


def check_hardware() -> bool:
    """
    Verifica se o Arduino está a responder.
    Devolve True se receber 'READY', False caso contrário.
    """
    if not USE_REAL_HARDWARE:
        return False
    try:
        response = _send_command("?")
        return response == "READY"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def hw_apply_input(u: float) -> None:
    """
    Envia um valor de actuação ao Arduino Due (DAC1).

    Parâmetros
    ----------
    u : float
        Valor normalizado no intervalo [0.0, 1.0], onde:
            0.0 -> tensão mínima do DAC1 (~0.60 V -> ~0 V após amplificador)
            1.0 -> tensão máxima do DAC1 (~3.05 V -> ~5 V após amplificador)

    Raises
    ------
    RuntimeError
        Se USE_REAL_HARDWARE=1 e a comunicação falhar.
    ValueError
        Se u estiver fora do intervalo [0.0, 1.0].
    """
    u = float(u)
    if not (0.0 <= u <= 1.0):
        raise ValueError(f"Valor de actuação fora de intervalo: {u!r} (esperado 0.0-1.0).")

    if not USE_REAL_HARDWARE:
        _mock_apply_input(u)
        return

    try:
        response = _send_command(f"W {u:.6f}")
        if response != "OK":
            raise IOError(f"Resposta inesperada do Arduino: '{response}'.")
    except Exception as exc:
        raise RuntimeError(f"Falha ao enviar actuação ao Arduino: {exc}") from exc


def hw_read_output() -> float:
    """
    Lê o valor medido pelo ADC do Arduino Due (pino A1).

    Devolve
    -------
    float
        Valor normalizado no intervalo [0.0, 1.0], onde:
            0.0 -> 0 V na entrada do sensor (após divisor de tensão)
            1.0 -> 10 V na entrada do sensor (3.3 V na entrada ADC)

    Raises
    ------
    RuntimeError
        Se USE_REAL_HARDWARE=1 e a comunicação falhar.
    """
    if not USE_REAL_HARDWARE:
        return _mock_read_output()

    try:
        raw = _send_command("R")
        value = float(raw)
    except ValueError:
        raise RuntimeError(f"Resposta não numérica do Arduino: '{raw}'.")
    except Exception as exc:
        raise RuntimeError(f"Falha ao ler ADC do Arduino: {exc}") from exc

    # Garante que o valor fica no intervalo esperado mesmo perante ruído.
    return max(0.0, min(1.0, value))


# ---------------------------------------------------------------------------
# Modelo simulado (mock)
# ---------------------------------------------------------------------------
#
# Sistema de primeira ordem discreto:
#   y[k+1] = alpha * y[k] + (1 - alpha) * u[k]
#
# Parâmetros escolhidos para simular um motor DC de resposta lenta típica
# de bancada laboratorial (constante de tempo ≈ 5 amostras).

_MOCK_ALPHA = 0.8   # polo do sistema discreto

_mock_state: dict = {
    "y": 0.0,   # saída actual
    "u": 0.0,   # última actuação
}


def _mock_apply_input(u: float) -> None:
    _mock_state["u"] = u
    _mock_state["y"] = _MOCK_ALPHA * _mock_state["y"] + (1.0 - _MOCK_ALPHA) * u


def _mock_read_output() -> float:
    return _mock_state["y"]


def reset_mock() -> None:
    """Repõe o estado do modelo simulado (útil em testes)."""
    _mock_state["y"] = 0.0
    _mock_state["u"] = 0.0