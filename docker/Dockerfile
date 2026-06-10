# docker/Dockerfile
#
# Imagem do container Django + Daphne.
# Construída a partir da raiz do projecto:
#   docker build -f docker/Dockerfile -t lab-django .

FROM python:3.10-slim

# Evita que o Python escreva .pyc e que o stdout seja bufferizado
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para compilar pacotes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código fonte
COPY . .

# Recolhe ficheiros estáticos
RUN python manage.py collectstatic --noinput

# Cria a directoria para o SQLite (montada como volume em Docker)
RUN mkdir -p /app/db

# Porta exposta pelo Daphne (HTTP)
EXPOSE 8000

# Comando de arranque: migra a BD e inicia o Daphne
CMD ["sh", "-c", "python manage.py migrate --noinput && daphne -b 0.0.0.0 -p 8000 config.asgi:application"]