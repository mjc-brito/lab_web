#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
PROJECT_DIR=~/django_playground/lab_web
VENV=$PROJECT_DIR/venv
CERTS_DIR=$PROJECT_DIR/certs
HTTP_PORT=8000
HTTPS_PORT=8443

# ---------------------------------------------------------------------------
# Redis via Docker
# ---------------------------------------------------------------------------
echo "[1/3] A iniciar Redis..."
docker stop redis 2>/dev/null || true
docker rm   redis 2>/dev/null || true
docker run -d -p 6379:6379 --name redis redis:6

echo "      A aguardar Redis ficar pronto..."
until redis-cli ping 2>/dev/null | grep -q PONG; do
  sleep 0.5
done
echo "      Redis OK"

# ---------------------------------------------------------------------------
# Activar ambiente virtual
# ---------------------------------------------------------------------------
echo "[2/3] A activar venv..."
source $VENV/bin/activate
cd $PROJECT_DIR

# ---------------------------------------------------------------------------
# Mostrar endereços de acesso
# ---------------------------------------------------------------------------
IP_HOST_ONLY=$(ip addr show enp0s8 2>/dev/null \
  | grep "inet " | awk '{print $2}' | cut -d/ -f1)
IP_NAT=$(ip addr show enp0s3 2>/dev/null \
  | grep "inet " | awk '{print $2}' | cut -d/ -f1)

echo ""
echo "========================================================"
echo " Laboratório Remoto"
echo "========================================================"
echo " HTTP  (só esta máquina):  http://localhost:${HTTP_PORT}"
if [ -n "$IP_HOST_ONLY" ]; then
  echo " HTTP  (rede local):       http://${IP_HOST_ONLY}:${HTTP_PORT}"
fi

# só mostra HTTPS se o certificado existir
if [ -f "$CERTS_DIR/cert.pem" ] && [ -f "$CERTS_DIR/key.pem" ]; then
  echo " HTTPS (localhost):        https://localhost:${HTTPS_PORT}"
  if [ -n "$IP_HOST_ONLY" ]; then
    echo " HTTPS (rede local):       https://${IP_HOST_ONLY}:${HTTPS_PORT}"
  fi
  HTTPS_ARGS="-e ssl:${HTTPS_PORT}:privateKey=${CERTS_DIR}/key.pem:certKey=${CERTS_DIR}/cert.pem"
else
  echo ""
  echo " AVISO: certificado não encontrado em $CERTS_DIR"
  echo "        A correr só em HTTP. showSaveFilePicker não disponível."
  echo "        Para gerar o certificado:"
  echo "        mkdir certs && openssl req -x509 -newkey rsa:4096 \\"
  echo "          -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes \\"
  echo "          -subj \"/CN=${IP_HOST_ONLY:-127.0.0.1}\" \\"
  echo "          -addext \"subjectAltName=IP:${IP_HOST_ONLY:-127.0.0.1},IP:127.0.0.1\""
  HTTPS_ARGS=""
fi
echo "========================================================"
echo ""

# ---------------------------------------------------------------------------
# Arrancar Daphne com HTTP + HTTPS (se certificado disponível)
# ---------------------------------------------------------------------------
echo "[3/3] A arrancar servidor..."
daphne \
  $HTTPS_ARGS \
  -b 0.0.0.0 -p $HTTP_PORT \
  config.asgi:application
