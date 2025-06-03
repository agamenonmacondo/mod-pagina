import os
import sys
import json
import logging
import requests
import base64
from datetime import datetime
from pathlib import Path
import io
from PIL import Image, ImageDraw, ImageFont

# Setup logging
logger = logging.getLogger(__name__)

class ImageAdapter:
    def __init__(self):
        """Inicializar adaptador de imágenes con Together API"""
        self.description = "Ava Bot Image Generator - Together API FLUX.1"
        
        # ✅ CONFIGURACIÓN TOGETHER API
        self.together_api_key = os.getenv("TOGETHER_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.has_real_generator = bool(self.together_api_key)
        
        # Configurar directorio de salida
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(current_dir, "..", "..", "generated_images")
        os.makedirs(self.output_dir, exist_ok=True)
        
        if self.has_real_generator:
            logger.info("✅ Together API FLUX.1 configurado correctamente")
        else:
            logger.warning("⚠️ TOGETHER_API_KEY no encontrada - usando modo simulación")
    
    def execute(self, arguments: dict) -> dict:
        """Ejecutar generación de imagen REAL con Together API"""
        try:
            prompt = arguments.get('prompt', 'beautiful landscape')
            style = arguments.get('style', 'photorealistic')
            
            if not self.has_real_generator:
                return self._fallback_message(prompt, style)
            
            # ✅ GENERAR IMAGEN REAL CON TOGETHER API
            logger.info(f"🎨 Generando imagen con Together API: {prompt[:50]}...")
            result = self._generate_with_together_flux(prompt, style)
            
            if result.get('success'):
                return {
                    "content": [{
                        "type": "text",
                        "text": f"🎨 **¡Imagen generada exitosamente con IA!**\n\n"
                               f"📝 **Descripción:** {prompt}\n"
                               f"🎭 **Estilo:** {style}\n"
                               f"📁 **Guardada en:** {result['filepath']}\n"
                               f"🤖 **Modelo:** FLUX.1-schnell-Free\n"
                               f"⚡ **Generada en:** {result.get('generation_time', 'N/A')} segundos\n\n"
                               f"✨ **¡Tu imagen está lista para usar!**"
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ **Error generando imagen**\n\n"
                               f"**Error:** {result.get('error', 'Error desconocido')}\n"
                               f"**Prompt:** {prompt}\n\n"
                               f"🔧 **Posibles soluciones:**\n"
                               f"• Verificar TOGETHER_API_KEY\n"
                               f"• Simplificar la descripción\n"
                               f"• Intentar nuevamente en unos minutos"
                    }]
                }
                
        except Exception as e:
            logger.error(f"Error en image adapter: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error del sistema de imágenes: {str(e)}"
                }]
            }
    
    def _generate_with_together_flux(self, prompt: str, style: str) -> dict:
        """Generar imagen real con Together API FLUX.1"""
        start_time = datetime.now()
        
        try:
            # ✅ MEJORAR PROMPT SEGÚN ESTILO
            enhanced_prompt = self._enhance_prompt(prompt, style)
            logger.info(f"🎯 Prompt mejorado: {enhanced_prompt[:100]}...")
            
            # ✅ CONFIGURACIÓN TOGETHER API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.together_api_key}"
            }
            
            payload = {
                "model": "black-forest-labs/FLUX.1-schnell-Free",
                "prompt": enhanced_prompt,
                "width": 1024,
                "height": 768,
                "steps": 4,  # FLUX schnell es rápido con pocos steps
                "response_format": "b64_json"
            }
            
            logger.info("📡 Enviando solicitud a Together API...")
            response = requests.post(
                "https://api.together.xyz/v1/images/generations",
                headers=headers,
                json=payload,
                timeout=120  # 2 minutos timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("data") and data["data"][0].get("b64_json"):
                # ✅ DECODIFICAR Y GUARDAR IMAGEN
                image_data = base64.b64decode(data["data"][0]["b64_json"])
                filepath = self._save_image(image_data, enhanced_prompt)
                
                generation_time = (datetime.now() - start_time).total_seconds()
                
                return {
                    'success': True,
                    'filepath': filepath,
                    'prompt_used': enhanced_prompt,
                    'generation_time': round(generation_time, 2),
                    'model': 'FLUX.1-schnell-Free'
                }
            else:
                return {
                    'success': False,
                    'error': 'Respuesta inválida de la API - no se recibió imagen'
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Timeout - La generación tardó demasiado (>2 min)'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Error de conexión con Together API: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """Mejorar prompt según estilo solicitado"""
        # Limpiar y preparar prompt base
        base_prompt = prompt.strip()
        
        # Agregar modificadores según estilo
        if style.lower() == "photorealistic":
            enhancement = ", photorealistic, high quality, detailed, professional photography, studio lighting, sharp focus, 8k resolution"
        elif style.lower() == "artistic":
            enhancement = ", artistic style, beautiful composition, creative, expressive, masterpiece, fine art"
        elif style.lower() == "anime":
            enhancement = ", anime style, manga art, colorful, detailed animation style, japanese art"
        elif style.lower() == "cyberpunk":
            enhancement = ", cyberpunk style, neon lights, futuristic, dark atmosphere, sci-fi, digital art"
        elif style.lower() == "fantasy":
            enhancement = ", fantasy art, magical, ethereal, mystical, detailed fantasy illustration"
        else:
            enhancement = ", high quality, detailed, professional art style"
        
        enhanced = f"{base_prompt}{enhancement}"
        
        # Limpiar prompt para evitar problemas
        enhanced = enhanced.replace('\n', ' ').replace('\r', ' ')
        enhanced = ' '.join(enhanced.split())  # Normalizar espacios
        
        return enhanced[:500]  # Limitar longitud
    
    def _save_image(self, image_data: bytes, prompt: str) -> str:
        """Guardar imagen y metadatos"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # ✅ GUARDAR IMAGEN
            img_filename = f"ava_generated_{timestamp}.png"
            img_path = os.path.join(self.output_dir, img_filename)
            
            with open(img_path, 'wb') as f:
                f.write(image_data)
            
            # ✅ GUARDAR METADATOS
            meta_data = {
                "prompt": prompt,
                "generated_at": datetime.now().isoformat(),
                "model": "FLUX.1-schnell-Free",
                "api": "Together AI",
                "filename": img_filename,
                "size": len(image_data)
            }
            
            meta_filename = f"ava_generated_{timestamp}_meta.json"
            meta_path = os.path.join(self.output_dir, meta_filename)
            
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Imagen guardada: {img_path}")
            logger.info(f"✅ Metadatos guardados: {meta_path}")
            
            return img_path
            
        except Exception as e:
            logger.error(f"Error guardando imagen: {e}")
            return f"Error guardando archivo: {str(e)}"
    
    def _fallback_message(self, prompt: str, style: str) -> dict:
        """Mensaje de fallback cuando no hay API configurada"""
        return {
            "content": [{
                "type": "text",
                "text": f"🎨 **Generador de imágenes no configurado**\n\n"
                       f"📝 **Descripción solicitada:** {prompt}\n"
                       f"🎭 **Estilo:** {style}\n\n"
                       f"🔧 **Para activar generación real de imágenes:**\n\n"
                       f"1. **Obtén una API key de Together AI:**\n"
                       f"   • Ve a https://api.together.xyz/\n"
                       f"   • Regístrate y obtén tu API key\n\n"
                       f"2. **Configura la variable de entorno:**\n"
                       f"   • Agrega: `TOGETHER_API_KEY=tu_api_key_aquí`\n"
                       f"   • En tu archivo .env o variables del sistema\n\n"
                       f"3. **Reinicia el servidor MCP**\n\n"
                       f"💡 **Nota:** Together AI ofrece generación rápida con FLUX.1"
            }]
        }
    
    def process(self, arguments: dict) -> str:
        """Alias para execute - compatibilidad"""
        result = self.execute(arguments)
        if isinstance(result, dict) and "content" in result:
            return result["content"][0]["text"]
        return str(result)

# ✅ FUNCIÓN DE PRUEBA INDEPENDIENTE
def test_together_api():
    """Función para probar Together API directamente"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("❌ TOGETHER_API_KEY no encontrada")
        return False
    
    adapter = ImageAdapter()
    
    test_args = {
        "prompt": "a beautiful sunset over mountains, photorealistic",
        "style": "photorealistic"
    }
    
    print("🧪 Probando generación de imagen...")
    result = adapter.execute(test_args)
    print(f"📄 Resultado: {result}")
    
    return True

if __name__ == "__main__":
    # Ejecutar prueba si se llama directamente
    test_together_api()