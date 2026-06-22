#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
PROJECT_DIR=~/lab_web
VENV=$PROJECT_DIR/venv
CERTS_DIR=$PROJECT_DIR/certs
HTTP_PORT=8000
HTTPS_PORT=8443

# ---------------------------------------------------------------------------
# Ler USE_REAL_HARDWARE apenas do .env (por omissão 0)
# ---------------------------------------------------------------------------
USE_REAL_HARDWARE=0
if [ -f "$PROJECT_DIR/.env" ]; then
    VALUE=$(grep -E '^[[:space:]]*USE_REAL_HARDWARE[[:space:]]*=' "$PROJECT_DIR/.env" | tail -1 | cut -d= -f2- | tr -d "[:space:]\"'")
    USE_REAL_HARDWARE="${VALUE:-0}"
fi

# ---------------------------------------------------------------------------
# Passar Arduino para o WSL (apenas com hardware real)
# ---------------------------------------------------------------------------
if [ "$USE_REAL_HARDWARE" = "1" ]; then
    echo "[1/4] A verificar permissões..."
    IS_ADMIN=$(powershell.exe -NoProfile -Command \
        "([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)" \
        2>/dev/null | tr -d '[:space:]')

    if [ "$IS_ADMIN" != "True" ]; then
        echo ""
        echo "========================================================"
        echo " ERRO: permissões insuficientes."
        echo ""
        echo " Este script requer permissões de administrador"
        echo " para passar o Arduino para o WSL."
        echo ""
        echo " Feche este terminal e abra novamente clicando com"
        echo " o botão direito no Ubuntu → 'Executar como administrador'."
        echo "========================================================"
        echo ""
        exit 1
    fi
    echo "      Permissões OK"

    echo "[2/4] A passar Arduino para o WSL..."
    PS_SCRIPT="$(wslpath -w "$(dirname "$(realpath "$0")")/attach_arduino.ps1")"
    powershell.exe -ExecutionPolicy Bypass -File "$PS_SCRIPT"

    if [ $? -ne 0 ]; then
        echo ""
        echo "========================================================"
        echo " ERRO: nao foi possivel passar o Arduino para o WSL."
        echo " Verifica se o Arduino esta ligado ao computador."
        echo "========================================================"
        echo ""
        exit 1
    fi
else
    echo "[1/4] Hardware real desactivado (USE_REAL_HARDWARE != 1)."
    echo "[2/4] A saltar verificação de permissões e ligação do Arduino."
fi

# ---------------------------------------------------------------------------
# Redis via Docker
# ---------------------------------------------------------------------------
echo "[3/4] A iniciar Redis..."
docker stop redis &>/dev/null || true
docker rm   redis &>/dev/null || true
docker stop lab_web-redis-1 &>/dev/null || true
docker rm   lab_web-redis-1 &>/dev/null || true
docker run -d -p 6379:6379 --name redis redis:6

echo "      A aguardar Redis ficar pronto..."
until redis-cli ping 2>/dev/null | grep -q PONG; do
  sleep 0.5
done
echo "      Redis OK"

# ---------------------------------------------------------------------------
# Activar ambiente virtual
# ---------------------------------------------------------------------------
source $VENV/bin/activate
cd $PROJECT_DIR

# ---------------------------------------------------------------------------
# Mostrar endereços de acesso
# ---------------------------------------------------------------------------
IP_WSL=$(ip addr show eth0 2>/dev/null \
  | grep "inet " | awk '{print $2}' | cut -d/ -f1)
IP_WINDOWS=$(powershell.exe -NoProfile -Command \
  "(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi','Ethernet' | Select-Object -First 1).IPAddress" \
  2>/dev/null | tr -d '[:space:]')

echo ""
echo "========================================================"
echo " Laboratório Remoto"
echo "========================================================"
echo " HTTP  (só esta máquina):  http://localhost:${HTTP_PORT}"
if [ -n "$IP_WINDOWS" ]; then
  echo " HTTP  (rede da faculdade): http://${IP_WINDOWS}:${HTTP_PORT}"
fi

if [ -f "$CERTS_DIR/cert.pem" ] && [ -f "$CERTS_DIR/key.pem" ]; then
  echo " HTTPS (localhost):        https://localhost:${HTTPS_PORT}"
  if [ -n "$IP_WINDOWS" ]; then
    echo " HTTPS (rede da faculdade): https://${IP_WINDOWS}:${HTTPS_PORT}"
  fi
  HTTPS_ARGS="-e ssl:${HTTPS_PORT}:privateKey=${CERTS_DIR}/key.pem:certKey=${CERTS_DIR}/cert.pem"
else
  echo ""
  echo " AVISO: certificado não encontrado em $CERTS_DIR"
  echo "        A correr só em HTTP. showSaveFilePicker não disponível."
  echo "        Para gerar o certificado:"
  echo "        mkdir certs && openssl req -x509 -newkey rsa:4096 \\"
  echo "          -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes \\"
  echo "          -subj \"/CN=${IP_WINDOWS:-127.0.0.1}\" \\"
  echo "          -addext \"subjectAltName=IP:${IP_WINDOWS:-127.0.0.1},IP:127.0.0.1\""
  HTTPS_ARGS=""
fi
echo "========================================================"
echo ""

# ---------------------------------------------------------------------------
# Arrancar Daphne com HTTP + HTTPS (se certificado disponível)
# ---------------------------------------------------------------------------
echo "[4/4] A arrancar servidor..."
daphne \
  $HTTPS_ARGS \
  -b 0.0.0.0 -p $HTTP_PORT \
  config.asgi:application