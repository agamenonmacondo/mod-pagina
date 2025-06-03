"""
Adaptador simplificado para mostrar información de imágenes
"""
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ImageDisplayAdapter:
    def __init__(self):
        """Inicialización básica"""
        try:
            self.description = "Ava Bot image display tool"
            logger.info("✅ ImageDisplayAdapter inicializado")
        except Exception as e:
            logger.error(f"❌ Error inicializando ImageDisplayAdapter: {e}")
            self.description = "Ava Bot image display tool - Basic mode"
    
    def execute(self, arguments: dict) -> dict:
        """Mostrar información de imagen"""
        try:
            image_path = arguments.get('image_path', '')
            description = arguments.get('description', 'Imagen')
            
            response_text = f"🖼️ **Información de imagen**\n\n" + \
                          f"📁 **Ruta:** {image_path}\n" + \
                          f"📝 **Descripción:** {description}\n\n" + \
                          f"*Esta herramienta mostraría la imagen en un entorno compatible.*"
            
            return {
                "content": [{
                    "type": "text",
                    "text": response_text
                }]
            }
            
        except Exception as e:
            logger.error(f"Error en ImageDisplayAdapter.execute: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error mostrando imagen: {str(e)}"
                }]
            }
    
    def process(self, arguments: dict) -> str:
        """Alias para execute"""
        result = self.execute(arguments)
        if isinstance(result, dict) and "content" in result:
            return result["content"][0]["text"]
        return str(result)