#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
PROJECT_DIR=~/lab_web
CERTS_DIR=$PROJECT_DIR/certs
HTTP_PORT=8000
HTTPS_PORT=8443

# ---------------------------------------------------------------------------
# Argumentos
# ---------------------------------------------------------------------------
BUILD_FLAG=""
if [ "$1" = "--build" ]; then
    BUILD_FLAG="--build"
fi

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
    echo "[1/3] A verificar permissões..."
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

    echo "[2/3] A passar Arduino para o WSL..."
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
    echo "[1/3] Hardware real desactivado (USE_REAL_HARDWARE != 1)."
    echo "[2/3] A saltar verificação de permissões e ligação do Arduino."
fi

# ---------------------------------------------------------------------------
# Mostrar endereços de acesso
# ---------------------------------------------------------------------------
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
fi
echo "========================================================"
echo ""

# ---------------------------------------------------------------------------
# Arrancar com Docker Compose
# ---------------------------------------------------------------------------
echo "[3/3] A arrancar com Docker Compose..."
cd $PROJECT_DIR
docker stop redis &>/dev/null || true
docker rm   redis &>/dev/null || true
docker stop lab_web-redis-1 &>/dev/null || true
docker rm   lab_web-redis-1 &>/dev/null || true
docker compose up $BUILD_FLAG