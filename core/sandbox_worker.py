"""
Sandbox worker — processo filho isolado.
Lê comandos JSON do stdin, executa, devolve resultados JSON no stdout.
Namespace persiste entre execuções da mesma sessão.
"""
import sys
import io
import json
import traceback
import base64
import numpy as np

_namespace = {}


# ---------------------------------------------------------------------------
# Builtins — bloqueia acesso ao OS/ficheiros, permite imports
# ---------------------------------------------------------------------------

def _safe_builtins():
    import builtins
    blocked = {"open", "breakpoint", "input", "memoryview"}
    return {
        name: getattr(builtins, name)
        for name in dir(builtins)
        if name not in blocked and not name.startswith("_")
    }


# ---------------------------------------------------------------------------
# Serialização para o painel de variáveis
# ---------------------------------------------------------------------------

def _serialize_value(v):
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, (int, float, bool, str, type(None))):
        return v
    if isinstance(v, (list, tuple)):
        return [_serialize_value(i) for i in v]
    if isinstance(v, dict):
        return {str(k): _serialize_value(val) for k, val in v.items()}
    return str(v)


def _get_user_vars():
    skip = (type, type(sys))
    result = {}
    for k, v in _namespace.items():
        if k.startswith("_"):
            continue
        if isinstance(v, skip):
            continue
        if callable(v) and not isinstance(v, np.ufunc):
            continue
        try:
            result[k] = _serialize_value(v)
        except Exception:
            result[k] = str(v)
    return result


# ---------------------------------------------------------------------------
# Serialização para download — apenas .npz
# ---------------------------------------------------------------------------

def _save_vars(names: list, stem: str = None) -> dict:
    to_save = {n: _namespace[n] for n in names if n in _namespace}
    missing = [n for n in names if n not in _namespace]
    if missing:
        print(f"Aviso: variáveis não encontradas: {', '.join(missing)}")

    file_stem = stem or "variaveis"

    arrays = {}
    for name, val in to_save.items():
        try:
            arr = np.asarray(val)
            if arr.dtype.kind not in ("U", "O"):
                arrays[name] = arr
        except Exception:
            pass

    buf = io.BytesIO()
    np.savez(buf, **arrays)
    buf.seek(0)
    return {
        "type": "save_result",
        "format": "npz",
        "filename": file_stem + ".npz",
        "data_b64": base64.b64encode(buf.getvalue()).decode()
    }


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------

def execute(code: str) -> dict:
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = captured_out
    sys.stderr = captured_err

    if "_ctrl_state" not in _namespace:
        _namespace["_ctrl_state"] = {
            "running": False,
            "last_output": 0.0,
            "outputs": [],
        }
    state = _namespace["_ctrl_state"]

    def start_control():
        state["running"] = True
        state["last_output"] = 0.0
        state["outputs"] = []
        print("Controlo iniciado.")

    def apply_input(u):
        if not state["running"]:
            raise RuntimeError("Chame start_control() primeiro.")
        state["last_output"] = 0.8 * state["last_output"] + 0.2 * float(u)
        return state["last_output"]

    def read_output():
        if not state["running"]:
            raise RuntimeError("Chame start_control() primeiro.")
        val = state["last_output"]
        state["outputs"].append(val)
        return val

    def stop_control():
        state["running"] = False
        print("Controlo encerrado.")

    _namespace["start_control"] = start_control
    _namespace["apply_input"]   = apply_input
    _namespace["read_output"]   = read_output
    _namespace["stop_control"]  = stop_control
    if "np" not in _namespace:
        _namespace["np"] = np

    error = None
    try:
        exec(code, {"__builtins__": _safe_builtins()}, _namespace)
    except Exception:
        error = traceback.format_exc()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return {
        "type": "exec_result",
        "stdout": captured_out.getvalue(),
        "stderr": captured_err.getvalue(),
        "error": error,
        "vars": _get_user_vars(),
    }


def get_var(name: str) -> dict:
    if name not in _namespace:
        return {"type": "var_result", "name": name,
                "error": f"Variável '{name}' não existe."}
    v = _namespace[name]
    if isinstance(v, np.ndarray):
        preview = f"shape={v.shape}  dtype={v.dtype}\n{v}"
    else:
        preview = str(_serialize_value(v))
    return {"type": "var_result", "name": name, "value": preview}


def save_all() -> dict:
    names = [k for k in _namespace
             if not k.startswith("_") and not callable(_namespace[k])]
    return _save_vars(names)


def clear_vars() -> dict:
    _namespace.clear()
    return {"type": "cleared"}


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------

def main():
    sys.stdout.write(json.dumps({"type": "ready"}) + "\n")
    sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            cmd = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({"type": "error", "error": "JSON inválido"}) + "\n")
            sys.stdout.flush()
            continue

        action = cmd.get("action")
        if action == "exec":
            result = execute(cmd.get("code", ""))
        elif action == "get_var":
            result = get_var(cmd.get("name", ""))
        elif action == "save_vars":
            result = _save_vars(cmd.get("names", []), cmd.get("stem"))
        elif action == "save_all":
            result = save_all()
        elif action == "clear":
            result = clear_vars()
        else:
            result = {"type": "error", "error": f"Acção desconhecida: {action}"}

        sys.stdout.write(json.dumps(result) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()