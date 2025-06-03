"""
Tool Registry for MCP Server
===========================

Sistema que descubre automáticamente los adapters existentes de Ava Bot
y los registra como herramientas MCP compatibles.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Type
import importlib.util

logger = logging.getLogger(__name__)

# Agregar el proyecto root al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ToolRegistry:
    """
    Registro automático de herramientas MCP desde adapters existentes
    
    Escanea el directorio tools/adapters/ y convierte automáticamente
    cada adapter en una herramienta MCP compatible.
    """
    
    def __init__(self):
        self.tools = {}
        self._discover_tools()
    
    def _discover_tools(self):
        """Descubre automáticamente todos los adapters disponibles"""
        adapters_dir = project_root / "tools" / "adapters"
        
        if not adapters_dir.exists():
            logger.warning(f"❌ Adapters directory not found: {adapters_dir}")
            return
        
        # Lista de adapters conocidos (se puede expandir automáticamente)
        known_adapters = [
            ("calendar_adapter.py", "CalendarAdapter"),
            ("meet_adapter.py", "MeetAdapter"), 
            ("gmail_adapter.py", "GmailAdapter"),
            ("search_adapter.py", "SearchAdapter"),
            ("drive_adapter.py", "DriveAdapter"),
            ("image_adapter.py", "ImageAdapter"),
            ("calendar_check_adapter.py", "CalendarCheckAdapter")
        ]
        
        for filename, class_name in known_adapters:
            adapter_path = adapters_dir / filename
            
            if adapter_path.exists():
                try:
                    tool_instance = self._load_adapter(adapter_path, class_name)
                    if tool_instance:
                        tool_name = getattr(tool_instance, 'name', class_name.lower().replace('adapter', ''))
                        self.tools[tool_name] = tool_instance
                        logger.info(f"✅ Registered tool: {tool_name} ({class_name})")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to load {filename}: {e}")
            else:
                logger.debug(f"⚠️ Adapter not found: {filename}")
    
    def _load_adapter(self, adapter_path: Path, class_name: str):
        """
        Carga dinámicamente un adapter y lo convierte en herramienta MCP
        
        Args:
            adapter_path: Ruta al archivo del adapter
            class_name: Nombre de la clase del adapter
            
        Returns:
            Instancia del adapter lista para usar como herramienta MCP
        """
        try:
            # Cargar módulo dinámicamente
            spec = importlib.util.spec_from_file_location(
                f"adapter_{adapter_path.stem}", 
                adapter_path
            )
            
            if not spec or not spec.loader:
                logger.error(f"❌ Could not load spec for {adapter_path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Obtener la clase del adapter
            if not hasattr(module, class_name):
                logger.error(f"❌ Class {class_name} not found in {adapter_path}")
                return None
            
            adapter_class = getattr(module, class_name)
            
            # Crear instancia del adapter
            adapter_instance = adapter_class()
            
            # Verificar que sea un adapter válido
            if not hasattr(adapter_instance, 'process'):
                logger.error(f"❌ {class_name} missing 'process' method")
                return None
            
            # Wrap con funcionalidad MCP si es necesario
            return MCPToolWrapper(adapter_instance)
            
        except Exception as e:
            logger.error(f"❌ Error loading adapter {class_name}: {e}")
            return None
    
    def get_all_tools(self) -> Dict[str, Any]:
        """Retorna todas las herramientas registradas"""
        return self.tools.copy()
    
    def get_tool(self, name: str) -> Any:
        """Obtiene una herramienta específica por nombre"""
        return self.tools.get(name)
    
    def list_tool_names(self) -> list:
        """Lista los nombres de todas las herramientas disponibles"""
        return list(self.tools.keys())


class MCPToolWrapper:
    """
    Wrapper que convierte un adapter de Ava Bot en herramienta MCP compatible
    
    Proporciona la interfaz estándar que espera el servidor MCP mientras
    preserva toda la funcionalidad del adapter original.
    """
    
    def __init__(self, adapter_instance):
        self.adapter = adapter_instance
        
        # Propagar propiedades importantes del adapter
        self.name = getattr(adapter_instance, 'name', 'unknown_tool')
        self.description = getattr(adapter_instance, 'description', f'Tool: {self.name}')
        self.schema = getattr(adapter_instance, 'schema', {})
    
    def process(self, params: Dict[str, Any]) -> Any:
        """
        Ejecuta la herramienta usando el adapter original
        
        Args:
            params: Parámetros de entrada para la herramienta
            
        Returns:
            Resultado de la ejecución del adapter
        """
        try:
            # Validar parámetros si el adapter lo soporta
            if hasattr(self.adapter, 'validate_params'):
                validated_params = self.adapter.validate_params(params)
            else:
                validated_params = params
            
            # Ejecutar adapter original
            result = self.adapter.process(validated_params)
            
            logger.info(f"✅ Tool {self.name} executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Tool {self.name} execution failed: {e}")
            raise
    
    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida parámetros usando el adapter original si está disponible
        
        Args:
            params: Parámetros a validar
            
        Returns:
            Parámetros validados
        """
        if hasattr(self.adapter, 'validate_params'):
            return self.adapter.validate_params(params)
        return params
    
    def get_schema(self) -> Dict[str, Any]:
        """Obtiene el schema de la herramienta"""
        return self.schema
    
    def get_description(self) -> str:
        """Obtiene la descripción de la herramienta"""
        return self.description


# Función de utilidad para registro manual de herramientas
def register_tool(tool_instance, name: str = None):
    """
    Registra manualmente una herramienta en el registry
    
    Args:
        tool_instance: Instancia de la herramienta
        name: Nombre opcional para la herramienta
    """
    registry = ToolRegistry()
    tool_name = name or getattr(tool_instance, 'name', 'custom_tool')
    registry.tools[tool_name] = tool_instance
    logger.info(f"✅ Manually registered tool: {tool_name}")


if __name__ == "__main__":
    # Test del registry
    print("🔍 Testing Tool Registry...")
    
    registry = ToolRegistry()
    tools = registry.get_all_tools()
    
    print(f"\n📋 Found {len(tools)} tools:")
    for name, tool in tools.items():
        print(f"   • {name}: {tool.description}")
        print(f"     Schema: {bool(tool.schema)}")
