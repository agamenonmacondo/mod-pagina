# Ava Bot MCP Server

Este servidor convierte las herramientas existentes de Ava Bot en un servidor **MCP (Model Context Protocol)** compatible con cualquier cliente MCP.

## ¿Qué es MCP?

**Model Context Protocol (MCP)** es un protocolo estándar que permite a modelos de IA y aplicaciones conectarse con herramientas y fuentes de datos externas de manera segura y estandarizada.

### Ventajas de MCP para Ava Bot:

- ✅ **Compatibilidad Universal**: Cualquier cliente MCP puede usar nuestras herramientas
- ✅ **Arquitectura Modular**: Herramientas independientes y reutilizables  
- ✅ **Seguridad**: Acceso controlado a operaciones sensibles
- ✅ **Escalabilidad**: Fácil agregar nuevas herramientas

## Herramientas Disponibles

El servidor MCP expone automáticamente todas las herramientas de Ava Bot:

| Herramienta | Descripción | Funcionalidades |
|-------------|-------------|-----------------|
| `calendar` | Gestión de eventos Google Calendar | Crear, listar, eliminar eventos |
| `meet` | Reuniones Google Meet | Crear reuniones con enlace automático |
| `gmail` | Gestión de correos Gmail | Enviar, leer, buscar emails |
| `search` | Búsquedas web | Búsquedas en Google y otros buscadores |
| `drive` | Gestión Google Drive | Subir, descargar, organizar archivos |
| `image` | Procesamiento de imágenes | Análisis y manipulación de imágenes |
| `calendar_check` | Verificación de disponibilidad | Verificar conflictos de horarios |

## Instalación

```bash
# Navegar al directorio del proyecto
cd ava_bot

# Instalar dependencias (si no están instaladas)
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Verificar que las herramientas se cargan correctamente
python mcp_server/run_server.py list
```

## Uso

### 1. Modo Servidor (Para clientes MCP)

```bash
# Ejecutar servidor MCP en modo stdio
python mcp_server/run_server.py server
```

Este modo es para clientes MCP como Claude Desktop.

### 2. Modo Prueba (Para desarrollo)

```bash
# Ejecutar pruebas automáticas
python mcp_server/run_server.py test
```

### 3. Modo Interactivo (Para debugging)

```bash
# Modo interactivo para pruebas manuales
python mcp_server/run_server.py interactive
```

### 4. Listar Herramientas

```bash
# Ver todas las herramientas disponibles
python mcp_server/run_server.py list
```

## Integración con Claude Desktop

Para usar las herramientas de Ava Bot en Claude Desktop:

1. **Editar configuración de Claude Desktop**:
   
   En Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   En macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. **Agregar configuración MCP**:

```json
{
  "mcpServers": {
    "ava-bot": {
      "command": "python",
      "args": [
        "C:\\path\\to\\ava_bot\\mcp_server\\run_server.py",
        "server"
      ],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\ava_bot"
      }
    }
  }
}
```

3. **Reiniciar Claude Desktop**

4. **Verificar conexión**: Las herramientas de Ava Bot aparecerán disponibles en Claude.

## Uso con Otros Clientes MCP

Cualquier cliente compatible con MCP puede conectarse usando:

```json
{
  "command": "python",
  "args": ["mcp_server/run_server.py", "server"],
  "cwd": "/path/to/ava_bot"
}
```

## Ejemplos de Uso

### Crear Evento de Calendario

```json
{
  "tool": "calendar",
  "parameters": {
    "action": "create_event",
    "summary": "Reunión importante",
    "start_time": "2024-12-25T10:00:00",
    "duration_hours": 1.5,
    "attendees": "juan@email.com,maria@email.com"
  }
}
```

### Crear Reunión Google Meet

```json
{
  "tool": "meet",
  "parameters": {
    "title": "Reunión de equipo",
    "start_time": "2024-12-25T15:00:00",
    "duration_minutes": 60,
    "attendees": "equipo@empresa.com"
  }
}
```

### Enviar Email

```json
{
  "tool": "gmail",
  "parameters": {
    "action": "send",
    "to": "destinatario@email.com",
    "subject": "Asunto del email",
    "body": "Contenido del mensaje"
  }
}
```

## Arquitectura del Proyecto

```
mcp_server/
├── __init__.py          # Documentación del módulo
├── server.py            # Core del servidor MCP (JSON-RPC 2.0)
├── tool_registry.py     # Registro automático de herramientas
├── config.py            # Configuración del servidor
├── run_server.py        # Script de inicio
├── test_client.py       # Cliente de prueba
└── README.md           # Esta documentación
```

## Desarrollo

### Agregar Nueva Herramienta

1. **Crear adapter** en `tools/adapters/nueva_tool_adapter.py`:

```python
from tools.base_tool import BaseTool

class NuevaToolAdapter(BaseTool):
    name = "nueva_tool"
    description = "Descripción de la nueva herramienta"
    
    @property
    def schema(self):
        return {
            "type": "object",
            "properties": {
                "parametro": {
                    "type": "string",
                    "description": "Descripción del parámetro"
                }
            },
            "required": ["parametro"]
        }
    
    def process(self, params):
        # Lógica de la herramienta
        return {"message": "Resultado"}
```

2. **Registrar en tool_registry.py** (se hace automáticamente)

3. **Probar**:
```bash
python mcp_server/run_server.py test
```

### Debugging

Para debugging detallado:

```bash
python mcp_server/run_server.py interactive --log-level DEBUG
```

## Seguridad

- ✅ Las herramientas usan las mismas credenciales y permisos que Ava Bot
- ✅ Sin acceso directo al sistema de archivos del servidor
- ✅ Validación de parámetros en cada herramienta
- ⚠️ Configura autenticación adicional para producción

## Troubleshooting

### Error: "No tools found"

```bash
# Verificar que los adapters existen
ls tools/adapters/

# Verificar permisos de Python
python -c "import sys; print(sys.path)"

# Probar carga individual
python -c "from mcp_server.tool_registry import ToolRegistry; r = ToolRegistry(); print(r.tools)"
```

### Error de Credenciales Google

```bash
# Verificar token.json existe
ls token.json

# Regenerar credenciales si es necesario
python nodes/calendar/calendar_manager.py
```

### Cliente MCP no se conecta

1. Verificar ruta absoluta en configuración
2. Verificar que Python está en PATH
3. Probar modo test primero:
   ```bash
   python mcp_server/run_server.py test
   ```

## Recursos Adicionales

- [Especificación MCP](https://spec.modelcontextprotocol.io/)
- [Claude Desktop MCP Setup](https://docs.anthropic.com/claude/docs/mcp)
- [Documentación de Ava Bot](../README.md)

---

**¡Tu asistente Ava ahora es compatible con cualquier cliente MCP!** 🚀
