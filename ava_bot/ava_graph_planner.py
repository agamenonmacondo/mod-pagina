from langgraph.graph import StateGraph, MessagesState
from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq
from typing import Any, Dict, List, TypedDict 
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from ava_graph_state import AgentState
from role_promt import get_role_prompt

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class PlannerNode:
    """🎯 PLANNER NODE - Crear planes de ejecución"""
    
    def __init__(self):
        """Inicializar PlannerNode"""
        self.name = "planner"
        self.node_type = "strategic_planner"
        self.llm = ChatGroq(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            api_key=GROQ_API_KEY,
            temperature=0.3,
            max_tokens=2000,
        )
    
    def process(self, state: AgentState) -> AgentState:
        """🎯 PROCESO PRINCIPAL del planner"""
        try:
            print("🎯 PLANNER: Iniciando análisis completo...")
            
            # ✅ OBTENER HERRAMIENTAS DISPONIBLES DEL STATE
            available_tools = state.get("available_tools", {})
            tool_names = list(available_tools.keys()) if available_tools else []
            
            print(f"   🛠️ Herramientas disponibles: {tool_names}")
            
            # ✅ GENERAR PROMPT ÚNICO
            prompt = self.generate_complete_planner_prompt(state, tool_names)
            
            # ✅ INVOCAR LLM
            print("   🤖 Invocando LLM...")
            response = self.llm.invoke(prompt)
            response_content = response.content
            
            # ✅ MOSTRAR RESPUESTA COMPLETA DEL LLM
            print("="*80)
            print("🎯 RESPUESTA COMPLETA DEL PLANNER LLM:")
            print("="*80)
            print(response_content)
            print("="*80)
            
            # ✅ EXTRAER PLAN
            execution_plan = self._extract_execution_plan(response_content)
            
            if execution_plan:
                # ✅ MOSTRAR PLAN EXTRAÍDO
                print("📋 PLAN EXTRAÍDO EXITOSAMENTE:")
                print("-"*50)
                import json
                print(json.dumps(execution_plan, indent=2, ensure_ascii=False))
                print("-"*50)
                
                state["execution_plan"] = execution_plan
                state["node"] = "planner_completed"
                print("✅ PLANNER: Plan creado exitosamente")
            else:
                print("⚠️ PLANNER: No se pudo extraer plan válido - usando conversación directa")
                state["node"] = "planner_fallback"
            
            return state
            
        except Exception as e:
            print(f"❌ Error en planner: {e}")
            print(f"❌ Stack trace completo:")
            import traceback
            traceback.print_exc()
            state["node"] = "planner_error"
            state["error_message"] = f"Error en planner: {e}"
            return state

    def generate_complete_planner_prompt(self, state: AgentState, tool_names: List[str]) -> str:
        """🎯 PROMPT MEJORADO CON INSTRUCCIONES CONTEXTUALES AVANZADAS"""
        
        role_prompt = get_role_prompt()
        available_tools = state.get("available_tools", {})
        messages = state.get("messages", [])
        current_query = messages[-1].content if messages else ""
        context_memory = state.get("context_memory", [])
        conversation_history = state.get("conversation_history", [])
        
        # 🧠 CONTEXTO DE CONVERSACIÓN ANTERIOR
        conversation_context = ""
        if conversation_history:
            recent_messages = conversation_history[-3:]  # Últimos 3 mensajes
            conversation_context = "\n**🧠 CONTEXTO DE CONVERSACIÓN ANTERIOR:**\n"
            for i, msg in enumerate(recent_messages, 1):
                content = msg.content if hasattr(msg, 'content') else str(msg)
                conversation_context += f"{i}. {content[:100]}{'...' if len(content) > 100 else ''}\n"
        
        # 🔧 CONTEXTO DE HERRAMIENTAS EJECUTADAS RECIENTEMENTE
        tools_context = ""
        if context_memory:
            tools_context = "\n**🔧 HERRAMIENTAS EJECUTADAS RECIENTEMENTE:**\n"
            for mem in context_memory[:2]:  # Últimas 2 ejecuciones
                if isinstance(mem, dict):
                    tools_used = mem.get('tools', [])
                    query = mem.get('query', 'N/A')
                    tools_context += f"- Query: {query[:50]}{'...' if len(query) > 50 else ''}\n"
                    tools_context += f"  Tools: {tools_used}\n"
        
        # 🛠️ SCHEMAS COMPLETOS DE HERRAMIENTAS - NUEVO
        detailed_tools_info = self._get_complete_tools_schemas()
        
        prompt = f"""Eres un planificador estratégico experto para {role_prompt} que analiza el CONTEXTO COMPLETO para determinar la mejor estrategia de respuesta.

🎯 **CONSULTA ACTUAL:**
"{current_query}"

{conversation_context}

{tools_context}

🛠️ **HERRAMIENTAS DISPONIBLES CON SCHEMAS COMPLETOS:**
{detailed_tools_info}

📋 **INSTRUCCIONES PARA PLANIFICACIÓN:**

🎯 **REGLA 1 - ANÁLISIS DEL CONTEXTO:**
- Si es una consulta de SEGUIMIENTO (referencias a resultados anteriores), NO ejecutar herramientas nuevamente
- Si menciona "analiza esto", "revisa eso", "qué piensas de...", "explícame más", es seguimiento conversacional
- Si pide "más información" sobre algo ya mostrado, es seguimiento
- Si hace referencia a información previamente proporcionada, es conversacional

🎯 **REGLA 2 - CONSULTAS SIMPLES (0 PASOS - needs_tools: false):**
- Saludos: "hola", "hi", "buenas", "hello"
- Preguntas sobre capacidades: "qué puedes hacer", "ayuda", "help"
- Seguimiento conversacional: "qué opinas", "explícame más", "y qué más", "cuéntame"
- Agradecimientos: "gracias", "perfecto", "está bien", "ok"
- Despedidas: "adiós", "hasta luego", "bye"

🎯 **REGLA 3 - CONSULTAS ESPECÍFICAS (1-2 PASOS - needs_tools: true):**
- Análisis de imagen con ruta específica → `vision`
- Generar imagen con descripción → `image`
- Enviar email con destinatario y contenido → `gmail`
- Búsqueda específica con términos claros → `search`

🎯 **REGLA 4 - CONSULTAS COMPLEJAS (3-5 PASOS - needs_tools: true):**
- E-commerce: "comprar", "precios", "comparar productos"
- Investigación: múltiples fuentes, análisis profundo
- Automatización: múltiples pasos secuenciales

🎯 **REGLA 5 - DETECCIÓN DE SEGUIMIENTO:**
- Si en el contexto anterior se ejecutaron herramientas exitosamente
- Y la consulta actual hace referencia a esos resultados
- O pide elaboración sobre respuestas anteriores
- NO volver a ejecutar herramientas, crear plan conversacional

🚫 **REGLAS CRÍTICAS:**
- NUNCA usar "None", "none", "N/A" o null como nombre de herramienta
- Solo usar nombres EXACTOS de herramientas disponibles
- Si no necesitas herramientas, crear plan con steps: []
- Todos los parámetros requeridos DEBEN estar presentes

📊 **FORMATOS DE RESPUESTA:**

**PARA CONSULTAS CONVERSACIONALES (Sin herramientas):**
```json
{{
  "execution_plan": {{
    "project_type": "conversational",
    "needs_tools": false,
    "total_steps": 0,
    "strategy": "respuesta_conversacional_directa",
    "steps": []
  }}
}}
```

**PARA CONSULTAS CON HERRAMIENTAS:**
```json
{{
  "execution_plan": {{
    "project_type": "specific_task",
    "needs_tools": true,
    "total_steps": 1-5,
    "strategy": "ejecución_específica",
    "steps": [
      {{
        "step_number": 1,
        "objective": "objetivo_específico",
        "tool": "herramienta_exacta_de_la_lista", 
        "arguments": {{"campo_requerido": "valor", "campo_opcional": "valor"}},
        "expected_output": "resultado_esperado"
      }}
    ]
  }}
}}
```

🎯 **PROCESO DE DECISIÓN:**
1. **ANALIZA** la consulta actual y su contenido
2. **REVISA** el contexto de conversación previa
3. **IDENTIFICA** si es seguimiento/conversacional o nueva tarea específica
4. **DETERMINA** si necesita herramientas o respuesta conversacional
5. **SELECCIONA** herramientas exactas de la lista con parámetros correctos
6. **CREA** el plan apropiado según las reglas contextuales

**RESPONDE SOLO CON EL JSON DEL PLAN:**"""

        return prompt

    def _analyze_query_type(self, query: str) -> dict:
        """🔍 Analizar automáticamente el tipo de consulta"""
        query_lower = query.lower()
        
        # 🖼️ ANÁLISIS DE IMAGEN
        if any(keyword in query_lower for keyword in ['analiza', 'analizar', 'imagen', 'foto', '.png', '.jpg']):
            return {
                'type': 'image_analysis',
                'complexity': 'simple',
                'suggested_tools': ['vision'],
                'recommended_steps': 1
            }
        
        # ✈️ BÚSQUEDA DE VUELOS
        elif any(keyword in query_lower for keyword in ['vuelo', 'vuelos', 'volar', 'viaje']):
            return {
                'type': 'flight_search',
                'complexity': 'complex',
                'suggested_tools': ['search', 'playwright'],
                'recommended_steps': 5
            }
        
        # 🛒 E-COMMERCE
        elif any(keyword in query_lower for keyword in ['comprar', 'precio', 'venta', 'tienda']):
            return {
                'type': 'ecommerce',
                'complexity': 'moderate',
                'suggested_tools': ['search', 'playwright'],
                'recommended_steps': 3
            }
        
        # 📧 COMUNICACIÓN
        elif any(keyword in query_lower for keyword in ['email', 'enviar', 'mandar', 'correo']):
            return {
                'type': 'communication',
                'complexity': 'simple',
                'suggested_tools': ['gmail'],
                'recommended_steps': 1
            }
        
        # 🔍 BÚSQUEDA GENERAL
        else:
            return {
                'type': 'general_search',
                'complexity': 'moderate',
                'suggested_tools': ['search'],
                'recommended_steps': 2
            }

    def _get_complete_tools_schemas(self) -> str:
        """🛠️ NUEVO: Obtener información completa de todas las herramientas"""
        
        tools_info = """
🔧 **VISION** - Análisis de imágenes con Llama Vision
   • Parámetros requeridos: action, image_path
   • Acciones: "analyze_image", "describe_image", "ocr_text"
   • Ejemplo: {"action": "describe_image", "image_path": "C:\\path\\image.png"}

🔧 **PLAYWRIGHT** - Automatización web universal
   • Parámetros requeridos: action, url
   • Acciones principales:
     - "navigate" - Ir a una URL
     - "extract_text" - Extraer texto de la página
     - "extract_prices" - Extraer precios (e-commerce)
     - "smart_extract" - Extracción inteligente
     - "take_screenshot" - Captura de pantalla
   • Ejemplo: {"action": "navigate", "url": "https://example.com"}

🔧 **FILE_MANAGER** - Gestión de archivos locales
   • Parámetros requeridos: action
   • Acciones: "list_files", "get_latest_image", "read_file"
   • Directorios: "downloads", "generated_images", "temp"
   • Ejemplo: {"action": "get_latest_image", "directory": "downloads"}

🔧 **SEARCH** - Búsqueda web inteligente
   • Parámetros requeridos: query
   • Ejemplo: {"query": "precios iPhone 15", "num_results": 5}

🔧 **IMAGE** - Generador de imágenes FLUX.1
   • Parámetros requeridos: prompt
   • Ejemplo: {"prompt": "Un gato jugando en el jardín", "style": "realista"}

🔧 **GMAIL** - Envío de emails
   • Parámetros requeridos: to, subject, body
   • Ejemplo: {"to": "user@email.com", "subject": "Hola", "body": "Mensaje"}

🔧 **CALENDAR** - Gestión de calendario
   • Parámetros requeridos: summary, start_time
   • Ejemplo: {"summary": "Reunión", "start_time": "2025-06-15T14:00:00"}

🔧 **MEET** - Creación de reuniones
   • Parámetros requeridos: summary
   • Ejemplo: {"summary": "Video llamada", "start_time": "2025-06-15T15:00:00"}

🔧 **MEMORY** - Sistema de memoria
   • Parámetros requeridos: user_id, action
   • Acciones: "search", "store", "get_context"
   • Ejemplo: {"user_id": "user123", "action": "search", "query": "conversaciones"}

🔧 **MULTIMODAL_MEMORY** - Memoria multimodal avanzada
   • Parámetros requeridos: action, user_id
   • Acciones: "store_text_memory", "search_semantic_memories"
   • Ejemplo: {"action": "get_user_stats", "user_id": "user123"}

🔧 **OPENAI_TTS** - Síntesis de voz OpenAI
   • Parámetros requeridos: action, text
   • Acciones: "text_to_speech", "get_voices"
   • Voces: "coral", "alloy", "nova", "onyx"
   • Ejemplo: {"action": "text_to_speech", "text": "Hola mundo", "voice": "coral"}

🔧 **GROQ_SPEECH** - STT/TTS con Groq y Whisper
   • Parámetros requeridos: action
   • Acciones: "speech_to_text", "text_to_speech", "transcribe_file"
   • Ejemplo: {"action": "text_to_speech", "text": "Hola", "language": "es"}

🔧 **IMAGE_DISPLAY** - Visualización de imágenes
   • Para mostrar imágenes generadas o procesadas
   • Ejemplo: {"action": "display", "image_path": "path/to/image.png"}
"""
        
        return tools_info

    def _extract_execution_plan(self, response_content: str) -> dict:
        """Extraer plan de ejecución del JSON con logging mejorado"""
        try:
            print("🔍 EXTRAYENDO PLAN DE EJECUCIÓN...")
            print(f"   📝 Contenido a parsear: {len(response_content)} caracteres")
            
            # Buscar JSON en la respuesta
            json_match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                print("   ✅ JSON encontrado dentro de bloques de código")
            else:
                # Si no hay bloques de código, buscar JSON directo
                json_str = response_content.strip()
                print("   ⚠️ No se encontraron bloques de código, usando contenido completo")
            
            print(f"   📄 JSON a parsear:")
            print("-"*40)
            print(json_str)
            print("-"*40)
            
            # Parsear JSON
            plan_data = json.loads(json_str)
            
            print("   ✅ JSON parseado exitosamente")
            print(f"   📊 Estructura: {list(plan_data.keys())}")
            
            if "execution_plan" in plan_data:
                return plan_data
            else:
                return {"execution_plan": plan_data}
                
        except json.JSONDecodeError as e:
            print(f"   ❌ Error JSON: {e}")
            return None
        except Exception as e:
            print(f"   ❌ Error general: {e}")
            return None

def create_planner_node() -> callable:
    """🏭 Factory function que retorna el nodo planner"""
    planner_instance = PlannerNode()
    
    def planner_node(state: AgentState) -> AgentState:
        """Función que ejecuta el proceso planner"""
        print("🔄 Planner node iniciando...")
        try:
            result = planner_instance.process(state)
            print("🔄 Planner node completado exitosamente")
            return result
        except Exception as e:
            print(f"❌ Error en planner node: {e}")
            state["execution_plan"] = {}
            state["node"] = "planner_error"
            state["error_message"] = f"Error en planner: {e}"
            return state
    
    return planner_node