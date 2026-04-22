# ─────────────────────────────────────────────────────────────────
# Backend Dockerfile — Python 3.11 + FastAPI + uvicorn
# ─────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Evitar archivos .pyc y buffering de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema necesarias para sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python primero (aprovecha cache de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente del backend
COPY . .

# Puerto de la API
EXPOSE 8000

# Iniciar uvicorn apuntando al app FastAPI
# --host 0.0.0.0 es necesario para que Docker exponga el puerto
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
