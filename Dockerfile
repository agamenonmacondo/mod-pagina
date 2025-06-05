# ✅ IMAGEN BASE OPTIMIZADA
FROM python:3.11-slim

# ✅ METADATA
LABEL maintainer="AVA Development Team"
LABEL description="AVA - Asistente Virtual Avanzado"
LABEL version="2.0.0"

# ✅ INSTALAR DEPENDENCIAS DEL SISTEMA PRIMERO
RUN apt-get update && apt-get install -y \
    gcc g++ sqlite3 curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# ✅ CREAR DIRECTORIOS PERSISTENTES
RUN mkdir -p /data /mnt/memory /app
WORKDIR /app

# ✅ COPIAR REQUIREMENTS E INSTALAR
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ✅ COPIAR CÓDIGO
COPY . .

# ✅ VERIFICAR QUE LA ESTRUCTURA DE ARCHIVOS ES CORRECTA
RUN echo "=== VERIFICANDO ESTRUCTURA DE ARCHIVOS ===" && \
    echo "Contenido del directorio raíz:" && \
    ls -la && \
    echo "" && \
    echo "Verificando app.py:" && \
    ls -la app.py && \
    echo "" && \
    echo "Verificando directorio llmpagina:" && \
    ls -la llmpagina/ && \
    echo "" && \
    echo "Verificando directorio ava_bot:" && \
    ls -la llmpagina/ava_bot/ && \
    echo "" && \
    echo "Verificando ava_bot.py:" && \
    ls -la llmpagina/ava_bot/ava_bot.py && \
    echo "" && \
    echo "Verificando tools:" && \
    ls -la llmpagina/ava_bot/tools/ && \
    echo "" && \
    echo "Verificando adapters:" && \
    ls -la llmpagina/ava_bot/tools/adapters/ && \
    echo "" && \
    echo "Verificando openai_tts_adapter.py:" && \
    ls -la llmpagina/ava_bot/tools/adapters/openai_tts_adapter.py && \
    echo "=== VERIFICACIÓN COMPLETADA ==="

# ✅ VARIABLES DE ENTORNO CRÍTICAS
ENV PYTHONPATH=/app:/app/llmpagina:/app/llmpagina/ava_bot
ENV MEMORY_PATH=/data
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ✅ PERMISOS
RUN chmod -R 755 /data /mnt/memory /app

# ✅ HEALTH CHECK
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:$PORT/health || exit 1

# ✅ EXPONER PUERTO
EXPOSE $PORT

# ✅ COMANDO CON PUERTO DINÁMICO
CMD ["python", "app.py"]