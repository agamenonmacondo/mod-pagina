"""
MCP Server Implementation
========================

Core del servidor MCP que expone las herramientas de Ava Bot usando el protocolo JSON-RPC 2.0.
Compatible con cualquier cliente MCP (Claude Desktop, etc.)
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict, List, Optional, Sequence
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agregar el proyecto root al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class MCPServer:
    """
    Servidor MCP que expone herramientas de Ava Bot
    
    Implementa el protocolo JSON-RPC 2.0 para comunicación con clientes MCP.
    Convierte automáticamente los adapters existentes en herramientas MCP.
    """
    
    def __init__(self):
        self.tools = {}
        self.resources = {}
        self.prompts = {}
        self._load_tools()
    
    def _load_tools(self):
        """Carga automáticamente todas las herramientas disponibles"""
        try:
            from mcp_server.tool_registry import ToolRegistry
            registry = ToolRegistry()
            self.tools = registry.get_all_tools()
            logger.info(f"✅ Loaded {len(self.tools)} MCP tools")
            
            # Log herramientas cargadas
            for tool_name in self.tools.keys():
                logger.info(f"   📋 {tool_name}")
                
        except Exception as e:
            logger.error(f"❌ Error loading tools: {e}")
            self.tools = {}
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja solicitudes JSON-RPC 2.0 del cliente MCP
        
        Args:
            request: Solicitud JSON-RPC del cliente
            
        Returns:
            Respuesta JSON-RPC
        """
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            logger.info(f"🔍 MCP Request: {method}")
            
            # Ruteo de métodos MCP
            if method == "initialize":
                return await self._handle_initialize(params, request_id)
            elif method == "tools/list":
                return await self._handle_tools_list(request_id)
            elif method == "tools/call":
                return await self._handle_tools_call(params, request_id)
            elif method == "resources/list":
                return await self._handle_resources_list(request_id)
            elif method == "prompts/list":
                return await self._handle_prompts_list(request_id)
            else:
                return self._error_response(request_id, -32601, f"Method not found: {method}")
                
        except Exception as e:
            logger.error(f"❌ Error handling request: {e}")
            return self._error_response(request.get("id"), -32603, str(e))
    
    async def _handle_initialize(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Maneja inicialización del servidor MCP"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                    "logging": {}
                },
                "serverInfo": {
                    "name": "ava-bot-mcp-server",
                    "version": "1.0.0",
                    "description": "Ava Bot Tools MCP Server - Calendar, Gmail, Search, Meet, Drive, Images"
                }
            }
        }
    
    async def _handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """Lista todas las herramientas disponibles"""
        tools_list = []
        
        for tool_name, tool_instance in self.tools.items():
            # Obtener schema de la herramienta
            schema = getattr(tool_instance, 'schema', {})
            description = getattr(tool_instance, 'description', f"Tool: {tool_name}")
            
            # Crear definición MCP
            tool_def = {
                "name": tool_name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", [])
                }
            }
            
            tools_list.append(tool_def)
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools_list
            }
        }
    
    async def _handle_tools_call(self, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
        """Ejecuta una herramienta específica"""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name not in self.tools:
                return self._error_response(request_id, -32602, f"Tool not found: {tool_name}")
            
            tool_instance = self.tools[tool_name]
            logger.info(f"🔧 Executing tool: {tool_name} with args: {arguments}")
            
            # Validar parámetros si la herramienta lo soporta
            if hasattr(tool_instance, 'validate_params'):
                try:
                    arguments = tool_instance.validate_params(arguments)
                except Exception as validation_error:
                    return self._error_response(request_id, -32602, f"Validation error: {validation_error}")
            
            # Ejecutar herramienta
            result = tool_instance.process(arguments)
            
            # Formatear resultado para MCP
            if isinstance(result, dict):
                content = [
                    {
                        "type": "text",
                        "text": result.get("message", str(result))
                    }
                ]
                
                # Agregar metadatos si están disponibles
                if "event_created" in result or "meet_created" in result:
                    content.append({
                        "type": "text", 
                        "text": f"📊 Metadata: {json.dumps({k: v for k, v in result.items() if k != 'message'}, indent=2)}"
                    })
            else:
                content = [
                    {
                        "type": "text",
                        "text": str(result)
                    }
                ]
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": content,
                    "isError": False
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Tool execution error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ Error ejecutando {tool_name}: {str(e)}"
                        }
                    ],
                    "isError": True
                }
            }
    
    async def _handle_resources_list(self, request_id: Any) -> Dict[str, Any]:
        """Lista recursos disponibles (implementación futura)"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": []
            }
        }
    
    async def _handle_prompts_list(self, request_id: Any) -> Dict[str, Any]:
        """Lista prompts disponibles (implementación futura)"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "prompts": []
            }
        }
    
    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Crea respuesta de error JSON-RPC"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def run_stdio(self):
        """
        Ejecuta el servidor usando stdio (para integración con clientes MCP)
        
        Este modo permite que clientes como Claude Desktop se conecten al servidor
        """
        logger.info("🚀 Starting Ava Bot MCP Server on stdio...")
        logger.info("📋 Available tools:")
        for tool_name in self.tools.keys():
            logger.info(f"   • {tool_name}")
        
        async def handle_stdin():
            """Lee solicitudes de stdin y las procesa"""
            while True:
                try:
                    line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                    if not line:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parsear solicitud JSON-RPC
                    try:
                        request = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON: {e}")
                        continue
                    
                    # Procesar solicitud
                    response = await self.handle_request(request)
                    
                    # Enviar respuesta
                    print(json.dumps(response), flush=True)
                    
                except KeyboardInterrupt:
                    logger.info("🛑 Server shutdown requested")
                    break
                except Exception as e:
                    logger.error(f"❌ Error in stdio loop: {e}")
        
        await handle_stdin()


async def main():
    """Punto de entrada principal del servidor MCP"""
    server = MCPServer()
    
    # Verificar que las herramientas se cargaron correctamente
    if not server.tools:
        logger.warning("⚠️ No tools loaded. Check tool registry.")
    
    # Ejecutar servidor
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
