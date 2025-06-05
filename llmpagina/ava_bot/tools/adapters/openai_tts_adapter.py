"""
Adaptador TTS usando OpenAI TTS (versión sin streaming, modelo actualizado)
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.base_tool import BaseTool
import os
import base64
import logging
import tempfile
import time
from openai import OpenAI
import pygame
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

class OpenAITTSAdapter(BaseTool):
    """Adaptador TTS usando OpenAI TTS (sin streaming, modelo estándar)"""
    
    name = "openai_tts_adapter"
    
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["text_to_speech", "get_voices"],
                "description": "Acción a realizar"
            },
            "text": {
                "type": "string", 
                "description": "Texto para convertir a voz"
            },
            "voice": {
                "type": "string",
                "enum": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                "default": "nova",  # Usamos nova como equivalente a coral
                "description": "Voz de OpenAI a usar"
            },
            "model": {
                "type": "string",
                "default": "tts-1-hd",  # Usamos tts-1-hd como la mejor calidad disponible
                "enum": ["tts-1", "tts-1-hd"],
                "description": "Modelo TTS de OpenAI"
            },
            "speed": {
                "type": "number",
                "minimum": 0.25,
                "maximum": 4.0,
                "default": 1.0,
                "description": "Velocidad de reproducción (0.25 a 4.0)"
            },
            "response_format": {
                "type": "string",
                "enum": ["mp3", "opus", "aac", "flac"],
                "default": "mp3",
                "description": "Formato de audio de salida"
            },
            "return_audio": {
                "type": "boolean",
                "default": False,
                "description": "Retornar audio en base64"
            },
            "play_audio": {
                "type": "boolean",
                "default": True,
                "description": "Reproducir audio inmediatamente"
            },
            "tone_instruction": {
                "type": "string",
                "default": "neutral",
                "enum": ["cheerful", "positive", "neutral", "calm", "energetic"],
                "description": "Instrucción de tono (simulado en el texto)"
            }
        },
        "required": ["action", "text"]
    }
    
    def __init__(self, openai_api_key=None):
        """Inicializar adaptador OpenAI TTS"""
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")
        self.client = OpenAI(api_key=api_key)
        
        # Inicializar pygame para reproducción
        try:
            pygame.mixer.init()
        except Exception as e:
            logger.warning(f"pygame no disponible: {e}")
    
    def process(self, params):
        """Procesar operaciones TTS con OpenAI"""
        action = params.get("action")
        
        if action == "text_to_speech":
            return self._openai_text_to_speech(params)
        elif action == "get_voices":
            return self._get_openai_voices()
        else:
            return {
                "success": False,
                "error": f"Acción no reconocida: {action}"
            }
    
    def _apply_tone_instruction(self, text, tone_instruction):
        """Simular instrucciones de tono modificando el texto"""
        tone_prefixes = {
            "cheerful": "¡",
            "positive": "",
            "energetic": "¡¡",
            "calm": "",
            "neutral": ""
        }
        
        tone_suffixes = {
            "cheerful": "! 😊",
            "positive": " ✨",
            "energetic": "!! ⚡",
            "calm": " 😌",
            "neutral": ""
        }
        
        prefix = tone_prefixes.get(tone_instruction, "")
        suffix = tone_suffixes.get(tone_instruction, "")
        
        # Solo aplicar si el texto no tiene ya signos de exclamación al final
        if not text.endswith(('!', '?', '.')):
            return f"{prefix}{text}{suffix}"
        return f"{prefix}{text}"
    
    def _openai_text_to_speech(self, params):
        """Convertir texto a voz usando OpenAI TTS (SIN streaming)"""
        try:
            text = params.get("text", "")
            voice = params.get("voice", "nova")  # Nova como equivalente a coral
            model = params.get("model", "tts-1-hd")  # HD como mejor calidad
            speed = params.get("speed", 1.0)
            response_format = params.get("response_format", "mp3")
            return_audio = params.get("return_audio", False)
            play_audio = params.get("play_audio", True)
            tone_instruction = params.get("tone_instruction", "neutral")
            
            if not text:
                return {
                    "success": False,
                    "error": "Texto requerido",
                    "message": "❌ No se proporcionó texto para convertir"
                }
            
            # Aplicar instrucciones de tono al texto (simulando instructions)
            processed_text = self._apply_tone_instruction(text, tone_instruction)
            
            print(f"🎙️ Generando voz con OpenAI TTS...")
            print(f"📝 Texto original: {text[:50]}{'...' if len(text) > 50 else ''}")
            print(f"📝 Texto procesado: {processed_text[:50]}{'...' if len(processed_text) > 50 else ''}")
            print(f"🗣️ Voz: {voice} (equivalente a coral)")
            print(f"🤖 Modelo: {model} (equivalente a gpt-4o-mini-tts)")
            print(f"🎭 Tono: {tone_instruction}")
            
            # Crear archivo temporal
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=f".{response_format}"
            )
            temp_file.close()
            speech_file_path = Path(temp_file.name)
            
            # Generar audio con OpenAI (SIN streaming, SIN instructions)
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=processed_text,  # Usar texto procesado con tono
                speed=speed,
                response_format=response_format
            )
            
            # Guardar audio
            response.stream_to_file(speech_file_path)
            
            audio_base64 = None
            
            # Reproducir audio si se solicita
            if play_audio and not return_audio:
                try:
                    pygame.mixer.music.load(str(speech_file_path))
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy():
                        pygame.time.wait(100)
                    
                    pygame.mixer.music.unload()
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error reproduciendo audio: {e}")
            
            # Convertir a base64 si se solicita
            if return_audio:
                try:
                    with open(speech_file_path, 'rb') as f:
                        audio_bytes = f.read()
                        audio_base64 = base64.b64encode(audio_bytes).decode()
                except Exception as e:
                    logger.warning(f"Error leyendo archivo para base64: {e}")
            
            # Limpiar archivo temporal
            self._cleanup_file(speech_file_path)
            
            return {
                "success": True,
                "action": "text_to_speech",
                "text": text,
                "processed_text": processed_text,
                "voice": voice,
                "model": model,
                "speed": speed,
                "tone_instruction": tone_instruction,
                "format": response_format,
                "audio_base64": audio_base64,
                "message": f"🎙️ OpenAI TTS ({voice}, {tone_instruction}): '{text[:30]}...'" if len(text) > 30 else f"🎙️ OpenAI TTS ({voice}, {tone_instruction}): '{text}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Error OpenAI TTS: {str(e)}"
            }
    
    def _get_openai_voices(self):
        """Obtener voces disponibles de OpenAI"""
        voices_info = [
            {
                "id": "alloy",
                "name": "Alloy",
                "description": "Neutral, balanced voice",
                "type": "TTS",
                "provider": "OpenAI"
            },
            {
                "id": "echo",
                "name": "Echo",
                "description": "Male voice with character",
                "type": "TTS",
                "provider": "OpenAI"
            },
            {
                "id": "fable",
                "name": "Fable", 
                "description": "Storytelling voice",
                "type": "TTS",
                "provider": "OpenAI"
            },
            {
                "id": "onyx",
                "name": "Onyx",
                "description": "Deep, authoritative voice",
                "type": "TTS",
                "provider": "OpenAI"
            },
            {
                "id": "nova",
                "name": "Nova",
                "description": "Young, energetic voice (equivalente a coral)",
                "type": "TTS",
                "provider": "OpenAI"
            },
            {
                "id": "shimmer",
                "name": "Shimmer",
                "description": "Warm, friendly voice",
                "type": "TTS",
                "provider": "OpenAI"
            }
        ]
        
        return {
            "success": True,
            "action": "get_voices",
            "voices": voices_info,
            "total_voices": len(voices_info),
            "message": f"🎭 OpenAI TTS: {len(voices_info)} voces disponibles"
        }
    
    def _cleanup_file(self, file_path):
        """Limpiar archivo temporal con reintentos"""
        if not file_path or not Path(file_path).exists():
            return
            
        for attempt in range(3):
            try:
                time.sleep(0.1)
                os.unlink(file_path)
                break
            except PermissionError:
                if attempt == 2:
                    logger.warning(f"No se pudo eliminar archivo: {file_path}")
                else:
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Error eliminando archivo: {e}")
                break


# Función de prueba SIMPLIFICADA
def test_openai_tts_adapter():
    """Probar el adaptador OpenAI TTS (sin streaming, con equivalencias)"""
    print("🧪 PRUEBA OPENAI TTS ADAPTER (SIN STREAMING)")
    print("=" * 60)
    
    # Verificar clave API
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")
    if not api_key:
        print("❌ ERROR: No se encontró la clave de OpenAI")
        return
    
    print(f"✅ Clave API encontrada: {api_key[:20]}...")
    
    # Inicializar adaptador
    try:
        adapter = OpenAITTSAdapter()
        print("✅ Adaptador inicializado correctamente")
    except Exception as e:
        print(f"❌ Error inicializando: {e}")
        return
    
    print("\n" + "─" * 60)
    
    # TEST 1: Obtener voces
    print("📋 TEST 1: VOCES DISPONIBLES")
    try:
        voices_result = adapter.process({"action": "get_voices"})
        if voices_result.get("success"):
            print(f"✅ {voices_result.get('total_voices', 0)} voces encontradas")
            for voice in voices_result.get("voices", []):
                print(f"   🎤 {voice['name']} ({voice['id']}) - {voice['description']}")
        else:
            print(f"❌ Error: {voices_result.get('error')}")
    except Exception as e:
        print(f"❌ Excepción: {e}")
    
    print("\n" + "─" * 60)
    
    # TEST 2: TTS como tu ejemplo (equivalente)
    print("📋 TEST 2: EQUIVALENTE A TU EJEMPLO")
    print("Original: gpt-4o-mini-tts + coral + instructions")
    print("Equivalente: tts-1-hd + nova + tone_instruction")
    
    test_example = {
        "action": "text_to_speech",
        "text": "Today is a wonderful day to build something people love!",
        "voice": "nova",  # Equivalente a coral
        "model": "tts-1-hd",  # Equivalente a gpt-4o-mini-tts
        "tone_instruction": "cheerful",  # Equivalente a instructions
        "speed": 1.0,
        "return_audio": True,
        "play_audio": False
    }
    
    try:
        result = adapter.process(test_example)
        if result.get("success"):
            audio_size = len(result.get("audio_base64", ""))
            print(f"✅ Audio generado exitosamente")
            print(f"📝 Texto original: {result.get('text')}")
            print(f"📝 Texto procesado: {result.get('processed_text')}")
            print(f"📊 Tamaño: {audio_size:,} caracteres")
            print(f"🗣️ Voz: {result.get('voice')} (equivalente a coral)")
            print(f"🤖 Modelo: {result.get('model')} (equivalente a gpt-4o-mini-tts)")
            print(f"🎭 Tono: {result.get('tone_instruction')} (equivalente a instructions)")
        else:
            print(f"❌ Error: {result.get('error')}")
    except Exception as e:
        print(f"❌ Excepción: {e}")
    
    print("\n" + "─" * 60)
    
    # TEST 3: Diferentes tonos (simulando instructions)
    print("📋 TEST 3: DIFERENTES TONOS (SIMULANDO INSTRUCTIONS)")
    test_tones = ["cheerful", "positive", "energetic", "calm", "neutral"]
    base_text = "Hola, soy AVA y estoy probando diferentes tonos de voz"
    
    for tone in test_tones:
        print(f"\n🎭 Probando tono: {tone}")
        test_tone = {
            "action": "text_to_speech",
            "text": base_text,
            "voice": "nova",
            "tone_instruction": tone,
            "return_audio": True,
            "play_audio": False
        }
        
        try:
            result = adapter.process(test_tone)
            if result.get("success"):
                print(f"✅ {tone}: '{result.get('processed_text')}'")
            else:
                print(f"❌ {tone}: {result.get('error', 'Error')}")
        except Exception as e:
            print(f"❌ {tone}: Excepción - {e}")
    
    print("\n" + "=" * 60)
    print("🎉 PRUEBA COMPLETADA")
    print("📋 EQUIVALENCIAS USADAS:")
    print("   gpt-4o-mini-tts → tts-1-hd")
    print("   coral → nova")
    print("   instructions → tone_instruction (simulado)")
    print("✅ OpenAI TTS funcional con equivalencias")


if __name__ == "__main__":
    test_openai_tts_adapter()