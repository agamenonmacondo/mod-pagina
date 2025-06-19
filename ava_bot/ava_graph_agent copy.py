from langgraph.graph import StateGraph, MessagesState
from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq
from typing import Any, Dict, List, TypedDict 
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import json
from operational_promt import get_operational_prompt
import os
from datetime import datetime
from dotenv import load_dotenv
from role_promt import get_role_prompt
import logging

# ✅ SOLO IMPORTAR AGENTSTATE - NO LAS FUNCIONES QUE RECONECTAN
from ava_graph_state import AgentState

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class AgentNode:
    """AgentNode - RESPUESTA FINAL SIN RECONEXIONES MCP"""
    
    def __init__(self):
        """Inicializar AgentNode para respuesta conversacional"""
        self.llm = ChatGroq(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            api_key=GROQ_API_KEY,
            temperature=0.7,  # ✅ Más creatividad para respuestas conversacionales
            max_tokens=1000,  # ✅ Más tokens para respuestas completas
        )
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "{agent_prompt}"),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        self.chain = self.prompt_template | self.llm

    def agent_prompt(self, state: AgentState) -> str:
        """Generar prompt conversacional usando SOLO datos del state"""
        
        try:
            # ✅ USAR ROLE PROMPT PARA PERSONALIDAD
            role_prompt = get_role_prompt()
            operational_prompt = get_operational_prompt("unknown_user")
            base_prompt = f"{role_prompt}\n\n{operational_prompt}"
        except Exception as e:
            base_prompt = "Eres Ava, un asistente inteligente y amigable."
        
        # ✅ USAR SOLO available_tools DEL STATE (sin reconectar)
        available_tools = state.get("available_tools", {})
        
        # ✅ INFORMACIÓN DE HERRAMIENTAS PARA CONTEXTO
        tools_context = ""
        if available_tools:
            tools_context = f"\n\n🔧 **HERRAMIENTAS DISPONIBLES:** {len(available_tools)}\n"
            # Solo mencionar las herramientas principales
            main_tools = list(available_tools.keys())[:5]  # Primeras 5
            for tool_name in main_tools:
                tools_context += f"• {tool_name}\n"
            if len(available_tools) > 5:
                tools_context += f"• ... y {len(available_tools) - 5} más\n"
        
        # ✅ CONTEXTO DE HERRAMIENTAS USADAS POR EL ROUTER
        router_analysis = ""
        tool_result = state.get("tool_result", "")
        if tool_result:
            tool_used = state.get("tool", "")
            router_analysis = f"\n\n🔧 **ACCIÓN REALIZADA:**\n"
            router_analysis += f"Herramienta usada: {tool_used}\n"
            router_analysis += f"Resultado: {tool_result}\n"
        
        # ✅ CONTEXTO DE CONVERSACIÓN
        conversation_history = state.get("conversation_history", [])
        memory_section = ""
        if conversation_history:
            memory_section = "\n\n📚 **CONTEXTO DE CONVERSACIÓN:**\n"
            for i, msg in enumerate(conversation_history[-2:]):  # Solo últimos 2
                msg_type = "Usuario" if isinstance(msg, HumanMessage) else "Ava"
                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                memory_section += f"{i+1}. {msg_type}: {content}\n"
        
        # ✅ PROMPT FINAL CONVERSACIONAL
        full_prompt = f"""{base_prompt}

{tools_context}

{router_analysis}

{memory_section}

**INSTRUCCIONES PARA RESPUESTA:**

1. **RESPONDE** de manera conversacional y amigable
2. **USA** el contexto de herramientas si están disponibles
3. **INCORPORA** los resultados de acciones previas si los hay
4. **MANTÉN** el tono personalizado según el role_prompt
5. **NO** generes JSON ni código técnico
6. **SÉ** útil y específico en tus respuestas

**GENERA UNA RESPUESTA NATURAL AL USUARIO:**"""

        return full_prompt

    def process(self, state: AgentState) -> AgentState:
        """Procesar AgentNode - RESPUESTA FINAL SIN RECONEXIONES"""
        try:
            print(f"🤖 AgentNode generando respuesta conversacional...")
            
            available_tools = state.get("available_tools", {})
            print(f"   🔧 Herramientas del state: {len(available_tools)}")
            print(f"   📚 Historial: {len(state.get('conversation_history', []))} mensajes")
            print(f"   🔧 Tool result: {len(state.get('tool_result', ''))} chars")
            
            # ✅ FILTRAR MENSAJES DEL ROUTER (técnicos)
            messages = state["messages"]
            user_messages = []
            
            for msg in messages:
                # ✅ INCLUIR mensajes del usuario y respuestas finales (no técnicas)
                if isinstance(msg, HumanMessage):
                    user_messages.append(msg)
                elif isinstance(msg, AIMessage):
                    # Solo incluir si no es análisis técnico
                    if not msg.content.startswith("[ANÁLISIS") and not "```json" in msg.content:
                        user_messages.append(msg)
            
            # ✅ GENERAR PROMPT CONVERSACIONAL
            conversational_prompt = self.agent_prompt(state)
            
            # ✅ GENERAR RESPUESTA FINAL
            response = self.chain.invoke({
                "agent_prompt": conversational_prompt,
                "messages": user_messages  # Solo mensajes relevantes para conversación
            })
            
            print(f"   ✅ AgentNode respuesta: {response.content[:50]}...")
            
            # ✅ CREAR ESTADO FINAL
            return {
                "messages": user_messages + [response],  # Conversación limpia
                "conversation_history": state.get("conversation_history", []),
                "node": "agent_completed",
                "tool": state.get("tool", ""),
                "tool_result": state.get("tool_result", ""),
                "timestamp": datetime.now(),
                "available_tools": available_tools  # ✅ PRESERVAR herramientas
            }
            
        except Exception as e:
            print(f"❌ Error en AgentNode: {e}")
            import traceback
            traceback.print_exc()
            return {
                **state,
                "node": "agent_error",
                "timestamp": datetime.now(),
                "error": str(e)
            }

def create_agent_node():
    """Crear función del AgentNode SIN RECONEXIONES"""
    agent = AgentNode()
    
    def agent_function(state: AgentState) -> AgentState:
        return agent.process(state)
    
    return agent_function

# ❌ ELIMINAR TODAS LAS FUNCIONES DE PRUEBA QUE USAN MCP
# def test_with_mcp_tools():         # ← ELIMINAR
# def test_schema_extraction():      # ← ELIMINAR  
# def test_schema_comparison():      # ← ELIMINAR

def test_agent_conversation():
    """Prueba simple del AgentNode SIN MCP"""
    print("🤖 === PRUEBA: AGENTNODE CONVERSACIONAL ===")
    print("📋 Verificando respuesta conversacional sin reconexiones")
    print("="*60)
    
    try:
        # ✅ CREAR STATE SIMULADO (sin MCP)
        test_state = {
            "messages": [HumanMessage(content="¡Hola! ¿Cómo estás?")],
            "conversation_history": [],
            "node": "router_completed",
            "tool": "",
            "tool_result": "",
            "timestamp": datetime.now(),
            "available_tools": {  # ✅ Herramientas simuladas
                "gmail": "Enviar correos electrónicos",
                "search": "Buscar información en línea",
                "calendar": "Gestionar calendario"
            }
        }
        
        print(f"📊 STATE DE PRUEBA:")
        print(f"   • Mensaje: {test_state['messages'][0].content}")
        print(f"   • Herramientas simuladas: {len(test_state['available_tools'])}")
        
        # ✅ CREAR AGENTE Y PROBAR
        agent = AgentNode()
        result = agent.process(test_state)
        
        # ✅ MOSTRAR RESULTADO
        response = result['messages'][-1].content
        print(f"\n📤 RESPUESTA DEL AGENTE:")
        print(f"   • Estado final: {result['node']}")
        print(f"   • Longitud: {len(response)} caracteres")
        print(f"   • Es conversacional: {'hola' in response.lower() or 'bien' in response.lower()}")
        
        print(f"\n📝 RESPUESTA COMPLETA:")
        print(f"{response}")
        
        print("\n✅ AgentNode responde conversacionalmente SIN reconexiones MCP")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Función principal - Solo pruebas SIN MCP"""
    print("🤖 === AGENTNODE SIN RECONEXIONES MCP ===")
    print("📋 AgentNode conversacional usando role_prompt")
    print("="*60)
    
    # ✅ Prueba simple sin MCP
    test_agent_conversation()
    
    print("\n" + "="*60)
    print("✅ AGENTNODE CORREGIDO:")
    print("   • Sin imports de funciones MCP")
    print("   • Usa solo available_tools del state")
    print("   • Respuestas conversacionales con role_prompt")
    print("   • Sin reconexiones innecesarias")
    print("="*60)

if __name__ == "__main__":
    main()

