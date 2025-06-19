import os
import sys
from datetime import datetime
from langgraph.graph import StateGraph, END
from ava_graph_state import AgentState
from ava_graph_planner import create_planner_node
from ava_graph_orchestrator import OrchestratorNode, create_orchestrator_node
from ava_graph_agent import create_agent_node, ConversationalNode
from ava_graph_summary_agent import SummaryAgent,ShortMemoryContext,create_summary_node,create_short_memory_context_node
from mcp_client import connect_to_ava
from langchain_core.messages import AIMessage, HumanMessage



_global_ava_client = None

def initialize_ava_client():
    global _global_ava_client
    _global_ava_client = connect_to_ava()
    return _global_ava_client

def get_global_ava_client():
    global _global_ava_client
    if _global_ava_client is None:
        initialize_ava_client()
    return _global_ava_client

class MCPToolExecutor:
    """Clase dedicada para ejecutar herramientas del servidor MCP"""
    
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.available_tools = mcp_client.list_tools() if mcp_client else {}
        
        self.tool_mapping = {
            "SEARCH": "search",
            "PLAYWRIGHT": "playwright", 
            "MEMORY": "memory",
            "GMAIL": "gmail",
            "IMAGE": "image",
            "MEET": "meet",
            "CALENDAR": "calendar",
            "VISION": "vision",
            "FILE_MANAGER": "file_manager",
            "OPENAI_TTS": "openai_tts",
            "GROQ_SPEECH": "groq_speech",
            "MULTIMODAL_MEMORY": "multimodal_memory",
            "IMAGE_DISPLAY": "image_display"
        }
    
    def execute_tool(self, tool_name: str, arguments: dict):
        """Ejecutar una herramienta específica"""
        actual_tool_name = self.tool_mapping.get(tool_name.upper(), tool_name.lower())
        
        print(f"🔧 MCPToolExecutor ejecutando: {actual_tool_name}")
        print(f"   📝 Argumentos: {arguments}")
        
        result = self.mcp_client.use_tool(actual_tool_name, **arguments)
        
        print(f"   ✅ Resultado tipo: {type(result)}")
        
        if isinstance(result, dict):
            if result.get("success", True):
                return {
                    "success": True,
                    "result": result.get("result", str(result)),
                    "raw_result": result.get("raw_result", "")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Error desconocido"),
                    "result": ""
                }
        else:
            return {
                "success": True,
                "result": str(result),
                "raw_result": str(result)
            }
    
    def is_tool_available(self, tool_name: str) -> bool:
        """Verificar si una herramienta está disponible"""
        actual_tool_name = self.tool_mapping.get(tool_name.upper(), tool_name.lower())
        return actual_tool_name in self.available_tools
    
    def get_available_tools(self) -> dict:
        """Obtener lista de herramientas disponibles"""
        return self.available_tools.copy()

def create_tool_executor_node():
    """Nodo que ejecuta herramientas usando MCPToolExecutor - CORREGIDO"""
    def tool_executor_function(state):
        tool_name = state.get("tool_to_execute")
        tool_arguments = state.get("tool_arguments", {})
        current_step_info = state.get("current_step_info", {})
        
        print(f"🔧 TOOL EXECUTOR - Ejecutando: {tool_name}")
        print(f"   📝 Argumentos: {tool_arguments}")
        
        ava_client = get_global_ava_client()
        tool_executor = MCPToolExecutor(ava_client)
        
        print(f"   🚀 Ejecutando {tool_name} con MCPToolExecutor...")
        result = tool_executor.execute_tool(tool_name, tool_arguments)
        
        if result.get("success", False):
            tool_result = result.get("result", "")
            print(f"   ✅ Herramienta ejecutada exitosamente")
            print(f"   📊 Resultado: {len(str(tool_result))} caracteres")
            
            step_result = {
                "tool": tool_name,
                "arguments": tool_arguments,
                "result": tool_result,
                "success": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            error_msg = result.get("error", "Error desconocido")
            tool_result = f"Error: {error_msg}"
            print(f"   ❌ Error en herramienta: {error_msg}")
            
            step_result = {
                "tool": tool_name,
                "arguments": tool_arguments,
                "error": error_msg,
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
        
        state["tool_result"] = tool_result
        
        # ✅ CRÍTICO: ACTUALIZAR EL PLAN_STATUS DESPUÉS DE EJECUTAR
        if "plan_status" not in state:
            state["plan_status"] = {}
        if "results" not in state["plan_status"]:
            state["plan_status"]["results"] = []
        
        # 🔥 AGREGAR ESTA LÍNEA FALTANTE:
        state["plan_status"]["results"].append(step_result)
        
        # ✅ INCREMENTAR PASO ACTUAL
        current_step = state.get("plan_status", {}).get("current_step", 0)
        state["plan_status"]["current_step"] = current_step + 1
        
        print(f"   ✅ {tool_name} completado - avanzando a paso {current_step + 1}")
        print(f"   📊 Guardado en results: {len(state['plan_status']['results'])} resultados")
        
        # ✅ LIMPIAR HERRAMIENTAS Y MARCAR COMPLETADO
        state["tool_to_execute"] = None
        state["tool_arguments"] = {}
        state["current_step_info"] = {}
        state["node"] = "tool_executor_completed"
        
        return state
    
    return tool_executor_function

def create_orchestrator_success_node():
    """Nodo para manejar cuando la orquestación es exitosa"""
    def orchestrator_success_function(state):
        print("✅ ORCHESTRATOR SUCCESS - Plan completado exitosamente")
        
        if "plan_status" not in state:
            state["plan_status"] = {}
        
        state["plan_status"]["completed"] = True
        state["node"] = "orchestrator_completed"
        
        results = state.get("plan_status", {}).get("results", [])
        successful_tools = [r for r in results if r.get("success", False)]
        failed_tools = [r for r in results if not r.get("success", False)]
        
        print(f"   📊 Herramientas exitosas: {len(successful_tools)}")
        print(f"   📊 Herramientas fallidas: {len(failed_tools)}")
        
        return state
    
    return orchestrator_success_function

def create_conversational_node():
    """Crear nodo conversacional usando ConversationalNode"""
    conversational_agent = ConversationalNode()
    
    def conversational_function(state):
        print("💬 CONVERSATIONAL NODE (LLM) - Procesando con LLM...")
        return conversational_agent.process(state)
    
    return conversational_function

def planner_decision(state):
    node = state.get("node", "")
    if node == "planner_completed":
        return "orchestrator"
    else:
        return "conversational"

def orchestrator_decision(state):
    """Decisión del orchestrator principal"""
    tool_to_execute = state.get("tool_to_execute")
    plan_status = state.get("plan_status", {})
    node = state.get("node", "")
    
    print(f"🤖 ORCHESTRATOR DECISION:")
    print(f"   🔧 Tool to execute: {tool_to_execute}")
    print(f"   🎯 Node actual: {node}")
    print(f"   📊 Plan completado: {plan_status.get('completed', False)}")
    
    if node == "orchestrator_step_ready" and tool_to_execute:
        print(f"   ➡️ Ejecutar herramienta: {tool_to_execute}")
        return "tool_executor"
    elif node == "orchestrator_completed" or plan_status.get("completed", False):
        print(f"   ➡️ Plan completado -> SUCCESS")
        return "orchestrator_success"
    elif node == "orchestrator_error":
        print(f"   ➡️ Error -> CONVERSATIONAL")
        return "conversational"
    else:
        print(f"   ➡️ Estado intermedio -> SUCCESS")
        return "orchestrator_success"

def tool_executor_decision(state):
    """Decisión después de ejecutar herramienta"""
    node = state.get("node", "")
    
    print(f"🔧 TOOL EXECUTOR DECISION:")
    print(f"   🎯 Node: {node}")
    
    # ✅ SIEMPRE REGRESAR AL ORCHESTRATOR
    if node in ["tool_executor_completed", "tool_executor_error"]:
        print(f"   ➡️ DECISION: Regresar al ORCHESTRATOR")
        return "orchestrator"
    else:
        print(f"   ➡️ DECISION: Estado desconocido -> ORCHESTRATOR")
        return "orchestrator"

def orchestrator_success_decision(state: AgentState) -> str:
    """Decidir qué hacer después del éxito del orchestrator"""
    
    print("🎯 SUCCESS DECISION: Analizando resultados...")
    
    # ✅ OBTENER RESULTADOS DE PLAN_STATUS
    plan_status = state.get("plan_status", {})
    results = plan_status.get("results", [])
    
    # ✅ CONTAR HERRAMIENTAS EXITOSAS
    successful_tools = [r for r in results if r.get("success", False)]
    
    print(f"   📊 Herramientas exitosas: {len(successful_tools)}")
    
    # ✅ SIEMPRE IR AL CONVERSATIONAL PRIMERO
    print(f"   ➡️ DECISION: Plan completado → CONVERSATIONAL")
    return "conversational"

def create_graph():
    """Crear el grafo StateGraph con todos los nodos"""
    
    workflow = StateGraph(AgentState)
    
    orchestrator_node = OrchestratorNode()
    
    workflow.add_node("planner", create_planner_node())
    workflow.add_node("orchestrator", orchestrator_node.process)
    workflow.add_node("tool_executor", create_tool_executor_node())
    workflow.add_node("conversational", create_conversational_node())
    workflow.add_node("orchestrator_success", create_orchestrator_success_node())
    workflow.add_node("summary", create_summary_node())
    workflow.add_node("short_memory_context", create_short_memory_context_node())
    
    workflow.set_entry_point("short_memory_context")

    workflow.add_edge("short_memory_context", "planner")
    
    workflow.add_conditional_edges("planner", planner_decision, {
        "orchestrator": "orchestrator",
        "conversational": "conversational"
    })
    
    workflow.add_conditional_edges("orchestrator", orchestrator_decision, {
        "tool_executor": "tool_executor",
        "orchestrator_success": "orchestrator_success",
        "conversational": "conversational",
        "summary": "summary"
    })
    
    workflow.add_conditional_edges("tool_executor", tool_executor_decision, {
        "orchestrator": "orchestrator"
    })
    
    # ✅ SIMPLIFICAR: orchestrator_success SIEMPRE va a conversational
    workflow.add_conditional_edges("orchestrator_success", orchestrator_success_decision, {
        "conversational": "conversational"
    })
    
    # ✅ FLUJO CORRECTO: conversational → summary → END
    workflow.add_edge("conversational", "summary")
    workflow.add_edge("summary", END)
    
    return workflow.compile()

def run_graph(user_input: str):
    """Ejecutar el grafo con input del usuario"""
    print("🔄 Inicializando cliente MCP...")
    ava_client = initialize_ava_client()
    
    print("🔄 Creando grafo...")
    graph = create_graph()
    
    # ✅ ESTADO INICIAL COMPLETO CON TODAS LAS VARIABLES DEL AgentState
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "conversation_history": [],
        "available_tools": ava_client.list_tools() if ava_client else {},
        "execution_plan": {},
        "plan_status": {},  
        "tool_to_execute": None,
        "tool_arguments": {},   
        "tool_result": "",
        "node": "start",    
        "user_id": "default_user",
        "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(),
        "error_message": None,
        "context_memory": []  # ← AGREGAR ESTA LÍNEA FALTANTE
    }
    
    print(f"🚀 Ejecutando grafo con input: {user_input}")
    print(f"📊 Estado inicial completo:")
    print(f"   📝 Messages: {len(initial_state['messages'])}")
    print(f"   📚 Conversation history: {len(initial_state['conversation_history'])}")
    print(f"   🛠️ Available tools: {len(initial_state['available_tools'])}")
    print(f"   📋 Execution plan: {'Vacío' if not initial_state['execution_plan'] else 'Disponible'}")
    print(f"   📊 Plan status: {'Vacío' if not initial_state['plan_status'] else 'Disponible'}")
    print(f"   🔧 Tool to execute: {initial_state['tool_to_execute']}")
    print(f"   ⚙️ Tool arguments: {'Vacíos' if not initial_state['tool_arguments'] else 'Disponibles'}")
    print(f"   📤 Tool result: {'Vacío' if not initial_state['tool_result'] else 'Disponible'}")
    print(f"   🎯 Node: {initial_state['node']}")
    print(f"   👤 User ID: {initial_state['user_id']}")
    print(f"   🆔 Session ID: {initial_state['session_id']}")
    print(f"   ⏰ Timestamp: {initial_state['timestamp']}")
    print(f"   ❌ Error message: {initial_state['error_message']}")
    
    result = graph.invoke(initial_state)
    
    