"""
Adaptador Speech usando Groq Whisper Large v3 Turbo
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.base_tool import BaseTool
import pyttsx3
from gtts import gTTS
import pygame
import tempfile
import os
import base64
import logging
from groq import Groq
from pydub import AudioSegment
import io
import requests
import time

logger = logging.getLogger(__name__)

class GroqSpeechAdapter(BaseTool):
    """Adaptador Speech usando Groq Whisper Large v3 Turbo"""
    
    name = "groq_speech_adapter"
    
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["speech_to_text", "text_to_speech", "get_voices", "transcribe_file", "transcribe_url"],
                "description": "Acción a realizar"
            },
            "audio_data": {
                "type": "string",
                "description": "Audio en base64 para STT"
            },
            "audio_url": {
                "type": "string",
                "description": "URL del audio para transcribir"
            },
            "text": {
                "type": "string", 
                "description": "Texto para convertir a voz"
            },
            "language": {
                "type": "string",
                "default": "es",
                "description": "Idioma (es, en, etc.)"
            },
            "engine": {
                "type": "string",
                "enum": ["gtts", "pyttsx3"],
                "default": "gtts",
                "description": "Motor TTS a usar"
            },
            "file_path": {
                "type": "string",
                "description": "Ruta del archivo de audio para transcribir"
            },
            "return_audio": {
                "type": "boolean",
                "default": False,
                "description": "Retornar audio en base64"
            },
            "model": {
                "type": "string",
                "default": "whisper-large-v3-turbo",
                "description": "Modelo Whisper de Groq"
            },
            "prompt": {
                "type": "string",
                "description": "Prompt opcional para guiar la transcripción"
            },
            "temperature": {
                "type": "number",
                "default": 0,
                "description": "Temperatura para la transcripción (0-1)"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self, groq_api_key=None):
        """Inicializar adaptador con Groq"""
        self.groq_client = Groq(api_key=groq_api_key or os.getenv("GROQ_API_KEY"))
        
        # Inicializar TTS
        try:
            self.pyttsx3_engine = pyttsx3.init()
            self.pyttsx3_engine.setProperty('rate', 150)
            self.pyttsx3_engine.setProperty('volume', 0.8)
        except Exception as e:
            self.pyttsx3_engine = None
            logger.warning(f"pyttsx3 no disponible: {e}")
        
        # Inicializar pygame
        try:
            pygame.mixer.init()
        except Exception as e:
            logger.warning(f"pygame no disponible: {e}")
    
    def process(self, params):
        """Procesar operaciones de voz con Groq"""
        action = params.get("action")
        
        if action == "speech_to_text":
            return self._groq_speech_to_text(params)
        elif action == "text_to_speech":
            return self._text_to_speech(params)
        elif action == "get_voices":
            return self._get_voices()
        elif action == "transcribe_file":
            return self._groq_transcribe_file(params)
        elif action == "transcribe_url":
            return self._groq_transcribe_url(params)
        else:
            return {
                "success": False,
                "error": f"Acción no reconocida: {action}"
            }
    
    def _groq_speech_to_text(self, params):
        """Convertir voz a texto usando Groq Whisper Large v3 Turbo"""
        try:
            audio_data = params.get("audio_data")
            model = params.get("model", "whisper-large-v3-turbo")
            prompt = params.get("prompt")
            temperature = params.get("temperature", 0)
            language = params.get("language", "es")
            
            if not audio_data:
                return {
                    "success": False,
                    "error": "Audio data requerido",
                    "message": "❌ No se proporcionó audio para transcribir"
                }
            
            # Decodificar audio base64
            audio_bytes = base64.b64decode(audio_data)
            
            # Crear archivo temporal con manejo mejorado
            temp_file = None
            try:
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_file.write(audio_bytes)
                temp_file.close()  # Cerrar antes de usar en Windows
                
                # Transcribir con Groq Whisper
                with open(temp_file.name, 'rb') as audio_file:
                    transcription = self.groq_client.audio.transcriptions.create(
                        file=audio_file,
                        model=model,
                        prompt=prompt,
                        response_format="json",
                        language=language,
                        temperature=temperature
                    )
                
                text = transcription.text
                
                return {
                    "success": True,
                    "action": "speech_to_text",
                    "text": text,
                    "model": model,
                    "language": language,
                    "confidence": getattr(transcription, 'confidence', None),
                    "message": f"🎤 Whisper Turbo: '{text}'"
                }
                
            finally:
                # Limpiar archivo temporal
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar archivo temporal: {e}")
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Error Groq STT: {str(e)}"
            }
    
    def _groq_transcribe_file(self, params):
        """Transcribir archivo de audio usando Groq"""
        try:
            file_path = params.get("file_path")
            model = params.get("model", "whisper-large-v3-turbo")
            prompt = params.get("prompt")
            temperature = params.get("temperature", 0)
            language = params.get("language", "es")
            
            if not file_path or not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": "Archivo no encontrado",
                    "message": f"❌ El archivo no existe: {file_path}"
                }
            
            print(f"📁 Procesando archivo: {file_path}")
            
            # Convertir archivo si es necesario
            audio_file_path = self._prepare_audio_file(file_path)
            
            try:
                print(f"🚀 Enviando a Groq Whisper {model}...")
                
                with open(audio_file_path, 'rb') as audio_file:
                    transcription = self.groq_client.audio.transcriptions.create(
                        file=audio_file,
                        model=model,
                        prompt=prompt,
                        response_format="json",
                        language=language,
                        temperature=temperature
                    )
                
                text = transcription.text
                
                return {
                    "success": True,
                    "action": "transcribe_file",
                    "text": text,
                    "file_path": file_path,
                    "model": model,
                    "language": language,
                    "message": f"📄 Archivo transcrito con Whisper Turbo: '{text[:100]}...'" if len(text) > 100 else f"📄 Archivo transcrito: '{text}'"
                }
                
            finally:
                # Limpiar archivo temporal si se creó
                if audio_file_path != file_path and os.path.exists(audio_file_path):
                    try:
                        os.unlink(audio_file_path)
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar archivo temporal: {e}")
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Error transcribiendo archivo: {str(e)}"
            }
    
    def _groq_transcribe_url(self, params):
        """Transcribir audio desde URL usando Groq"""
        try:
            audio_url = params.get("audio_url")
            model = params.get("model", "whisper-large-v3-turbo")
            
            if not audio_url:
                return {
                    "success": False,
                    "error": "URL requerida",
                    "message": "❌ No se proporcionó URL de audio"
                }
            
            # Descargar audio
            response = requests.get(audio_url)
            response.raise_for_status()
            
            # Crear archivo temporal
            temp_file = None
            try:
                temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
                temp_file.write(response.content)
                temp_file.close()
                
                # Transcribir
                with open(temp_file.name, 'rb') as audio_file:
                    transcription = self.groq_client.audio.transcriptions.create(
                        file=audio_file,
                        model=model,
                        response_format="json"
                    )
                
                return {
                    "success": True,
                    "action": "transcribe_url",
                    "text": transcription.text,
                    "url": audio_url,
                    "model": model,
                    "message": f"🌐 URL transcrita: '{transcription.text}'"
                }
                
            finally:
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except Exception as e:
                        logger.warning(f"No se pudo eliminar archivo temporal: {e}")
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Error transcribiendo URL: {str(e)}"
            }
    
    def _prepare_audio_file(self, file_path):
        """Preparar archivo de audio para Groq (convertir si es necesario)"""
        # Groq acepta: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm
        supported_formats = ['.flac', '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.ogg', '.wav', '.webm']
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in supported_formats:
            print(f"✅ Formato soportado: {file_ext}")
            return file_path
        
        # Convertir usando pydub
        try:
            print(f"🔄 Convirtiendo {file_ext} a WAV...")
            audio = AudioSegment.from_file(file_path)
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_file.close()  # Cerrar para permitir escritura en Windows
            audio.export(temp_file.name, format='wav')
            print(f"✅ Archivo convertido: {temp_file.name}")
            return temp_file.name
        except Exception as e:
            logger.error(f"Error convirtiendo audio: {e}")
            print(f"❌ Error convirtiendo, usando archivo original: {e}")
            return file_path
    
    def _text_to_speech(self, params):
        """Convertir texto a voz (TTS local) - FIX para Windows"""
        try:
            text = params.get("text", "")
            engine = params.get("engine", "gtts")
            language = params.get("language", "es")
            return_audio = params.get("return_audio", False)
            
            if not text:
                return {
                    "success": False,
                    "error": "Texto requerido",
                    "message": "❌ No se proporcionó texto para convertir"
                }
            
            audio_file = None
            audio_base64 = None
            temp_file = None
            
            if engine == "pyttsx3" and self.pyttsx3_engine:
                # Usar pyttsx3
                if return_audio:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                    temp_file.close()  # Cerrar en Windows
                    self.pyttsx3_engine.save_to_file(text, temp_file.name)
                    self.pyttsx3_engine.runAndWait()
                    audio_file = temp_file.name
                else:
                    self.pyttsx3_engine.say(text)
                    self.pyttsx3_engine.runAndWait()
            else:
                # Usar gTTS
                tts = gTTS(text=text, lang=language, slow=False)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_file.close()  # Cerrar en Windows antes de escribir
                tts.save(temp_file.name)
                audio_file = temp_file.name
                
                if not return_audio:
                    # Reproducir audio
                    try:
                        pygame.mixer.music.load(audio_file)
                        pygame.mixer.music.play()
                        
                        while pygame.mixer.music.get_busy():
                            pygame.time.wait(100)
                        
                        # Esperar un poco antes de limpiar
                        pygame.mixer.music.unload()
                        time.sleep(0.1)
                        
                    except Exception as e:
                        logger.warning(f"Error reproduciendo audio: {e}")
            
            # Convertir a base64 si se solicita
            if return_audio and audio_file and os.path.exists(audio_file):
                try:
                    with open(audio_file, 'rb') as f:
                        audio_bytes = f.read()
                        audio_base64 = base64.b64encode(audio_bytes).decode()
                except Exception as e:
                    logger.warning(f"Error leyendo archivo para base64: {e}")
            
            # Limpiar archivo temporal con reintentos
            if audio_file and os.path.exists(audio_file):
                for attempt in range(3):
                    try:
                        time.sleep(0.1)  # Pequeña espera
                        os.unlink(audio_file)
                        break
                    except PermissionError:
                        if attempt == 2:  # Último intento
                            logger.warning(f"No se pudo eliminar archivo: {audio_file}")
                        else:
                            time.sleep(0.5)  # Esperar más tiempo
                    except Exception as e:
                        logger.warning(f"Error eliminando archivo: {e}")
                        break
            
            return {
                "success": True,
                "action": "text_to_speech",
                "text": text,
                "engine": engine,
                "language": language,
                "audio_base64": audio_base64,
                "message": f"🔊 TTS: '{text[:50]}...'" if len(text) > 50 else f"🔊 TTS: '{text}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Error en TTS: {str(e)}"
            }
    
    def _get_voices(self):
        """Obtener voces disponibles"""
        try:
            voices_info = []
            
            # Voces de Groq Whisper (modelos disponibles)
            groq_models = [
                "whisper-large-v3-turbo",
                "whisper-large-v3", 
                "distil-whisper-large-v3-en"
            ]
            
            for model in groq_models:
                voices_info.append({
                    "id": model,
                    "name": f"Groq {model}",
                    "type": "STT",
                    "provider": "Groq"
                })
            
            # Voces locales TTS
            if self.pyttsx3_engine:
                try:
                    voices = self.pyttsx3_engine.getProperty('voices')
                    for voice in voices:
                        voices_info.append({
                            "id": voice.id,
                            "name": voice.name,
                            "type": "TTS",
                            "provider": "pyttsx3",
                            "language": getattr(voice, 'languages', ['unknown'])
                        })
                except Exception as e:
                    logger.warning(f"Error obteniendo voces pyttsx3: {e}")
            
            return {
                "success": True,
                "action": "get_voices",
                "voices": voices_info,
                "total_voices": len(voices_info),
                "message": f"🎭 Encontradas {len(voices_info)} voces/modelos disponibles"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Error obteniendo voces: {str(e)}"
            }


# Función de prueba mejorada
def test_groq_speech_adapter():
    """Probar el adaptador Groq Speech"""
    print("🧪 PROBANDO GROQ SPEECH ADAPTER...")
    adapter = GroqSpeechAdapter()
    
    # Test obtener modelos/voces
    print(f"\n📋 TEST MODELOS GROQ:")
    voices_result = adapter.process({"action": "get_voices"})
    print(voices_result.get("message", "Sin modelos"))
    
    # Test TTS con return_audio=True para evitar problemas de reproducción
    test_tts = {
        "action": "text_to_speech",
        "text": "Hola, probando Groq Whisper Large v3 Turbo",
        "engine": "gtts",
        "return_audio": True  # Cambiado a True para evitar problemas de archivos
    }
    
    print(f"\n📋 TEST TTS:")
    result = adapter.process(test_tts)
    print(result.get("message", "Sin mensaje"))
    if result.get("success") and result.get("audio_base64"):
        print(f"✅ Audio generado exitosamente (base64 length: {len(result['audio_base64'])})")
    
    # TEST TRANSCRIPCIÓN CON TU ARCHIVO
    test_file_path = r"C:\Users\h\Downloads\ElevenLabs_2024-10-17T06_55_05_Tuqui_ivc_s44_sb87_se40_b_m2.mp3"
    
    print(f"\n📋 TEST TRANSCRIPCIÓN DE ARCHIVO:")
    print(f"📁 Archivo: {test_file_path}")
    
    if os.path.exists(test_file_path):
        test_transcribe = {
            "action": "transcribe_file",
            "file_path": test_file_path,
            "model": "whisper-large-v3-turbo",
            "language": "es"
        }
        
        transcribe_result = adapter.process(test_transcribe)
        print(transcribe_result.get("message", "Sin resultado"))
        
        if transcribe_result.get("success"):
            print(f"\n✅ TRANSCRIPCIÓN EXITOSA:")
            print(f"📝 Texto: {transcribe_result.get('text', 'Sin texto')}")
            print(f"🤖 Modelo: {transcribe_result.get('model', 'Sin modelo')}")
            print(f"🌐 Idioma: {transcribe_result.get('language', 'Sin idioma')}")
        else:
            print(f"❌ Error en transcripción: {transcribe_result.get('error', 'Error desconocido')}")
    else:
        print(f"❌ Archivo no encontrado: {test_file_path}")
    
    print(f"\n🔚 Test completado")


if __name__ == "__main__":
    test_groq_speech_adapter()