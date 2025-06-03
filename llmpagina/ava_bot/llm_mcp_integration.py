import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from groq import Groq
from mcp_client import MCPClient
import re
from dataclasses import dataclass
from functools import wraps

# Importar los prompts modulares
from role_promt import get_role_prompt
from operational_promt import get_operational_prompt
from tools.adapters.memory_adapter import SQLiteMemoryManager, MemoryAdapter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ DATACLASS PARA CONFIGURACIÓN CENTRALIZADA
@dataclass
class AvaConfig:
    """Configuración centralizada del sistema Ava"""
    # Timeouts por herramienta
    TOOL_TIMEOUTS = {
        'search': 60.0,
        'image': 180.0,
        'gmail': 30.0,
        'calendar': 30.0,
        'meet': 30.0,
        'memory': 10.0,
        'image_display': 10.0,
        'default': 30.0
    }
    
    # Constantes
    EMAIL_PATTERN = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    
    # Modelos LLM
    PRIMARY_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
    DECISION_TEMPERATURE = 0.2
    RESPONSE_TEMPERATURE = 0.4

# ✅ FUNCIONES UTILITARIAS CONSOLIDADAS
class TextUtils:
    """Utilidades para procesamiento de texto"""
    
    @staticmethod
    def extract_email(text: str, conversation_history: List[Dict] = None) -> str:
        """Extrae email del texto o historial"""
        # Buscar en texto actual
        email_matches = re.findall(AvaConfig.EMAIL_PATTERN, text)
        if email_matches:
            return email_matches[0].lower()
        
        # Buscar en historial
        if conversation_history:
            for message in reversed(conversation_history):
                content = message.get('content', '')
                email_matches = re.findall(AvaConfig.EMAIL_PATTERN, content)
                if email_matches:
                    return email_matches[0].lower()
        
        return "email_pendiente"
    
    @staticmethod
    def extract_personal_info(text: str) -> Dict[str, str]:
        """Extrae información personal del texto"""
        text_lower = text.lower()
        info = {}
        
        # Patrones de extracción
        patterns = {
            'name': [r'mi nombre es (.+)', r'soy (.+)', r'me llamo (.+)'],
            'business': [r'mi empresa es (.+)', r'trabajo en (.+)', r'tengo un (.+)'],
            'sector': [r'sector (.+)', r'industria (.+)', r'área de (.+)']
        }
        
        for info_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text_lower)
                if match:
                    info[info_type] = match.group(1).strip()
                    break
        
        return info

class JSONUtils:
    """Utilidades para manejo de JSON"""
    
    @staticmethod
    def extract_tool_request(response: str) -> Optional[Dict]:
        """Extrae solicitud de herramienta del response del LLM"""
        try:
            # Patrones de búsqueda
            patterns = [
                r'\{\s*"use_tool"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^}]*\}\s*\}',
                r'\{\s*"use_tool"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*\}',
                r'\{"use_tool":\s*"([^"]+)"[^}]*\}'
            ]
            
            for i, pattern in enumerate(patterns, 1):
                matches = re.findall(pattern, response, re.DOTALL | re.MULTILINE)
                if matches:
                    json_str = matches[-1] if isinstance(matches[-1], str) else matches[-1][0]
                    try:
                        tool_request = json.loads(json_str)
                        if 'use_tool' in tool_request and 'arguments' in tool_request:
                            return tool_request
                    except json.JSONDecodeError:
                        # Intentar reparación
                        repaired = JSONUtils._repair_json(json_str)
                        if repaired:
                            try:
                                return json.loads(repaired)
                            except:
                                continue
            
            # Búsqueda manual como último recurso
            if '"use_tool"' in response:
                return JSONUtils._manual_extraction(response)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extrayendo tool request: {e}")
            return None
    
    @staticmethod
    def _repair_json(json_str: str) -> Optional[str]:
        """Repara JSON malformado"""
        try:
            repaired = json_str.strip()
            
            # Balancear llaves
            open_braces = repaired.count('{')
            close_braces = repaired.count('}')
            
            if open_braces > close_braces:
                repaired += '}' * (open_braces - close_braces)
            elif close_braces > open_braces:
                for _ in range(close_braces - open_braces):
                    if repaired.endswith('}'):
                        repaired = repaired[:-1]
            
            # Validar reparación
            json.loads(repaired)
            return repaired
            
        except Exception:
            return None
    
    @staticmethod
    def _manual_extraction(response: str) -> Optional[Dict]:
        """Extracción manual de JSON"""
        try:
            positions = []
            start = 0
            while True:
                pos = response.find('"use_tool"', start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            
            for pos in positions:
                json_start = response.rfind('{', 0, pos)
                if json_start == -1:
                    continue
                
                brace_count = 0
                json_end = json_start
                
                for i in range(json_start, len(response)):
                    char = response[i]
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > json_start:
                    json_str = response[json_start:json_end]
                    try:
                        tool_request = json.loads(json_str)
                        if 'use_tool' in tool_request and 'arguments' in tool_request:
                            return tool_request
                    except:
                        repaired = JSONUtils._repair_json(json_str)
                        if repaired:
                            try:
                                return json.loads(repaired)
                            except:
                                continue
            
            return None
            
        except Exception:
            return None

# ✅ DECORADOR PARA MANEJO DE ERRORES
def handle_errors(default_return=None, log_errors=True):
    """Decorador para manejo centralizado de errores"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error en {func.__name__}: {e}")
                return default_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error en {func.__name__}: {e}")
                return default_return
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# ✅ CLASE PRINCIPAL SIMPLIFICADA - SIN HARDCODEO
class LLMWithMCPTools:
    """LLM Groq Llama con herramientas MCP - Sin lógica hardcodeada"""
    
    def __init__(self, groq_api_key: str, mcp_server_path: str):
        self.groq_client = Groq(api_key=groq_api_key)
        self.config = AvaConfig()
        
        if not os.path.exists(mcp_server_path):
            raise FileNotFoundError(f"MCP server not found at: {mcp_server_path}")
        
        self.mcp_client = MCPClient([sys.executable, mcp_server_path, "server"])
        self.available_tools = []
        self.conversation_history = []
        self.current_user_email = None
        self._cached_schemas = {}
        
        # Inicializar memoria
        self._initialize_memory()

    @handle_errors(default_return=None)
    def _initialize_memory(self):
        """Inicializa el sistema de memoria SQLite"""
        try:
            self.memory_adapter = SQLiteMemoryManager()
            logger.info("✅ Sistema de memoria SQLite inicializado")
        except Exception as e:
            logger.warning(f"⚠️ Error inicializando SQLite: {e}")
            self.memory_adapter = None

    @handle_errors(default_return=False)
    async def initialize(self) -> bool:
        """Inicializa el cliente MCP y carga herramientas disponibles"""
        logger.info("🔌 Iniciando servidor MCP...")
        await self.mcp_client.start_server()
        logger.info("✅ Servidor MCP iniciado correctamente")
        
        self.available_tools = await self.mcp_client.list_tools()
        logger.info(f"✅ {len(self.available_tools)} herramientas cargadas")
        
            
        
        self._cached_schemas = await self.get_tool_schemas()
        
        logger.info(f"✅ {len(self.available_tools)} herramientas + schemas cargados")
        
        return True
    
    async def get_tool_schemas(self) -> Dict[str, Any]:
        """Extrae schemas de herramientas del servidor MCP"""
        try:
            schemas = {}
            for tool in self.available_tools:
                tool_name = tool.get('name', 'unknown')
                tool_schema = tool.get('inputSchema', {})
                schemas[tool_name] = tool_schema
            return schemas
        except Exception as e:
            logger.error(f"Error obteniendo schemas: {e}")
            return {}
    def _format_tool_schemas(self) -> str:
        """Formatea schemas para el LLM"""
        if not self._cached_schemas:
            return self._format_available_tools()
        
        formatted = []
        for tool_name, schema in self._cached_schemas.items():
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            formatted.append(f"**{tool_name}**:")
            for prop, details in properties.items():
                req_mark = " (requerido)" if prop in required else ""
                prop_type = details.get('type', 'any')
                desc = details.get('description', 'Sin descripción')
                formatted.append(f"  • {prop} ({prop_type}){req_mark}: {desc}")
        
        return "\n".join(formatted)

    def _process_user_data(self, text: str):
        """Procesa y extrae datos del usuario automáticamente - SIN HARDCODEO"""
        # ✅ EXTRACCIÓN AUTOMÁTICA - NO DECISIONES HARDCODEADAS
        personal_info = TextUtils.extract_personal_info(text)
        if personal_info:
            self._save_personal_info(personal_info)
        
        # ✅ EXTRACCIÓN DE EMAIL - NO DECISIONES
        email_found = TextUtils.extract_email(text, self.conversation_history)
        if email_found != "email_pendiente":
            self._set_user_email(email_found)

    @handle_errors(default_return=False)
    def _save_personal_info(self, info: Dict[str, str]) -> bool:
        """Guarda información personal en memoria"""
        if not self.memory_adapter:
            return False
        
        user_id = self.current_user_email or "unknown_user"
        success = False
        
        for key, value in info.items():
            try:
                self.memory_adapter.add_user_data(user_id, key, value)
                logger.info(f"📊 {key.title()} guardado: {value}")
                success = True
            except AttributeError:
                logger.warning(f"⚠️ Método add_user_data no disponible")
                break
        
        return success

    def _set_user_email(self, email: str):
        """Establece el email del usuario actual"""
        if not self.current_user_email:
            self.current_user_email = email
            self._save_personal_info({'email': email})
            logger.info(f"📧 Email establecido: {email}")

    @handle_errors(default_return="No hay información disponible.")
    async def get_conversation_context(self, user_input: str) -> str:
        """Obtiene contexto de conversaciones previas de forma optimizada"""
        if not self.memory_adapter:
            return "No hay información previa disponible."
        
        user_id = self.current_user_email or "unknown_user"
        context_parts = []
        
        # Métodos de obtención de memoria con fallbacks
        memory_methods = [
            ('get_recent_conversations', lambda: self.memory_adapter.get_recent_conversations(user_id, limit=5)),
            ('get_user_messages', lambda: self.memory_adapter.get_user_messages(user_id, limit=10)),
            ('get_all_data', lambda: self.memory_adapter.get_all_data(user_id))
        ]
        
        for method_name, method_call in memory_methods:
            if hasattr(self.memory_adapter, method_name):
                try:
                    data = method_call()
                    if data:
                        context_parts.append(f"INFORMACIÓN DISPONIBLE ({method_name}):")
                        context_parts.append(str(data)[:500] + "..." if len(str(data)) > 500 else str(data))
                        break
                except Exception as e:
                    logger.debug(f"Error con {method_name}: {e}")
                    continue
        
        return "\n".join(context_parts) if context_parts else "No hay información previa específica."

    @handle_errors(default_return="Error procesando solicitud")
    async def process_user_input(self, user_input: str) -> str:
        """✅ PROCESADOR PRINCIPAL - SOLO LLM DECIDE, SIN HARDCODEO"""
        logger.info(f"👤 Usuario: {user_input}")
        
        # ✅ AÑADIR A MEMORIA LOCAL - NO LÓGICA DE NEGOCIO
        self.conversation_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        # ✅ PROCESAR DATOS BÁSICOS - SIN DECISIONES DE COMPORTAMIENTO
        self._process_user_data(user_input)
        
        # ✅ OBTENER CONTEXTO - NO DECISIONES
        memory_context = await self.get_conversation_context(user_input)
        
        # ✅ EL LLM DECIDE TODO - CERO HARDCODEO
        final_response = await self._generate_llm_response(user_input, memory_context)
        
        # ✅ GUARDAR RESPUESTA - NO LÓGICA DE NEGOCIO
        self._save_conversation(user_input, final_response)
        
        return final_response

    async def _generate_llm_response(self, user_input: str, memory_context: str) -> str:
        """✅ GENERACIÓN DE RESPUESTA CON DEBUG DETALLADO"""
        try:
            print("🔍 DEBUG: Paso 1 - Iniciando _generate_llm_response")
            
            # STEP 1: Role prompt
            print("🔍 DEBUG: Paso 2 - Obteniendo role_prompt...")
            role_prompt = get_role_prompt()
            print("✅ role_prompt obtenido")
            
            # STEP 2: Tools
            print("🔍 DEBUG: Paso 3 - Formateando tools...")
            tools_formatted = self._format_tool_schemas()
            print("✅ tools_formatted obtenido")
            
            # STEP 3: Fecha ULTRA SEGURA
            print("🔍 DEBUG: Paso 4 - Construyendo fecha...")
            now = datetime.now()
            date_part = now.strftime("%Y-%m-%d")
            day_part = now.strftime("%A")  
            time_part = now.strftime("%H:%M:%S")
            
            current_date_context = "📅 FECHA ACTUAL: " + date_part + " (" + day_part + ")\n"
            current_date_context += "⏰ HORA ACTUAL: " + time_part + "\n\n"
            print("✅ current_date_context construido")
            
            # STEP 4: Operational prompt
            print("🔍 DEBUG: Paso 5 - Obteniendo operational_prompt...")
            operational_prompt = get_operational_prompt(tools_formatted, self.current_user_email)
            print("✅ operational_prompt obtenido")
            
            # STEP 5: System prompt
            print("🔍 DEBUG: Paso 6 - Construyendo system_prompt...")
            system_prompt = self._build_pure_llm_system_prompt(role_prompt, operational_prompt, memory_context, user_input, current_date_context)
            print("✅ system_prompt construido")
            
            # STEP 6: Messages
            print("🔍 DEBUG: Paso 7 - Construyendo messages...")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            print("✅ messages construidos")
            
            # STEP 7: LLM Call
            print("🔍 DEBUG: Paso 8 - Llamando al LLM...")
            response = self.groq_client.chat.completions.create(
                messages=messages,
                model=self.config.PRIMARY_MODEL,
                temperature=self.config.DECISION_TEMPERATURE,
                max_tokens=1500
            )
            print("✅ LLM respondió")
            
            llm_response = response.choices[0].message.content
            
            # STEP 8: Tool extraction
            print("🔍 DEBUG: Paso 9 - Extrayendo tool request...")
            tool_request = JSONUtils.extract_tool_request(llm_response)
            print("✅ tool request extraído")
            
            if tool_request:
                print("🔍 DEBUG: Paso 10 - Ejecutando herramienta...")
                return await self._execute_tool_and_respond(user_input, tool_request, memory_context)
            
            print("🔍 DEBUG: Paso 11 - Retornando respuesta directa")
            return llm_response
            
        except Exception as e:
            print("💥 ERROR EN _generate_llm_response:")
            print("❌ Error: " + str(e))
            print("❌ Tipo: " + str(type(e)))
            import traceback
            traceback.print_exc()
            return "Error procesando: " + str(e)

    def _build_pure_llm_system_prompt(self, role_prompt: str, operational_prompt: str, memory_context: str, user_input: str, current_date_context: str) -> str:
        """✅ CONSTRUYE SYSTEM PROMPT - ORDEN CORRECTO"""
        return f"""{role_prompt}

{operational_prompt}

INFORMACIÓN PREVIA DEL USUARIO:
{memory_context}

{current_date_context}

CONVERSACIÓN ACTUAL:
{self._format_conversation_history()}

Analiza la solicitud del usuario: "{user_input}"
"""

    @handle_errors(default_return="Error ejecutando herramienta")
    async def _execute_tool_and_respond(self, user_input: str, tool_request: dict, memory_context: str) -> str:
        """✅ EJECUTA HERRAMIENTA Y RESPONDE - SIN LÓGICA HARDCODEADA"""
        tool_name = tool_request['use_tool']
        arguments = tool_request['arguments']
        
        logger.info(f"🎯 Ejecutando herramienta: {tool_name}")
        
        # ✅ EJECUTAR HERRAMIENTA REAL
        tool_result = await self.execute_tool(tool_name, arguments)
        
        if tool_result is not None:
            # ✅ PROCESAR RESULTADO CON LLM - SIN DECISIONES HARDCODEADAS
            return await self._generate_autonomous_response(user_input, tool_request, tool_result, memory_context)
        
        return "La herramienta se ejecutó pero no devolvió un resultado válido."

    async def execute_tool(self, tool_name: str, arguments: Dict) -> Any:
        """✅ EJECUTA HERRAMIENTA MCP - CON DEBUG COMPLETO"""
        if not self.mcp_client:
            return {"error": "MCP client no disponible", "tool": tool_name, "status": "failed"}
        
        try:
            timeout = self.config.TOOL_TIMEOUTS.get(tool_name, self.config.TOOL_TIMEOUTS['default'])
            
            # ✅ MOSTRAR QUÉ SE ENVÍA AL MCP
            print(f"\n🎯 EJECUTANDO HERRAMIENTA: {tool_name}")
            print(f"📤 ARGUMENTOS: {json.dumps(arguments, indent=2, ensure_ascii=False)}")
            
            result = await asyncio.wait_for(
                self.mcp_client.call_tool(tool_name, arguments),
                timeout=timeout
            )
            
            # ✅ MOSTRAR RESULTADO CRUDO DEL MCP
            print(f"\n📥 RESULTADO MCP:")
            print(f"{'='*50}")
            print(f"{json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)}")
            print(f"{'='*50}")
            
            logger.info(f"✅ {tool_name} completado")
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout ejecutando {tool_name} ({timeout}s)"
            logger.error(error_msg)
            return {"error": error_msg, "tool": tool_name, "status": "timeout"}
        except Exception as e:
            error_msg = f"Error ejecutando {tool_name}: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "tool": tool_name, "status": "failed", "exception": str(e)}

    async def _generate_autonomous_response(self, user_input: str, tool_request: dict, tool_result: dict, memory_context: str, first_llm_response: str = "") -> str:
        """✅ SEGUNDA LLAMADA AL LLM - PROCESAR RESULTADO SIN HARDCODEO"""
        try:
            role_prompt = get_role_prompt()
           
            # ✅ SYSTEM PROMPT PARA ANÁLISIS DE RESULTADO - SIN LÓGICA PREDEFINIDA
            analysis_system_prompt = f"""{role_prompt}



🔄 **SEGUNDA LLAMADA - PROCESA RESULTADO:**

**CONTEXTO:**
- Usuario pidió: "{user_input}"
- Herramienta ejecutada: {tool_request.get('use_tool', 'desconocida')}
- Argumentos enviados: {tool_request.get('arguments', {})}

**PRIMERA RESPUESTA DEL LLM:**
{first_llm_response}

**RESULTADO REAL OBTENIDO:**
{str(tool_result)}



**INFORMACIÓN PREVIA DEL USUARIO:**
{memory_context}

✨ **RESPONDE COMO AVA - NATURAL Y ÚTIL**"""

            messages = [
                {"role": "system", "content": analysis_system_prompt},
                {"role": "user", "content": f"Analiza y responde sobre el resultado de la herramienta para: '{user_input}'"}
            ]
            
            response = self.groq_client.chat.completions.create(
                messages=messages,
                model=self.config.PRIMARY_MODEL,
                temperature=self.config.RESPONSE_TEMPERATURE,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error en segunda llamada al LLM: {e}")
            return f"Completé la operación. Resultado: {str(tool_result)}"

    # ✅ MÉTODOS UTILITARIOS - SIN LÓGICA DE NEGOCIO
    def _format_available_tools(self) -> str:
        """Formatea herramientas disponibles"""
        if not self.available_tools:
            return "No hay herramientas MCP disponibles"
        
        return "\n".join(f"• {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')}" 
                        for tool in self.available_tools)

    def _format_conversation_history(self) -> str:
        """Formatea historial de conversación"""
        if not self.conversation_history:
            return "No hay historial de conversación"
        
        return "\n".join(f"{msg.get('role', 'unknown').upper()}: {msg.get('content', '')}" 
                        for msg in self.conversation_history[-5:])

    def _save_conversation(self, user_input: str, response: str):
        """Guarda conversación en memoria - SIN LÓGICA DE NEGOCIO"""
        self.conversation_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        if self.memory_adapter:
            try:
                # Intentar múltiples métodos de guardado
                save_methods = [
                    lambda: self.memory_adapter.add_conversation(
                        self.current_user_email or "unknown_user", user_input, response),
                    lambda: self.memory_adapter.add_message(
                        self.current_user_email or "unknown_user", user_input, "conversation")
                ]
                
                for method in save_methods:
                    try:
                        method()
                        print(f"💬 Mensaje agregado a SQLite para {self.current_user_email or 'unknown_user'}")
                        logger.info("✅ Conversación guardada en memoria")
                        break
                    except AttributeError:
                        continue
            except Exception as e:
                logger.warning(f"⚠️ Error guardando conversación: {e}")

    async def cleanup(self):
        """Limpieza de recursos"""
        try:
            if self.mcp_client:
                await self.mcp_client.cleanup()
                logger.info("🧹 Cliente MCP limpiado")
        except Exception as e:
            logger.warning(f"⚠️ Error en cleanup: {e}")

# ✅ FUNCIÓN MAIN SIN CAMBIOS
async def main():
    """Función principal optimizada"""
    print("\n🎯 INICIANDO SISTEMA AVA...")
    print("-" * 40)
    
    # Configuración inicial
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("❌ Error: GROQ_API_KEY no encontrada")
        print("💡 Para configurar: set GROQ_API_KEY=tu_clave_aqui")
        return
    
    mcp_server_path = os.path.join(os.path.dirname(__file__), "mcp_server", "run_server.py")
    
    # Inicializar sistema
    llm = None
    try:
        llm = LLMWithMCPTools(groq_api_key, mcp_server_path)
        mcp_initialized = await llm.initialize()
        
        # Mostrar estado del sistema - SIN F-STRINGS PROBLEMÁTICOS
        print("\n" + "="*50)
        print("🎯 SISTEMA AVA INICIALIZADO")
        print("="*50)
        
        # ✅ CONCATENACIÓN SEGURA
        tools_count = str(len(llm.available_tools))
        tools_status = '✅' if mcp_initialized else '❌'
        memory_status = '✅' if llm.memory_adapter else '❌'
        
        print("📊 Herramientas MCP: " + tools_count + " " + tools_status)
        print("💾 Memoria SQLite: " + memory_status)
        
        # Loop principal de conversación
        await conversation_loop(llm, mcp_initialized)
        
    except Exception as e:
        logger.error("❌ ERROR FATAL: " + str(e))
    finally:
        if llm:
            await llm.cleanup()

async def conversation_loop(llm: LLMWithMCPTools, mcp_initialized: bool):
    """Loop principal de conversación optimizada"""
    print("\n💬 ¡Empecemos a conversar! Escribe tu mensaje:")
    
    while True:
        try:
            user_input = input("\n💬 Tú: ").strip()
            
            # Comandos de salida
            if user_input.lower() in ['quit', 'exit', 'salir', 'bye', 'adiós']:
                print("\n👋 ¡Hasta luego!")
                break
            
            if not user_input:
                print("💭 Escribe algo para continuar...")
                continue
            
            # Comandos especiales
            if await handle_special_commands(user_input, llm, mcp_initialized):
                continue
            
            # Procesar entrada normal
            print("🔄 Ava está procesando...")
            response = await llm.process_user_input(user_input)
            # ✅ CONCATENACIÓN SEGURA
            print("\n🤖 Ava: " + str(response))
            
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            # ✅ CONCATENACIÓN SEGURA
            print("\n❌ Error: " + str(e))

async def handle_special_commands(user_input: str, llm: LLMWithMCPTools, mcp_initialized: bool) -> bool:
    """Maneja comandos especiales de forma optimizada"""
    command = user_input.lower()
    
    command_handlers = {
        'debug': lambda: print_debug_info(llm, mcp_initialized),
        'tools': lambda: print_tools_info(llm, mcp_initialized),
        'help': lambda: print_help_info(mcp_initialized),
        'clear': lambda: clear_session(llm),
        'test': lambda: asyncio.create_task(test_system(llm, mcp_initialized))
    }
    
    if command in command_handlers:
        handler = command_handlers[command]
        if asyncio.iscoroutine(handler()):
            await handler()
        else:
            handler()
        return True
    
    return False

def print_debug_info(llm: LLMWithMCPTools, mcp_initialized: bool):
    """Imprime información de debug"""
    # ✅ REEMPLAZAR F-STRING PROBLEMÁTICO
    tools_status = '✅' if mcp_initialized else '❌'
    memory_status = '✅' if llm.memory_adapter else '❌'
    current_user = llm.current_user_email or 'No identificado'
    
    print("\n🔍 ESTADO DEL SISTEMA:")
    print("  • Herramientas MCP: " + str(len(llm.available_tools)) + " " + tools_status)
    print("  • Usuario actual: " + current_user)
    print("  • Memoria SQLite: " + memory_status)

def print_tools_info(llm: LLMWithMCPTools, mcp_initialized: bool):
    """Imprime información de herramientas"""
    print("\n🛠️ HERRAMIENTAS DISPONIBLES:")
    if mcp_initialized and llm.available_tools:
        for i, tool in enumerate(llm.available_tools, 1):
            tool_name = tool.get('name', 'Sin nombre')
            tool_desc = tool.get('description', 'Sin descripción')
            # ✅ CONCATENACIÓN SEGURA
            print("  " + str(i) + ". ✅ " + tool_name + ": " + tool_desc)
    else:
        print("  ❌ No hay herramientas MCP disponibles")

def print_help_info(mcp_initialized: bool):
    """Imprime información de ayuda"""
    print("\n❓ COMANDOS DISPONIBLES:")
    print("  🔧 debug - Estado del sistema")
    print("  🛠️ tools - Listar herramientas")
    print("  🧹 clear - Limpiar historial")
    print("  👋 quit - Salir")

def clear_session(llm: LLMWithMCPTools):
    """Limpia la sesión actual"""
    llm.conversation_history = []
    llm.current_user_email = None
    print("\n🧹 ✅ Sesión limpiada")

async def test_system(llm: LLMWithMCPTools, mcp_initialized: bool):
    """Prueba el sistema"""
    print("\n🧪 PROBANDO SISTEMA...")
    test_message = "Hola, háblame sobre ti" if mcp_initialized else "Hola, soy usuario de prueba"
    response = await llm.process_user_input(test_message)
    print("📊 Resultado: " + str(response))

# ✅ PUNTO DE ENTRADA PRINCIPAL
if __name__ == "__main__":
    """Punto de entrada principal optimizado"""
    print("🎭 SISTEMA AVA - AGENTE VIRTUAL AVANZADO")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Programa terminado por el usuario.")
    except Exception as e:
        logger.error("ERROR FATAL: " + str(e))
        print("\n❌ Error fatal: " + str(e))
    finally:
        print("\n🔚 Sistema AVA finalizado.")
