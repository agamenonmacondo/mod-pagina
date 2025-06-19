# ✅ IMPORTS REORGANIZADOS
from ava_graph_state import (
    AgentState, 
    create_initial_state, 
    create_state_with_history,
    update_conversation_history,
    convert_state_to_json,
    get_conversation_summary
)
from ava_ghaph_grafo import create_graph
from langchain_core.messages import HumanMessage, AIMessage
import json
import uuid
import os
import threading
import time
import subprocess
import sys
from datetime import datetime
from typing import Optional, Dict, Any

# ✅ IMPORTAR SERVIDOR Y CLIENTE
from mcp_server.run_server import AvaBotServicer, CleanMCPServer
from mcp_client import AvaToolsClient, connect_to_ava

# ✅ IMPORTAR CLIENTE GLOBAL INDEPENDIENTE
from ava_client import set_global_ava_client, get_global_ava_client, cleanup_global_client

# ✅ SOLO VARIABLES LOCALES
_server_process = None

def start_server_parallel(port: int = 50051) -> bool:
    """Iniciar servidor gRPC en paralelo - VERSIÓN SIMPLIFICADA"""
    global _server_process
    
    try:
        server_script = os.path.join(os.path.dirname(__file__), "mcp_server", "run_server.py")
        
        if not os.path.exists(server_script):
            return False
        
        _server_process = subprocess.Popen(
            [sys.executable, server_script],
            cwd=os.path.dirname(server_script),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )
        
        return True
        
    except Exception:
        return False

def wait_for_server(max_seconds: int = 30) -> bool:
    """Esperar servidor - VERSIÓN SIMPLIFICADA"""
    
    for i in range(max_seconds):
        try:
            client = AvaToolsClient()
            if client.connect():
                client.cleanup()
                return True
        except:
            pass
        
        time.sleep(1)
    
    return False

def check_dependencies() -> bool:
    """Verificar dependencias básicas"""
    try:
        import grpc
        return True
    except ImportError:
        return False


class AvaGraphBot:
    """Bot simplificado con servidor paralelo"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.current_state: Optional[AgentState] = None
        self.conversation_active = False
        self.thread_id = str(uuid.uuid4())
        
        self.graph = None
        self.ava_client = None
        self.config = None
        
        self._initialize()
    
    def _initialize(self):
        """Inicialización simplificada"""
        try:
            # 1. Verificar dependencias
            if not check_dependencies():
                raise Exception("Dependencias faltantes")
            
            # 2. Servidor paralelo
            self._setup_server()
            
            # 3. Cliente MCP
            self._setup_client()
            
            # 4. Grafo (obligatorio)
            self.graph = create_graph()
            if not self.graph:
                raise Exception("Error creando grafo")
            
            # 5. Config
            self.config = {"configurable": {"thread_id": self.thread_id}}
            
        except Exception as e:
            raise
    
    def _setup_server(self) -> bool:
        """Setup servidor simplificado"""
        # Verificar si ya existe
        try:
            client = AvaToolsClient()
            if client.connect():
                client.cleanup()
                return True
        except:
            pass
        
        # Iniciar nuevo
        if start_server_parallel():
            return wait_for_server(30)
        return False
    
    def _setup_client(self) -> bool:
        """Setup cliente simplificado"""
        try:
            self.ava_client = AvaToolsClient()
            if self.ava_client.connect():
                set_global_ava_client(self.ava_client)  # ✅ Usar función independiente
                return True
        except Exception:
            pass
        
        return False
    
    def chat(self, user_input: str) -> Dict[str, Any]:
        """Chat simplificado - SOLO MENSAJE FINAL PARA WEBHOOK"""
        
        try:
            # Preparar estado
            if self.conversation_active and self.current_state:
                state = create_state_with_history(user_input, self.current_state)
            else:
                state = create_initial_state(user_input)
                self.conversation_active = True
            
            # Añadir herramientas disponibles
            if self.ava_client and self.ava_client.tools:
                state["available_tools"] = self.ava_client.tools.copy()
            
            # ✅ EJECUTAR GRAFO
            final_result = None
            ava_response = None
            
            for step in self.graph.stream(state, config=self.config):
                for node_name, node_state in step.items():
                    # ✅ CAPTURAR RESPUESTA SIN IMPRIMIR ESTADO
                    if node_name == "conversational" and not ava_response:
                        try:
                            messages = node_state.get('messages', []) if node_state else []
                            
                            for msg in reversed(messages):
                                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                                    if hasattr(msg, 'content') and msg.content and msg.content.strip():
                                        ava_response = msg.content
                                        break
                        except Exception as e:
                            pass  # Silenciar errores de captura
                    
                    # ✅ GUARDAR EL ÚLTIMO RESULTADO VÁLIDO
                    if node_state is not None:
                        final_result = node_state
            
            # ✅ EXTRAER RESPUESTA FINAL SI NO SE CAPTURÓ
            if not ava_response:
                try:
                    result_to_use = final_result or state
                    messages = result_to_use.get('messages', []) if result_to_use else []
                    for msg in reversed(messages):
                        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                            if hasattr(msg, 'content') and msg.content and msg.content.strip():
                                ava_response = msg.content
                                break
                except Exception as e:
                    ava_response = "Error procesando respuesta"
            
            # ✅ IMPRIMIR SOLO EL MENSAJE DEL AGENTE
            if ava_response:
                print(ava_response)
            
            # Actualizar estado
            try:
                self.current_state = update_conversation_history(final_result or state)
            except Exception as e:
                self.current_state = final_result or state
            
            # ✅ RETORNAR RESPUESTA PARA WEBHOOK
            return {
                "error": False,
                "message": ava_response or "Respuesta procesada",
                "session_id": (final_result or state).get("session_id", ""),
                "user_id": (final_result or state).get("user_id", "")
            }
            
        except Exception as e:
            error_msg = f"Error en chat(): {e}"
            print(error_msg)
            return {"error": True, "error_message": error_msg}
    
    def _show_response(self, result: AgentState):
        """Mostrar respuesta - SIMPLIFICADO PARA WEBHOOK"""
        # Obtener messages del state final
        messages = result.get('messages', [])
        
        # Buscar el último AIMessage
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    return msg.content
        
        # Si no encuentra AIMessage, buscar en conversation_history
        conversation_history = result.get('conversation_history', [])
        for msg in reversed(conversation_history):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    return msg.content
        
        return "Procesamiento completado."
    
    def reset_conversation(self):
        """Reset simplificado"""
        self.current_state = None
        self.conversation_active = False
        self.thread_id = str(uuid.uuid4())
        
        self.config["configurable"]["thread_id"] = self.thread_id
    
    def get_status(self) -> Dict[str, Any]:
        """Status simplificado"""
        global _server_process
        
        return {
            "bot_ready": bool(self.graph),
            "mcp_connected": bool(self.ava_client and self.ava_client.connected),
            "tools_count": len(self.ava_client.tools) if self.ava_client and self.ava_client.tools else 0,
            "server_running": bool(_server_process and _server_process.poll() is None),
            "conversation_active": self.conversation_active,
            "thread_id": self.thread_id[:8]
        }
    
    def shutdown(self):
        """Cierre simplificado"""
        
        # Cerrar cliente
        if self.ava_client:
            try:
                self.ava_client.cleanup()
            except:
                pass
        
        # Cerrar servidor
        global _server_process
        if _server_process:
            try:
                _server_process.terminate()
                _server_process.wait(timeout=3)
            except:
                pass
        
        # Limpiar global
        cleanup_global_client()  # ✅ Usar función independiente

def main():
    """Main simplificado"""
    print("🤖 AVA GRAPH BOT")
    print("-" * 40)
    
    try:
        bot = AvaGraphBot(debug_mode=False)
        
        # ✅ MOSTRAR CONEXIONES EXITOSAS
        status = bot.get_status()
        if status["mcp_connected"]:
            print(f"✅ Conectado a Ava Bot gRPC - {status['tools_count']} herramientas")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("Comandos: /quit /reset /status")
    print("-" * 40)
    
    try:
        while True:
            try:
                user_input = input("\n👤 Tú: ").strip()
                
                if not user_input:
                    continue
                
                if user_input == "/quit":
                    break
                elif user_input == "/reset":
                    bot.reset_conversation()
                elif user_input == "/status":
                    status = bot.get_status()
                    print("📊 Estado:")
                    for key, value in status.items():
                        icon = "✅" if value else "❌"
                        print(f"   • {key}: {icon} {value}")
                else:
                    bot.chat(user_input)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                
    finally:
        bot.shutdown()
        print("👋 ¡Hasta luego!")

if __name__ == "__main__":
    main()

#
