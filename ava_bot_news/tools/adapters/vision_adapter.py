"""
Vision Adapter - meta-llama/llama-4-scout-17b-16e-instruct
===========================================================

Adapter para procesamiento de imágenes usando Llama 4 Scout.
Funciona completamente offline sin necesidad de servidor web.
"""

import os
import sys
import logging
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import requests
from PIL import Image
from datetime import datetime
from io import BytesIO

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisionAdapter:
    """
    Adapter para análisis de visión completamente offline
    
    Funcionalidades:
    - Análisis de imágenes sin servidor web
    - Procesamiento directo con base64
    - Múltiples tipos de análisis
    - Compatible con archivos locales
    """
    
    def __init__(self):
        self.name = "vision"
        self.description = "Análisis de imágenes con Llama 4 Scout Vision - modo offline"
        
        # Configuración del modelo
        self.model_name = "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo"  # Modelo con soporte de visión confirmado
        self.api_key = os.getenv('TOGETHER_API_KEY')
        self.api_base = "https://api.together.xyz/v1"
        
        # Tipos de archivo soportados
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        self.max_file_size = 20 * 1024 * 1024  # 20MB
        
        # Esquema para análisis
        self.schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "analyze_image",
                        "describe_image",
                        "ocr_text",
                        "test_analyze"
                    ],
                    "description": "Acción para análisis de imagen"
                },
                "image_path": {
                    "type": "string",
                    "description": "Ruta completa de la imagen a analizar"
                },
                "user_question": {
                    "type": "string",
                    "description": "Pregunta específica del usuario sobre la imagen"
                },
                "detail_level": {
                    "type": "string",
                    "enum": ["low", "high", "auto"],
                    "description": "Nivel de detalle para el análisis",
                    "default": "high"
                }
            },
            "required": ["action", "image_path"]
        }
        
        logger.info(f"✅ VisionAdapter inicializado en modo offline")
    
    def _encode_image_to_base64(self, image_path: Path) -> Optional[str]:
        """Convertir imagen a base64 optimizado para API"""
        try:
            if not image_path.exists():
                logger.error(f"❌ Archivo no existe: {image_path}")
                return None
            
            logger.info(f"📷 Procesando imagen: {image_path.name} ({image_path.stat().st_size // 1024}KB)")
            
            # Abrir y optimizar imagen
            with Image.open(image_path) as img:
                # Convertir a RGB si es necesario
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Redimensionar si es muy grande (mantener calidad para análisis)
                max_dimension = 1024  # Reducir para evitar errores de API
                if max(img.size) > max_dimension:
                    ratio = max_dimension / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    logger.info(f"🔧 Imagen redimensionada a: {new_size}")
                
                # Convertir a bytes optimizado
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=90, optimize=True)
                image_bytes = buffer.getvalue()
            
            # Verificar tamaño final
            if len(image_bytes) > 10 * 1024 * 1024:  # 10MB límite
                logger.warning(f"⚠️ Imagen muy grande después de optimización: {len(image_bytes) // 1024}KB")
                return None
            
            # Codificar en base64
            base64_string = base64.b64encode(image_bytes).decode('utf-8')
            
            logger.info(f"✅ Imagen codificada: {len(base64_string)} caracteres")
            return base64_string
            
        except Exception as e:
            logger.error(f"❌ Error procesando imagen: {e}")
            return None
    
    def _call_vision_api_direct(self, prompt: str, image_base64: str) -> str:
        """Llamar API directamente con base64"""
        try:
            if not self.api_key:
                return "❌ Error: TOGETHER_API_KEY no configurada en variables de entorno"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Estructura del mensaje para visión
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ]
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.3,
                "top_p": 0.9,
                "stream": False
            }
            
            logger.info(f"🔍 Enviando a API: {self.model_name}")
            logger.info(f"📝 Prompt: {prompt[:100]}...")
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120  # Aumentar timeout
            )
            
            logger.info(f"📡 Respuesta API: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    
                    # Log de uso de tokens
                    if 'usage' in result:
                        usage = result['usage']
                        logger.info(f"📊 Tokens: {usage.get('total_tokens', 0)} (prompt: {usage.get('prompt_tokens', 0)}, completion: {usage.get('completion_tokens', 0)})")
                    
                    logger.info(f"✅ Análisis completado: {len(content)} caracteres")
                    return content
                else:
                    logger.error(f"❌ Respuesta sin contenido: {result}")
                    return "❌ La API no devolvió contenido válido"
            
            elif response.status_code == 400:
                error_detail = response.json() if response.content else {"error": "Bad request"}
                logger.error(f"❌ Error 400: {error_detail}")
                return f"❌ Error de solicitud: {error_detail.get('error', {}).get('message', 'Solicitud inválida')}"
            
            elif response.status_code == 401:
                logger.error("❌ Error 401: API key inválida")
                return "❌ Error de autenticación: Verifica tu TOGETHER_API_KEY"
            
            elif response.status_code == 429:
                logger.error("❌ Error 429: Límite de rate excedido")
                return "❌ Demasiadas solicitudes. Intenta de nuevo en unos momentos"
            
            else:
                error_text = response.text[:500] if response.text else "Error desconocido"
                logger.error(f"❌ Error {response.status_code}: {error_text}")
                return f"❌ Error de API ({response.status_code}): {error_text}"
                
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout en la solicitud")
            return "❌ La solicitud tardó demasiado. Intenta con una imagen más pequeña"
        
        except requests.exceptions.ConnectionError:
            logger.error("❌ Error de conexión")
            return "❌ No se pudo conectar a la API. Verifica tu conexión a internet"
        
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return f"❌ Error procesando imagen: {str(e)}"
    
    def _generate_prompt(self, action: str, user_question: str = "") -> str:
        """Generar prompt según la acción"""
        prompts = {
            "analyze_image": "Analiza esta imagen detalladamente. Describe lo que ves, incluyendo objetos, personas, colores, composición y cualquier detalle relevante.",
            "describe_image": "Describe esta imagen de manera clara y completa. Incluye todos los elementos visibles y su disposición.",
            "ocr_text": "Extrae y transcribe todo el texto visible en esta imagen. Si no hay texto, indica 'No se encontró texto legible'.",
            "test_analyze": "Realiza un análisis completo de esta imagen de prueba. Describe todo lo que puedas observar con el máximo detalle posible."
        }
        
        base_prompt = prompts.get(action, prompts["describe_image"])
        
        if user_question:
            base_prompt += f"\n\nPregunta específica: {user_question}"
        
        base_prompt += "\n\nResponde en español de manera clara y estructurada."
        
        return base_prompt
    
    def analyze_image(self, params: Dict[str, Any]) -> str:
        """Método principal de análisis"""
        try:
            action = params.get('action', 'describe_image')
            image_path = Path(params.get('image_path', ''))
            user_question = params.get('user_question', '')
            
            logger.info(f"🔍 Iniciando análisis: {action}")
            logger.info(f"📁 Archivo: {image_path}")
            
            # Validar archivo
            if not image_path.exists():
                return f"❌ El archivo no existe: {image_path}"
            
            if image_path.suffix.lower() not in self.supported_formats:
                return f"❌ Formato no soportado: {image_path.suffix}. Usa: {', '.join(self.supported_formats)}"
            
            if image_path.stat().st_size > self.max_file_size:
                return f"❌ Archivo muy grande: {image_path.stat().st_size // 1024 // 1024}MB. Máximo: {self.max_file_size // 1024 // 1024}MB"
            
            # Procesar imagen
            image_base64 = self._encode_image_to_base64(image_path)
            if not image_base64:
                return f"❌ No se pudo procesar la imagen: {image_path.name}"
            
            # Generar prompt
            prompt = self._generate_prompt(action, user_question)
            
            # Llamar API
            result = self._call_vision_api_direct(prompt, image_base64)
            
            # Formatear respuesta
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            response = f"""
🖼️ **Análisis de Imagen: {image_path.name}**

{result}

---
🤖 **Detalles del análisis:**
• Archivo: {image_path.name} ({image_path.stat().st_size // 1024}KB)
• Modelo: {self.model_name}
• Hora: {timestamp}
• Acción: {action}
"""
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error en análisis: {e}")
            return f"❌ Error procesando imagen: {str(e)}"
    
    def process(self, params: Dict[str, Any]) -> str:
        """Método principal del adapter"""
        try:
            action = params.get('action', 'describe_image')
            logger.info(f"🔍 VisionAdapter procesando: {action}")
            
            valid_actions = ['analyze_image', 'describe_image', 'ocr_text', 'test_analyze']
            
            if action in valid_actions:
                return self.analyze_image(params)
            else:
                return f"❌ Acción no válida: {action}. Acciones disponibles: {', '.join(valid_actions)}"
                
        except Exception as e:
            logger.error(f"❌ Error en VisionAdapter: {e}")
            return f"❌ Error procesando solicitud: {str(e)}"
    
    def execute(self, params: Dict[str, Any]) -> str:
        """Alias para process (compatibilidad MCP)"""
        return self.process(params)

# ==========================================
# PRUEBA OFFLINE SIN SERVIDOR
# ==========================================

def test_vision_offline():
    """Prueba offline sin servidor web"""
    print("\n" + "="*60)
    print("🧪 PRUEBA VISION ADAPTER - MODO OFFLINE")
    print("="*60)
    
    # Crear adapter
    adapter = VisionAdapter()
    
    # Verificar API key
    api_key = os.getenv('TOGETHER_API_KEY')
    if not api_key:
        print("❌ ERROR: TOGETHER_API_KEY no encontrada en variables de entorno")
        print("   Agrega la key a tu .env: TOGETHER_API_KEY=tu_key_aqui")
        return
    
    print(f"✅ API Key configurada: {api_key[:20]}...")
    
    # Ruta de la imagen de prueba
    test_image_path = r"D:\ComfyUI_windows_portable\ComfyUI\output\ComfyUI_00137_.png"
    
    print(f"📸 Imagen a analizar: {test_image_path}")
    
    # Verificar que existe
    if not Path(test_image_path).exists():
        print(f"❌ ERROR: La imagen no existe en la ruta especificada")
        print(f"   Verifica que el archivo existe: {test_image_path}")
        return
    
    # Casos de prueba simplificados
    test_cases = [
        {
            'name': 'Análisis Básico',
            'params': {
                'action': 'test_analyze',
                'image_path': test_image_path
            }
        },
        {
            'name': 'Descripción Detallada',
            'params': {
                'action': 'describe_image',
                'image_path': test_image_path,
                'user_question': '¿Qué tipo de imagen es esta y qué elementos principales contiene?'
            }
        },
        {
            'name': 'Extracción de Texto',
            'params': {
                'action': 'ocr_text',
                'image_path': test_image_path
            }
        }
    ]
    
    # Ejecutar pruebas
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔬 PRUEBA {i}: {test_case['name']}")
        print("-" * 50)
        
        try:
            result = adapter.process(test_case['params'])
            print(result)
            
        except Exception as e:
            print(f"❌ Error en prueba {i}: {e}")
        
        print("\n" + "="*50)
        
        # Pausa entre pruebas para evitar rate limiting
        if i < len(test_cases):
            print("⏱️ Esperando 2 segundos...")
            import time
            time.sleep(2)
    
    print("✅ Pruebas offline completadas")

if __name__ == "__main__":
    # Ejecutar prueba offline
    test_vision_offline()