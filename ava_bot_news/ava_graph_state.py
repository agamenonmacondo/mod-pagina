from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq
from typing import Any, Dict, List, TypedDict, Annotated, Optional
import sys
import os
import json
from datetime import datetime

# ✅ IMPORTAR SOLO CLASES Y TIPOS - NO FUNCIONES DE CONEXIÓN
# from mcp_client import AvaToolsClient  # ✅ Solo la clase, no connect_to_ava

# ✅ AgentState LIMPIO Y OPTIMIZADO
class AgentState(TypedDict, total=False):
    """Estado del agente con tipado correcto para LangGraph - SIN DUPLICADOS"""
    
    # ✅ MENSAJES PRINCIPALES
    messages: List[AIMessage | HumanMessage]
    conversation_history: Optional[List[AIMessage | HumanMessage]]
    
    # ✅ PLAN Y EJECUCIÓN
    execution_plan: Optional[Dict[str, Any]]
    plan_status: Optional[Dict[str, Any]]
    
    # ✅ HERRAMIENTAS - CAMPOS ESENCIALES
    tool_to_execute: Optional[str]
    tool_arguments: Optional[Dict[str, Any]]
    tool_result: Optional[str]
    available_tools: Optional[Dict[str, Any]]
    
    # ✅ CONTROL DE FLUJO
    node: Optional[str]
    
    # ✅ SESIÓN Y METADATOS
    user_id: Optional[str]
    session_id: Optional[str]
    timestamp: Optional[datetime]
    
    # ✅ MANEJO DE ERRORES
    error_message: Optional[str]
    context_memory: Optional[Dict[str, Any]]  # ✅ Campo opcional para memoria de contexto
# ❌ ELIMINAR CLIENTE GLOBAL - El bot lo maneja
# _global_ava_client = None

# ❌ ELIMINAR FUNCIONES QUE CONECTAN - El bot las maneja
# def get_or_create_ava_client():
# def get_available_tools():
# def get_tool_schemas():

# ✅ ARREGLAR create_initial_state para usar AgentState correcto
def create_initial_state(user_input: str, ava_client = None) -> AgentState:
    """Crear estado inicial usando AgentState definido"""
    from langchain_core.messages import HumanMessage
    from datetime import datetime
    
    # ✅ USAR EXACTAMENTE LOS CAMPOS DE TU AGENTSTATE
    state = {
        "messages": [HumanMessage(content=user_input)],
        "conversation_history": [],
        "execution_plan": {},           # ✅ Campo del AgentState
        "plan_status": {},              # ✅ Campo del AgentState
        "tool_to_execute": None,        # ✅ Campo del AgentState - ESTE FALTABA
        "tool_arguments": {},           # ✅ Campo del AgentState - ESTE FALTABA
        "tool_result": "",              # ✅ Campo del AgentState
        "available_tools": ava_client.list_tools() if ava_client else {},
        "node": "start",                # ✅ Campo del AgentState
        "user_id": "default_user",      # ✅ Campo del AgentState
        "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(),    # ✅ Campo del AgentState
        "error_message": None ,          # ✅ Campo del AgentState
        "context_memory":{},
        
          # ✅ Campo opcional para memoria de contexto

    }
    
    return state

# ✅ ARREGLAR create_state_with_history para preservar campos correctos
def create_state_with_history(user_input: str, previous_state: AgentState, ava_client = None) -> AgentState:
    """Crear estado con historial usando AgentState correcto"""
    from langchain_core.messages import HumanMessage
    from datetime import datetime
    
    new_message = HumanMessage(content=user_input)
    
    # ✅ USAR EXACTAMENTE LOS CAMPOS DE TU AGENTSTATE
    new_state = {
        "messages": [new_message],  # Solo el nuevo mensaje
        "conversation_history": previous_state.get("conversation_history", []) + previous_state.get("messages", []),
        # ✅ PRESERVAR RESULTADOS PARA QUE CONVERSATIONAL LOS VEA
        "execution_plan": previous_state.get("execution_plan", {}),      # ✅ Preservar plan
        "plan_status": previous_state.get("plan_status", {}),            # ✅ Preservar status CON RESULTADOS
        "tool_to_execute": None,        # ✅ Limpiar herramienta anterior
        "tool_arguments": {},           # ✅ Limpiar argumentos anteriores
        "tool_result": previous_state.get("tool_result", ""),            # ✅ Preservar resultado ACTUAL
        "available_tools": previous_state.get("available_tools", {}),    # ✅ Preservar herramientas
        "node": "start",                # ✅ Reiniciar flujo
        "user_id": previous_state.get("user_id", "default_user"),
        "session_id": previous_state.get("session_id"),
        "timestamp": datetime.now(),
        "error_message": None,
        "context_memory":  previous_state.get("context_memory", {})

    }
    
    return new_state

def state_limit(state: AgentState, max_messages: int = 5) -> AgentState:
    """Limitar el número de mensajes en el estado"""
    if len(state["messages"]) > max_messages:
        state["messages"] = state["messages"][-max_messages:]
    
    if len(state["conversation_history"]) > max_messages:
        state["conversation_history"] = state["conversation_history"][-max_messages:]
    
    return state  

# ❌ ELIMINAR FUNCIONES DUPLICADAS:
# def create_conversation_node():      # Ya existe en otros archivos
# def create_planner_node():           # Ya existe en ava_graph_planner.py
# def create_orchestrator_node():      # Ya existe en ava_graph_orchestrator.py
# def create_summary_agent_node():     # Ya existe en ava_graph_summary_agent.py

# ✅ MANTENER SOLO LAS FUNCIONES DE UTILIDAD:
def update_conversation_history(state: AgentState) -> AgentState:
    """Actualizar historial"""
    current_messages = state["messages"]
    current_history = state["conversation_history"]
    
    updated_history = current_history + current_messages
    
    # Limitar historial
    max_history = 10
    if len(updated_history) > max_history:
        updated_history = updated_history[-max_history:]
    
    # ✅ PRESERVAR TODOS LOS CAMPOS DEL AGENTSTATE
    return {
        "messages": [],
        "conversation_history": updated_history,
        "execution_plan": state.get("execution_plan", {}),     # ✅ Preservar
        "plan_status": state.get("plan_status", {}),           # ✅ Preservar
        "tool_to_execute": state.get("tool_to_execute"),       # ✅ Preservar
        "tool_arguments": state.get("tool_arguments", {}),     # ✅ Preservar
        "tool_result": state.get("tool_result", ""),
        "available_tools": state.get("available_tools", {}),
        "node": state.get("node", "updated"),
        "user_id": state.get("user_id"),
        "session_id": state.get("session_id"),
        "timestamp": datetime.now(),
        "error_message": state.get("error_message"),
        "context_memory": state.get("context_memory", {})
    }

def convert_state_to_json(state: AgentState) -> Dict[str, Any]:
    """Convertir estado a JSON serializable"""
    json_result = {}
    
    for key, value in state.items():
        if key in ["messages", "conversation_history"]:
            messages_json = []
            for i, msg in enumerate(value):
                messages_json.append({
                    "index": i + 1,
                    "type": type(msg).__name__,
                    "content": str(msg.content) if hasattr(msg, 'content') else str(msg)
                })
            json_result[key] = messages_json
        elif key == "timestamp":
            json_result[key] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
        else:
            json_result[key] = value
    
    return json_result

def get_conversation_summary(state: AgentState) -> Dict[str, Any]:
    """Obtener resumen de conversación SIN RECONECTAR"""
    history = state["conversation_history"]
    current = state["messages"]
    available_tools = state.get("available_tools", {})
    
    return {
        "total_messages": len(history) + len(current),
        "history_messages": len(history),
        "current_messages": len(current),
        "last_message": current[-1].content if current else None,
        "conversation_active": len(history) > 0,
        "available_tools_count": len(available_tools),
        "state_size": len(str(state))
    }

# ❌ ELIMINAR TODAS LAS FUNCIONES QUE CONECTAN:
# def get_or_create_ava_client():
# def get_available_tools():
# def get_tool_schemas():
# def format_tools_for_prompt():
# def get_mcp_tools_with_schema_via_client():
# def cleanup_ava_client():

def main():
    """Prueba SIN conexiones automáticas"""
    print("🧪 PRUEBA SIN CONEXIONES AUTOMÁTICAS")
    print("-" * 50)
    
    try:
        # ✅ CREAR estado SIN cliente (modo desconectado)
        state = create_initial_state("Prueba sin conexión automática")
        
        # Verificar que NO hay herramientas
        tools = state.get("available_tools", {})
        print(f"✅ Herramientas sin cliente: {len(tools)}")
        
        if not tools:
            print("   ✅ Correcto: No hay herramientas sin cliente del bot")
        
        print("✅ State funciona sin conexiones automáticas")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()