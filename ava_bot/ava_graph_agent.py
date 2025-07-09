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

from base_context_agent import BaseContextAgent

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ✅ VERIFICAR QUE role_promt.py EXISTE
# Si no existe, crear archivo role_promt.py o cambiar importación
try:
    from role_promt import get_role_prompt
except ImportError:
    def get_role_prompt():
        return "Responde como Ava, consultora especializada en IA y agentes virtuales."

class ConversationalNode(BaseContextAgent):  # ✅ HEREDAR DE BaseContextAgent
    
    def __init__(self):
        """Inicializar ConversationalNode"""
        self.llm = ChatGroq(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            api_key=GROQ_API_KEY,
            temperature=0.7,
            max_tokens=1500,
        )
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "{conversational_prompt}"),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        self.chain = self.prompt_template | self.llm

    def process(self, state: AgentState) -> AgentState:
        """Procesar ConversationalNode - MEJORADO"""
        print("💬 ConversationalNode procesando...")
        
        try:
            # ✅ VERIFICAR ESTADO INICIAL
            if not isinstance(state, dict):
                print(f"❌ State no es dict: {type(state)}")
                return {"error_message": "Estado inválido"}
            
            # ✅ OBTENER DATOS DEL STATE CON DEFAULTS SEGUROS - SOLO CAMPOS QUE EXISTEN
            messages = state.get("messages", [])
            execution_plan = state.get("execution_plan", {})
            tool_result = state.get("tool_result", "")
            
            print(f"   📝 Messages: {len(messages)}")
            print(f"   📊 Tool Result Length: {len(str(tool_result))}")
            
            # ✅ VERIFICAR QUE HAY MENSAJES
            if not messages:
                print("❌ No hay mensajes en el state")
                # Crear mensaje por defecto
                default_message = HumanMessage(content="Consulta general")
                messages = [default_message]
                state["messages"] = messages
            
            # ✅ OBTENER ÚLTIMO MENSAJE HUMANO
            user_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
            if not user_messages:
                print("❌ No hay mensajes de usuario")
                last_user_message = HumanMessage(content="Consulta general")
            else:
                last_user_message = user_messages[-1]
            
            print(f"   📝 Procesando: {last_user_message.content[:50]}...")
            
            # ✅ GENERAR PROMPT
            try:
                conversational_prompt = self.generate_conversational_prompt(state)
                print(f"   📋 Prompt generado: {len(conversational_prompt)} chars")
            except Exception as e:
                print(f"   ❌ Error generando prompt: {e}")
                conversational_prompt = "Responde como Ava, consultora en IA."
            
            # ✅ INVOCAR LLM CON MEJOR MANEJO DE ERRORES
            llm_input = {
                "conversational_prompt": conversational_prompt,
                "messages": [last_user_message]
            }
            
            try:
                print("   🤖 Invocando LLM...")
                response = self.chain.invoke(llm_input)
                
                # ✅ VERIFICAR RESPUESTA
                if hasattr(response, 'content'):
                    response_content = response.content
                else:
                    response_content = str(response)
                
                if not response_content or response_content.strip() == "":
                    raise Exception("Respuesta vacía del LLM")
                
                print(f"   ✅ Respuesta generada: {len(response_content)} chars")
                
            except Exception as e:
                print(f"   ❌ Error LLM: {e}")
                print("   🔄 Usando respuesta directa...")
                response_content = self.create_direct_response(state)
            
            # ✅ CREAR MENSAJE AI
            ai_message = AIMessage(content=response_content)
            
            # ✅ ACTUALIZAR STATE DE FORMA SEGURA
            updated_messages = messages.copy()
            updated_messages.append(ai_message)
            
            # ✅ ACTUALIZAR CONVERSATION_HISTORY
            conversation_history = state.get("conversation_history", [])
            updated_conversation_history = conversation_history.copy()
            updated_conversation_history.append(ai_message)
            
            # ✅ RETURN STATE ACTUALIZADO
            updated_state = state.copy()  # Crear copia del estado
            updated_state.update({
                "messages": updated_messages,
                "conversation_history": updated_conversation_history,
                "node": "conversational_completed"
            })
            
            print("✅ ConversationalNode completado")
            return updated_state
            
        except Exception as e:
            print(f"❌ Error crítico en ConversationalNode: {e}")
            import traceback
            traceback.print_exc()
            
            # ✅ FALLBACK SEGURO
            fallback_state = state.copy() if isinstance(state, dict) else {}
            fallback_state.update({
                "error_message": f"Error conversational: {str(e)}",
                "node": "conversational_error",
                "messages": state.get("messages", []) + [AIMessage(content="Lo siento, hubo un error procesando tu consulta.")]
            })
            return fallback_state

    def generate_conversational_prompt(self, state: AgentState) -> str:
        """🎯 PROMPT CON CONTEXTO COMPLETO ESTANDARIZADO"""
        role_promt = get_role_prompt()
        
        # ✅ USAR MÉTODO ESTANDARIZADO
        context = self.get_complete_context(state)
        
        # ✅ FORMATEAR CONTEXTO COMPLETO
        conversation_context = self.format_full_conversation_context(context['conversation_history'])
        
        # ✅ EXTRAER DATOS ESPECÍFICOS DE TODAS LAS FUENTES
        extracted_data = self.extract_all_specific_data(context)
        formatted_data = self.format_extracted_data(extracted_data)
        
        # ✅ ANALIZAR TOOL_RESULT ACTUAL
        current_tool_data = self._force_extract_all_specific_data(context['tool_result'])
        
        # ✅ CONSULTA ACTUAL
        user_messages = [msg for msg in context['messages'] if isinstance(msg, HumanMessage)]
        current_query = user_messages[-1].content if user_messages else "consulta general"
        
        prompt = f"""ERES AVA - DEBES USAR TODO EL CONTEXTO DISPONIBLE OBLIGATORIAMENTE.

🎯 **CONSULTA ACTUAL:** "{current_query}"

usa esta información que va determinar tu manera de relacionarte: {role_promt}

{conversation_context}

{formatted_data}

🚨 **DATOS DEL RESULTADO ACTUAL:**
{current_tool_data}

🧠 **ESTADO DE LA SESIÓN:**
- Sesión ID: {context['session_id']}
- Mensajes en historial: {len(context['conversation_history'])}
- Memoria contextual: {len(context['context_memory']) if isinstance(context['context_memory'], list) else 'Dict'}
- Herramientas disponibles: {len(context['available_tools'])}

📋 **INSTRUCCIONES ABSOLUTAS:**

1. **PRIORIDAD MÁXIMA:** Si hay {len(context['conversation_history'])} mensajes en el historial, úsalos OBLIGATORIAMENTE
2. **COHERENCIA:** Mantén continuidad con conversaciones previas mostradas arriba
3. **DATOS ESPECÍFICOS:** Usa TODOS los datos extraídos (URLs, precios, fechas, hoteles, etc.)
4. **REFERENCIAS:** Menciona información específica de conversaciones anteriores
5. **SEGUIMIENTO:** Si la consulta actual es seguimiento, elabora sobre información previa

⚠️ **PROHIBIDO TOTALMENTE:**
- Decir "no hemos hablado" cuando hay {len(context['conversation_history'])} mensajes en historial
- Actuar como primera conversación cuando hay historial previo
- Ignorar datos específicos extraídos del contexto
- Generar información nueva cuando hay datos reales disponibles
- Omitir referencias a conversaciones anteriores cuando existen

✅ **FORMATO DE RESPUESTA:**
- Reconoce conversaciones previas si las hay
- Usa datos específicos del contexto (precios, fechas, URLs, etc.)
- Mantén coherencia con el historial de la sesión
- Responde de manera natural pero informada

🎯 **RESPUESTA BASADA EN TODO EL CONTEXTO DISPONIBLE:**"""

        return prompt

    def _format_conversation_history(self, conversation_history: list) -> str:
        """NUEVA FUNCIÓN: Formatear conversation_history para incluir en el prompt"""
        if not conversation_history:
            return "📝 **ESTADO:** Primera conversación\n"
        
        history_text = "📚 **HISTORIAL DE CONVERSACIÓN COMPLETO - USAR OBLIGATORIAMENTE:**\n"
        history_text += "=" * 60 + "\n"
        
        # Incluir los últimos 6 mensajes para contexto suficiente
        for i, msg in enumerate(conversation_history[-6:]):
            if hasattr(msg, 'content') and msg.content:
                role = "👤 USUARIO" if isinstance(msg, HumanMessage) else "🤖 AVA"
                content = msg.content[:800]  # Suficiente contexto
                history_text += f"{role}: {content}\n"
                history_text += "-" * 50 + "\n"
        
        history_text += "=" * 60 + "\n"
        history_text += "🚨 **CRÍTICO:** Este historial muestra nuestra conversación previa. DEBES referenciarla.\n"
        history_text += "❌ **PROHIBIDO:** Decir que 'no hemos hablado' o 'acabamos de empezar' cuando hay historial.\n\n"
        
        return history_text

    def _force_extract_all_specific_data(self, tool_result: str) -> str:
        """Extracción forzada y agresiva de TODOS los datos específicos"""
        
        if not tool_result:
            return "❌ No hay datos disponibles en tool_result"
        
        extracted = "📊 **DATOS ESPECÍFICOS OBLIGATORIOS A USAR:**\n\n"
        
        # 🚗 EXTRAER MODELOS DE CARROS ESPECÍFICOS
        car_models = re.findall(r'(Chevrolet|Renault|Hyundai|Toyota|Nissan|Ford|Kia|Mazda)\s+\w+', tool_result, re.IGNORECASE)
        if car_models:
            extracted += f"🚗 **MODELOS ESPECÍFICOS ENCONTRADOS:** {', '.join(set(car_models))}\n"
        
        # 💰 EXTRAER PRECIOS EXACTOS DE CARROS
        car_prices = re.findall(r'\$[\d,]+\.?\d*(?:\s*(?:millones?|mil))?', tool_result, re.IGNORECASE)
        if car_prices:
            extracted += f"💰 **PRECIOS EXACTOS:** {', '.join(set(car_prices))}\n"
        
        # 🏨 EXTRAER HOTELES ESPECÍFICOS  
        hotels = re.findall(r'(Hotel\s+\w+(?:\s+\w+)*|Casa\s+de\s+Alba|GHL\s+San\s+Lazaro)', tool_result, re.IGNORECASE)
        if hotels:
            extracted += f"🏨 **HOTELES ESPECÍFICOS:** {', '.join(set(hotels))}\n"
        
        # 🎯 EXTRAER ACTIVIDADES Y LUGARES
        activities = re.findall(r'(Ciudad Amurallada|Castillo San Felipe|Torre del Reloj|Plaza de la Aduana|Bocagrande|Getsemaní)', tool_result, re.IGNORECASE)
        if activities:
            extracted += f"🎯 **ACTIVIDADES/LUGARES:** {', '.join(set(activities))}\n"
        
        # 📊 EXTRAER CANTIDADES ESPECÍFICAS
        quantities = re.findall(r'(\d+)\s+(?:carros?|vehículos?|encontrados?|resultados?|personas?)', tool_result, re.IGNORECASE)
        if quantities:
            extracted += f"📊 **CANTIDADES:** {', '.join(quantities)} encontrados\n"
        
        # 🔗 EXTRAER URLs REALES
        urls = re.findall(r'https?://[^\s\'"]+', tool_result)
        if urls:
            extracted += f"🔗 **ENLACES REALES:** {chr(10).join(urls[:5])}\n"  # Primeros 5 links
        
        # 🏢 EXTRAER NOMBRES DE SITIOS/TIENDAS
        sites = re.findall(r'(tucarro|mercadolibre|olx|autotrader|bancolombia|tripadvisor|booking|airbnb)\.com?(?:\.co)?', tool_result, re.IGNORECASE)
        if sites:
            extracted += f"🏢 **SITIOS VERIFICADOS:** {', '.join(set(sites))}\n"
        
        # 📅 EXTRAER FECHAS
        dates = re.findall(r'(\d{1,2}\s+de\s+\w+|\d{1,2}/\d{1,2}/\d{4}|17\s+de\s+julio)', tool_result, re.IGNORECASE)
        if dates:
            extracted += f"📅 **FECHAS MENCIONADAS:** {', '.join(set(dates))}\n"
        
        # 📝 EXTRAER TÍTULOS ESPECÍFICOS
        titles = re.findall(r'"title":\s*"([^"]+)"', tool_result)
        if titles:
            extracted += f"📝 **TÍTULOS ESPECÍFICOS:** {chr(10).join(titles[:3])}\n"
        
        # 🎯 EXTRAER SNIPPETS CON INFORMACIÓN CLAVE
        snippets = re.findall(r'"snippet":\s*"([^"]+)"', tool_result)
        if snippets:
            extracted += f"🎯 **INFORMACIÓN CLAVE:** {chr(10).join(snippets[:2])}\n"
        
        # ⚠️ VALIDACIÓN CRÍTICA
        if len(extracted) < 100:  # Si no hay suficientes datos extraídos
            extracted += f"\n⚠️ **DATOS RAW DISPONIBLES:**\n{tool_result[:500]}...\n"
        
        extracted += f"\n🚨 **OBLIGATORIO:** Usar TODA esta información específica en la respuesta\n"
        
        return extracted

# ✅ FUNCIÓN QUE FALTABA - create_agent_node
def create_agent_node():
    """Crear nodo del agente conversacional"""
    conversational_node = ConversationalNode()
    
    def agent_node_function(state: AgentState) -> AgentState:
        """Función del nodo del agente"""
        return conversational_node.process(state)
    
    return agent_node_function

# ✅ FUNCIÓN ADICIONAL PARA COMPATIBILIDAD
def create_conversational_node() -> callable:
    """Crear nodo conversacional - CON DISPLAY INMEDIATO"""
    conversational_node = ConversationalNode()
    
    def conversational_wrapper(state: AgentState) -> AgentState:
        print("💬 CONVERSATIONAL NODE (LLM) - Procesando con LLM...")
        
        # Ejecutar el proceso conversacional
        result = conversational_node.process(state)
        
        # ✅ MOSTRAR RESPUESTA INMEDIATAMENTE AQUÍ
        messages = result.get('messages', [])
        print(f"✅ ConversationalNode completado con {len(messages)} mensajes")
        
        # Extraer y mostrar la respuesta AI
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    # ✅ AQUÍ ES DONDE SE DEBE MOSTRAR
                    print(f"\n🤖 Ava: {msg.content}")
                    break
        
        result["node"] = "conversational_completed"
        return result
    
    return conversational_wrapper
