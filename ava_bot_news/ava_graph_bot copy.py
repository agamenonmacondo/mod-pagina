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

def print_raw_state(state, location="", max_chars=1000000):
    """Imprimir estado con límite de caracteres configurable"""
    print(f"\n--- STATE SUMMARY {location} ---")
    
    if isinstance(state, dict):
        # Convertir a string y truncar si es necesario
        state_str = str(state)
        if len(state_str) > max_chars:
            truncated = state_str[:max_chars] + f"... [TRUNCADO - {len(state_str)} chars total]"
            print(truncated)
        else:
            print(state_str)
    else:
        # Para otros tipos
        state_str = str(state)
        if len(state_str) > max_chars:
            truncated = state_str[:max_chars] + f"... [TRUNCADO - {len(state_str)} chars total]"
            print(truncated)
        else:
            print(state_str)
    
    print(f"--- END SUMMARY {location} ---")

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
        """Chat simplificado - CON DEBUG Y MANEJO DE ERRORES"""
        
        try:
            print(f"🔄 CHAT INICIANDO con input: '{user_input}'")
            
            # Preparar estado
            if self.conversation_active and self.current_state:
                state = create_state_with_history(user_input, self.current_state)
                print_raw_state(state, "AFTER_CREATE_WITH_HISTORY")
            else:
                state = create_initial_state(user_input)
                print_raw_state(state, "AFTER_CREATE_INITIAL")
                self.conversation_active = True
            
            # Añadir herramientas disponibles
            if self.ava_client and self.ava_client.tools:
                state["available_tools"] = self.ava_client.tools.copy()
                print_raw_state(state, "AFTER_ADD_TOOLS")
            
            # ✅ EJECUTAR GRAFO - CORREGIDO CON VALIDACIONES
            final_result = None
            step_num = 0
            response_shown = False
            
            print(f"🚀 Iniciando stream del grafo...")
            
            for step in self.graph.stream(state, config=self.config):
                step_num += 1
                print(f"📍 STEP {step_num} - Procesando...")
                
                try:
                    print_raw_state(step, f"STEP_{step_num}")
                except Exception as e:
                    print(f"⚠️ Error en print_raw_state STEP: {e}")
                
                for node_name, node_state in step.items():
                    print(f"   🔄 Procesando nodo: {node_name}")
                    
                    try:
                        print_raw_state(node_state, f"NODE_{node_name}")
                    except Exception as e:
                        print(f"⚠️ Error en print_raw_state NODE: {e}")
                    
                    # ✅ MOSTRAR RESPUESTA INMEDIATAMENTE EN CONVERSATIONAL
                    if node_name == "conversational" and not response_shown:
                        try:
                            messages = node_state.get('messages', []) if node_state else []
                            print(f"   📝 Mensajes en conversational: {len(messages)}")
                            
                            for msg in reversed(messages):
                                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                                    if hasattr(msg, 'content') and msg.content and msg.content.strip():
                                        print(f"\n🤖 Ava: {msg.content}")
                                        response_shown = True
                                        break
                        except Exception as e:
                            print(f"⚠️ Error mostrando respuesta conversational: {e}")
                    
                    # ✅ GUARDAR EL ÚLTIMO RESULTADO VÁLIDO
                    if node_state is not None:
                        final_result = node_state
                        print(f"   ✅ Final result actualizado desde nodo: {node_name}")
            
            print(f"🏁 Stream completado. Final result: {'✅ OK' if final_result else '❌ None'}")
            
            # ✅ USAR EL RESULTADO FINAL CORRECTO
            result_to_use = final_result or state
            
            # Actualizar estado
            try:
                self.current_state = update_conversation_history(result_to_use)
                print_raw_state(self.current_state, "FINAL_CURRENT_STATE")
            except Exception as e:
                print(f"⚠️ Error actualizando current_state: {e}")
                self.current_state = result_to_use  # Fallback
            
            # ✅ EXTRAER RESPUESTA FINAL SI NO SE MOSTRÓ
            if not response_shown:
                try:
                    messages = result_to_use.get('messages', []) if result_to_use else []
                    for msg in reversed(messages):
                        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                            if hasattr(msg, 'content') and msg.content and msg.content.strip():
                                print(f"\n🤖 Ava (Final): {msg.content}")
                                break
                except Exception as e:
                    print(f"⚠️ Error extrayendo respuesta final: {e}")
            
            # ✅ CONVERTIR A JSON CON MANEJO DE ERRORES
            try:
                return convert_state_to_json(result_to_use)
            except Exception as e:
                print(f"⚠️ Error convirtiendo a JSON: {e}")
                return {"error": False, "message": "Respuesta generada pero error en conversión", "raw_state": str(result_to_use)}
            
        except Exception as e:
            error_msg = f"Error en chat(): {e}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()  # Para ver el stack trace completo
            return {"error": True, "error_message": error_msg}
    
    def _show_response(self, result: AgentState):
        """Mostrar respuesta - DEFINITIVO"""
        # Obtener messages del state final
        messages = result.get('messages', [])
        
        # Debug para ver qué tenemos
        print(f"\n🔍 Debug: {len(messages)} mensajes encontrados")
        
        # Buscar el último AIMessage
        for msg in reversed(messages):
            # Verificar si es AIMessage y tiene contenido
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    print(f"\n🤖 Ava: {msg.content}")
                    return
        
        # Si no encuentra AIMessage, buscar en conversation_history
        conversation_history = result.get('conversation_history', [])
        for msg in reversed(conversation_history):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                    print(f"\n🤖 Ava: {msg.content}")
                    return
        
        # Fallback
        print(f"\n🤖 Ava: Procesamiento completado.")
    
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
