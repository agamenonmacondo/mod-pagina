"""
MCP Client Test
===============

Cliente simple para probar el servidor MCP de Ava Bot.
Útil para verificar que las herramientas funcionan correctamente.
"""

import asyncio
import json
import sys
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPClient:
    """Cliente MCP simple para testing"""
    
    def __init__(self):
        self.request_id = 0
    
    def _next_id(self) -> int:
        """Genera el siguiente ID de solicitud"""
        self.request_id += 1
        return self.request_id
    
    def create_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Crea una solicitud JSON-RPC 2.0"""
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._next_id()
        }
        
        if params:
            request["params"] = params
        
        return request
    
    async def test_server_locally(self):
        """
        Prueba el servidor MCP directamente (sin stdio)
        Útil para debugging y desarrollo
        """
        try:
            from mcp_server.server import MCPServer
            server = MCPServer()
            
            print("🧪 Testing MCP Server Locally...")
            print("=" * 50)
            
            # Test 1: Initialize
            print("\n1️⃣ Testing Initialize...")
            init_request = self.create_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            })
            
            init_response = await server.handle_request(init_request)
            print(f"✅ Initialize Response: {json.dumps(init_response, indent=2)}")
            
            # Test 2: List Tools
            print("\n2️⃣ Testing Tools List...")
            tools_request = self.create_request("tools/list")
            tools_response = await server.handle_request(tools_request)
            print(f"✅ Tools List Response: {json.dumps(tools_response, indent=2)}")
            
            # Extraer herramientas disponibles
            available_tools = []
            if "result" in tools_response and "tools" in tools_response["result"]:
                available_tools = [tool["name"] for tool in tools_response["result"]["tools"]]
                print(f"\n📋 Available Tools: {available_tools}")
            
            # Test 3: Test Calendar Tool (si está disponible)
            if "calendar" in available_tools:
                print("\n3️⃣ Testing Calendar Tool...")
                calendar_request = self.create_request("tools/call", {
                    "name": "calendar",
                    "arguments": {
                        "action": "create_event",
                        "summary": "Reunión de prueba MCP",
                        "start_time": "2024-12-25T10:00:00",
                        "duration_hours": 1,
                        "description": "Test desde MCP Server"
                    }
                })
                
                calendar_response = await server.handle_request(calendar_request)
                print(f"✅ Calendar Response: {json.dumps(calendar_response, indent=2)}")
            
            # Test 4: Test Meet Tool (si está disponible)
            if "meet" in available_tools:
                print("\n4️⃣ Testing Meet Tool...")
                meet_request = self.create_request("tools/call", {
                    "name": "meet",
                    "arguments": {
                        "title": "Reunión Google Meet MCP",
                        "start_time": "2024-12-25T15:00:00",
                        "duration_minutes": 60,
                        "description": "Test de Google Meet desde MCP Server"
                    }
                })
                
                meet_response = await server.handle_request(meet_request)
                print(f"✅ Meet Response: {json.dumps(meet_response, indent=2)}")
            
            print("\n🎉 All tests completed!")
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def interactive_test():
    """Prueba interactiva del servidor MCP"""
    client = MCPClient()
    
    print("🔧 Interactive MCP Server Test")
    print("=" * 40)
    print("Available commands:")
    print("  init     - Initialize server")
    print("  tools    - List available tools")
    print("  call     - Call a specific tool")
    print("  test     - Run automated tests")
    print("  quit     - Exit")
    print()
    
    try:
        from mcp_server.server import MCPServer
        server = MCPServer()
        
        while True:
            command = input("\n📝 Enter command (init/tools/call/test/quit): ").strip().lower()
            
            if command == "quit":
                break
            elif command == "init":
                request = client.create_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "interactive-client", "version": "1.0.0"}
                })
                response = await server.handle_request(request)
                print(json.dumps(response, indent=2))
                
            elif command == "tools":
                request = client.create_request("tools/list")
                response = await server.handle_request(request)
                print(json.dumps(response, indent=2))
                
            elif command == "call":
                tool_name = input("Tool name: ").strip()
                print("Enter tool arguments (JSON format):")
                args_input = input("> ")
                
                try:
                    arguments = json.loads(args_input) if args_input else {}
                except json.JSONDecodeError:
                    print("❌ Invalid JSON format")
                    continue
                
                request = client.create_request("tools/call", {
                    "name": tool_name,
                    "arguments": arguments
                })
                response = await server.handle_request(request)
                print(json.dumps(response, indent=2))
                
            elif command == "test":
                await client.test_server_locally()
                
            else:
                print("❌ Unknown command")
    
    except Exception as e:
        logger.error(f"❌ Interactive test failed: {e}")


def main():
    """Punto de entrada principal"""
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_test())
    else:
        asyncio.run(MCPClient().test_server_locally())


if __name__ == "__main__":
    main()
