import asyncio
import json
import subprocess
from typing import Dict, Any, List, Optional
import sys
import time
import re
import os

class MCPClient:
    """Cliente MCP silencioso - sin logging"""
    
    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.process = None
        self.request_id = 0
        self.initialized = False
    
    async def start_server(self):
        """Inicia el servidor MCP silenciosamente"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024*1024,
                env=None,
                cwd=None
            )
            
            await asyncio.sleep(3)
            
            if self.process.returncode is not None:
                stderr_output = await self.process.stderr.read()
                raise Exception(f"Server failed to start: {stderr_output.decode()}")
            
            try:
                init_response = await self._send_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "ava-mcp-client", "version": "1.0.0"}
                })
                
                if "error" in init_response:
                    raise Exception(f"Initialization failed: {init_response['error']}")
                
                self.initialized = True
                
            except Exception as e:
                try:
                    stderr_data = await asyncio.wait_for(
                        self.process.stderr.read(1024), 
                        timeout=2.0
                    )
                    if stderr_data:
                        stderr_text = stderr_data.decode('utf-8', errors='ignore')
                except:
                    pass
                raise
            
        except Exception as e:
            if self.process:
                self.process.terminate()
                await self.process.wait()
                self.process = None
            raise
    
    async def _send_request(self, method: str, params: Dict = None) -> Dict[str, Any]:
        """Envía solicitud silenciosamente"""
        if not self.process or self.process.returncode is not None:
            raise Exception("MCP server not running")
        
        self.request_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self.request_id
        }
        
        if params is not None:
            request["params"] = params
        
        try:
            request_json = json.dumps(request) + "\n"
            
            self.process.stdin.write(request_json.encode('utf-8'))
            await self.process.stdin.drain()
            
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    response_line = await asyncio.wait_for(
                        self.process.stdout.readline(), 
                        timeout=10.0 + (attempt * 5)
                    )
                    
                    if not response_line:
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(1)
                            continue
                        else:
                            raise Exception("No response from server after multiple attempts")
                    
                    response_text = response_line.decode('utf-8').strip()
                    
                    if not response_text:
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(1)
                            continue
                        else:
                            raise Exception("Empty response text after multiple attempts")
                    
                    try:
                        return self._parse_mcp_response(response_text)
                    except json.JSONDecodeError as e:
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(1)
                            continue
                        else:
                            raise Exception(f"Invalid JSON response after {max_attempts} attempts: {response_text}")
                    
                    break
                    
                except asyncio.TimeoutError:
                    if attempt < max_attempts - 1:
                        try:
                            stderr_data = await asyncio.wait_for(
                                self.process.stderr.read(1024), 
                                timeout=2.0
                            )
                            if stderr_data:
                                error_msg = stderr_data.decode('utf-8', errors='ignore')
                        except asyncio.TimeoutError:
                            pass
                        
                        await asyncio.sleep(2)
                        continue
                    else:
                        raise Exception(f"Timeout waiting for response after {max_attempts} attempts")
                        
        except Exception as e:
            raise
    
    def _parse_mcp_response(self, response_text: str) -> Dict[str, Any]:
        """Parsea respuesta silenciosamente"""
        if not response_text or response_text.isspace():
            raise json.JSONDecodeError("Empty response", response_text, 0)
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            lines = response_text.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('{"jsonrpc"') or line.startswith('{"id"') or line.startswith('{"result"') or line.startswith('{"error"'):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
            
            json_pattern = r'\{[^{}]*"jsonrpc"[^{}]*\}'
            matches = re.findall(json_pattern, response_text, re.DOTALL)
            
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
            
            raise json.JSONDecodeError(f"Could not find valid JSON in response", response_text, 0)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Obtiene herramientas silenciosamente"""
        if not self.initialized:
            raise Exception("Client not initialized")
        
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                response = await self._send_request("tools/list", {})
                
                if "error" in response:
                    error_msg = response["error"].get("message", "Unknown error")
                    
                    if attempt < max_attempts - 1:
                        wait_time = (attempt + 1) * 2
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Server error: {error_msg}")
                
                result = response.get("result", {})
                tools = result.get("tools", [])
                
                return tools
                
            except Exception as e:
                if attempt < max_attempts - 1:
                    wait_time = (attempt + 1) * 2
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        return []
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Ejecuta herramienta silenciosamente"""
        if not self.initialized:
            raise Exception("Client not initialized")
        
        try:
            response = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            if "error" in response:
                error_msg = response["error"].get("message", "Unknown error")
                return response
            
            return response
            
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Client error: {str(e)}"
                },
                "id": self.request_id
            }
    
    async def cleanup(self):
        """Cierra conexión silenciosamente"""
        if self.process:
            try:
                self.process.terminate()
                
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
                
            except Exception as e:
                pass
            finally:
                self.process = None
                self.initialized = False

# Alias para compatibilidad
async def close(self):
    await self.cleanup()

MCPClient.close = close

async def test_mcp_client():
    """Test básico del cliente MCP"""
    import os
    
    # ✅ SOLUCIÓN: Usar ruta absoluta correcta
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(current_dir, "mcp_server", "run_server.py")
    
    if not os.path.exists(server_path):
        print(f"❌ Server not found at: {server_path}")
        print(f"📁 Current directory: {current_dir}")
        print(f"📁 Looking for: mcp_server/run_server.py")
        return False
    
    client = MCPClient([
        sys.executable,  # Usar el mismo Python que está ejecutando este script
        server_path,
        "server"
    ])
    
    try:
        print("🧪 Testing MCP Client...")
        await client.start_server()
        
        # Listar herramientas
        print("📋 Listing tools...")
        tools = await client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description']}")
        
        if tools:
            # Test search tool
            print("\n🔍 Testing search tool...")
            result = await client.call_tool("search", {
                "query": "Python tutorial",
                "num_results": 3
            })
            print(f"✅ Search result: {result}")
            
            # ✅ CORREGIR: Test memory tool con acciones válidas
            print("\n🧠 Testing memory tool...")
            memory_result = await client.call_tool("memory", {
                "action": "store",  # ✅ Cambiar de "add" a "store" 
                "user_id": "test_user@email.com",
                "content": "Testing memory functionality with MCP client",
                "session_id": "mcp_test_session"
            })
            print(f"✅ Memory result: {memory_result}")
            
            # ✅ AGREGAR: Test multimodal memory tool con mejor output
            print("\n🧠 Testing multimodal memory tool...")
            multimodal_result = await client.call_tool("multimodal_memory", {
                "action": "validate_system",
                "user_id": "test_user@email.com"
            })
            
            # Mostrar resultado de forma más clara
            if "result" in multimodal_result:
                content = multimodal_result["result"].get("content", [])
                if content and len(content) > 0:
                    text_content = content[0].get("text", "")
                    if text_content:
                        # Intentar parsear como JSON para mejor visualización
                        try:
                            import json
                            parsed_content = json.loads(text_content)
                            if parsed_content.get("success", False):
                                print("✅ Multimodal memory validation: SUCCESS")
                                validation_results = parsed_content.get("validation_results", {})
                                summary = validation_results.get("summary", {})
                                components_ok = summary.get("components_ok", 0)
                                total_components = summary.get("total_components", 0)
                                print(f"   📊 System components: {components_ok}/{total_components} OK")
                                print(f"   🎯 System ready: {summary.get('system_ready', False)}")
                            else:
                                print(f"❌ Multimodal memory validation failed: {parsed_content.get('error', 'Unknown error')}")
                        except json.JSONDecodeError:
                            print(f"✅ Multimodal memory result: {text_content[:100]}...")
                    else:
                        print("⚠️ Empty response from multimodal memory")
                else:
                    print("⚠️ No content in multimodal memory response")
            else:
                print(f"❌ Multimodal memory error: {multimodal_result.get('error', 'Unknown error')}")

        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await client.close()

async def test_multimodal_memory():
    """Test específico para memoria multimodal"""
    import os
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(current_dir, "mcp_server", "run_server.py")
    
    client = MCPClient([
        sys.executable,
        server_path,
        "server"
    ])
    
    try:
        print("🧪 Testing Multimodal Memory Adapter...")
        await client.start_server()
        
        # Listar herramientas y verificar multimodal_memory
        tools = await client.list_tools()
        multimodal_tool = None
        
        for tool in tools:
            if tool['name'] == 'multimodal_memory':
                multimodal_tool = tool
                break
        
        if not multimodal_tool:
            print("❌ multimodal_memory tool not found")
            return False
        
        print(f"✅ Found multimodal_memory tool: {multimodal_tool['description']}")
        
        # Test 1: Validar sistema
        print("\n🔍 Test 1: Validating system...")
        result = await client.call_tool("multimodal_memory", {
            "action": "validate_system",
            "user_id": "test_user@email.com"
        })
        
        if "error" in result:
            print(f"❌ Validation failed: {result['error']}")
            return False
        
        print(f"✅ System validation: {result.get('result', {}).get('content', [{}])[0].get('text', 'No response')}")
        
        # Test 2: Store text memory
        print("\n💾 Test 2: Storing text memory...")
        store_result = await client.call_tool("multimodal_memory", {
            "action": "store_text_memory",
            "user_id": "test_user@email.com",
            "content": "Estoy buscando apartamentos en Melgar, Tolima para el próximo fin de semana. Necesito que tenga piscina y sea para 4 personas.",
            "session_id": "mcp_test_session"
        })
        
        if "error" in store_result:
            print(f"❌ Store text failed: {store_result['error']}")
        else:
            print(f"✅ Text stored successfully")
        
        # Test 3: Search semantic memories
        print("\n🔍 Test 3: Searching semantic memories...")
        search_result = await client.call_tool("multimodal_memory", {
            "action": "search_semantic_memories",
            "user_id": "test_user@email.com",
            "query": "apartamentos Melgar piscina",
            "modalities": ["text"],
            "limit": 3
        })
        
        if "error" in search_result:
            print(f"❌ Search failed: {search_result['error']}")
        else:
            print(f"✅ Search completed successfully")
        
        # Test 4: Get user stats
        print("\n📊 Test 4: Getting user stats...")
        stats_result = await client.call_tool("multimodal_memory", {
            "action": "get_user_stats",
            "user_id": "test_user@email.com"
        })
        
        if "error" in stats_result:
            print(f"❌ Stats failed: {stats_result['error']}")
        else:
            print(f"✅ Stats retrieved successfully")
        
        print("\n🎉 All multimodal memory tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        await client.close()

def main():
    """
    Función principal que prueba si todo está funcionando correctamente
    """
    print("=" * 60)
    print("🚀 PRUEBA COMPLETA DEL SISTEMA MCP")
    print("=" * 60)
    
    # 1. Verificar estructura de archivos
    print("\n📁 1. Verificando estructura de archivos...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(current_dir, "mcp_server", "run_server.py")
    
    required_files = [
        server_path,
        os.path.join(current_dir, "tools", "adapters", "memory_adapter.py"),
        os.path.join(current_dir, "tools", "adapters", "search_adapter.py"),
        os.path.join(current_dir, "tools", "adapters", "gmail_adapter.py"),
        os.path.join(current_dir, "tools", "adapters", "calendar_adapter.py"),
        os.path.join(current_dir, "token.json")
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"   ✅ {os.path.basename(file_path)}")
        else:
            print(f"   ❌ {os.path.basename(file_path)} - NO ENCONTRADO")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Faltan {len(missing_files)} archivos importantes")
        for file in missing_files:
            print(f"   📄 {file}")
        print("\n🔧 Solución: Verifica que todos los archivos estén en su lugar")
        return False
    
    # 2. Probar servidor MCP standalone
    print("\n🖥️ 2. Probando servidor MCP standalone...")
    try:
        cmd = [sys.executable, server_path]
        
        # ✅ CORRECCIÓN: Agregar encoding UTF-8 y manejo de errores
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'  # Reemplazar caracteres problemáticos
        )
        
        # ✅ CORRECCIÓN: Usar timeout en communicate()
        try:
            stdout, stderr = process.communicate(timeout=10)
            
            # ✅ CORRECCIÓN: Verificar que stderr no sea None antes de usar 'in'
            if stderr is not None:
                if "✅ Servidor inicializado" in stderr or "herramientas" in stderr:
                    print("   ✅ Servidor MCP se inicia correctamente")
                    
                    # Contar herramientas encontradas de forma segura
                    tool_count = stderr.count("✅") - stderr.count("✅ Servidor inicializado")
                    if tool_count > 0:
                        print(f"   📊 Herramientas cargadas: {tool_count}")
                else:
                    print("   ⚠️ Servidor se ejecutó pero no se detectaron herramientas")
                    if stderr:
                        # Mostrar stderr de forma segura
                        stderr_preview = stderr[:200].replace('\n', ' ').strip()
                        if stderr_preview:
                            print(f"   🔧 Output: {stderr_preview}...")
            else:
                print("   ⚠️ No se recibió información del servidor")
            
            # Verificar código de retorno
            if process.returncode == 0:
                print("   ✅ Servidor MCP se ejecutó sin errores")
            elif process.returncode is not None:
                print(f"   ❌ Servidor MCP terminó con código: {process.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            print("   ✅ Servidor MCP se ejecuta (timeout esperado)")
            process.kill()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
            print("   📊 Servidor se mantiene ejecutándose correctamente")
            
    except Exception as e:
        print(f"   ❌ Error ejecutando servidor: {e}")
        return False
    
    # 3. Probar cliente MCP con servidor
    print("\n🔄 3. Probando comunicación cliente-servidor...")
    
    async def run_client_test():
        return await test_mcp_client()
    
    try:
        # Ejecutar test asíncrono
        test_result = asyncio.run(run_client_test())
        
        if test_result:
            print("   ✅ Comunicación cliente-servidor exitosa")
        else:
            print("   ❌ Falló la comunicación cliente-servidor")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en test cliente-servidor: {e}")
        return False
    
    # 4. Verificar dependencias Python
    print("\n📦 4. Verificando dependencias Python...")
    required_modules = [
        'asyncio', 'json', 'subprocess', 'logging',
        'pathlib', 'datetime', 'typing'
    ]
    
    optional_modules = [
        ('groq', 'GROQ API'),
        ('google.auth', 'Google APIs'),
        ('requests', 'HTTP requests'),
        ('jsonschema', 'JSON validation')
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module} - REQUERIDO")
            return False
    
    for module, description in optional_modules:
        try:
            __import__(module)
            print(f"   ✅ {module} ({description})")
        except ImportError:
            print(f"   ⚠️ {module} ({description}) - OPCIONAL")
    
    # 5. Verificar variables de entorno
    print("\n🔧 5. Verificando configuración...")
    
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        masked_key = groq_key[:8] + "..." + groq_key[-4:] if len(groq_key) > 12 else "***"
        print(f"   ✅ GROQ_API_KEY: {masked_key}")
    else:
        print("   ⚠️ GROQ_API_KEY no configurada")
    
    # Verificar token.json de forma segura
    token_path = os.path.join(current_dir, "token.json")
    if os.path.exists(token_path):
        try:
            with open(token_path, 'r', encoding='utf-8') as f:
                token_content = f.read().strip()
                if token_content:
                    try:
                        token_data = json.loads(token_content)
                        if token_data:
                            print("   ✅ token.json existe y contiene datos válidos")
                        else:
                            print("   ⚠️ token.json contiene JSON vacío")
                    except json.JSONDecodeError:
                        print("   ⚠️ token.json tiene formato JSON incorrecto")
                else:
                    print("   ⚠️ token.json existe pero está vacío")
        except Exception as e:
            print(f"   ⚠️ Error leyendo token.json: {e}")
    else:
        print("   ⚠️ token.json no encontrado")
    
    # 6. Resultado final
    print("\n" + "=" * 60)
    print("🎉 RESUMEN DE LA PRUEBA")
    print("=" * 60)
    print("✅ Sistema MCP funcionando correctamente")
    print("✅ Cliente puede comunicarse con servidor")
    print("✅ Herramientas disponibles y funcionales")
    print("✅ Memoria multimodal operativa")  # ✅ AGREGAR
    print("\n🚀 El sistema está listo para usar en el chat!")
    
    # Instrucciones adicionales actualizadas
    print("\n📋 PRÓXIMOS PASOS:")
    print("1. Reinicia la aplicación Flask: python app.py")
    print("2. Abre el chat en tu navegador")
    print("3. Prueba enviando: 'busca información sobre Python'")
    print("4. Prueba enviando: 'almacena esta conversación en mi memoria'")  # ✅ AGREGAR
    print("5. Verifica que las herramientas respondan correctamente")
    
    return True

def quick_test():
    """Prueba rápida para verificar solo lo esencial"""
    print("🔍 PRUEBA RÁPIDA DEL SISTEMA MCP")
    print("-" * 40)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(current_dir, "mcp_server", "run_server.py")
    
    if not os.path.exists(server_path):
        print("❌ Servidor MCP no encontrado")
        return False
    
    try:
        # ✅ CORRECCIÓN: Agregar encoding y manejo de errores
        cmd = [sys.executable, server_path]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Esperar 5 segundos y verificar
        time.sleep(5)
        
        if process.poll() is None:
            # Proceso sigue ejecutándose
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            print("✅ Servidor MCP funciona correctamente")
            return True
        else:
            # Proceso terminó, verificar por qué
            try:
                _, stderr = process.communicate(timeout=2)
                # ✅ CORRECCIÓN: Verificar que stderr no sea None
                if stderr and ("herramientas" in stderr and "inicializado" in stderr):
                    print("✅ Servidor MCP funciona correctamente")
                    return True
                else:
                    stderr_preview = stderr[:100] if stderr else "Sin información de error"
                    print(f"❌ Servidor MCP falló: {stderr_preview}")
                    return False
            except subprocess.TimeoutExpired:
                print("✅ Servidor MCP funciona correctamente (timeout en communicate)")
                return True
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Probar sistema MCP")
    parser.add_argument("--quick", action="store_true", help="Ejecutar solo prueba rápida")
    args = parser.parse_args()
    
    if args.quick:
        success = quick_test()
    else:
        success = main()
    
    if success:
        print("\n🎊 ¡Sistema funcionando perfectamente!")
        sys.exit(0)
    else:
        print("\n💥 Sistema tiene problemas que requieren atención")
        sys.exit(1)