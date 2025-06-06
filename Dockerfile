# ✅ IMAGEN BASE OPTIMIZADA PARA PRODUCCIÓN
FROM python:3.11-slim

# ✅ METADATA DEL PROYECTO
LABEL maintainer="AVA Development Team"
LABEL description="AVA - Asistente Virtual Avanzado con IA Multimodal"
LABEL version="2.1.0"
LABEL repository="https://github.com/YOUR_USERNAME/ava-assistant"

# ✅ VARIABLES DE ENTORNO CRÍTICAS
ENV PYTHONPATH=/app:/app/llmpagina:/app/llmpagina/ava_bot
ENV MEMORY_PATH=/data
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# ✅ INSTALAR DEPENDENCIAS DEL SISTEMA
RUN apt-get update && apt-get install -y \
    # Build tools
    gcc g++ make \
    # Database
    sqlite3 \
    # Web tools
    curl wget \
    # Version control
    git \
    # Image processing
    libmagic1 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ✅ CREAR USUARIO NO-ROOT PARA SEGURIDAD
RUN groupadd -r appuser && useradd -r -g appuser appuser

# ✅ CREAR DIRECTORIOS CON PERMISOS
RUN mkdir -p /data /app/logs /app/instance \
    && chown -R appuser:appuser /data /app

# ✅ CAMBIAR A DIRECTORIO DE TRABAJO
WORKDIR /app

# ✅ COPIAR Y INSTALAR DEPENDENCIAS COMO ROOT
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ✅ INSTALAR PLAYWRIGHT BROWSERS
RUN playwright install chromium && \
    playwright install-deps

# ✅ COPIAR CÓDIGO DE LA APLICACIÓN
COPY --chown=appuser:appuser . .

# ✅ VERIFICAR ESTRUCTURA DE ARCHIVOS
RUN echo "=== VERIFICANDO ESTRUCTURA AVA ===" && \
    echo "📁 Directorio raíz:" && ls -la && \
    echo "📄 app.py:" && ls -la app.py && \
    echo "📁 llmpagina/:" && ls -la llmpagina/ && \
    echo "📁 ava_bot/:" && ls -la llmpagina/ava_bot/ && \
    echo "📁 tools/:" && ls -la llmpagina/ava_bot/tools/ && \
    echo "📁 routes/:" && ls -la routes/ && \
    echo "📁 database/:" && ls -la database/ && \
    echo "✅ Estructura verificada"

# ✅ CONFIGURAR PERMISOS FINALES
RUN chmod +x /app/app.py && \
    chmod -R 755 /data /app

# ✅ CAMBIAR A USUARIO NO-ROOT
USER appuser

# ✅ HEALTH CHECK ROBUSTO
HEALTHCHECK --interval=30s --timeout=30s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# ✅ EXPONER PUERTO
EXPOSE $PORT

# ✅ COMANDO DE INICIO
CMD ["python", "app.py"]