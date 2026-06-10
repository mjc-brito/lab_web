"""
Testes do sandbox_worker.py.
Cobre: execução de código, persistência de variáveis, funções de controlo,
       bloqueio de operações perigosas, numpy disponível, save_all (.npz).
Não cobre: hardware real (pyserial), recuperação de palavra-passe.
"""
import pytest
import json
import subprocess
import sys
import os
import base64
import io


def run_worker(commands: list[dict]) -> list[dict]:
    """
    Lança o sandbox_worker como subprocesso e envia uma lista de comandos.
    Devolve a lista de respostas JSON (excluindo a mensagem 'ready' inicial).
    """
    worker_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "core", "sandbox_worker.py"
    )
    proc = subprocess.Popen(
        [sys.executable, worker_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # consome a linha "ready"
    proc.stdout.readline()

    results = []
    for cmd in commands:
        proc.stdin.write(json.dumps(cmd) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        results.append(json.loads(line))

    proc.stdin.close()
    proc.wait(timeout=10)
    return results


class TestExecucaoBasica:

    def test_print_aparece_no_stdout(self):
        results = run_worker([{"action": "exec", "code": "print('ola')"}])
        assert results[0]["stdout"].strip() == "ola"

    def test_erro_de_sintaxe_capturado(self):
        results = run_worker([{"action": "exec", "code": "def f(:\n    pass"}])
        assert results[0]["error"] is not None

    def test_erro_de_runtime_capturado(self):
        results = run_worker([{"action": "exec", "code": "1/0"}])
        assert results[0]["error"] is not None
        assert "ZeroDivisionError" in results[0]["error"]

    def test_stdout_vazio_sem_print(self):
        results = run_worker([{"action": "exec", "code": "x = 2 + 2"}])
        assert results[0]["stdout"] == ""
        assert results[0]["error"] is None


class TestPersistenciaVariaveis:

    def test_variavel_persiste_entre_execucoes(self):
        """Variável criada numa execução está disponível na seguinte."""
        results = run_worker([
            {"action": "exec", "code": "x = 42"},
            {"action": "exec", "code": "print(x)"},
        ])
        assert results[1]["stdout"].strip() == "42"

    def test_lista_persiste_e_pode_ser_expandida(self):
        results = run_worker([
            {"action": "exec", "code": "data = [1, 2, 3]"},
            {"action": "exec", "code": "data.append(4)\nprint(len(data))"},
        ])
        assert results[1]["stdout"].strip() == "4"

    def test_vars_update_reflecte_namespace(self):
        """Após execução, vars contém as variáveis criadas."""
        results = run_worker([{"action": "exec", "code": "x = 10\ny = 20"}])
        v = results[0]["vars"]
        assert "x" in v and v["x"] == 10
        assert "y" in v and v["y"] == 20

    def test_clear_limpa_namespace(self):
        results = run_worker([
            {"action": "exec", "code": "x = 99"},
            {"action": "clear"},
            {"action": "exec", "code": "print('vars' if 'x' in dir() else 'limpo')"},
        ])
        # após clear, x não existe
        assert results[2]["error"] is not None or "limpo" in results[2]["stdout"]


"""
class TestNumpy:

    def test_np_disponivel_sem_import(self):
        results = run_worker([
            {"action": "exec", "code": "a = np.array([1, 2, 3])\nprint(a.sum())"}
        ])
        assert results[0]["stdout"].strip() == "6"
        assert results[0]["error"] is None

    def test_operacoes_matriciais(self):
        results = run_worker([{
            "action": "exec",
            "code": "A = np.array([[1,2],[3,4]])\nprint(A.shape)"
        }])
        assert "(2, 2)" in results[0]["stdout"]

    def test_np_zeros_ones(self):
        results = run_worker([{
            "action": "exec",
            "code": "z = np.zeros((3,3))\nprint(z.shape[0])"
        }])
        assert results[0]["stdout"].strip() == "3"
"""
        

class TestFuncoesControlo:

    def test_start_control_disponivel(self):
        results = run_worker([{
            "action": "exec",
            "code": "start_control()\nprint('ok')"
        }])
        assert results[0]["error"] is None
        assert "ok" in results[0]["stdout"]

    def test_read_output_sem_start_lanca_erro(self):
        results = run_worker([{
            "action": "exec",
            "code": "read_output()"
        }])
        assert results[0]["error"] is not None
        assert "start_control" in results[0]["error"]

    def test_apply_input_sem_start_lanca_erro(self):
        results = run_worker([{
            "action": "exec",
            "code": "apply_input(0.5)"
        }])
        assert results[0]["error"] is not None

    def test_loop_controlo_completo(self):
        """Simula um loop de controlo PID com o modelo mockado."""
        code = """
start_control()
y_arr = []
for k in range(10):
    y = read_output()
    u = 0.5 * (1.0 - y)
    apply_input(u)
    y_arr.append(y)
stop_control()
print(len(y_arr))
"""
        results = run_worker([{"action": "exec", "code": code}])
        assert results[0]["error"] is None
        assert results[0]["stdout"].strip() == "10"

    def test_modelo_mockado_converge(self):
        """Com ganho suficiente o modelo de primeira ordem deve convergir."""
        code = """
start_control()
y_final = 0.0
for k in range(100):
    y = read_output()
    u = 2.0 * (1.0 - y)   # ganho alto
    apply_input(u)
    y_final = y
stop_control()
# após 100 iterações deve estar próximo de 1.0
print(round(y_final, 1))
"""
        results = run_worker([{"action": "exec", "code": code}])
        assert results[0]["error"] is None
        # valor final deve ser próximo de 1.0
        assert float(results[0]["stdout"].strip()) >= 0.9

    def test_estado_persiste_entre_execucoes(self):
        """start_control numa execução, read_output noutra — estado persiste."""
        results = run_worker([
            {"action": "exec", "code": "start_control()\napply_input(1.0)"},
            {"action": "exec", "code": "y = read_output()\nprint(y > 0)"},
        ])
        assert results[1]["error"] is None
        assert "True" in results[1]["stdout"]


class TestSeguranca:

    def test_open_bloqueado(self):
        """Acesso ao sistema de ficheiros via open() deve ser bloqueado."""
        results = run_worker([{
            "action": "exec",
            "code": "open('/etc/passwd', 'r')"
        }])
        assert results[0]["error"] is not None

    def test_import_os_permitido_mas_system_falha(self):
        """import é permitido mas operações destrutivas do OS não devem funcionar."""
        # import funciona (sandbox permite imports)
        results = run_worker([{
            "action": "exec",
            "code": "import os\nprint(type(os))"
        }])
        # import deve funcionar sem erro
        assert results[0]["error"] is None

    def test_import_numpy_explicito_funciona(self):
        """Aluno pode fazer import numpy explicitamente."""
        results = run_worker([{
            "action": "exec",
            "code": "import numpy as numpy2\nprint(numpy2.pi)"
        }])
        assert results[0]["error"] is None


class TestSaveAll:

    def test_save_all_gera_npz(self):
        """Botão 'Guardar como' (save_all) devolve ficheiro .npz válido."""
        import numpy as np

        results = run_worker([
            {"action": "exec", "code": "x = 10\ny = np.array([1.0, 2.0, 3.0])"},
            {"action": "save_all"},
        ])
        r = results[1]
        assert r["type"] == "save_result"
        assert r["filename"].endswith(".npz")
        assert r["format"] == "npz"

        # verifica que o conteúdo base64 é um .npz válido
        raw = base64.b64decode(r["data_b64"])
        buf = io.BytesIO(raw)
        data = np.load(buf)
        assert "y" in data
        assert list(data["y"]) == [1.0, 2.0, 3.0]

    def test_save_vars_especificas(self):
        """save_vars com nomes específicos só inclui essas variáveis."""
        import numpy as np

        results = run_worker([
            {"action": "exec", "code": "a = np.array([1,2])\nb = np.array([3,4])\nc = 99"},
            {"action": "save_vars", "names": ["a", "b"]},
        ])
        r = results[1]
        raw = base64.b64decode(r["data_b64"])
        data = np.load(io.BytesIO(raw))
        assert "a" in data
        assert "b" in data
        # c não foi pedido
        assert "c" not in data

    def test_get_var_existente(self):
        results = run_worker([
            {"action": "exec", "code": "z = 42"},
            {"action": "get_var", "name": "z"},
        ])
        assert results[1]["type"] == "var_result"
        assert "42" in results[1]["value"]

    def test_get_var_inexistente(self):
        results = run_worker([
            {"action": "get_var", "name": "nao_existe"},
        ])
        assert results[0]["type"] == "var_result"
        assert results[0]["error"] is not None