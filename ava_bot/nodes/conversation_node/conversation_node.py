import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from groq import Groq
import json
import re

# Importar estado centralizado
import sys
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from state import AICompanionStateManager, normalize_state, validate_state
from nodes.conversation_node.system_prompt import SystemPrompt
from tool_manager import tool_manager  # ✅ IMPORTAR TOOL_MANAGER

logger = logging.getLogger(__name__)

class ConversationNode:
    """Nodo de conversación con conocimiento de schemas de herramientas"""
    
    def __init__(self):
        """Inicializa con acceso a schemas de herramientas"""
        self.groq_client = None
        # ✅ FIX: Inicializar tool_manager como atributo de instancia
        self.tool_manager = tool_manager  # ✅ AGREGAR ESTA LÍNEA
        
        self.tool_schemas = tool_manager.get_all_schemas()  # ✅ CARGAR TODOS LOS SCHEMAS
        logger.info(f"📋 Loaded schemas for {len(self.tool_schemas)} tools")
        
        # Cargar extractores específicos por herramienta
        self.param_extractors = self._setup_param_extractors()
    
    def _setup_param_extractors(self) -> Dict[str, callable]:
        """Configura extractores específicos para cada herramienta"""
        return {
            "gmail": self._extract_gmail_params,
            "web_search": self._extract_search_params,
            "calendar": self._extract_calendar_params,
            "meet": self._extract_meet_params,
            "image_generator": self._extract_image_params,
            "drive": self._extract_drive_params,
            "memory_save": self._extract_memory_params,
        }
    
    def _initialize_groq(self):
        """Inicializa el cliente Groq"""
        if self.groq_client is None:
            try:
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    raise ValueError("GROQ_API_KEY not found in environment variables")
                
                self.groq_client = Groq(api_key=api_key)
                logger.info("Groq client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                raise
    
    def process(self, state) -> AICompanionStateManager:
        """Procesa conversación y detecta si necesita herramientas"""
        
        logger.info("💬 Processing conversation with tool detection...")
        
        try:
            # Inicializar Groq
            self._initialize_groq()
            
            # 🔧 NORMALIZAR ESTADO DE ENTRADA
            if isinstance(state, dict):
                if not validate_state(state):
                    state = normalize_state(state)
                state_obj = AICompanionStateManager.from_dict(state)
            else:
                state_obj = state
            
            # Extraer datos necesarios
            user_input = state_obj.input
            conversation_history = state_obj.conversation_history
            
            logger.info(f"💬 Processing input: '{user_input[:50]}...'")
            
            # 🎯 DETECTAR SI NECESITA HERRAMIENTAS ANTES DE PROCESAR
            needs_tools, tool_info = self._analyze_for_tools(user_input)
            
            if needs_tools:
                logger.info(f"🛠️ Tools needed: {tool_info}")
                # Preparar datos de herramienta
                state_obj.tool_data = tool_info
                state_obj.current_node = "tools_node"  # Ir directamente a herramientas
                
                # Generar respuesta que indica que se usarán herramientas
                state_obj.response = self._generate_tool_response(user_input, tool_info)
                
                return state_obj
            else:
                # Conversación normal sin herramientas
                return self._process_pure_conversation(state_obj, user_input, conversation_history)
                
        except Exception as e:
            logger.error(f"Error in conversation processing: {e}")
            
            # Estado de error simple
            if isinstance(state, dict):
                state_obj = AICompanionStateManager.from_dict(state)
            else:
                state_obj = state
                
            state_obj.response = "Lo siento, hubo un error procesando tu mensaje."
            state_obj.current_node = "end_node"
            state_obj.tool_data = {}
            state_obj.multi_tool_requests = []
            
            return state_obj
    
    def _analyze_for_tools(self, user_input: str) -> tuple[bool, dict]:
        """Analiza si el input necesita herramientas usando schemas"""
        
        text = user_input.lower()
        
        # 🔍 WEB SEARCH
        if any(keyword in text for keyword in ["buscar", "search", "busca", "encuentra", "información sobre"]):
            params = self._extract_search_params(user_input)
            is_valid, error = tool_manager.validate_tool_params("web_search", params)
            
            if is_valid:
                return True, {
                    "tool_name": "web_search",
                    "parameters": params
                }
        
        # 📧 GMAIL
        elif any(keyword in text for keyword in ["correo", "email", "gmail", "enviar", "envía"]):
            params = self._extract_gmail_params(user_input)
            is_valid, error = tool_manager.validate_tool_params("gmail", params)
            
            if is_valid:
                return True, {
                    "tool_name": "gmail",
                    "parameters": params
                }
            else:
                logger.warning(f"Gmail params validation failed: {error}")
        
        # 📅 CALENDAR
        elif any(keyword in text for keyword in ["calendario", "calendar", "evento", "reunión", "cita"]):
            params = self._extract_calendar_params(user_input)
            is_valid, error = tool_manager.validate_tool_params("calendar", params)
            
            if is_valid:
                return True, {
                    "tool_name": "calendar",
                    "parameters": params
                }
        
        # 📹 MEET
        elif any(keyword in text for keyword in ["meet", "videollamada", "reunión virtual", "zoom"]):
            params = self._extract_meet_params(user_input)
            is_valid, error = tool_manager.validate_tool_params("meet", params)
            
            if is_valid:
                return True, {
                    "tool_name": "meet",
                    "parameters": params
                }
        
        # 🎨 IMAGE GENERATION
        elif any(keyword in text for keyword in ["imagen", "generar", "crear imagen", "dibujar", "dibuja"]):
            params = self._extract_image_params(user_input)
            is_valid, error = tool_manager.validate_tool_params("image_generator", params)
            
            if is_valid:
                return True, {
                    "tool_name": "image_generator",
                    "parameters": params
                }
        
        # 📁 DRIVE
        elif any(keyword in text for keyword in ["drive", "archivo", "documento", "subir", "descargar"]):
            params = self._extract_drive_params(user_input)
            is_valid, error = tool_manager.validate_tool_params("drive", params)
            
            if is_valid:
                return True, {
                    "tool_name": "drive",
                    "parameters": params
                }
        
        # 🧠 MEMORY
        elif any(keyword in text for keyword in ["recordar", "memoria", "guardar", "save"]):
            params = self._extract_memory_params(user_input)
            is_valid, error = tool_manager.validate_tool_params("memory_save", params)
            
            if is_valid:
                return True, {
                    "tool_name": "memory_save",
                    "parameters": params
                }
        
        return False, {}
    
    def _extract_gmail_params(self, user_input: str) -> Dict[str, Any]:
        """Extract Gmail parameters from user input"""
        
        # ✅ FIX: Verificar métodos disponibles y usar el correcto
        try:
            # Opción 1: Si tiene get_tool_by_name
            if hasattr(self.tool_manager, 'get_tool_by_name'):
                gmail_tool = self.tool_manager.get_tool_by_name("gmail")
            # Opción 2: Si tiene get_tool
            elif hasattr(self.tool_manager, 'get_tool'):
                gmail_tool = self.tool_manager.get_tool("gmail")
            # Opción 3: Si tiene tools como diccionario
            elif hasattr(self.tool_manager, 'tools'):
                gmail_tool = self.tool_manager.tools.get("gmail")
            # Opción 4: Si tiene get_tools y devuelve un dict
            elif hasattr(self.tool_manager, 'get_tools'):
                tools_dict = self.tool_manager.get_tools()
                gmail_tool = tools_dict.get("gmail") if isinstance(tools_dict, dict) else None
            else:
                gmail_tool = None
                
            logger.info(f"Gmail tool found: {gmail_tool is not None}")
            
            if not gmail_tool:
                # ✅ FIX: Si no hay tool, extraer parámetros manualmente
                return self._manual_gmail_extraction(user_input)
            
            # ✅ Verificar si el método validate_and_extract_params existe
            if hasattr(gmail_tool, 'validate_and_extract_params'):
                params = gmail_tool.validate_and_extract_params(user_input)
                
                # ✅ Procesar CONTENT_REQUEST si existe
                body = params.get('body', '')
                if body.startswith('CONTENT_REQUEST:'):
                    enhanced_body = self._process_content_request(body)
                    params['body'] = enhanced_body
                
                return {
                    "tool_name": "gmail",
                    "parameters": params
                }
            else:
                # ✅ Fallback: extracción manual
                return self._manual_gmail_extraction(user_input)
                
        except Exception as e:
            logger.error(f"Error accessing gmail tool: {e}")
            # ✅ Fallback: extracción manual
            return self._manual_gmail_extraction(user_input)
    
    def _process_content_request(self, content_request: str) -> str:
        """Procesar solicitud de contenido dinámico"""
        
        lines = content_request.split('\n')
        topic = ""
        original_request = ""
        
        for line in lines:
            if line.startswith('CONTENT_REQUEST:'):
                topic = line.replace('CONTENT_REQUEST:', '').strip()
            elif line.startswith('ORIGINAL_REQUEST:'):
                original_request = line.replace('ORIGINAL_REQUEST:', '').strip()
        
        # ✅ Buscar información relevante en el contexto de conversación
        context_info = self._find_relevant_context(topic)
        
        if context_info:
            return f"""Te comparto información sobre {topic}:

{context_info}

Esta información fue recopilada durante nuestra conversación.

Saludos,
Ava Bot"""
        else:
            return f"""Hola,

Te envío este mensaje sobre {topic} como solicitaste.

Para obtener información más detallada, no dudes en preguntar.

Saludos,
Ava Bot"""
    
    def _find_relevant_context(self, topic: str) -> str:
        """Buscar información relevante en el contexto de conversación mejorado"""
        
        try:
            # ✅ Buscar en múltiples fuentes de contexto
            context_sources = []
            
            # Fuente 1: Estado actual si está disponible
            if hasattr(self, '_current_state') and self._current_state:
                conversation_history = getattr(self._current_state, 'conversation_history', [])
                if conversation_history:
                    context_sources.extend(conversation_history)
            
            # Fuente 2: Buscar en mensajes recientes del state actual del proceso
            # (puede que el estado se pase de otra manera)
            
            # Procesar todas las fuentes
            relevant_content = []
            topic_lower = topic.lower() if topic else ""
            
            # Buscar en los mensajes
            for msg in context_sources[-15:]:  # Últimos 15 mensajes
                if isinstance(msg, dict):
                    content = msg.get('content', '')
                elif isinstance(msg, str):
                    content = msg
                else:
                    continue
                    
                # Filtrar contenido relevante
                if len(content) > 30:  # Mensajes sustanciales
                    # Si hay topic específico, buscarlo
                    if topic and topic_lower in content.lower():
                        # Extraer oraciones relevantes
                        sentences = content.split('.')
                        for sentence in sentences:
                            sentence = sentence.strip()
                            if len(sentence) > 20 and topic_lower in sentence.lower():
                                relevant_content.append(sentence)
                    # Si no hay topic específico, tomar contenido general
                    elif not topic and len(content) > 50:
                        # Tomar fragmentos del contenido
                        fragments = content.split('\n')
                        for fragment in fragments:
                            fragment = fragment.strip()
                            if len(fragment) > 30:
                                relevant_content.append(fragment)
            
            if relevant_content:
                # Eliminar duplicados manteniendo orden
                unique_content = []
                seen = set()
                for item in relevant_content:
                    if item not in seen:
                        unique_content.append(item)
                        seen.add(item)
                
                # Tomar los mejores fragmentos
                result = '. '.join(unique_content[:5])
                if len(result) > 1000:  # Limitar tamaño
                    result = result[:1000] + "..."
                
                return result
            
            return ""
            
        except Exception as e:
            logger.warning(f"Error finding relevant context: {e}")
            return ""
    
    def _extract_search_params(self, user_input: str) -> Dict[str, Any]:
        """Extrae parámetros específicos para Web Search usando su schema"""
        
        search_schema = tool_manager.get_tool_schema("web_search")
        properties = tool_manager.get_tool_properties("web_search")
        
        # Extraer query limpiando palabras de comando
        query = user_input
        for keyword in ["buscar", "busca", "search", "encuentra", "información sobre"]:
            query = query.replace(keyword, "").strip()
        
        # Limpiar palabras comunes
        query = re.sub(r'\b(en|la|el|internet|web|google)\b', '', query).strip()
        
        if not query:
            query = user_input
        
        params = {
            "query": query,
            "num_results": 5  # Valor por defecto según schema
        }
        
        return params
    
    def _extract_calendar_params(self, user_input: str) -> Dict[str, Any]:
        """Extrae parámetros específicos para Calendar usando su schema"""
        
        calendar_schema = tool_manager.get_tool_schema("calendar")
        required_params = tool_manager.get_required_params("calendar")
        
        params = {
            "action": "create_event"  # Por defecto crear evento
        }
        
        # Extraer título del evento (REQUERIDO)
        text = user_input.lower()
        if "reunión" in text:
            params["summary"] = "Reunión"
        elif "cita" in text:
            params["summary"] = "Cita"
        elif "evento" in text:
            params["summary"] = "Evento"
        else:
            params["summary"] = "Evento creado desde Ava"
        
        # Extraer fecha/hora (REQUERIDO)
        # Implementación básica - se puede mejorar con NLP
        if "mañana" in text:
            from datetime import datetime, timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            params["start_time"] = tomorrow.replace(hour=9, minute=0).isoformat()
        elif "hoy" in text:
            from datetime import datetime
            today = datetime.now()
            params["start_time"] = today.replace(hour=14, minute=0).isoformat()
        else:
            # Fallback: mañana a las 9 AM
            from datetime import datetime, timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            params["start_time"] = tomorrow.replace(hour=9, minute=0).isoformat()
        
        return params
    
    def _extract_meet_params(self, user_input: str) -> Dict[str, Any]:
        """Extrae parámetros específicos para Meet usando su schema"""
        
        meet_schema = tool_manager.get_tool_schema("meet")
        required_params = tool_manager.get_required_params("meet")
        
        params = {}
        
        # Extraer título (REQUERIDO)
        params["title"] = "Reunión Google Meet"
        
        # Extraer fecha/hora (REQUERIDO)
        # Similar a calendar pero para Meet
        text = user_input.lower()
        if "mañana" in text:
            from datetime import datetime, timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            params["start_time"] = tomorrow.replace(hour=10, minute=0).isoformat()
        else:
            from datetime import datetime, timedelta
            tomorrow = datetime.now() + timedelta(days=1)
            params["start_time"] = tomorrow.replace(hour=10, minute=0).isoformat()
        
        return params
    
    def _extract_image_params(self, user_input: str) -> Dict[str, Any]:
        """Extrae parámetros específicos para Image Generator usando su schema"""
        
        image_schema = tool_manager.get_tool_schema("image_generator")
        
        # Limpiar prompt removiendo palabras de comando
        prompt = user_input
        for keyword in ["generar", "crear", "imagen", "dibujar", "dibuja"]:
            prompt = prompt.replace(keyword, "").strip()
        
        if not prompt:
            prompt = user_input
        
        params = {
            "prompt": prompt,
            "width": 1024,  # Valores por defecto según schema
            "height": 1024,
            "steps": 20,
            "style": "realistic"
        }
        
        return params
    
    def _extract_drive_params(self, user_input: str) -> Dict[str, Any]:
        """Extrae parámetros específicos para Drive usando su schema"""
        
        drive_schema = tool_manager.get_tool_schema("drive")
        
        text = user_input.lower()
        
        if "subir" in text:
            action = "upload"
        elif "descargar" in text:
            action = "download"
        elif "compartir" in text:
            action = "share"
        elif "eliminar" in text:
            action = "delete"
        else:
            action = "list"  # Por defecto
        
        params = {
            "action": action,
            "limit": 10
        }
        
        return params
    
    def _extract_memory_params(self, user_input: str) -> Dict[str, Any]:
        """Extrae parámetros específicos para Memory usando su schema"""
        
        params = {
            "content": user_input,
            "tags": ["conversation"]
        }
        
        return params
    
    def _generate_tool_response(self, user_input: str, tool_info: Dict[str, Any]) -> str:
        """Generar respuesta cuando se van a usar herramientas"""
        
        tool_name = tool_info.get("tool_name", "")
        
        if tool_name == "gmail_request_clarification":
            return """Para enviar la información por correo, necesito que especifiques tu email de destino.

Por ejemplo:
- "envíalas a mi_email@gmail.com"
- "mándalas a juan@hotmail.com"

¿Podrías proporcionarme la dirección de correo?"""
        
        elif tool_name == "gmail":
            return "📧 Preparando el correo electrónico con la información solicitada..."
        
        elif tool_name == "web_search":
            return "🔍 Buscando información en internet..."
        
        # ... resto de herramientas existentes ...
        
        return f"🛠️ Procesando con {tool_name}..."
    
    def _process_pure_conversation(self, state_obj, user_input: str, conversation_history: list) -> AICompanionStateManager:
        """Procesa conversación pura sin herramientas"""
        
        logger.info("💬 Processing PURE conversation...")
        
        # Usar system prompt conversacional
        system_prompt = SystemPrompt.get_conversation_prompt()
        
        # Preparar mensajes para Groq
        messages = [{"role": "system", "content": system_prompt}]
        
        # Añadir historial reciente
        if conversation_history:
            recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
            for msg in recent_history:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    messages.append({
                        "role": msg["role"], 
                        "content": msg["content"]
                    })
        
        # Añadir mensaje actual
        messages.append({"role": "user", "content": user_input})
        
        # Llamar a Groq
        logger.info("Calling Groq API for PURE conversation...")
        response = self.groq_client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content
        logger.info(f"Got PURE conversation response: {response_text[:100]}...")
        
        # Configurar respuesta
        state_obj.response = response_text
        state_obj.current_node = "end_node"  # Terminar aquí
        state_obj.tool_data = {}
        state_obj.multi_tool_requests = []
        
        logger.info("💬 PURE conversation completed")
        return state_obj
    
    def _detect_tools_needed(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Detectar qué herramientas necesita el usuario"""
        
        user_lower = user_input.lower()
        
        # ✅ FIX: Detectar solicitudes de Gmail aún sin email explícito
        gmail_patterns = [
            'enviar correo', 'enviar email', 'mandar correo', 'envía correo',
            'envialas', 'envíalas', 'mi correo', 'mi email'
        ]
        
        # Verificar si es solicitud de Gmail
        if any(pattern in user_lower for pattern in gmail_patterns):
            # Buscar email en el texto
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, user_input)
            
            if emails:
                # Hay email explícito, procesar normalmente
                try:
                    return self._extract_gmail_params(user_input)
                except Exception as e:
                    logger.warning(f"Gmail detection failed: {e}")
            else:
                # No hay email explícito, solicitar aclaración
                logger.info("Gmail request detected but no email found")
                return {
                    "tool_name": "gmail_request_clarification",
                    "parameters": {
                        "original_request": user_input,
                        "missing": "destination_email"
                    }
                }
        
        # ✅ Continuar con otras detecciones (Meet, Calendar, etc.)
        meet_keywords = ['meet', 'reunión', 'reunion', 'cita virtual', 'videollamada']
        if any(keyword in user_lower for keyword in meet_keywords):
            # ... código existente para Meet
            pass
    
        # ... resto del código existente ...
        
        return None  # Por defecto, ninguna herramienta detectada

# Función wrapper para compatibilidad
def enhanced_conversation_node(state):
    """Función wrapper simplificada"""
    node = ConversationNode()
    return node.process(state)