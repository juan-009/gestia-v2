# ================================================
# Build Stage: Instalación de dependencias y compilación
# ================================================
FROM python:3.10-slim-bullseye AS builder

WORKDIR /app

# Instalar dependencias del sistema requeridas para paquetes Python y seguridad
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear entorno virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar dependencias
COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt && \
    find /opt/venv -type f -name '*.pyc' -delete && \
    find /opt/venv -type d -name '__pycache__' -exec rm -rf {} +

# ================================================
# Runtime Stage: Imagen de producción optimizada
# ================================================
FROM python:3.10-slim-bullseye

# Configuración de seguridad
RUN useradd --create-home appuser && \
    mkdir -p /app/keys && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copiar desde el builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Variables de entorno esenciales
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus

# Copiar aplicación y configuraciones
COPY . .
COPY --chown=appuser:appuser ./keys /app/keys

# Permisos y limpieza
RUN chmod 0500 /app/keys && \
    find . -name '*.pyc' -delete && \
    find . -type d -name '__pycache__' -exec rm -rf {} +

USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/auth/health || exit 1

# Comando principal
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", \
    "--workers", "4", "--proxy-headers", \
    "app.interfaces.api.main:app"]