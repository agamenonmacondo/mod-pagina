# ✅ IMAGEN BASE OPTIMIZADA
FROM python:3.11-slim

# ✅ METADATA
LABEL maintainer="AVA Development Team"
LABEL description="AVA - Asistente Virtual Avanzado"
LABEL version="2.0.0"

# ✅ VARIABLES DE ENTORNO OPTIMIZADAS
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080 \
    FLASK_ENV=production \
    FLASK_APP=app:app

# ✅ CREAR USUARIO NO-ROOT PARA SEGURIDAD
RUN groupadd --system --gid 1000 ava && \
    useradd --system --uid 1000 --gid ava --shell /bin/bash --create-home ava

# ✅ INSTALAR DEPENDENCIAS DEL SISTEMA
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ✅ ESTABLECER DIRECTORIO DE TRABAJO
WORKDIR /app

# ✅ ACTUALIZAR PIP
RUN pip install --upgrade pip

# ✅ COPIAR Y INSTALAR DEPENDENCIAS (CACHE LAYER)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ CREAR ESTRUCTURA DE DIRECTORIOS
RUN mkdir -p \
    logs \
    instance \
    database \
    uploads \
    static \
    templates \
    && chown -R ava:ava /app

# ✅ COPIAR CÓDIGO FUENTE
COPY --chown=ava:ava . .

# ✅ ASEGURAR PERMISOS
RUN chown -R ava:ava /app && \
    chmod +x /app/app.py

# ✅ CAMBIAR A USUARIO NO-ROOT
USER ava

# ✅ EXPONER PUERTO
EXPOSE $PORT

# ✅ HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:$PORT/ || exit 1

# ✅ COMANDO DE INICIO OPTIMIZADO
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --keep-alive 2 --max-requests 1000 --max-requests-jitter 100 --worker-class gthread app:app"]