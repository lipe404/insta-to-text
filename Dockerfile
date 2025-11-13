FROM python:3.10-slim

# Instalar apenas dependências essenciais
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Variáveis de ambiente para otimização
ENV FLASK_ENV=production
ENV WHISPER_MODEL=tiny
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Gunicorn com configurações leves
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "2", "--timeout", "120", "--max-requests", "100", "--max-requests-jitter", "10", "app:create_app()"]