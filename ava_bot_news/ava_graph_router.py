from langgraph.graph import StateGraph, MessagesState
from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq
from typing import Any, Dict, List, TypedDict, Tuple
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import json
import re
from dotenv import load_dotenv
import os
from datetime import datetime

# ✅ SOLO IMPORTAR AGENTSTATE
from ava_graph_state import AgentState

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")

class RouterNode:
    """RouterNode - COMPLETAMENTE SIN RECONEXIONES"""
    
    def __init__(self):
        self.llm = ChatGroq(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            api_key=GROQ_API_KEY,
            temperature=0.3,
            max_tokens=800,
        )
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "{agent_prompt}"),
            MessagesPlaceholder(variable_name="messages")
        ])
        
        self.chain = self.prompt_template | self.llm

    def _execute_tool_via_global_client(self, tool_name: str, arguments: dict) -> Tuple[str, str]:
        """Ejecutar herramienta USANDO CLIENTE GLOBAL"""
        try:
            print(f"🔧 Ejecutando {tool_name} con cliente global")
            
            # ✅ IMPORTAR Y USAR CLIENTE GLOBAL
            from ava_graph_bot import get_global_ava_client
            ava_client = get_global_ava_client()
            
            if not ava_client:
                return tool_name, "❌ Sin cliente global"
            
            if not hasattr(ava_client, 'connected') or not ava_client.connected:
                return tool_name, "❌ Cliente global desconectado"
            
            # ✅ USAR MÉTODO DEL CLIENTE GLOBAL
            if hasattr(ava_client, 'use_tool'):
                result = ava_client.use_tool(tool_name, **arguments)
                if result.get("success"):
                    return tool_name, f"✅ {result.get('result', 'Ejecutado')}"
                else:
                    return tool_name, f"❌ {result.get('error', 'Error desconocido')}"
            else:
                return tool_name, f"✅ Simulado: {tool_name} con {arguments}"
                
        except Exception as e:
            return tool_name, f"❌ Error: {e}"

    def router_prompt(self, state: AgentState) -> str:
        """Prompt usando SOLO datos del state"""
        
        base_prompt = "Eres Ava, un asistente inteligente y conversacional."
        
        # ✅ HERRAMIENTAS DEL STATE
        available_tools = state.get("available_tools", {})
        
        if available_tools:
            tools_section = f"\n\n🔧 HERRAMIENTAS ({len(available_tools)}):\n"
            for tool_name, tool_desc in available_tools.items():
                tools_section += f"- {tool_name}: {tool_desc}\n"
        else:
            tools_section = "\n\n⚠️ Modo conversación - sin herramientas MCP"
        
        # ✅ CONTEXTO SIMPLE
        conversation_history = state.get("conversation_history", [])
        memory_section = ""
        if conversation_history:
            memory_section = "\n\n📚 CONTEXTO:\n"
            for i, msg in enumerate(conversation_history[-2:]):
                msg_type = "Usuario" if isinstance(msg, HumanMessage) else "Ava"
                content = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
                memory_section += f"{i+1}. {msg_type}: {content}\n"
        
        prompt = f"""{base_prompt}

{tools_section}

{memory_section}

**INSTRUCCIONES:**
1. Analiza la solicitud del usuario
2. Responde de manera conversacional y útil
3. Si hay herramientas y necesitas usarlas, incluye JSON:

```json
{{
  "use_tool": "nombre_herramienta",
  "arguments": {{"param": "valor"}}
}}
```

**RESPUESTA:**"""

        return prompt

    def process(self, state: AgentState) -> AgentState:
        """Procesar RouterNode SIN RECONECTAR JAMÁS"""
        try:
            print(f"🔀 RouterNode procesando (ABSOLUTO sin reconexión)...")
            
            available_tools = state.get("available_tools", {})
            print(f"   🔧 Herramientas: {len(available_tools)}")
            
            # ✅ GENERAR PROMPT
            dynamic_prompt = self.router_prompt(state)
            
            # ✅ EJECUTAR LLM
            response = self.chain.invoke({
                "agent_prompt": dynamic_prompt,
                "messages": state["messages"]
            })
            
            print(f"   💬 Respuesta: {response.content[:50]}...")
            
            # ✅ BUSCAR JSON SOLO SI HAY HERRAMIENTAS
            tool_used = ""
            tool_result = ""
            
            if available_tools:
                try:
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response.content, re.DOTALL)
                    if json_match:
                        tool_call = json.loads(json_match.group(1))
                        tool_name = tool_call.get("use_tool")
                        arguments = tool_call.get("arguments", {})
                        
                        if tool_name in available_tools:
                            tool_used, tool_result = self._execute_tool_via_global_client(tool_name, arguments)
                except Exception as e:
                    tool_result = f"❌ Error procesando herramienta: {e}"
            
            # ✅ CREAR RESPUESTA FINAL
            if tool_result:
                final_content = f"{response.content}\n\n🔧 **RESULTADO:**\n{tool_result}"
            else:
                final_content = response.content
            
            final_message = AIMessage(content=final_content)
            
            return {
                "messages": state["messages"] + [final_message],
                "conversation_history": state.get("conversation_history", []),
                "node": "router_completed",
                "tool": tool_used,
                "tool_result": tool_result,
                "timestamp": datetime.now(),
                "available_tools": available_tools
            }
            
        except Exception as e:
            print(f"❌ Error RouterNode: {e}")
            return {
                **state,
                "node": "router_error",
                "timestamp": datetime.now(),
                "error": str(e)
            }

def create_router_node():
    """Crear RouterNode limpio"""
    router = RouterNode()
    
    def router_function(state: AgentState) -> AgentState:
        return router.process(state)
    
    return router_function

