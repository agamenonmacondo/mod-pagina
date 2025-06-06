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
ENV PIP_NO_CACHE_DIR=1

# ✅ INSTALAR DEPENDENCIAS DEL SISTEMA
RUN apt-get update && apt-get install -y \
    # Build tools
    gcc g++ make \
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

# ✅ ACTUALIZAR PIP Y HERRAMIENTAS
RUN pip install --upgrade pip setuptools wheel

# ✅ COPIAR Y INSTALAR DEPENDENCIAS CON MANEJO DE ERRORES
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || \
    (echo "Error en requirements.txt, probando versión mínima..." && \
     pip install Flask==3.0.0 Werkzeug==3.0.1 gunicorn==21.2.0 \
     bcrypt==4.0.1 python-dotenv==1.0.0 requests==2.31.0 \
     groq==0.4.1 httpx==0.25.2 google-auth==2.23.4 \
     Pillow==10.1.0 packaging==23.2)

# ✅ COPIAR CÓDIGO DE LA APLICACIÓN
COPY --chown=appuser:appuser . .

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