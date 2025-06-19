"""
Base class for all tools - archivo separado para evitar importaciones circulares
🔧 MODIFICADO: Schemas reales y ejecución estandarizada
"""
import jsonschema
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """Base class for tools with real schemas and standardized execution"""
    
    # 🎯 PROPIEDADES QUE DEBEN SER DEFINIDAS POR SUBCLASES
    name: str = "base_tool"
    description: str = "Base tool - should be overridden"
    
    # 🎯 SCHEMA POR DEFECTO - DEBE SER SOBRESCRITO
    schema: Dict[str, Any] = {
        "type": "object", 
        "properties": {}, 
        "required": []
    }
    
    def __init__(self):
        """Inicializa la herramienta base"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._validate_tool_definition()
    
    def _validate_tool_definition(self):
        """Valida que la herramienta esté correctamente definida"""
        if self.name == "base_tool":
            self.logger.warning(f"Tool {self.__class__.__name__} should override 'name' property")
        
        if not self.schema.get("properties"):
            self.logger.warning(f"Tool {self.name} has empty schema - should define properties")
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 MÉTODO ESTÁNDAR DE EJECUCIÓN - Usado por ToolManager
        Valida parámetros y ejecuta la lógica específica
        """
        try:
            self.logger.info(f"🛠️ Executing tool: {self.name}")
            
            # 1. Validar parámetros
            validated_params = self.validate_params(params)
            
            # 2. Ejecutar lógica específica
            result = self.process(validated_params)
            
            # 3. Estandarizar respuesta
            if isinstance(result, dict) and "success" in result:
                return result  # Ya está en formato estándar
            else:
                return {
                    "success": True,
                    "result": result,
                    "tool": self.name,
                    "message": f"Tool {self.name} executed successfully"
                }
                
        except ValueError as e:
            # Error de validación
            self.logger.error(f"❌ Validation error in {self.name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": self.name,
                "error_type": "validation_error"
            }
        except Exception as e:
            # Error de ejecución
            self.logger.error(f"❌ Execution error in {self.name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": self.name,
                "error_type": "execution_error"
            }
    
    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔧 VALIDACIÓN MEJORADA con mensajes más claros
        """
        try:
            # Validar contra schema JSON
            jsonschema.validate(instance=params, schema=self.schema)
            
            # Validación específica de la herramienta (opcional)
            custom_validated = self.custom_validation(params)
            
            self.logger.info(f"✅ Parameters validated for {self.name}")
            return custom_validated
            
        except jsonschema.ValidationError as e:
            # Error de schema JSON
            missing_props = []
            if e.validator == 'required' and isinstance(e.validator_value, list):
                missing_props = e.validator_value
            
            error_msg = f"Parameter validation failed: {e.message}"
            if missing_props:
                error_msg += f"\nMissing required parameters: {missing_props}"
                error_msg += f"\nProvided parameters: {list(params.keys())}"
            
            self.logger.error(f"JSON Schema validation error: {error_msg}")
            raise ValueError(error_msg)
            
        except Exception as e:
            self.logger.error(f"Unexpected validation error: {e}")
            raise ValueError(f"Parameter validation failed: {str(e)}")
    
    def custom_validation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 VALIDACIÓN PERSONALIZADA - Puede ser sobrescrita por subclases
        """
        return params
    
    @abstractmethod
    def process(self, params: Dict[str, Any]) -> Any:
        """
        🎯 LÓGICA ESPECÍFICA DE LA HERRAMIENTA - DEBE ser implementada
        """
        raise NotImplementedError(f"Tool {self.name} must implement process() method")
    
    def get_schema_info(self) -> Dict[str, Any]:
        """
        🎯 INFORMACIÓN COMPLETA DEL SCHEMA para el LLM
        """
        info = {
            "name": self.name,
            "description": self.description,
            "schema": self.schema.copy(),
            "required_params": self.schema.get("required", []),
            "optional_params": []
        }
        
        # Separar parámetros requeridos y opcionales
        properties = self.schema.get("properties", {})
        required = self.schema.get("required", [])
        
        for param_name, param_info in properties.items():
            param_detail = {
                "name": param_name,
                "type": param_info.get("type", "string"),
                "description": param_info.get("description", "No description"),
                "default": param_info.get("default")
            }
            
            if param_name in required:
                info["required_params"] = info.get("required_params", [])
                if isinstance(info["required_params"], list):
                    info["required_params"].append(param_detail)
            else:
                info["optional_params"].append(param_detail)
        
        return info
    
    def get_usage_example(self) -> Dict[str, Any]:
        """
        🎯 EJEMPLO DE USO para el LLM
        """
        required_params = self.schema.get("required", [])
        properties = self.schema.get("properties", {})
        
        example_params = {}
        for param in required_params:
            if param in properties:
                param_type = properties[param].get("type", "string")
                if param_type == "string":
                    example_params[param] = f"example_{param}"
                elif param_type == "integer":
                    example_params[param] = 1
                elif param_type == "boolean":
                    example_params[param] = True
                else:
                    example_params[param] = f"example_{param}"
        
        return {
            "tool": self.name,
            "params": example_params,
            "reasoning": f"Example usage of {self.name}"
        }

# 🎯 HERRAMIENTAS DE EJEMPLO CON SCHEMAS REALES
class MemorySaveTool(BaseTool):
    """Herramienta para guardar información en memoria"""
    
    name = "memory_save"
    description = "Guarda información importante en la memoria del sistema"
    
    schema = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Contenido a guardar en memoria (información del usuario, conversación importante, etc.)"
            },
            "session_id": {
                "type": "string", 
                "description": "ID de sesión para organizar memorias",
                "default": "default"
            },
            "data_type": {
                "type": "string",
                "enum": ["text", "conversation", "summary", "important"],
                "description": "Tipo de memoria a guardar",
                "default": "text"
            },
            "importance": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "description": "Nivel de importancia de la memoria",
                "default": "medium"
            },
            "tags": {
                "type": "string",
                "description": "Etiquetas separadas por comas para categorización"
            }
        },
        "required": ["content"]
    }
    
    def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Lógica específica para guardar memoria"""
        # Esta sería implementada por el adapter real
        return {
            "success": True,
            "message": f"Memoria guardada: {params['content'][:50]}...",
            "memory_id": "mem_" + str(hash(params['content']))[:8]
        }

class MemorySearchTool(BaseTool):
    """Herramienta para buscar en memoria"""
    
    name = "memory_search"
    description = "Busca información en la memoria del sistema"
    
    schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Consulta de búsqueda para encontrar memorias relevantes"
            },
            "session_id": {
                "type": "string",
                "description": "ID de sesión para buscar memorias específicas",
                "default": "default"
            },
            "limit": {
                "type": "integer",
                "description": "Número máximo de resultados",
                "default": 5,
                "minimum": 1,
                "maximum": 20
            },
            "data_type": {
                "type": "string",
                "enum": ["text", "conversation", "summary", "important", "all"],
                "description": "Filtrar por tipo de memoria",
                "default": "all"
            }
        },
        "required": ["query"]
    }
    
    def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Lógica específica para buscar memoria"""
        # Esta sería implementada por el adapter real
        return {
            "success": True,
            "message": f"Búsqueda completada para: {params['query']}",
            "results": [],
            "count": 0
        }

# 🎯 ADAPTERS DE MEMORIA
class MemorySaveAdapter:
    """Adapter para guardar memoria en el sistema unificado"""
    
    def __init__(self):
        """Inicializa el adapter de guardado de memoria"""
        self.logger = logging.getLogger(f"{__name__}.MemorySaveAdapter")
    
    def process(self, params):
        """Guardar información en la memoria del sistema"""
        try:
            from nodes.memory.unified_memory_manager import unified_memory
            
            # ✅ EXTRAER PARÁMETROS CORRECTAMENTE
            content = params.get("content") or params.get("value") or params.get("data", "")
            tags = params.get("tags", [])
            importance = params.get("importance", "medium")
            session_id = params.get("session_id", "default")
            memory_type = params.get("memory_type", "user_note")
            
            if not content:
                return {
                    "success": False,
                    "error": "Contenido a guardar es requerido"
                }
            
            # Procesar tags si vienen como string
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            elif not isinstance(tags, list):
                tags = []
            
            # ✅ USAR LA INTERFAZ CORRECTA DE store_memory
            # Verificar la signatura del método store_memory
            import inspect
            
            try:
                # Obtener la signatura actual del método
                store_method = getattr(unified_memory, 'store_memory')
                sig = inspect.signature(store_method)
                param_names = list(sig.parameters.keys())
                
                # ✅ LLAMAR CON LA INTERFAZ CORRECTA
                if len(param_names) >= 6:  # Interfaz completa
                    # store_memory(session_id, key, data, memory_type, tags=None, importance="medium", metadata=None)
                    import time
                    memory_key = f"user_note_{int(time.time())}"
                    
                    result = unified_memory.store_memory(
                        session_id,
                        memory_key,
                        content,
                        memory_type,
                        tags=tags,
                        importance=importance,
                        metadata={
                            "source": "memory_save_tool",
                            "user_provided": True,
                            "timestamp": time.time()
                        }
                    )
                else:
                    # Interfaz simplificada - usar solo parámetros básicos
                    result = unified_memory.store_memory(
                        session_id,
                        content,
                        memory_type
                    )
                
                # ✅ VERIFICAR RESULTADO
                if isinstance(result, dict):
                    successful_backends = [k for k, v in result.items() if v == "success"]
                    
                    if successful_backends:
                        return {
                            "success": True,
                            "message": f"Memoria guardada exitosamente en {len(successful_backends)} sistemas",
                            "result": {
                                "content": content,
                                "backends": successful_backends,
                                "tags": tags,
                                "importance": importance,
                                "session_id": session_id,
                                "storage_summary": f"Guardado en: {', '.join(successful_backends)}"
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"No se pudo guardar en ningún sistema de memoria: {result}"
                        }
                else:
                    # Resultado booleano o desconocido
                    return {
                        "success": bool(result),
                        "message": "Memoria guardada" if result else "Error guardando memoria",
                        "result": {
                            "content": content,
                            "tags": tags,
                            "importance": importance
                        }
                    }
                
            except Exception as store_error:
                self.logger.error(f"Error calling store_memory: {store_error}")
                return {
                    "success": False,
                    "error": f"Error en interfaz de memoria: {str(store_error)}"
                }
                
        except Exception as e:
            self.logger.error(f"Error saving memory: {e}")
            return {
                "success": False,
                "error": f"Error guardando memoria: {str(e)}"
            }

class MemorySearchAdapter:
    """Adapter para buscar en la memoria del sistema"""
    
    def __init__(self):
        """Inicializa el adapter de búsqueda de memoria"""
        self.logger = logging.getLogger(f"{__name__}.MemorySearchAdapter")
    
    def process(self, params):
        """Buscar en la memoria del sistema"""
        try:
            from nodes.memory.unified_memory_manager import unified_memory
            
            # ✅ EXTRAER PARÁMETROS CORRECTAMENTE
            query = params.get("query", "")
            session_id = params.get("session_id", "default")
            data_type = params.get("data_type", "all")
            limit = params.get("limit", 10)
            tags = params.get("tags", [])
            
            if not query:
                return {
                    "success": False,
                    "error": "Query de búsqueda es requerida"
                }
            
            # Procesar tags si vienen como string
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            
            # ✅ USAR EL MÉTODO RETRIEVE_MEMORY QUE ACABAMOS DE CREAR
            results = unified_memory.retrieve_memory(
                session_id=session_id,
                query=query,
                data_type=data_type,
                limit=limit,
                tags=tags
            )
            
            if results.get("error"):
                return {
                    "success": False,
                    "error": f"Error buscando en memoria: {results['error']}"
                }
            
            memories = results.get("memories", [])
            
            # ✅ FORMATEAR RESULTADOS PARA EL USUARIO
            if memories:
                formatted_memories = []
                for memory in memories:
                    formatted_memories.append({
                        "content": memory.get("content", ""),
                        "source": memory.get("source", "unknown"),
                        "score": memory.get("score", 0.0),
                        "timestamp": memory.get("timestamp", ""),
                        "tags": memory.get("tags", [])
                    })
                
                return {
                    "success": True,
                    "message": f"Encontradas {len(memories)} memorias relevantes",
                    "result": {
                        "query": query,
                        "total_found": results.get("total_found", 0),
                        "memories": formatted_memories,
                        "backends_used": results.get("backends_used", []),
                        "search_summary": f"Búsqueda '{query}' encontró {len(memories)} resultados"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"No se encontraron memorias para la búsqueda: {query}",
                    "result": {
                        "query": query,
                        "total_found": 0,
                        "memories": [],
                        "backends_used": results.get("backends_used", []),
                        "search_summary": f"Sin resultados para '{query}'"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error searching memory: {e}")
            return {
                "success": False,
                "error": f"Error buscando en memoria: {str(e)}"
            }

class ImageAdapter(BaseTool):
    """Adapter para generación de imágenes"""
    
    name = "image_generator"
    description = "Genera imágenes a partir de descripciones de texto"
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Schema para generación de imágenes"""
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Descripción detallada de la imagen a generar",
                    "minLength": 10,
                    "maxLength": 500
                },
                "width": {
                    "type": "integer",
                    "description": "Ancho de la imagen en píxeles",
                    "default": 512,
                    "minimum": 256,
                    "maximum": 1024
                },
                "height": {
                    "type": "integer", 
                    "description": "Alto de la imagen en píxeles",
                    "default": 512,
                    "minimum": 256,
                    "maximum": 1024
                },
                "style": {
                    "type": "string",
                    "description": "Estilo artístico de la imagen",
                    "enum": ["realistic", "digital_art", "anime", "oil_painting", "watercolor", "pencil_sketch", "photography", "3d_render"],
                    "default": "digital_art"
                },
                "quality": {
                    "type": "string",
                    "description": "Calidad de la imagen",
                    "enum": ["standard", "hd"],
                    "default": "standard"
                }
            },
            "required": ["prompt"],
            "additionalProperties": False
        }
    
    def custom_validation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validación específica de generación de imágenes"""
        prompt = params.get("prompt", "").strip()
        style = params.get("style", "digital_art")
        
        if not prompt:
            return {
                "valid": False,
                "error": "Prompt es requerido para generar imagen"
            }
        
        if len(prompt) < 10:
            return {
                "valid": False,
                "error": "Prompt debe tener al menos 10 caracteres"
            }
        
        # ✅ MAPEO AUTOMÁTICO DE ESTILOS NO VÁLIDOS
        style_mapping = {
            "oscuro y gótico": "digital_art",
            "gothic": "digital_art", 
            "dark": "digital_art",
            "metal": "digital_art",
            "rock": "digital_art",
            "artístico": "oil_painting",
            "realista": "realistic",
            "fotografía": "photography"
        }
        
        if style in style_mapping:
            params["style"] = style_mapping[style]
            logger.info(f"🎨 Style mapped: '{style}' → '{params['style']}'")
        
        return {"valid": True}