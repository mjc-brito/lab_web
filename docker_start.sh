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
# Verificar permissões de administrador no Windows
# ---------------------------------------------------------------------------
echo "[1/3] A verificar permissões..."
IS_ADMIN=$(powershell.exe -NoProfile -Command \
    "([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)" \
    2>/dev/null | tr -d '[:space:]')

if [ "$IS_ADMIN" != "True" ]; then
    echo ""
    echo "========================================================"
    echo " ERRO: permissões insuficientes."
    echo ""
    echo " Este script requer PowerShell com permissões de"
    echo " administrador para passar o Arduino para o WSL."
    echo ""
    echo " Feche este terminal e abra novamente clicando com"
    echo " o botão direito no Ubuntu → 'Executar como administrador'."
    echo "========================================================"
    echo ""
    exit 1
fi
echo "      Permissões OK"

# ---------------------------------------------------------------------------
# Passar Arduino para o WSL e configurar port forwarding
# ---------------------------------------------------------------------------
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
docker compose up $BUILD_FLAG