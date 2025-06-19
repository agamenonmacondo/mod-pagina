import sys
import grpc
import os
import json
import time
import subprocess
from typing import Dict, Any, Optional

# Añadir el directorio del servidor al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'mcp_server'))

# Función para corregir importaciones si es necesario
def fix_grpc_imports():
    """Corrige las importaciones del archivo gRPC si es necesario"""
    mcp_server_dir = os.path.join(os.path.dirname(__file__), 'mcp_server')
    grpc_file = os.path.join(mcp_server_dir, 'ava_bot_pb2_grpc.py')
    
    if os.path.exists(grpc_file):
        with open(grpc_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        old_import = "import ava_bot_pb2 as ava__bot__pb2"
        new_import = """try:
    import ava_bot_pb2 as ava__bot__pb2
except ImportError:
    from . import ava_bot_pb2 as ava__bot__pb2"""
        
        if old_import in content and new_import not in content:
            content = content.replace(old_import, new_import)
            with open(grpc_file, 'w', encoding='utf-8') as f:
                f.write(content)

# Intentar corregir importaciones antes de importar
fix_grpc_imports()

# Importar los módulos protobuf
try:
    import ava_bot_pb2
    import ava_bot_pb2_grpc
except ImportError as e:
    print(f"❌ Error importando módulos protobuf: {e}")
    print("💡 Ejecuta primero: cd mcp_server && python run_server.py")
    sys.exit(1)

from concurrent import futures

class AvaToolsClient:
    """Cliente gRPC para usar las herramientas de Ava Bot"""
    
    def __init__(self, host: str = "localhost", port: int = 50051):
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = ava_bot_pb2_grpc.AvaBotStub(self.channel)
        self.connected = False
        self.tools = {}
        
    def connect(self) -> bool:
        """Conectar al servidor gRPC de Ava Bot"""
        try:
            response = self.stub.Health(ava_bot_pb2.HealthRequest())
            self.connected = True
            print(f"✅ Conectado a Ava Bot gRPC - {response.total_tools} herramientas")
            
            # Cargar herramientas disponibles
            self._load_tools()
            return True
            
        except grpc.RpcError as e:
            print(f"❌ Error conectando al servidor gRPC: {e.code()}")
            return False
    
    def _load_tools(self):
        """Cargar herramientas disponibles desde el servidor"""
        try:
            response = self.stub.ListTools(ava_bot_pb2.ToolsRequest())
            self.tools = {name: desc for name, desc in response.tools.items()}
            print(f"📋 Herramientas de Ava Bot cargadas: {len(self.tools)}")
        except grpc.RpcError as e:
            print(f"⚠️ Error cargando herramientas: {e.code()}")

    def list_tools(self) -> Dict[str, str]:
        """Listar todas las herramientas disponibles"""
        if not self.connected:
            print("❌ No conectado al servidor")
            return {}
            
        print("\n🛠️ HERRAMIENTAS DE AVA BOT:")
        for i, (name, desc) in enumerate(self.tools.items(), 1):
            print(f"{i:2d}. {name:<18} - {desc[:60]}...")
            
        return self.tools

    def use_tool(self, tool_name: str, **params) -> Dict[str, Any]:
        """Usar una herramienta específica"""
        if not self.connected:
            return {"error": "No conectado al servidor"}
            
        if tool_name not in self.tools:
            return {"error": f"Herramienta '{tool_name}' no disponible"}
            
        try:
            # Convertir parámetros a JSON string
            parameters_json = json.dumps(params)
            
            request = ava_bot_pb2.ToolRequest(
                tool_name=tool_name,
                parameters=parameters_json
            )
                
            response = self.stub.ExecuteTool(request)
            
            return {
                "success": response.success,
                "result": response.text,
                "raw_result": response.raw_result
            }
            
        except grpc.RpcError as e:
            return {"error": f"Error gRPC: {e.code()}"}

    def search_web(self, query: str, num_results: int = 5) -> str:
        result = self.use_tool("search", query=query, num_results=num_results)
        return result.get("result", f"Error: {result.get('error', 'Desconocido')}")

    def remember(self, user_id: str, content: str) -> str:
        result = self.use_tool("memory", user_id=user_id, action="store", content=content)
        return "✅ Guardado" if result.get("success") else f"❌ Error: {result.get('error')}"

    def recall(self, user_id: str, query: str = None) -> str:
        params = {"user_id": user_id, "action": "search"}
        if query:
            params["query"] = query
        result = self.use_tool("memory", **params)
        return result.get("result", f"Error: {result.get('error', 'Desconocido')}")

    def generate_image(self, prompt: str) -> str:
        result = self.use_tool("image", prompt=prompt)
        return result.get("result", f"Error: {result.get('error', 'Desconocido')}")

    def send_email(self, to: str, subject: str, body: str) -> str:
        result = self.use_tool("gmail", to=to, subject=subject, body=body)
        return "✅ Email enviado" if result.get("success") else f"❌ Error: {result.get('error')}"

    def create_meet(self, title: str) -> str:
        result = self.use_tool("meet", title=title)
        return result.get("result", f"Error: {result.get('error', 'Desconocido')}")

    def get_tool_info(self, tool_name: str):
        if tool_name in self.tools:
            print(f"🔧 {tool_name}: {self.tools[tool_name]}")
        else:
            print(f"❌ Herramienta '{tool_name}' no encontrada")

    def cleanup(self):
        """Cerrar conexión gRPC"""
        if hasattr(self, 'channel'):
            self.channel.close()

def connect_to_ava(host: str = "localhost", port: int = 50051) -> Optional[AvaToolsClient]:
    """Conectar a Ava Bot via gRPC"""
    client = AvaToolsClient(host, port)
    if client.connect():
        return client
    print("❌ No se pudo conectar al servidor gRPC")
    print("💡 Asegúrate de que el servidor esté ejecutándose:")
    print("   cd mcp_server && python run_server.py")
    return None

def demo_ava_tools():
    """Demo de las herramientas de Ava Bot"""
    print("🌟 DEMO: Herramientas de Ava Bot")
    print("=" * 40)
    
    ava = connect_to_ava()
    if not ava:
        return False
    
    try:
        print("\n📋 Herramientas disponibles:")
        tools = ava.list_tools()
        
        print("\n🧪 EJEMPLOS DE USO:")
        print("-" * 30)
        
        # Ejemplo 1: Búsqueda
        print("\n1. 🔍 Búsqueda web:")
        try:
            result = ava.search_web("últimas noticias tecnología", 3)
            print(f"   Resultado: {result[:100]}..." if len(result) > 100 else f"   Resultado: {result}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Ejemplo 2: Memoria
        print("\n2. 🧠 Memoria:")
        try:
            ava.remember("demo_user", "Me gusta el café por las mañanas")
            memory_result = ava.recall("demo_user", "café")
            print(f"   Memoria: {memory_result}")
        except Exception as e:
            print(f"   Error: {e}")
        
        print("\n✅ Demo completado!")
        return True
        
    finally:
        ava.cleanup()

def interactive_ava():
    """Modo interactivo con Ava Bot"""
    print("🤖 MODO INTERACTIVO - AVA BOT")
    print("=" * 35)
    print("💡 Comandos disponibles:")
    print("   help     - Ver herramientas")
    print("   search   - Buscar en web")
    print("   remember - Guardar en memoria")
    print("   recall   - Recuperar memoria")
    print("   image    - Generar imagen")
    print("   email    - Enviar email")
    print("   meet     - Crear reunión")
    print("   exit     - Salir")
    print("-" * 35)
    
    ava = connect_to_ava()
    if not ava:
        return
    
    user_id = "interactive_user"
    
    try:
        while True:
            try:
                command = input("\n🤖 Ava> ").strip().lower()
                
                if command == "exit":
                    print("👋 ¡Hasta luego!")
                    break
                
                elif command == "help":
                    ava.list_tools()
                
                elif command == "search":
                    query = input("🔍 ¿Qué quieres buscar? ")
                    if query:
                        result = ava.search_web(query)
                        print(f"📊 Resultado: {result}")
                
                elif command == "remember":
                    content = input("🧠 ¿Qué quieres que recuerde? ")
                    if content:
                        result = ava.remember(user_id, content)
                        print(result)
                
                elif command == "recall":
                    query = input("🧠 ¿Qué quieres recordar? (enter para todo) ")
                    result = ava.recall(user_id, query if query else None)
                    print(f"🧠 Memoria: {result}")
                
                elif command == "image":
                    prompt = input("🎨 Describe la imagen: ")
                    if prompt:
                        result = ava.generate_image(prompt)
                        print(f"🎨 Imagen: {result}")
                
                elif command == "email":
                    to = input("📧 Email destino: ")
                    subject = input("📧 Asunto: ")
                    body = input("📧 Mensaje: ")
                    if to and subject and body:
                        result = ava.send_email(to, subject, body)
                        print(result)
                
                elif command == "meet":
                    title = input("📞 Título de reunión: ")
                    if title:
                        result = ava.create_meet(title)
                        print(result)
                
                else:
                    print("❓ Comando no reconocido. Usa 'help' para ver opciones.")
            
            except KeyboardInterrupt:
                print("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    finally:
        ava.cleanup()

def main():
    """Función principal"""
    print("🤖 CLIENTE AVA BOT - gRPC")
    print("=" * 25)
    
    import argparse
    parser = argparse.ArgumentParser(description="Cliente gRPC para Ava Bot")
    parser.add_argument("--demo", action="store_true", help="Ejecutar demo")
    parser.add_argument("--interactive", "-i", action="store_true", help="Modo interactivo")
    parser.add_argument("--tools", action="store_true", help="Listar herramientas")
    parser.add_argument("--info", type=str, help="Info de herramienta específica")
    
    args = parser.parse_args()
    
    # Si no hay argumentos, mostrar modo interactivo por defecto
    if len(sys.argv) == 1:
        print("🎯 INICIANDO MODO INTERACTIVO...")
        print("💡 Para otras opciones usa: python mcp_client.py --help")
        time.sleep(1)
        interactive_ava()
        return True
    
    if args.demo:
        return demo_ava_tools()
    
    elif args.interactive:
        interactive_ava()
        return True
    
    elif args.tools:
        ava = connect_to_ava()
        if ava:
            try:
                ava.list_tools()
                return True
            finally:
                ava.cleanup()
        return False
    
    elif args.info:
        ava = connect_to_ava()
        if ava:
            try:
                ava.get_tool_info(args.info)
                return True
            finally:
                ava.cleanup()
        return False
    
    else:
        parser.print_help()
        return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 ¡Adiós!")
        sys.exit(0)
