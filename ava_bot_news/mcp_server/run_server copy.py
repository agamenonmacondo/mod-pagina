#!/usr/bin/env python3
"""
Ava Bot MCP Server - Versión Corregida
====================================

Servidor MCP que envía SOLO JSON por stdout y logs por stderr.
"""
import asyncio
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

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
                        # FileManager usa método 'execute'
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
                
            # ✅ ESQUEMA PARA PLAYWRIGHT ADAPTER
            elif name == "playwright":
                input_schema["properties"] = {
                    "action": {
                        "type": "string",
                        "enum": [
                            "navigate",
                            "extract_text", 
                            "extract_html",
                            "extract_links",
                            "execute_js",
                            "take_screenshot",
                            "get_page_info"
                        ],
                        "description": "Acción de automatización web a realizar"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL de destino para navegación"
                    },
                    "selector": {
                        "type": "string",
                        "description": "Selector CSS del elemento objetivo (opcional)"
                    },
                    "javascript": {
                        "type": "string",
                        "description": "Código JavaScript a ejecutar en la página"
                    },
                    "screenshot_name": {
                        "type": "string",
                        "description": "Nombre del archivo de captura"
                    },
                    "full_page": {
                        "type": "boolean",
                        "default": True,
                        "description": "Captura de página completa"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 30000,
                        "description": "Timeout en milisegundos"
                    }
                }
                input_schema["required"] = ["action"]
                
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
                
            elif name == "search":
                input_schema["properties"] = {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "description": "Number of results"}
                }
                input_schema["required"] = ["query"]
                
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
            
            # ✅ ESQUEMA PARA MULTIMODAL MEMORY REAL
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

            # ✅ ESQUEMA PARA OPENAI TTS ADAPTER
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
                
            # ✅ ESQUEMA PARA GROQ SPEECH ADAPTER
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
        
    def create_json_rpc_response(self, request_id, result):
        """Crear respuesta JSON-RPC válida"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        return json.dumps(response, ensure_ascii=False)
    
    def create_error_response(self, request_id, code, message):
        """Crear respuesta de error JSON-RPC"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": str(message)
            }
        }
        return json.dumps(response, ensure_ascii=False)
    
    async def handle_request(self, request_data: str) -> str:
        """Manejar solicitudes JSON-RPC - SOLO retorna JSON"""
        try:
            request = json.loads(request_data.strip())
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            safe_log(f"📥 Request: {method} (ID: {request_id})")
            
            if method == "initialize":
                if not self.initialized:
                    self.initialize()
                
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "ava-clean-mcp-server",
                        "version": "3.0.0",
                        "description": "Ava Bot Clean MCP Server - JSON only"
                    }
                }
                
                safe_log(f"✅ Initialize successful - {len(self.adapters)} adapters loaded")
                return self.create_json_rpc_response(request_id, result)
                
            elif method == "tools/list":
                tools = self.get_available_tools()
                result = {"tools": tools}
                
                safe_log(f"📤 Returning {len(tools)} tools")
                for tool in tools:
                    safe_log(f"   🔧 {tool['name']}")
                
                return self.create_json_rpc_response(request_id, result)
                
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if not tool_name:
                    return self.create_error_response(request_id, -32602, "Tool name required")
                
                if tool_name not in self.adapters:
                    available = list(self.adapters.keys())
                    return self.create_error_response(request_id, -32601, f"Tool '{tool_name}' not found. Available: {available}")
                
                try:
                    safe_log(f"🔧 Executing {tool_name}")
                    
                    adapter = self.adapters[tool_name]
                    
                    # Capturar cualquier print del adapter
                    original_stdout = sys.stdout
                    
                    try:
                        # Ejecutar método del adapter con stdout silenciado
                        class CaptureStream:
                            def __init__(self):
                                self.content = []
                            def write(self, text):
                                self.content.append(text)
                            def flush(self):
                                pass
                        
                        capture = CaptureStream()
                        sys.stdout = capture
                        
                        if hasattr(adapter, 'execute'):
                            raw_result = adapter.execute(arguments)
                        elif hasattr(adapter, 'process'):
                            raw_result = adapter.process(arguments)
                        else:
                            return self.create_error_response(request_id, -32603, f"Adapter {tool_name} has no execute/process method")
                    
                    finally:
                        sys.stdout = original_stdout
                        # Los prints del adapter van a stderr si es necesario
                        if capture.content:
                            captured_output = ''.join(capture.content)
                            safe_log(f"📄 Adapter output: {captured_output[:100]}...")
                    
                    # Formatear resultado
                    if isinstance(raw_result, dict):
                        if "content" in raw_result:
                            formatted_result = raw_result
                        else:
                            formatted_result = {
                                "content": [{"type": "text", "text": str(raw_result)}]
                            }
                    elif isinstance(raw_result, str):
                        formatted_result = {
                            "content": [{"type": "text", "text": raw_result}]
                        }
                    else:
                        formatted_result = {
                            "content": [{"type": "text", "text": str(raw_result)}]
                        }
                    
                    safe_log(f"✅ {tool_name} completed successfully")
                    return self.create_json_rpc_response(request_id, formatted_result)
                    
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {str(e)}"
                    safe_log(f"❌ {error_msg}")
                    return self.create_error_response(request_id, -32603, error_msg)
            
            else:
                return self.create_error_response(request_id, -32601, f"Method not found: {method}")
                
        except json.JSONDecodeError as e:
            safe_log(f"❌ JSON Parse error: {e}")
            return self.create_error_response(None, -32700, f"Parse error: {e}")
        except Exception as e:
            safe_log(f"❌ Request handling error: {e}")
            return self.create_error_response(
                request.get("id") if 'request' in locals() else None, 
                -32603, 
                f"Internal error: {e}"
            )
    
    async def run_stdio(self):
        """Ejecutar servidor en modo stdio - SOLO JSON a stdout"""
        safe_log("📡 Iniciando servidor MCP limpio...")
        
        # Asegurar inicialización silenciosa
        if not self.initialized:
            self.initialize()
        
        safe_log(f"🎯 Servidor listo con {len(self.adapters)} herramientas")
        
        try:
            while True:
                try:
                    # Leer línea de entrada
                    line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                    
                    if not line:
                        safe_log("📪 EOF received, shutting down...")
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    safe_log(f"📨 Processing: {line[:50]}...")
                    
                    # Procesar request y enviar SOLO JSON
                    response = await self.handle_request(line)
                    
                    # ✅ STDOUT SOLO PARA JSON
                    print(response, flush=True)
                    safe_log(f"📤 JSON response sent")
                    
                except EOFError:
                    safe_log("📪 EOFError received")
                    break
                except Exception as e:
                    safe_log(f"❌ STDIO error: {e}")
                    error_response = self.create_error_response(None, -32603, f"Server error: {e}")
                    print(error_response, flush=True)
                    
        except KeyboardInterrupt:
            safe_log("🛑 Server interrupted")
        except Exception as e:
            safe_log(f"❌ Fatal error: {e}")
        finally:
            safe_log("🏁 Server shutting down")

# ✅ TEST CASES ACTUALIZADOS PARA INCLUIR PLAYWRIGHT
def get_test_cases():
    """Casos de prueba para todas las herramientas incluyendo TTS adapters"""
    return {
        'memory': {
            'basic': {
                "user_id": "test_user",
                "action": "search",
                "query": "test query"
            },
            'description': 'Búsqueda en memoria'
        },
        
        'calendar': {
            'basic': {
                "summary": "Test Event",
                "start_time": "2025-06-05T15:00:00",
                "duration_hours": 1,
                "description": "Test calendar event"
            },
            'description': 'Crear evento de calendario'
        },
        
        'gmail': {
            'basic': {
                "to": "test@example.com",
                "subject": "Test Email",
                "body": "Este es un email de prueba"
            },
            'description': 'Enviar email de prueba'
        },
        
        'search': {
            'basic': {
                "query": "Python programming",
                "num_results": 3
            },
            'description': 'Búsqueda web'
        },
        
        'meet': {
            'basic': {
                "summary": "Test Meeting",
                "start_time": "2025-06-05T16:00:00",
                "duration_hours": 1,
                "attendees": "test@example.com"
            },
            'description': 'Crear reunión Meet'
        },
        
        'image': {
            'basic': {
                "prompt": "A simple test image of a robot",
                "style": "digital art"
            },
            'description': 'Generar imagen'
        },
        
        'image_display': {
            'basic': {
                "action": "list_recent",
                "limit": 3
            },
            'description': 'Mostrar imágenes recientes'
        },
        
        'file_manager': {
            'basic': {
                "action": "list_files",
                "directory": "generated_images",
                "limit": 5
            },
            'description': 'Listar archivos'
        },
        
        # ✅ AGREGAR TEST CASE PARA VISION
        'vision': {
            'basic': {
                "action": "test_analyze",
                "image_path": r"D:\ComfyUI_windows_portable\ComfyUI\output\ComfyUI_00137_.png",
                "user_question": "¿Qué puedes ver en esta imagen?",
                "detail_level": "high"
            },
            'description': 'Análisis de imagen con IA'
        },
        
        # ✅ AGREGAR TEST CASE PARA PLAYWRIGHT
        'playwright': {
            'basic': {
                "action": "get_page_info",
                "url": "https://httpbin.org/html"
            },
            'description': 'Automatización web con Playwright'
        },
        
        # ✅ CAMBIAR TEST CASE PARA MULTIMODAL MEMORY REAL
        'multimodal_memory': {
            'basic': {
                "action": "validate_system",
                "user_id": "test_user@email.com"
            },
            'description': 'Validación del sistema de memoria multimodal real'
        },
        
        # ✅ TEST CASE PARA OPENAI TTS
        'openai_tts': {
            'basic': {
                "action": "text_to_speech",
                "text": "¡Hola! Soy AVA Assistant probando el sistema de voz de OpenAI con acento colombiano",
                "voice": "coral",
                "model": "gpt-4o-mini-tts",
                "preset_accent": "colombiano",
                "play_audio": False,  # No reproducir en tests
                "return_audio": True   # Generar base64 para verificar
            },
            'description': 'Generación de voz con OpenAI TTS y acentos'
        },
        
        # ✅ TEST CASE PARA GROQ SPEECH
        'groq_speech': {
            'basic': {
                "action": "text_to_speech",
                "text": "Probando Groq Speech con síntesis de voz local",
                "engine": "gtts",
                "language": "es",
                "return_audio": True   # Generar base64 para verificar
            },
            'description': 'Síntesis de voz con Groq Speech (TTS local)'
        }
    }

async def test_all_tools_comprehensive():
    """Test completo de todas las herramientas disponibles incluyendo playwright"""
    safe_log("🧪 INICIANDO TEST COMPLETO DE HERRAMIENTAS...")
    
    server = CleanMCPServer()
    server.initialize()
    
    if not server.initialized:
        safe_log("❌ ERROR: Servidor no se pudo inicializar")
        return False
    
    tools = server.get_available_tools()
    safe_log(f"📊 Probando {len(tools)} herramientas...")
    
    test_cases = get_test_cases()
    results = {}
    total_tests = len(test_cases)
    passed_tests = 0
    
    # 🔍 EJECUTAR TESTS PARA CADA HERRAMIENTA
    for tool_name, test_info in test_cases.items():
        safe_log(f"\n🔧 PROBANDO: {tool_name} - {test_info['description']}")
        
        if tool_name not in server.adapters:
            safe_log(f"   ❌ SKIP: {tool_name} no está cargado")
            results[tool_name] = {
                'status': 'not_loaded',
                'error': 'Adapter no cargado'
            }
            continue
        
        try:
            # Simular llamada JSON-RPC para la herramienta
            test_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": test_info['basic']
                }
            }
            
            # Ejecutar el test
            response_json = await server.handle_request(json.dumps(test_request))
            response = json.loads(response_json)
            
            # Analizar resultado
            if "error" in response:
                error_msg = response["error"]["message"]
                safe_log(f"   ❌ ERROR: {error_msg}")
                results[tool_name] = {
                    'status': 'error',
                    'error': error_msg,
                    'response': response
                }
            else:
                result_content = response.get("result", {})
                content = result_content.get("content", [])
                
                if content and len(content) > 0:
                    first_content = content[0]
                    text_content = first_content.get("text", "")
                    
                    # Análisis específico por herramienta
                    success_indicators = {
                        'memory': ['memoria', 'búsqueda', 'contexto'],
                        'calendar': ['evento', 'calendar', 'creado'],
                        'gmail': ['email', 'enviado', 'mensaje'],
                        'search': ['resultados', 'búsqueda', 'encontrado'],
                        'meet': ['reunión', 'meet', 'creada', 'solicitud'],
                        'image': ['imagen', 'generada', 'creando'],
                        'image_display': ['imágenes', 'archivos', 'encontradas'],
                        'file_manager': ['archivos', 'directorio', 'listado'],
                        # ✅ INDICADORES PARA VISION
                        'vision': ['imagen', 'análisis', 'llama', 'scout', 'vision', 'describe', 'elementos'],
                        # ✅ INDICADORES PARA PLAYWRIGHT
                        'playwright': ['página', 'navegación', 'título', 'información', 'estadísticas', 'enlaces', 'cargada'],
                        # ✅ INDICADORES PARA MULTIMODAL MEMORY REAL
                        'multimodal_memory': ['memoria', 'multimodal', 'texto', 'imagen', 'embedding', 'validación', 'sistema', 'directorio', 'base de datos'],
                        # ✅ INDICADORES PARA OPENAI TTS
                        'openai_tts': ['voz', 'audio', 'texto', 'speech', 'exito'],
                        # ✅ INDICADORES PARA GROQ SPEECH
                        'groq_speech': ['voz', 'audio', 'texto', 'speech', 'exito']
                    }
                    
                    error_indicators = ['error', 'fallo', 'no se pudo', 'failed', 'exception']
                    
                    text_lower = text_content.lower()
                    
                    has_success = any(indicator in text_lower for indicator in success_indicators.get(tool_name, []))
                    has_error = any(indicator in text_lower for indicator in error_indicators)
                    
                    if has_error and not has_success:
                        safe_log(f"   ⚠️ PARTIAL: Ejecutó pero con errores internos")
                        safe_log(f"      📝 Detalle: {text_content[:100]}...")
                        results[tool_name] = {
                            'status': 'partial',
                            'message': 'Ejecutó con errores',
                            'content': text_content[:200]
                        }
                    elif has_success or len(text_content) > 20:
                        safe_log(f"   ✅ SUCCESS: Funcionando correctamente")
                        safe_log(f"      📝 Respuesta: {text_content[:100]}...")
                        results[tool_name] = {
                            'status': 'success',
                            'message': 'Funcionando correctamente',
                            'content': text_content[:200]
                        }
                        passed_tests += 1
                    else:
                        safe_log(f"   ⚠️ UNCERTAIN: Respuesta muy corta")
                        results[tool_name] = {
                            'status': 'uncertain',
                            'message': 'Respuesta incierta',
                            'content': text_content
                        }
                else:
                    safe_log(f"   ❌ EMPTY: Sin contenido en respuesta")
                    results[tool_name] = {
                        'status': 'empty',
                        'message': 'Respuesta vacía'
                    }
            
        except Exception as e:
            safe_log(f"   ❌ EXCEPTION: {str(e)}")
            results[tool_name] = {
                'status': 'exception',
                'error': str(e)
            }
    
    # 📊 GENERAR REPORTE FINAL
    safe_log(f"\n{'='*60}")
    safe_log(f"📊 REPORTE FINAL DE TESTS")
    safe_log(f"{'='*60}")
    
    safe_log(f"🎯 RESUMEN GENERAL:")
    safe_log(f"   • Total herramientas: {total_tests}")
    safe_log(f"   • Tests exitosos: {passed_tests}")
    safe_log(f"   • Porcentaje éxito: {(passed_tests/total_tests)*100:.1f}%")
    
    # Agrupar por status
    by_status = {}
    for tool, result in results.items():
        status = result['status']
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(tool)
    
    safe_log(f"\n📋 DETALLE POR STATUS:")
    
    status_emojis = {
        'success': '✅',
        'partial': '⚠️',
        'error': '❌',
        'exception': '💥',
        'empty': '📭',
        'uncertain': '❓',
        'not_loaded': '🚫'
    }
    
    for status, tools in by_status.items():
        emoji = status_emojis.get(status, '❓')
        safe_log(f"   {emoji} {status.upper()}: {', '.join(tools)}")
    
    safe_log(f"\n{'='*60}")
    
    return passed_tests >= (total_tests * 0.7)  # 70% de éxito mínimo

# ✅ FUNCIÓN MAIN Y PUNTO DE ENTRADA
async def main():
    """Función principal"""
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Modo servidor MCP - SOLO JSON por stdout
        server = CleanMCPServer()
        await server.run_stdio()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # Modo test completo de herramientas
        success = await test_all_tools_comprehensive()
        if success:
            safe_log("🎉 TEST GENERAL: EXITOSO")
            sys.exit(0)
        else:
            safe_log("❌ TEST GENERAL: FALLÓ")
            sys.exit(1)
    else:
        # Modo diagnóstico básico
        safe_log("🧪 Modo diagnóstico básico...")
        
        server = CleanMCPServer()
        server.initialize()
        
        tools = server.get_available_tools()
        
        print("\n" + "="*60)
        print("🔍 DIAGNÓSTICO BÁSICO DEL SERVIDOR MCP")
        print("="*60)
        
        print(f"\n📊 RESUMEN:")
        print(f"   • Adapters cargados: {len(server.adapters)}")
        print(f"   • Herramientas disponibles: {len(tools)}")
        print(f"   • Estado: {'✅ Listo' if server.initialized else '❌ Error'}")
        
        if tools:
            print(f"\n🛠️ HERRAMIENTAS:")
            for i, tool in enumerate(tools, 1):
                name = tool['name']
                desc = tool['description'][:50] + "..." if len(tool['description']) > 50 else tool['description']
                required = tool.get('inputSchema', {}).get('required', [])
                print(f"   {i}. {name}: {desc}")
                if required:
                    print(f"      📋 Parámetros requeridos: {', '.join(required)}")
        
        print(f"\n💡 Para test completo ejecuta:")
        print(f"   python run_server.py test")
        print("="*60)

if __name__ == "__main__":
    """Punto de entrada principal"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        safe_log("🛑 Programa interrumpido por usuario")
        sys.exit(0)
    except Exception as e:
        safe_log(f"❌ Error fatal: {e}")
        sys.exit(1)
