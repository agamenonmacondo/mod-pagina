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
from tools.adapters.multimodal_memory_adapter import MultimodalMemoryAdapter

# Setup logging - COMPLETAMENTE SILENCIOSO
logging.basicConfig(
    level=logging.CRITICAL,  # Solo errores críticos
    format='',  # Sin formato
    handlers=[logging.NullHandler()]  # Handler nulo
)
logger = logging.getLogger(__name__)
logger.disabled = True  # ✅ DESHABILITAR COMPLETAMENTE

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
        'playwright': 20.0,
        'multimodal_memory': 10.0,
        'vision': 30.0,
        'default': 30.0
    }
    
    # ✅ MARCADOR ÚNICO DE FIN DE RESPUESTA
    RESPONSE_END_MARKER = "🔚 AVA_RESPONSE_END"
    
    # Constantes existentes
    EMAIL_PATTERN = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    PRIMARY_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
    DECISION_TEMPERATURE = 0.2
    RESPONSE_TEMPERATURE = 0.4
    
    # ✅ NUEVAS CONFIGURACIONES DE MEMORIA
    MULTIMODAL_MEMORY_ENABLED = True
    FAST_MODE = True
    MAX_MEMORY_SEARCH_TIME = 2.0

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
        """Extrae solicitud de herramienta del response del LLM - MEJORADO"""
        try:
            # ✅ DETECTAR MÚLTIPLES FORMATOS JSON
            patterns = [
                # Formato original esperado
                r'\{\s*"use_tool"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^}]*\}\s*\}',
                # ✅ NUEVO: Formato que está generando el LLM
                r'\{\s*"type"\s*:\s*"function"\s*,\s*"name"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:\s*\{[^}]*\}\s*\}',
                # Variantes adicionales
                r'\{\s*"function"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^}]*\}\s*\}',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response, re.DOTALL)
                if matches:
                    json_str = matches[-1]
                    try:
                        parsed_json = json.loads(json_str)
                        
                        # ✅ CONVERTIR FORMATO "type/name/parameters" AL FORMATO ESPERADO
                        if "type" in parsed_json and "name" in parsed_json and "parameters" in parsed_json:
                            if parsed_json["type"] == "function":
                                return {
                                    "use_tool": parsed_json["name"],
                                    "arguments": parsed_json["parameters"]
                                }
                        
                        # Formato original
                        if 'use_tool' in parsed_json and 'arguments' in parsed_json:
                            return parsed_json
                            
                    except json.JSONDecodeError:
                        # Intentar reparación
                        repaired = JSONUtils._repair_json(json_str)
                        if repaired:
                            try:
                                parsed_repaired = json.loads(repaired)
                                # Aplicar misma conversión al JSON reparado
                                if "type" in parsed_repaired and parsed_repaired["type"] == "function":
                                    return {
                                        "use_tool": parsed_repaired["name"],
                                        "arguments": parsed_repaired["parameters"]
                                    }
                                return parsed_repaired
                            except:
                                continue
            
            # Búsqueda manual como último recurso
            if '"use_tool"' in response or '"name"' in response:
                return JSONUtils._manual_extraction_enhanced(response)
            
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
    
    @staticmethod 
    def _manual_extraction_enhanced(response: str) -> Optional[Dict]:
        """Extracción manual mejorada para múltiples formatos"""
        try:
            # ✅ BUSCAR AMBOS FORMATOS
            patterns_to_find = [
                (r'"use_tool"\s*:\s*"([^"]+)"', r'"arguments"\s*:\s*(\{[^}]*\})'),
                (r'"name"\s*:\s*"([^"]+)"', r'"parameters"\s*:\s*(\{[^}]*\})'),  # ← NUEVO
                (r'"function"\s*:\s*"([^"]+)"', r'"arguments"\s*:\s*(\{[^}]*\})')
            ]
            
            for tool_pattern, args_pattern in patterns_to_find:
                tool_match = re.search(tool_pattern, response)
                args_match = re.search(args_pattern, response)
                
                if tool_match and args_match:
                    tool_name = tool_match.group(1)
                    args_str = args_match.group(1)
                    
                    try:
                        arguments = json.loads(args_str)
                        return {
                            "use_tool": tool_name,
                            "arguments": arguments
                        }
                    except json.JSONDecodeError:
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
    """LLM Groq Llama con herramientas MCP + MEMORIA MULTIMODAL AUTOMÁTICA"""
    
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
        
        # ✅ INICIALIZAR AMBOS SISTEMAS DE MEMORIA
        self._initialize_memory()
        self._initialize_multimodal_memory()

    @handle_errors(default_return=None)
    def _initialize_memory(self):
        """Inicializa el sistema de memoria SQLite"""
        try:
            self.memory_adapter = SQLiteMemoryManager()
            logger.info("✅ Sistema de memoria SQLite inicializado")
        except Exception as e:
            logger.warning(f"⚠️ Error inicializando SQLite: {e}")
            self.memory_adapter = None

    @handle_errors(default_return=None)
    def _initialize_multimodal_memory(self):
        """Inicializa el sistema de memoria multimodal"""
        try:
            self.multimodal_memory = MultimodalMemoryAdapter()
            logger.info("✅ Sistema de memoria multimodal inicializado")
            logger.info(f"📁 Base path: {self.multimodal_memory.base_path}")
        except Exception as e:
            logger.warning(f"⚠️ Error inicializando memoria multimodal: {e}")
            self.multimodal_memory = None

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

    def _format_available_tools(self) -> str:
        """Formatea lista de herramientas disponibles"""
        if not self.available_tools:
            return "No hay herramientas disponibles"
        
        formatted = []
        for tool in self.available_tools:
            name = tool.get('name', 'Unknown')
            description = tool.get('description', 'Sin descripción')
            formatted.append(f"• {name}: {description}")
        
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
        """
        ✅ INYECCIÓN OPTIMIZADA: Solo buscar memoria multimodal cuando sea necesario
        """
        context_parts = []
        user_id = self.current_user_email or "unknown_user"
        
        # ✅ 1. HISTORIAL LOCAL (siempre rápido)
        if self.conversation_history:
            context_parts.append("💬 CONVERSACIÓN ACTUAL:")
            for msg in self.conversation_history[-4:]:  # Reducido de 6 a 4
                role = "USUARIO" if msg.get('role') == 'user' else "AVA"
                content = msg.get('content', '')
                if len(content) > 80:  # Reducido de 100 a 80
                    content = content[:80] + "..."
                context_parts.append(f"{role}: {content}")

        # ✅ 2. MEMORIA MULTIMODAL SOLO SI ES NECESARIA
        if self._should_use_multimodal_memory(user_input):
            if self.multimodal_memory:
                multimodal_context = await self._get_multimodal_memory_context_fast(user_input, user_id)
                if multimodal_context:
                    context_parts.append(f"\n🧠 MEMORIA RELEVANTE:\n{multimodal_context}")
        
        # ✅ 3. MEMORIA TRADICIONAL como fallback rápido
        else:
            if self.memory_adapter:
                traditional_context = self._get_traditional_memory_context_sync(user_id)
                if traditional_context:
                    context_parts.append(f"\n📊 INFO BÁSICA:\n{traditional_context}")
        
        return "\n".join(context_parts) if context_parts else ""

    def _should_use_multimodal_memory(self, user_input: str) -> bool:
        """Decide si usar memoria multimodal basado en el input"""
        user_input_lower = user_input.lower()
        
        # ✅ USAR memoria multimodal SOLO para estos casos:
        multimodal_triggers = [
            # Búsquedas específicas
            r'\b(busca|encuentra|recuerda|qué.*imagen|foto.*anterior)\b',
            # Referencias a conversaciones pasadas
            r'\b(antes|anterior|ya.*hablamos|mencioné|dijiste)\b',
            # Información personal específica
            r'\b(mi.*apartamento|mi.*empresa|mis.*datos|mi.*perfil)\b',
            # Comparaciones o referencias
            r'\b(igual|similar|como.*antes|parecido)\b'
        ]
        
        for trigger in multimodal_triggers:
            if re.search(trigger, user_input_lower):
                return True
        
        return False

    def _get_traditional_memory_context_sync(self, user_id: str) -> str:
        """Obtiene contexto tradicional de forma síncrona y rápida"""
        if not self.memory_adapter:
            return ""
        
        try:
            # Método más rápido y simple
            if hasattr(self.memory_adapter, 'get_user_summary'):
                summary = self.memory_adapter.get_user_summary(user_id)
                return summary[:200] + "..." if len(str(summary)) > 200 else str(summary)
        except Exception:
            pass
        
        return ""

    async def _get_multimodal_memory_context_fast(self, user_input: str, user_id: str) -> str:
        """Versión rápida de búsqueda multimodal con límites reducidos"""
        try:
            context_parts = []
            
            # ✅ BÚSQUEDA LIMITADA Y RÁPIDA
            semantic_results = await self.multimodal_memory.search_semantic_memories(
                query=user_input,
                user_id=user_id,
                modalities=["text"],
                limit=2  # Reducido de 5 a 2
            )
            
            if semantic_results:
                context_parts.append("📝 RELEVANTE:")
                for i, result in enumerate(semantic_results[:2], 1):  # Solo 2 resultados
                    content = result.get('content', '')
                    if len(content) > 100:
                        content = content[:100] + "..."
                    context_parts.append(f"{i}. {content}")
            
            return "\n".join(context_parts) if context_parts else ""
            
        except Exception as e:
            logger.error(f"Error memoria rápida: {e}")
            return ""

    async def _extract_and_store_multimodal_memory(self, user_input: str, response: str) -> bool:
        """✅ GUARDADO MULTIMODAL SIMPLIFICADO - SIN DUPLICACIÓN"""
        if not self.multimodal_memory:
            return False
        
        try:
            user_id = self.current_user_email or "unknown_user"
            session_id = f"auto_session_{datetime.now().strftime('%Y%m%d_%H%M')}"
            
            # Combinar contenido
            combined_content = f"USUARIO: {user_input}\nAVA: {response}"
            
            # Guardar directamente (sin verificar should_store aquí, ya se verificó antes)
            conversation_id = await self.multimodal_memory.store_text_memory(
                user_id=user_id,
                content=combined_content,
                session_id=session_id
            )
            
            logger.info(f"🧠 Memoria multimodal guardada (ID: {conversation_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando memoria multimodal: {e}")
            return False

    async def _should_store_in_multimodal_memory(self, user_input: str, response: str) -> bool:
        """
        ✅ CRITERIOS MÁS SELECTIVOS: Solo guardar en momentos REALMENTE importantes
        """
        # Combinar texto para análisis
        combined_text = f"{user_input} {response}".lower()
        
        # ✅ CRITERIOS REDUCIDOS - SOLO INFORMACIÓN CRÍTICA
        critical_patterns = [
            # Solo información personal/empresarial NUEVA
            r'\b(mi nombre es|me llamo|soy|email|correo|teléfono)\b',
            r'\b(mi empresa es|trabajo en|mi negocio)\b',
            
            # Solo decisiones importantes o resultados de herramientas EXITOSOS
            r'\b(he encontrado|encontré.*resultados|reserva.*confirmada)\b',
            r'\b(aquí tienes.*resultados|datos.*obtenidos)\b',
            
            # Solo información específica de dominio con datos reales
            r'\b(apartamento.*melgar.*\$\d+|presupuesto.*\d+.*cop)\b',
            r'\b(\d{1,2}/\d{1,2}/\d{4}.*confirmado|\d+.*personas.*reservado)\b'
        ]
        
        # ✅ EXCLUIR conversaciones casuales, errores y respuestas genéricas
        exclude_patterns = [
            r'\b(hola|gracias|ok|bien|perfecto|entiendo|encantada)\b',
            r'\b(error|problema|timeout|no pudo|lo siento|hubo.*problema)\b',
            r'\b(cómo estás|qué tal|saludos|te gustaría|puedo ayudarte)\b',
            r'\b(no te preocupes|otra manera|paso a paso|recomendaciones)\b'
        ]
        
        # Verificar exclusiones primero
        for exclude_pattern in exclude_patterns:
            if re.search(exclude_pattern, combined_text):
                return False
        
        # ✅ SOLO GUARDAR si contiene información crítica
        for pattern in critical_patterns:
            if re.search(pattern, combined_text):
                return True
        
        # ✅ NO GUARDAR conversaciones cortas, casuales o sin resultados concretos
        if len(user_input) < 30 and len(response) < 200:
            return False
        
        # ✅ NO GUARDAR si la respuesta contiene frases genéricas
        generic_phrases = [
            'puedo ayudarte', 'te gustaría', 'qué te parece', 'empezamos por',
            'algunas recomendaciones', 'paso a paso', 'no te preocupes'
        ]
        
        for phrase in generic_phrases:
            if phrase in response.lower():
                return False
                
        return False  # Por defecto NO guardar

    def _save_conversation_simple(self, user_input: str, response: str):
        """Guarda conversación SOLO en historial local + SQLite básico"""
        # Historial local
        self.conversation_history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # SQLite básico si está disponible
        if self.memory_adapter:
            try:
                user_id = self.current_user_email or "unknown_user"
                if hasattr(self.memory_adapter, 'add_conversation'):
                    self.memory_adapter.add_conversation(user_id, user_input, response)
                print(f"💬 Mensaje agregado a SQLite para {user_id}")
            except Exception:
                pass

    @handle_errors(default_return="Error procesando solicitud")
    async def process_user_input(self, user_input: str) -> str:
        """✅ PROCESADOR PRINCIPAL CON MEMORIA SELECTIVA"""
        # ✅ AÑADIR A MEMORIA LOCAL
        self.conversation_history.append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        # ✅ PROCESAR DATOS BÁSICOS
        self._process_user_data(user_input)
        
        # ✅ OBTENER CONTEXTO (más rápido)
        memory_context = await self.get_conversation_context(user_input)
        
        # ✅ GENERAR RESPUESTA
        final_response = await self._generate_llm_response(user_input, memory_context)
        
        # ✅ GUARDAR EN SQLITE (siempre, es rápido)
        self._save_conversation_simple(user_input, final_response)
        
        # ✅ MEMORIA MULTIMODAL SOLO SI ES IMPORTANTE
        should_store_multimodal = await self._should_store_in_multimodal_memory(user_input, final_response)
        if should_store_multimodal:
            await self._extract_and_store_multimodal_memory(user_input, final_response)
            print("🧠 Guardado en memoria multimodal")
        
        return final_response

    @handle_errors(default_return="Error generando respuesta")
    async def _generate_llm_response(self, user_input: str, memory_context: str) -> str:
        """✅ GENERACIÓN DE RESPUESTA SILENCIOSA - SOLO RESULTADO FINAL"""
        try:
            # STEP 1: Role prompt
            role_prompt = get_role_prompt()
            
            # STEP 2: Tools
            tools_formatted = self._format_tool_schemas()
            
            # STEP 3: Fecha
            now = datetime.now()
            date_part = now.strftime("%Y-%m-%d")
            day_part = now.strftime("%A")  
            time_part = now.strftime("%H:%M:%S")
            
            current_date_context = "📅 FECHA ACTUAL: " + date_part + " (" + day_part + ")\n"
            current_date_context += "⏰ HORA ACTUAL: " + time_part + "\n\n"
            
            # STEP 4: Operational prompt
            operational_prompt = get_operational_prompt(tools_formatted, self.current_user_email)
            
            # STEP 5: System prompt
            system_prompt = self._build_pure_llm_system_prompt(role_prompt, operational_prompt, memory_context, user_input, current_date_context)
            
            # STEP 6: Messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            # STEP 7: PRIMERA LLAMADA AL LLM - SILENCIOSA
            response = self.groq_client.chat.completions.create(
                messages=messages,
                model=self.config.PRIMARY_MODEL,
                temperature=self.config.DECISION_TEMPERATURE,
                max_tokens=1500
            )
            
            first_llm_response = response.choices[0].message.content
            
            # STEP 8: Tool extraction - SILENCIOSO
            tool_request = JSONUtils.extract_tool_request(first_llm_response)
            
            if tool_request:
                return await self._execute_tool_and_respond(user_input, tool_request, memory_context, first_llm_response)
            
            return first_llm_response
        
        except Exception as e:
            return "Error procesando tu solicitud. Intenta nuevamente."

    def _build_pure_llm_system_prompt(self, role_prompt: str, operational_prompt: str, memory_context: str, user_input: str, current_date_context: str) -> str:
        """✅ CONSTRUYE SYSTEM PROMPT - ORDEN CORRECTO"""
        return f"""{role_prompt}

{operational_prompt}

**INFORMACIÓN PREVIA DEL USUARIO (YA DISPONIBLE):**
{memory_context}

**IMPORTANTE:** Esta información YA está disponible. NO uses herramientas de memoria para buscarla nuevamente.

{current_date_context}

CONVERSACIÓN ACTUAL:
{self._format_conversation_history()}

Analiza la solicitud del usuario: "{user_input}"

**DECISIÓN:** ¿Necesitas una ACCIÓN específica (análisis, búsqueda web, envío) o puedes responder con la información disponible?"""

    def _format_conversation_history(self) -> str:
        """Formatea historial de conversación"""
        if not self.conversation_history:
            return "No hay historial de conversación"
        
        return "\n".join(f"{msg.get('role', 'unknown').upper()}: {msg.get('content', '')}" 
                        for msg in self.conversation_history[-5:])

    async def _execute_tool_and_respond(self, user_input: str, tool_request: dict, memory_context: str, first_llm_response: str = "") -> str:
        """✅ EJECUTA HERRAMIENTA Y RESPONDE - SILENCIOSO"""
        tool_name = tool_request['use_tool']
        arguments = tool_request['arguments']
        
        # ✅ EJECUTAR HERRAMIENTA REAL - SIN PRINTS
        tool_result = await self.execute_tool(tool_name, arguments)
        
        if tool_result is not None:
            # ✅ SEGUNDA LLAMADA AL LLM - PROCESAR RESULTADO
            return await self._generate_autonomous_response(user_input, tool_request, tool_result, memory_context, first_llm_response)
        
        return "La herramienta se ejecutó pero no devolvió un resultado válido."

    async def execute_tool(self, tool_name: str, arguments: Dict) -> Any:
        """✅ EJECUTA HERRAMIENTA MCP - COMPLETAMENTE SILENCIOSO"""
        if not self.mcp_client:
            return {"error": "MCP client no disponible", "tool": tool_name, "status": "failed"}
        
        try:
            timeout = self.config.TOOL_TIMEOUTS.get(tool_name, self.config.TOOL_TIMEOUTS['default'])
            
            result = await asyncio.wait_for(
                self.mcp_client.call_tool(tool_name, arguments),
                timeout=timeout
            )
            
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Timeout ejecutando {tool_name} ({timeout}s)"
            return {"error": error_msg, "tool": tool_name, "status": "timeout"}
        except Exception as e:
            error_msg = f"Error ejecutando {tool_name}: {str(e)}"
            return {"error": error_msg, "tool": tool_name, "status": "failed", "exception": str(e)}

    async def _generate_autonomous_response(self, user_input: str, tool_request: dict, tool_result: dict, memory_context: str, first_llm_response: str = "") -> str:
        """✅ SEGUNDA LLAMADA AL LLM - SILENCIOSA"""
        try:
            role_prompt = get_role_prompt()
           
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

✨ **RESPONDE COMO AVA - NATURAL Y ÚTIL**

Por favor, interpreta este resultado y proporciona una respuesta final clara y útil al usuario en español. NO muestres código JSON al usuario."""

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
            return f"Completé la operación. Resultado: {str(tool_result)}"

    async def cleanup(self):
        """Limpieza de recursos"""
        try:
            if self.mcp_client:
                await self.mcp_client.cleanup()
                logger.info("🧹 Cliente MCP limpiado")
        except Exception as e:
            logger.warning(f"⚠️ Error en cleanup: {e}")

# ✅ FUNCIÓN MAIN RESTAURADA
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
        multimodal_status = '✅' if llm.multimodal_memory else '❌'
        
        print("📊 Herramientas MCP: " + tools_count + " " + tools_status)
        print("💾 Memoria SQLite: " + memory_status)
        print("🧠 Memoria Multimodal: " + multimodal_status)
        
        # Loop principal de conversación CON MARCADOR
        await conversation_loop_with_marker(llm, mcp_initialized)
        
    except Exception as e:
        logger.error("❌ ERROR FATAL: " + str(e))
    finally:
        if llm:
            await llm.cleanup()

# ✅ LOOP DE CONVERSACIÓN CON MARCADOR
async def conversation_loop_with_marker(llm: LLMWithMCPTools, mcp_initialized: bool):
    """Loop principal de conversación optimizada CON MARCADOR DE FIN"""
    print("\n💬 ¡Empecemos a conversar! Escribe tu mensaje:")
    
    while True:
        try:
            user_input = input("\n💬 Tú: ").strip()
            
            # Comandos de salida
            if user_input.lower() in ['quit', 'exit', 'salir', 'bye', 'adiós']:
                print("\n👋 ¡Hasta luego!")
                print(AvaConfig.RESPONSE_END_MARKER)  # ✅ MARCADOR EN SALIDA
                break
            
            if not user_input:
                print("💭 Escribe algo para continuar...")
                continue
            
            # Comandos especiales
            if await handle_special_commands_with_marker(user_input, llm, mcp_initialized):
                continue
            
            # Procesar entrada normal
            print("🔄 Ava está procesando...")
            response = await llm.process_user_input(user_input)
            
            # ✅ RESPUESTA + MARCADOR DE FIN
            print("\n🤖 Ava: " + str(response))
            print(AvaConfig.RESPONSE_END_MARKER)  # ✅ MARCADOR ÚNICO DE FIN
            
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            print(AvaConfig.RESPONSE_END_MARKER)  # ✅ MARCADOR EN INTERRUPCIÓN
            break
        except Exception as e:
            print("\n❌ Error: " + str(e))
            print(AvaConfig.RESPONSE_END_MARKER)  # ✅ MARCADOR EN ERROR

# ✅ COMANDOS ESPECIALES CON MARCADOR
async def handle_special_commands_with_marker(user_input: str, llm: LLMWithMCPTools, mcp_initialized: bool) -> bool:
    """Maneja comandos especiales del sistema CON MARCADOR"""
    user_input_lower = user_input.lower()
    
    # ✅ NUEVO: Control de memoria multimodal
    if user_input_lower == 'fastmode':
        llm.config.FAST_MODE = not llm.config.FAST_MODE
        status = "ACTIVADO" if llm.config.FAST_MODE else "DESACTIVADO"
        print(f"⚡ Modo rápido {status}")
        print(AvaConfig.RESPONSE_END_MARKER)
        return True
    
    if user_input_lower == 'memoria off':
        llm.config.MULTIMODAL_MEMORY_ENABLED = False
        print("🧠 Memoria multimodal DESACTIVADA")
        print(AvaConfig.RESPONSE_END_MARKER)
        return True
    
    if user_input_lower == 'memoria on':
        llm.config.MULTIMODAL_MEMORY_ENABLED = True
        print("🧠 Memoria multimodal ACTIVADA")
        print(AvaConfig.RESPONSE_END_MARKER)
        return True
    
    if user_input_lower == 'debug':
        print_debug_info(llm, mcp_initialized)
        print(AvaConfig.RESPONSE_END_MARKER)  # ✅ MARCADOR EN DEBUG
        return True
    
    if user_input_lower == 'tools':
        print("\n🔧 HERRAMIENTAS DISPONIBLES:")
        for tool in llm.available_tools:
            name = tool.get('name', 'Unknown')
            desc = tool.get('description', 'No description')
            print("  • " + name + ": " + desc)
        print(AvaConfig.RESPONSE_END_MARKER)  # ✅ MARCADOR EN TOOLS
        return True
    
    if user_input_lower == 'clear':
        llm.conversation_history.clear()
        print("🧹 Historial de conversación limpiado")
        print(AvaConfig.RESPONSE_END_MARKER)  # ✅ MARCADOR EN CLEAR
        return True
    
    if user_input_lower.startswith('email:'):
        email = user_input[6:].strip()
        llm.current_user_email = email
        print("📧 Email establecido: " + email)
        print(AvaConfig.RESPONSE_END_MARKER)  # ✅ MARCADOR EN EMAIL
        return True
    
    # ✅ NUEVOS COMANDOS PARA MEMORIA MULTIMODAL
    if user_input_lower == 'memoria':
        await show_memory_stats(llm)
        print(AvaConfig.RESPONSE_END_MARKER)
        return True
    
    if user_input_lower.startswith('buscar:'):
        query = user_input[7:].strip()
        await search_multimodal_memory(llm, query)
        print(AvaConfig.RESPONSE_END_MARKER)
        return True
    
    if user_input_lower == 'stats':
        await show_full_system_stats(llm, mcp_initialized)
        print(AvaConfig.RESPONSE_END_MARKER)
        return True
    
    return False

# ✅ FUNCIÓN DEBUG MEJORADA
def print_debug_info(llm: LLMWithMCPTools, mcp_initialized: bool):
    """Muestra información de debug del sistema"""
    print("\n🔍 INFORMACIÓN DE DEBUG:")
    print("-" * 30)
    
    # Estado del sistema
    status = "🟢 Activo" if mcp_initialized else "🔴 Inactivo"
    print("  • Estado MCP: " + status)
    
    # Herramientas
    tools_count = str(len(llm.available_tools))
    tools_status = '✅' if mcp_initialized else '❌'
    print("  • Herramientas MCP: " + tools_count + " " + tools_status)
    
    # Memoria tradicional
    memory_status = '✅' if llm.memory_adapter else '❌'
    print("  • Memoria SQLite: " + memory_status)
    
    # ✅ NUEVA: Memoria multimodal
    multimodal_status = '✅' if llm.multimodal_memory else '❌'
    print("  • Memoria Multimodal: " + multimodal_status)
    
    # Usuario current_user
    current_user = llm.current_user_email or "No identificado"
    print("  • Usuario actual: " + current_user)
    
    # Historial
    history_count = str(len(llm.conversation_history))
    print("  • Mensajes en historial: " + history_count)
    
    # Schemas
    schemas_count = str(len(llm._cached_schemas))
    print("  • Schemas cargados: " + schemas_count)

# ✅ NUEVAS FUNCIONES PARA MEMORIA MULTIMODAL
async def show_memory_stats(llm: LLMWithMCPTools):
    """Muestra estadísticas de memoria multimodal"""
    print("\n🧠 ESTADÍSTICAS DE MEMORIA MULTIMODAL:")
    print("-" * 40)
    
    if not llm.multimodal_memory:
        print("❌ Memoria multimodal no disponible")
        return
    
    try:
        user_id = llm.current_user_email or "unknown_user"
        
        # Obtener estadísticas
        stats = await llm.multimodal_memory.get_memory_stats(user_id)
        
        if stats:
            print(f"👤 Usuario: {user_id}")
            print(f"📝 Total conversaciones: {stats.get('total_conversations', 0)}")
            print(f"🖼️ Total imágenes: {stats.get('total_images', 0)}")
            print(f"📊 Total embeddings: {stats.get('total_embeddings', 0)}")
            print(f"📅 Última actividad: {stats.get('last_activity', 'N/A')}")
        else:
            print("📭 No hay datos de memoria para este usuario")
            
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")

async def search_multimodal_memory(llm: LLMWithMCPTools, query: str):
    """Busca en memoria multimodal"""
    print(f"\n🔍 BUSCANDO EN MEMORIA: '{query}'")
    print("-" * 40)
    
    if not llm.multimodal_memory:
        print("❌ Memoria multimodal no disponible")
        return
    
    try:
        user_id = llm.current_user_email or "unknown_user"
        
        # Búsqueda semántica
        results = await llm.multimodal_memory.search_semantic_memories(
            query=query,
            user_id=user_id,
            modalities=["text"],
            limit=5
        )
        
        if results:
            print(f"✅ Encontrados {len(results)} resultados:")
            for i, result in enumerate(results, 1):
                content = result.get('content', '')[:100] + "..."
                similarity = result.get('similarity_score', 0)
                timestamp = result.get('created_at', '')
                
                print(f"\n{i}. [{timestamp}] (Relevancia: {similarity:.2f})")
                print(f"   {content}")
        else:
            print("📭 No se encontraron resultados")
            
    except Exception as e:
        print(f"❌ Error en búsqueda: {e}")

async def show_full_system_stats(llm: LLMWithMCPTools, mcp_initialized: bool):
    """Muestra estadísticas completas del sistema"""
    print("\n📊 ESTADÍSTICAS COMPLETAS DEL SISTEMA:")
    print("=" * 50)
    
    # Información básica
    print_debug_info(llm, mcp_initialized)
    
    # Estadísticas de memoria multimodal
    await show_memory_stats(llm)
    
    # Herramientas disponibles
    print("\n🔧 HERRAMIENTAS DISPONIBLES:")
    print("-" * 30)
    for tool in llm.available_tools:
        name = tool.get('name', 'Unknown')
        desc = tool.get('description', 'Sin descripción')[:50] + "..."
        print(f"  • {name}: {desc}")

# ✅ PUNTO DE ENTRADA PRINCIPAL
if __name__ == "__main__":
    """Punto de entrada principal"""
    try:
        print("🎭 SISTEMA AVA - AGENTE VIRTUAL AVANZADO")
        print("=" * 50)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Programa terminado por el usuario.")
    except Exception as e:
        print("❌ Error fatal: " + str(e))
    finally:
        print("\n🔚 Sistema finalizado.")
