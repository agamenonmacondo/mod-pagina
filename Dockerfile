# ✅ IMAGEN BASE OPTIMIZADA
FROM python:3.11-slim

# ✅ METADATA
LABEL maintainer="AVA Development Team"
LABEL description="AVA - Asistente Virtual Avanzado"
LABEL version="2.0.0"

# ✅ INSTALAR DEPENDENCIAS DEL SISTEMA PRIMERO
RUN apt-get update && apt-get install -y \
    gcc g++ sqlite3 curl \
    && rm -rf /var/lib/apt/lists/*

# ✅ CREAR DIRECTORIOS PERSISTENTES
RUN mkdir -p /data /mnt/memory /app
WORKDIR /app

# ✅ COPIAR REQUIREMENTS E INSTALAR
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ INSTALAR PLAYWRIGHT (con manejo de errores)
RUN playwright install chromium || echo "Playwright install failed, continuing..."

# ✅ COPIAR CÓDIGO
COPY . .

# ✅ VARIABLES DE ENTORNO CRÍTICAS
ENV PYTHONPATH=/app
ENV MEMORY_PATH=/data
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# ✅ PERMISOS
RUN chmod -R 755 /data /mnt/memory /app

# ✅ HEALTH CHECK
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:$PORT/health || exit 1

# ✅ EXPONER PUERTO
EXPOSE $PORT

# ✅ COMANDO CON PUERTO DINÁMICO
CMD ["python", "-c", "import os; import asyncio; from llmpagina.ava_bot.ava_bot import main; asyncio.run(main())"]