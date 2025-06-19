#!/usr/bin/env python3
"""
Ava Bot MCP Server - Versión gRPC
================================

Servidor MCP con modo gRPC únicamente.
"""
import json
import os
import sys
import time
from datetime import datetime

# CONFIGURAR CODIFICACIÓN UTF-8 PARA WINDOWS
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# CONFIGURACIÓN DE PATHS
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

paths_to_add = [
    project_root,
    os.path.join(project_root, 'memory'),
    os.path.join(project_root, 'tools'),
    current_dir
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

# LOGGING MEJORADO - SOLO STDERR
def safe_log(message: str, level: str = "INFO"):
    """Log seguro que SOLO va a stderr - NUNCA a stdout"""
    try:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}][MCP-{level}] {message}", file=sys.stderr, flush=True)
    except:
        pass

class SilentAdapterLoader:
    """Cargador de adapters SILENCIOSO - sin prints a stdout"""
    
    def __init__(self):
        self.loaded_adapters = {}
        self.adapter_definitions = [
            ("memory", "tools.adapters.memory_adapter", "MemoryAdapter"),
            ("calendar", "tools.adapters.calendar_adapter", "CalendarAdapter"),
            ("gmail", "tools.adapters.gmail_adapter", "GmailAdapter"),
            ("search", "tools.adapters.search_adapter", "SearchAdapter"),
            ("meet", "tools.adapters.meet_adapter", "MeetAdapter"),
            ("image", "tools.adapters.image_adapter", "ImageAdapter"),
            ("image_display", "tools.adapters.image_display_adapter", "ImageDisplayAdapter"),
            ("file_manager", "tools.adapters.file_adapter", "FileManagerAdapter"),
            ("vision", "tools.adapters.vision_adapter", "VisionAdapter"),
            ("playwright", "tools.adapters.playwright_adapter", "PlaywrightAdapter"),
            ("multimodal_memory", "tools.adapters.multimodal_memory_adapter", "MultimodalMemoryAdapter"),
            ("openai_tts", "tools.adapters.openai_tts_adapter", "OpenAITTSAdapter"),
            ("groq_speech", "tools.adapters.groq_speech_adapter", "GroqSpeechAdapter")
        ]
        
    def load_all_adapters(self):
        """Cargar todos los adapters SIN PRINTS a stdout"""
        safe_log("🚀 Iniciando carga silenciosa de adapters...")
        
        # Redirigir temporalmente prints de los adapters
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        try:
            # Crear un "null" stream para capturar prints no deseados
            class NullStream:
                def write(self, text): pass
                def flush(self): pass
                
            # Durante la carga, redirigir prints de adapters
            null_stream = NullStream()
            
            for name, module_path, class_name in self.adapter_definitions:
                try:
                    safe_log(f"📦 Cargando {name}...")
                    
                    # Temporalmente silenciar stdout durante import
                    sys.stdout = null_stream
                    
                    # Verificar que el módulo existe
                    try:
                        module = __import__(module_path, fromlist=[class_name])
                    except ImportError as ie:
                        safe_log(f"❌ No se pudo importar {module_path}: {ie}")
                        continue
                    finally:
                        sys.stdout = original_stdout
                    
                    # Verificar que la clase existe
                    if not hasattr(module, class_name):
                        safe_log(f"❌ Clase {class_name} no encontrada")
                        continue
                    
                    adapter_class = getattr(module, class_name)
                    
                    # Crear instancia - también silenciar prints durante init
                    sys.stdout = null_stream
                    try:
                        adapter_instance = adapter_class()
                    except Exception as e:
                        safe_log(f"❌ Error inicializando {name}: {e}")
                        continue
                    finally:
                        sys.stdout = original_stdout
                    
                    # Verificar métodos necesarios
                    if name == "file_manager":
                        required_methods = ['execute']
                    else:
                        required_methods = ['process', 'execute']
                    
                    available_methods = [method for method in required_methods if hasattr(adapter_instance, method)]
                    
                    if available_methods:
                        self.loaded_adapters[name] = adapter_instance
                        safe_log(f"✅ {name} cargado correctamente")
                    else:
                        safe_log(f"❌ {name} no tiene métodos requeridos: {required_methods}")
                        
                except Exception as e:
                    safe_log(f"❌ Error cargando {name}: {e}")
            
        finally:
            # Restaurar streams originales
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
        safe_log(f"📊 Carga completada: {len(self.loaded_adapters)}/{len(self.adapter_definitions)} adapters")
        return self.loaded_adapters

class CleanMCPServer:
    """Servidor MCP que envía SOLO JSON por stdout"""
    
    def __init__(self):
        self.adapter_loader = SilentAdapterLoader()
        self.adapters = {}
        self.initialized = False
        
    def initialize(self):
        """Inicializar servidor SILENCIOSAMENTE"""
        safe_log("🔄 Inicializando servidor MCP...")
        self.adapters = self.adapter_loader.load_all_adapters()
        self.initialized = True
        safe_log(f"✅ Servidor inicializado con {len(self.adapters)} herramientas")
        
    def get_available_tools(self):
        """Obtener herramientas disponibles"""
        tools = []
        
        for name, adapter in self.adapters.items():
            description = getattr(adapter, 'description', f'Ava Bot {name} tool')
            
            # Crear esquema básico
            input_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            # ✅ ESQUEMAS ESPECÍFICOS PARA CADA HERRAMIENTA
            if name == "vision":
                input_schema["properties"] = {
                    "action": {
                        "type": "string",
                        "enum": ["analyze_image", "describe_image", "ocr_text", "test_analyze"],
                        "description": "Tipo de análisis visual a realizar"
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Ruta completa de la imagen a analizar"
                    },
                    "user_question": {
                        "type": "string",
                        "description": "Pregunta específica sobre la imagen"
                    },
                    "detail_level": {
                        "type": "string",
                        "enum": ["low", "high", "auto"],
                        "description": "Nivel de detalle del análisis",
                        "default": "high"
                    }
                }
                input_schema["required"] = ["action", "image_path"]
                
            elif name == "playwright":
                input_schema["properties"] = {
                    "action": {
                        "type": "string",
                        "enum": [
                            # 🔍 Navegación
                            "navigate", "go_back", "go_forward", "reload", "close_page",
                            
                            # 📊 Extracción
                            "extract_text", "extract_html", "extract_links", "extract_images",
                            "extract_tables", "extract_forms", "extract_metadata",
                            
                            # 🧠 Acciones Inteligentes - NUEVAS
                            "smart_extract", "auto_search", "analyze_site",
                            
                            # 🛒 E-commerce
                            "extract_prices", "extract_product_info", "extract_reviews", 
                            "extract_ratings", "compare_prices",
                            
                            # 🎯 Interacción
                            "click_element", "double_click", "right_click", "hover",
                            "fill_input", "select_option", "check_checkbox", "upload_file",
                            
                            # 📱 Scroll
                            "scroll_to_element", "scroll_page", "infinite_scroll", "scroll_to_bottom",
                            
                            # ⏱️ Esperas
                            "wait_for_element", "wait_for_text", "wait_for_url", "wait_for_load_state",
                            
                            # 📸 Capturas
                            "take_screenshot", "take_element_screenshot", "create_pdf",
                            
                            # 🔧 JavaScript
                            "execute_js", "evaluate_expression", "inject_css",
                            
                            # 🌐 Red
                            "intercept_requests", "block_resources", "get_network_activity",
                            
                            # 🔐 Sesiones
                            "login_form", "save_cookies", "load_cookies", "clear_cookies",
                            
                            # 🎨 Dispositivos
                            "set_viewport", "emulate_device", "set_geolocation",
                            
                            # 📋 Utilidades
                            "get_page_info", "download_file", "handle_popup"
                        ],
                        "description": "Acción de automatización web a realizar"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL de destino para navegación y extracción"
                    },
                    "selector": {
                        "type": "string", 
                        "description": "Selector CSS del elemento objetivo"
                    },
                    "search_query": {
                        "type": "string",
                        "description": "Query para búsqueda automática inteligente"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 5,
                        "description": "Máximo número de resultados para extracción inteligente"
                    },
                    "text": {
                        "type": "string",
                        "description": "Texto para buscar o llenar"
                    },
                    "javascript": {
                        "type": "string",
                        "description": "Código JavaScript a ejecutar"
                    },
                    "screenshot_options": {
                        "type": "object",
                        "properties": {
                            "full_page": {"type": "boolean", "default": True},
                            "filename": {"type": "string"},
                            "quality": {"type": "integer", "minimum": 0, "maximum": 100}
                        }
                    },
                    "viewport": {
                        "type": "object", 
                        "properties": {
                            "width": {"type": "integer", "default": 1920},
                            "height": {"type": "integer", "default": 1080}
                        }
                    },
                    "device": {
                        "type": "string",
                        "enum": ["iPhone 12", "iPad", "Galaxy S21", "Pixel 5", "Desktop"],
                        "description": "Dispositivo a emular"
                    },
                    "wait_options": {
                        "type": "object",
                        "properties": {
                            "timeout": {"type": "integer", "default": 30000},
                            "state": {"type": "string", "enum": ["visible", "hidden", "attached", "detached"]}
                        }
                    },
                    "scroll_options": {
                        "type": "object",
                        "properties": {
                            "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                            "amount": {"type": "integer", "default": 500},
                            "smooth": {"type": "boolean", "default": True}
                        }
                    },
                    "price_selectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": [".price", ".precio", ".amount", ".cost", "[data-price]"],
                        "description": "Selectores CSS para precios"
                    },
                    "max_items": {
                        "type": "integer",
                        "default": 10,
                        "description": "Máximo número de elementos a extraer"
                    }
                }
                # 🔧 CORRECCIÓN CRÍTICA: URL ES REQUERIDA PARA LA MAYORÍA DE ACCIONES
                input_schema["required"] = ["action", "url"]
                
            elif name == "file_manager":
                input_schema["properties"] = {
                    "action": {
                        "type": "string",
                        "enum": ["list_files", "get_file_info", "read_file", "get_latest_image", "prepare_for_email", "copy_file", "delete_file"],
                        "description": "Acción a realizar"
                    },
                    "directory": {
                        "type": "string",
                        "enum": ["generated_images", "downloads", "temp", "uploads"],
                        "description": "Directorio objetivo"
                    },
                    "filename": {"type": "string", "description": "Nombre del archivo"},
                    "pattern": {"type": "string", "description": "Patrón para filtrar archivos"},
                    "limit": {"type": "integer", "description": "Límite de resultados", "default": 10}
                }
                input_schema["required"] = ["action"]
                
            elif name == "calendar":
                input_schema["properties"] = {
                    "summary": {"type": "string", "description": "Event title"},
                    "start_time": {"type": "string", "description": "Start time in ISO format"},
                    "duration_hours": {"type": "number", "description": "Duration in hours"},
                    "attendees": {"type": "string", "description": "Attendee emails"},
                    "description": {"type": "string", "description": "Event description"}
                }
                input_schema["required"] = ["summary", "start_time"]
                
           
                
            elif name == "gmail":
                input_schema["properties"] = {
                    "to": {"type": "string", "description": "Recipient email"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body"},
                    "send_latest_image": {"type": "boolean", "description": "Send latest generated image"},
                    "attachment_data": {"type": "object", "description": "Attachment data from file_manager"}
                }
                input_schema["required"] = ["to", "subject", "body"]
                
            elif name == "meet":
                input_schema["properties"] = {
                    "summary": {"type": "string", "description": "Título de la reunión"},
                    "start_time": {"type": "string", "description": "Fecha y hora en formato ISO (YYYY-MM-DDTHH:MM:SS)"},
                    "duration_hours": {"type": "number", "description": "Duración en horas", "default": 1},
                    "description": {"type": "string", "description": "Descripción opcional de la reunión"},
                    "attendees": {"type": "string", "description": "Emails de asistentes separados por comas"}
                }
                input_schema["required"] = ["summary"]
                
            elif name == "image":
                input_schema["properties"] = {
                    "prompt": {"type": "string", "description": "Image description"},
                    "style": {"type": "string", "description": "Image style"}
                }
                input_schema["required"] = ["prompt"]
                
            elif name == "memory":
                input_schema["properties"] = {
                    "user_id": {"type": "string", "description": "User identifier"},
                    "action": {"type": "string", "description": "Action: search, store, get_context"},
                    "query": {"type": "string", "description": "Search query"},
                    "content": {"type": "string", "description": "Content to store"}
                }
                input_schema["required"] = ["user_id", "action"]
            
            elif name == "multimodal_memory":
                input_schema["properties"] = {
                    "action": {
                        "type": "string",
                        "enum": [
                            "store_text_memory", "store_image_memory", 
                            "search_semantic_memories", "get_recent_multimodal_context",
                            "find_related_images", "get_user_stats",
                            "create_semantic_link", "validate_system"
                        ],
                        "description": "Acción de memoria multimodal a realizar"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "ID del usuario",
                        "required": True
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenido de texto para almacenar"
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Ruta de la imagen"
                    },
                    "description": {
                        "type": "string",
                        "description": "Descripción de la imagen"
                    },
                    "query": {
                        "type": "string",
                        "description": "Query para búsqueda semántica"
                    },
                    "modalities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Modalidades: ['text', 'image']",
                        "default": ["text"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Límite de resultados",
                        "default": 5
                    },
                    "session_id": {
                        "type": "string",
                        "description": "ID de sesión"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Días hacia atrás",
                        "default": 7
                    },
                    "text_query": {
                        "type": "string",
                        "description": "Query para buscar imágenes relacionadas"
                    },
                    "memory_id_1": {
                        "type": "integer",
                        "description": "ID de primera memoria para enlace"
                    },
                    "memory_id_2": {
                        "type": "integer", 
                        "description": "ID de segunda memoria para enlace"
                    },
                    "memory_type_1": {
                        "type": "string",
                        "description": "Tipo de primera memoria"
                    },
                    "memory_type_2": {
                        "type": "string",
                        "description": "Tipo de segunda memoria"
                    },
                    "similarity_score": {
                        "type": "number",
                        "description": "Puntuación de similitud"
                    },
                    "link_type": {
                        "type": "string",
                        "description": "Tipo de enlace semántico"
                    }
                }
                input_schema["required"] = ["action", "user_id"]

            elif name == "openai_tts":
                input_schema["properties"] = {
                    "action": {
                        "type": "string",
                        "enum": ["text_to_speech", "get_voices"],
                        "description": "Acción a realizar"
                    },
                    "text": {
                        "type": "string", 
                        "description": "Texto para convertir a voz"
                    },
                    "voice": {
                        "type": "string",
                        "enum": ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"],
                        "default": "coral",
                        "description": "Voz de OpenAI a usar"
                    },
                    "model": {
                        "type": "string",
                        "default": "gpt-4o-mini-tts",
                        "enum": ["gpt-4o-mini-tts"],
                        "description": "Modelo TTS de OpenAI"
                    },
                    "speed": {
                        "type": "number",
                        "minimum": 0.25,
                        "maximum": 4.0,
                        "default": 1.0,
                        "description": "Velocidad de reproducción"
                    },
                    "preset_accent": {
                        "type": "string",
                        "enum": ["colombiano", "mexicano", "argentino", "español", "neutral", "custom"],
                        "default": "neutral",
                        "description": "Acento preconfigurado"
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Instrucciones específicas para el habla"
                    },
                    "return_audio": {
                        "type": "boolean",
                        "default": False,
                        "description": "Retornar audio en base64"
                    },
                    "play_audio": {
                        "type": "boolean",
                        "default": True,
                        "description": "Reproducir audio inmediatamente"
                    }
                }
                input_schema["required"] = ["action", "text"]
                
            elif name == "groq_speech":
                input_schema["properties"] = {
                    "action": {
                        "type": "string",
                        "enum": ["speech_to_text", "text_to_speech", "get_voices", "transcribe_file", "transcribe_url"],
                        "description": "Acción a realizar"
                    },
                    "audio_data": {
                        "type": "string",
                        "description": "Audio en base64 para STT"
                    },
                    "audio_url": {
                        "type": "string",
                        "description": "URL del audio para transcribir"
                    },
                    "text": {
                        "type": "string", 
                        "description": "Texto para convertir a voz"
                    },
                    "language": {
                        "type": "string",
                        "default": "es",
                        "description": "Idioma (es, en, etc.)"
                    },
                    "engine": {
                        "type": "string",
                        "enum": ["gtts", "pyttsx3"],
                        "default": "gtts",
                        "description": "Motor TTS a usar"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Ruta del archivo de audio para transcribir"
                    },
                    "model": {
                        "type": "string",
                        "default": "whisper-large-v3-turbo",
                        "description": "Modelo Whisper de Groq"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Prompt opcional para guiar la transcripción"
                    },
                    "temperature": {
                        "type": "number",
                        "default": 0,
                        "description": "Temperatura para la transcripción"
                    },
                    "return_audio": {
                        "type": "boolean",
                        "default": False,
                        "description": "Retornar audio en base64"
                    }
                }
                input_schema["required"] = ["action"]

            tools.append({
                "name": name,
                "description": description,
                "inputSchema": input_schema
            })
        
        return tools

# ==================== PROTOBUF DEFINITION ====================
PROTO_DEFINITION = """
syntax = "proto3";

package ava_bot;

service AvaBot {
    rpc Health (HealthRequest) returns (HealthResponse);
    rpc ListTools (ToolsRequest) returns (ToolsList);
    rpc ExecuteTool (ToolRequest) returns (ToolResponse);
}

message HealthRequest {}

message HealthResponse {
    string status = 1;
    string timestamp = 2;
    double uptime_seconds = 3;
    int32 total_tools = 4;
    int32 request_count = 5;
}

message ToolsRequest {}

message ToolsList {
    map<string, string> tools = 1;
    map<string, string> schemas = 2;
    int32 total_count = 3;
    string timestamp = 4;
}

message ToolRequest {
    string tool_name = 1;
    string parameters = 2;
}

message ToolResponse {
    bool success = 1;
    string text = 2;
    string raw_result = 3;
    string tool_name = 4;
    string timestamp = 5;
}
"""

def generate_proto_files():
    """Genera los archivos protobuf necesarios si no existen"""
    try:
        # Primero intentar importar directamente
        import ava_bot_pb2
        import ava_bot_pb2_grpc
        return True
    except ImportError:
        try:
            import os
            import subprocess
            import sys
            from pathlib import Path
            
            # Crear archivo proto en el directorio actual
            proto_content = PROTO_DEFINITION.strip()
            proto_path = Path("ava_bot.proto")
            
            # Escribir el archivo proto
            with open(proto_path, 'w', encoding='utf-8') as f:
                f.write(proto_content)
            
            # Generar archivos Python
            cmd = [
                sys.executable,
                '-m', 'grpc_tools.protoc',
                f'-I{os.getcwd()}',
                '--python_out=.',
                '--grpc_python_out=.',
                str(proto_path)
            ]
            
            # Ejecutar el comando
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # ✅ NUEVO: Corregir importaciones automáticamente
            fix_protobuf_imports()
            
            # Verificar que se generaron los archivos
            required_files = ['ava_bot_pb2.py', 'ava_bot_pb2_grpc.py']
            if not all(os.path.exists(f) for f in required_files):
                raise RuntimeError(f"No se generaron todos los archivos necesarios: {required_files}")
            
            # Limpiar archivo proto (opcional)
            try:
                proto_path.unlink()
            except:
                pass
                
            return True
            
        except subprocess.CalledProcessError as e:
            safe_log(f"❌ Error en protoc (code {e.returncode}): {e.stderr}")
            return False
        except Exception as e:
            safe_log(f"❌ Error generando archivos protobuf: {str(e)}")
            return False

def fix_protobuf_imports():
    """Corrige automáticamente las importaciones en los archivos protobuf generados"""
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    grpc_file = os.path.join(current_dir, 'ava_bot_pb2_grpc.py')
    
    if not os.path.exists(grpc_file):
        return False
    
    # Leer el archivo
    with open(grpc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar y reemplazar la línea problemática
    old_import = "import ava_bot_pb2 as ava__bot__pb2"
    new_import = """try:
    import ava_bot_pb2 as ava__bot__pb2
except ImportError:
    from . import ava_bot_pb2 as ava__bot__pb2"""
    
    if old_import in content and new_import not in content:
        content = content.replace(old_import, new_import)
        
        # Escribir el archivo corregido
        with open(grpc_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        safe_log("✅ Importaciones protobuf corregidas automáticamente")
        return True
    
    return True

# Modificar el bloque try-except para incluir el fix
try:
    if not generate_proto_files():
        raise ImportError("No se pudieron generar los archivos protobuf")
        
    import grpc
    from concurrent import futures
    
    # Importar con manejo de errores y fix automático
    try:
        import ava_bot_pb2
        import ava_bot_pb2_grpc
    except ImportError:
        # Si fallan las importaciones, intentar generar de nuevo y corregir
        safe_log("🔄 Regenerando archivos protobuf...")
        generate_proto_files()
        fix_protobuf_imports()  # <-- Añadir fix
        import ava_bot_pb2
        import ava_bot_pb2_grpc
        
    GRPC_AVAILABLE = True
    
except ImportError as e:
    GRPC_AVAILABLE = False
    safe_log(f"⚠️ gRPC no disponible: {str(e)}")
    safe_log("Instala las dependencias con: pip install grpcio grpcio-tools")
    sys.exit(1)

# Mover la definición de la clase después del bloque try-except
if GRPC_AVAILABLE:
    class AvaBotServicer(ava_bot_pb2_grpc.AvaBotServicer):
        """Servidor gRPC que envuelve el CleanMCPServer"""
        
        def __init__(self, mcp_server):
            self.mcp_server = mcp_server
            self.start_time = time.time()
            self.request_count = 0
            
        def Health(self, request, context):
            uptime = time.time() - self.start_time
            return ava_bot_pb2.HealthResponse(
                status="ok",
                timestamp=datetime.now().isoformat(),
                uptime_seconds=round(uptime, 2),
                total_tools=len(self.mcp_server.adapters),
                request_count=self.request_count
            )
            
        def ListTools(self, request, context):
            self.request_count += 1
            tools = self.mcp_server.get_available_tools()
            
            response = ava_bot_pb2.ToolsList()
            for tool in tools:
                response.tools[tool['name']] = tool['description']
                response.schemas[tool['name']] = json.dumps(tool['inputSchema'])
                
            response.total_count = len(tools)
            response.timestamp = datetime.now().isoformat()
            return response
            
        def ExecuteTool(self, request, context):
            self.request_count += 1
            tool_name = request.tool_name
            args = json.loads(request.parameters)
            
            if tool_name not in self.mcp_server.adapters:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Tool {tool_name} not found")
                return ava_bot_pb2.ToolResponse()
                
            try:
                adapter = self.mcp_server.adapters[tool_name]
                
                if hasattr(adapter, 'execute'):
                    raw_result = adapter.execute(args)
                elif hasattr(adapter, 'process'):
                    raw_result = adapter.process(args)
                else:
                    context.set_code(grpc.StatusCode.INTERNAL)
                    context.set_details("Adapter has no execute/process method")
                    return ava_bot_pb2.ToolResponse()
                    
                if isinstance(raw_result, dict):
                    main_text = raw_result.get("content", [{}])[0].get("text", "") if "content" in raw_result else str(raw_result)
                else:
                    main_text = str(raw_result)
                    
                return ava_bot_pb2.ToolResponse(
                    success=True,
                    text=main_text,
                    raw_result=json.dumps(raw_result),
                    tool_name=tool_name,
                    timestamp=datetime.now().isoformat()
                )
                
            except Exception as e:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(e))
                return ava_bot_pb2.ToolResponse()

def start_grpc_server(host='localhost', port=50051):
    """Iniciar servidor gRPC"""
    if not GRPC_AVAILABLE:
        raise ImportError("gRPC requerido: pip install grpcio grpcio-tools")
        
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    mcp_server = CleanMCPServer()
    mcp_server.initialize()
    
    ava_bot_pb2_grpc.add_AvaBotServicer_to_server(
        AvaBotServicer(mcp_server), server)
        
    server.add_insecure_port(f'{host}:{port}')
    safe_log(f"🚀 Iniciando servidor gRPC en {host}:{port}")
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        safe_log("🛑 Servidor gRPC interrumpido por usuario")
    except Exception as e:
        safe_log(f"❌ Error fatal del servidor gRPC: {e}")
        sys.exit(1)

def main():
    """Función principal - gRPC por defecto"""
    if len(sys.argv) > 1 and sys.argv[1] == "info":
        # Modo información (sin cambios)
        safe_log("🧪 Mostrando información del servidor...")
        
        server = CleanMCPServer()
        server.initialize()
        
        tools = server.get_available_tools()
        
        print("\n" + "="*60)
        print("🔍 SERVIDOR MCP - AVA BOT")
        print("="*60)
        
        print(f"\n📊 RESUMEN:")
        print(f"   • Adapters cargados: {len(server.adapters)}")
        print(f"   • Herramientas disponibles: {len(tools)}")
        print(f"   • Estado: {'✅ Listo' if server.initialized else '❌ Error'}")
        
        if tools:
            print(f"\n🛠️ HERRAMIENTAS DISPONIBLES:")
            for i, tool in enumerate(tools, 1):
                name = tool['name']
                desc = tool['description'][:60] + "..." if len(tool['description']) > 60 else tool['description']
                required = tool.get('inputSchema', {}).get('required', [])
                print(f"   {i:2d}. {name:<18} - {desc}")
                if required:
                    print(f"       🔑 Parámetros requeridos: {', '.join(required)}")
        
        print("="*60)
        
    else:
        # Modo servidor gRPC por defecto
        host = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "grpc" else 'localhost'
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 50051
        
        if len(sys.argv) > 1 and sys.argv[1] == "grpc":
            host = sys.argv[2] if len(sys.argv) > 2 else 'localhost'
            port = int(sys.argv[3]) if len(sys.argv) > 3 else 50051
        
        safe_log(f"🌐 Iniciando servidor gRPC en {host}:{port}")
        start_grpc_server(host=host, port=port)

if __name__ == "__main__":
    main()
