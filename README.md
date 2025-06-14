# Prometheus - Plataforma de IA

Aplicación web desarrollada con Flask que ofrece servicios inteligentes basados en LLM, generación SEO, y más.

## Cambios Estructurales Recientes

Esta aplicación ha sido reestructurada para mayor flexibilidad. Los archivos principales que antes estaban en el subdirectorio `llmpagina/` ahora se encuentran en la raíz del proyecto. La aplicación es compatible con ambas estructuras y puede funcionar correctamente independientemente de dónde se ubiquen los archivos principales.

La nueva estructura admite:
- Ejecución desde la raíz o desde el subdirectorio llmpagina/
- Importaciones desde ambas ubicaciones
- Rutas de acceso a templates, static, y archivos de contenido desde cualquier ubicación

## Características

- Autenticación de usuarios (registro, inicio de sesión, recuperación de contraseña)
- Generación de contenido SEO automatizada
- Interfaz web moderna y responsive
- Integración con Groq para modelos LLM
- Dashboard administrativo
- Estadísticas y análisis
- Sistema de gestión de clientes
- Procesamiento avanzado de Markdown en artículos

## Tecnologías

- Python 3.10+
- Flask
- SQLite
- Groq API
- Docker
- HTML5/CSS3
- JavaScript

## Requisitos

- Python 3.10+
- Groq API Key
- Git
- Docker (opcional)
- Cuenta en Google Cloud (para despliegue)

## Instalación

1. Clonar el repositorio
   ```bash
   git clone https://github.com/YOUR_USERNAME/prometheus.git
   cd prometheus
   ```

2. Crear y activar entorno virtual
   ```bash
   python -m venv venv
   source venv/bin/activate   # En Windows: venv\Scripts\activate
   ```

3. Instalar dependencias
   ```bash
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno
   ```bash
   cp env.example .env
   # Editar .env con tus claves
   ```

## Ejecución

### Desarrollo local

```bash
python app.py
```

### Con Docker

```bash
docker build -t prometheus .
docker run -p 8080:8080 prometheus
```

### Con Docker Compose

```bash
docker-compose up
```

## Despliegue

El proyecto está configurado para despliegue automático en Google Cloud Run.

```bash
gcloud builds submit --config cloudbuild.yaml
```

## Variables de Entorno
Crear un archivo `.env` con:

```
GROQ_API_KEY=sk-xxxxx
SECRET_KEY=your_secret_key
PORT=8080
```

## Estructura de directorios

```
/
├── app.py                 # Aplicación principal Flask  
├── requirements.txt       # Dependencias
├── Dockerfile             # Configuración para Docker
├── llmpagina/             # Directorio legacy
│   ├── templates/         # Templates de Jinja2
│   └── static/            # Archivos estáticos
├── templates/             # Templates alternativos
├── static/                # Archivos estáticos alternativos
├── ava_modular/           # Módulo de agente virtual
└── ava_seo/               # Módulo de generación SEO
```

# AVA - Asistente Virtual Avanzado 🤖

[![Cloud Run](https://img.shields.io/badge/Google%20Cloud-Run-blue)](https://cloud.google.com/run)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0+-red)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

Sistema web avanzado de asistente virtual con IA multimodal, memoria persistente y herramientas integradas.

## 🌟 **Características Principales**

### 🤖 **IA Avanzada**
- **Modelos múltiples**: Groq, OpenAI, Together AI
- **Memoria multimodal**: Texto, imágenes, documentos
- **Búsqueda semántica**: ChromaDB + embeddings
- **Generación de imágenes**: Fal.ai integration

### 💻 **Interfaz Moderna**
- **Chat inteligente**: Interfaz responsive y moderna
- **Dashboard completo**: Estadísticas y gestión
- **Autenticación segura**: Sistema completo de usuarios
- **Temas**: Modo claro/oscuro

### 🛠️ **Herramientas Integradas**
- **Navegación web**: Playwright + Selenium
- **Búsqueda web**: Tavily integration
- **Gmail**: Gestión de emails (opcional)
- **Calendario**: Google Calendar (opcional)

### ☁️ **Cloud Ready**
- **Google Cloud Run**: Deploy automático
- **App Engine**: Configuración incluida
- **Docker**: Containerización completa
- **Memoria persistente**: Sistema cloud adaptativo

## 🚀 **Inicio Rápido**

### **Instalación Local**

```bash
# 1. Clonar repositorio
git clone https://github.com/YOUR_USERNAME/ava-assistant.git
cd ava-assistant

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 5. Ejecutar aplicación
python app.py
```

### **Con Docker**

```bash
# Build y ejecutar
docker build -t ava-assistant .
docker run -p 8080:8080 --env-file .env ava-assistant

# O con Docker Compose
docker-compose up
```

### **Deploy en Google Cloud**

```bash
# 1. Configurar proyecto
gcloud config set project TU_PROJECT_ID

# 2. Deploy automático
gcloud builds submit --config cloudbuild.yaml

# 3. Verificar deployment
gcloud run services describe ava-app --region=us-central1
```

## 🔧 **Configuración**

### **Variables de Entorno Críticas**

```env
# API Keys (obligatorias)
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...

# Configuración básica
SECRET_KEY=tu-clave-super-secreta
PORT=8080
FLASK_ENV=production

# Configuración cloud (automática en GCP)
GOOGLE_CLOUD_PROJECT=tu-project-id
CLOUD_ENV=production
```

### **Configuración Avanzada**

Ver [`.env.example`](.env.example) para todas las opciones disponibles.

## 📁 **Estructura del Proyecto**

```
ava-assistant/
├── 📄 app.py                    # Aplicación principal Flask
├── 📁 routes/                   # Rutas y endpoints
│   ├── auth_routes.py          # Autenticación
│   ├── chat_routes.py          # Chat y IA
│   ├── dashboard_routes.py     # Dashboard
│   └── api_routes.py           # API REST
├── 📁 database/                 # Gestión de datos
│   ├── db_manager.py           # BD local
│   └── cloud_db_manager.py     # BD cloud
├── 📁 llmpagina/               # Módulo principal AVA
│   ├── 📁 ava_bot/             # Core del asistente
│   │   ├── ava_bot.py          # Lógica principal
│   │   └── 📁 tools/           # Herramientas integradas
│   ├── 📁 templates/           # Templates HTML
│   └── 📁 static/              # Archivos estáticos
├── 📄 requirements.txt         # Dependencias Python
├── 📄 Dockerfile              # Configuración Docker
├── 📄 cloudbuild.yaml         # Google Cloud Build
└── 📄 docker-compose.yml      # Docker Compose
```

## 🔑 **API Endpoints**

### **Públicos**
- `GET /` - Página principal
- `GET /health` - Health check
- `POST /login` - Iniciar sesión
- `POST /register` - Registrar usuario

### **Autenticados**
- `GET /dashboard` - Dashboard principal
- `POST /api/chat` - Chat con AVA
- `GET /api/memory/status` - Estado de memoria
- `POST /api/upload` - Subir archivos

### **Administración**
- `GET /admin` - Panel admin
- `GET /api/system/health` - Estado del sistema
- `POST /api/admin/users` - Gestión de usuarios

## 👤 **Usuarios por Defecto**

```
Admin:  admin / admin123
Demo:   demo  / demo123
```

## 🧪 **Testing**

```bash
# Ejecutar tests
pytest tests/ -v

# Con coverage
pytest --cov=. tests/

# Test específico
pytest tests/test_auth.py
```

## 🛡️ **Seguridad**

- ✅ **Contraseñas hasheadas** con Werkzeug
- ✅ **Sesiones seguras** con Flask-Session
- ✅ **Rate limiting** incorporado
- ✅ **Validación de entrada** en todos los endpoints
- ✅ **HTTPS** en producción
- ✅ **Variables sensibles** en variables de entorno

## 📊 **Monitoreo**

### **Health Checks**
- `/health` - Estado básico
- `/api/system/health` - Estado detallado
- `/api/memory/status` - Estado de memoria

### **Logs**
```bash
# Ver logs en Cloud Run
gcloud run services logs tail ava-app --region=us-central1

# Logs locales
tail -f logs/app.log
```

## 🔄 **Actualizaciones**

```bash
# Pull últimos cambios
git pull origin main

# Actualizar dependencias
pip install -r requirements.txt --upgrade

# Re-deploy en cloud
gcloud builds submit --config cloudbuild.yaml
```

## 🤝 **Contribuir**

1. **Fork** el proyecto
2. **Crear** rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. **Commit** cambios (`git commit -m 'Agregar funcionalidad'`)
4. **Push** (`git push origin feature/nueva-funcionalidad`)
5. **Crear** Pull Request

### **Guías de Contribución**
- Seguir PEP 8 para Python
- Agregar tests para nuevas funcionalidades
- Documentar cambios en CHANGELOG.md
- Usar conventional commits

## 📄 **Licencia**

MIT License - ver [LICENSE](LICENSE) para detalles.

## 🆘 **Soporte y Recursos**

- 📖 **Documentación**: [Wiki del proyecto](https://github.com/YOUR_USERNAME/ava-assistant/wiki)
- 🐛 **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/ava-assistant/issues)
- 💬 **Discusiones**: [GitHub Discussions](https://github.com/YOUR_USERNAME/ava-assistant/discussions)
- 📧 **Email**: soporte@ava-assistant.com

## 🏆 **Agradecimientos**

- **Google Cloud** - Infraestructura cloud
- **OpenAI** - Modelos de IA
- **Groq** - Inferencia rápida
- **Flask** - Framework web
- **ChromaDB** - Base de datos vectorial

---

**🤖 Desarrollado con ❤️ para AVA - Asistentes Virtuales Avanzados**

*¿Te gusta el proyecto? ¡Dale una ⭐ en GitHub!*
