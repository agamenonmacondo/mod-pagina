import sys
import os
import json
import uuid
import logging
import traceback
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import base64
from PIL import Image
import io

# CONFIGURACIÓN DE LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('webhook_chat.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# CONFIGURACIÓN FLASK
app = Flask(__name__)
CORS(app)

# CONFIGURACIÓN DE DIRECTORIOS
BASE_DIR = Path(r"c:\Users\h\Downloads\pagina ava")
AVA_BOT_DIR = BASE_DIR / "ava_bot"
AVA_SHARED_DIR = AVA_BOT_DIR / "shared_files"
GENERATED_IMAGES_DIR = AVA_BOT_DIR / "generated_images"
CHAT_UPLOADS_DIR = BASE_DIR / "chat_uploads"
CHAT_LOGS_DIR = BASE_DIR / "chat_logs"
USER_IMAGES_DIR = BASE_DIR / "user_images"

# CONFIGURACIÓN
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'pdf', 'txt', 'docx', 'mp3', 'wav', 'mp4', 'avi'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# MEMORIA PERSISTENTE PARA INSTANCIAS AVAGRAPHBOT
ava_instances = {}

def create_directories():
    """Crear carpetas necesarias"""
    directories = [AVA_SHARED_DIR, GENERATED_IMAGES_DIR, CHAT_UPLOADS_DIR, CHAT_LOGS_DIR, USER_IMAGES_DIR]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directorio verificado: {directory}")
        except Exception as e:
            logger.error(f"Error creando directorio {directory}: {e}")

def import_ava_graph_bot():
    """Importar AvaGraphBot siguiendo el patrón del webhook_server"""
    try:
        logger.info("Importando AvaGraphBot...")
        
        # Verificar archivo existe
        ava_file = AVA_BOT_DIR / "ava_graph_bot.py"
        if not ava_file.exists():
            logger.error(f"Archivo no encontrado: {ava_file}")
            return None, None
        
        # Añadir directorio al PATH
        ava_bot_path = str(AVA_BOT_DIR)
        if ava_bot_path not in sys.path:
            sys.path.insert(0, ava_bot_path)
            logger.info(f"Añadido al PATH: {ava_bot_path}")
        
        # Cambiar directorio de trabajo
        original_cwd = os.getcwd()
        os.chdir(str(AVA_BOT_DIR))
        logger.info(f"Directorio cambiado a: {AVA_BOT_DIR}")
        
        try:
            # Limpiar módulos previos para evitar conflictos
            modules_to_remove = [name for name in sys.modules.keys() if 'ava_graph_bot' in name]
            for module_name in modules_to_remove:
                del sys.modules[module_name]
                logger.info(f"Módulo limpiado: {module_name}")
            
            # MÉTODO 1: Importación directa
            try:
                logger.info("Intentando importación directa...")
                import ava_graph_bot
                ava_module = ava_graph_bot
                logger.info("✅ Importación directa exitosa")
                
            except ImportError as e:
                logger.warning(f"Importación directa falló: {e}")
                
                # MÉTODO 2: Importación con importlib
                logger.info("Intentando importación con importlib...")
                spec = importlib.util.spec_from_file_location("ava_graph_bot", ava_file)
                if not spec or not spec.loader:
                    logger.error("No se pudo crear especificación del módulo")
                    return None, None
                
                ava_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ava_module)
                sys.modules['ava_graph_bot'] = ava_module
                logger.info("✅ Importación con importlib exitosa")
            
            # Verificar clase AvaGraphBot
            if hasattr(ava_module, 'AvaGraphBot'):
                AvaGraphBot = getattr(ava_module, 'AvaGraphBot')
                logger.info("✅ Clase AvaGraphBot encontrada")
                
                # Verificar que es una clase
                if isinstance(AvaGraphBot, type):
                    logger.info("✅ AvaGraphBot es una clase válida")
                    return ava_module, AvaGraphBot
                else:
                    logger.error("❌ AvaGraphBot no es una clase")
                    return ava_module, None
            else:
                available_attrs = [attr for attr in dir(ava_module) if not attr.startswith('_')]
                logger.error(f"❌ Clase AvaGraphBot no encontrada. Atributos disponibles: {available_attrs}")
                return ava_module, None
                
        finally:
            # Restaurar directorio original
            os.chdir(original_cwd)
            logger.info(f"Directorio restaurado a: {original_cwd}")
        
    except Exception as e:
        logger.error(f"Error crítico importando AvaGraphBot: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None, None

def create_ava_instance(session_id: str = None):
    """Crear instancia de AvaGraphBot con manejo de errores"""
    global AVA_CLASS
    
    if not AVA_CLASS:
        logger.error("Clase AvaGraphBot no disponible")
        return None
    
    try:
        logger.info(f"Creando instancia AvaGraphBot para sesión: {session_id}")
        
        # Cambiar al directorio AVA para la creación
        original_cwd = os.getcwd()
        os.chdir(str(AVA_BOT_DIR))
        
        try:
            # Crear instancia con debug_mode=False para webhook
            ava_instance = AVA_CLASS(debug_mode=False)
            logger.info("✅ Instancia AvaGraphBot creada exitosamente")
            
            # Verificar que tiene método chat
            if hasattr(ava_instance, 'chat') and callable(getattr(ava_instance, 'chat')):
                logger.info("✅ Método chat disponible")
                return ava_instance
            else:
                logger.error("❌ Método chat no encontrado o no es callable")
                return None
                
        finally:
            os.chdir(original_cwd)
        
    except Exception as e:
        logger.error(f"Error creando instancia AvaGraphBot: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def get_or_create_ava_instance(session_id: str):
    """Obtener o crear instancia persistente de AvaGraphBot"""
    
    # Reutilizar instancia existente (MEMORIA PERSISTENTE)
    if session_id in ava_instances:
        logger.info(f"♻️ Reutilizando instancia AvaGraphBot para sesión: {session_id}")
        
        # Verificar que la instancia sigue siendo válida
        instance = ava_instances[session_id]
        try:
            # Test rápido de la instancia
            status = instance.get_status()
            if status.get('bot_ready', False):
                return instance
            else:
                logger.warning("Instancia existente no está lista, creando nueva...")
                del ava_instances[session_id]
        except Exception as e:
            logger.warning(f"Instancia existente tiene problemas: {e}, creando nueva...")
            del ava_instances[session_id]
    
    # Crear nueva instancia
    logger.info(f"🆕 Creando nueva instancia AvaGraphBot para sesión: {session_id}")
    ava_instance = create_ava_instance(session_id)
    
    if ava_instance:
        ava_instances[session_id] = ava_instance
        logger.info(f"✅ Instancia AvaGraphBot almacenada para sesión: {session_id}")
        logger.info(f"📊 Total sesiones activas: {len(ava_instances)}")
        return ava_instance
    else:
        logger.error(f"❌ No se pudo crear instancia AvaGraphBot para sesión: {session_id}")
        return None

def process_ava_response(result: Dict[str, Any], user_message: str = "") -> Dict[str, Any]:
    """Procesar respuesta específica de AvaGraphBot"""
    try:
        logger.info(f"🔄 Procesando respuesta AvaGraphBot: {result}")
        
        # AvaGraphBot retorna estructura específica
        if isinstance(result, dict):
            
            # Si hay error
            if result.get('error', False):
                error_msg = result.get('error_message', 'Error desconocido en AvaGraphBot')
                logger.error(f"❌ Error en AvaGraphBot: {error_msg}")
                return {
                    'success': False,
                    'response': f'Error procesando mensaje: {error_msg}',
                    'metadata': {
                        'error': True,
                        'error_message': error_msg,
                        'processing_timestamp': datetime.now().isoformat()
                    }
                }
            
            # Respuesta exitosa
            message = result.get('message', '')
            if message and message.strip():
                logger.info(f"✅ Mensaje AvaGraphBot procesado: {len(message)} caracteres")
                return {
                    'success': True,
                    'response': message.strip(),
                    'metadata': {
                        'session_id': result.get('session_id', ''),
                        'user_id': result.get('user_id', ''),
                        'processing_timestamp': datetime.now().isoformat(),
                        'source': 'AvaGraphBot'
                    }
                }
            else:
                logger.warning("⚠️ Respuesta AvaGraphBot vacía")
                return {
                    'success': False,
                    'response': 'AvaGraphBot no generó respuesta válida',
                    'metadata': {
                        'empty_response': True,
                        'raw_result': result,
                        'processing_timestamp': datetime.now().isoformat()
                    }
                }
        else:
            # Resultado no es diccionario (inesperado)
            logger.warning(f"⚠️ Resultado inesperado de AvaGraphBot: {type(result)}")
            return {
                'success': False,
                'response': f'Formato de respuesta inesperado: {str(result)}',
                'metadata': {
                    'unexpected_format': True,
                    'result_type': str(type(result)),
                    'processing_timestamp': datetime.now().isoformat()
                }
            }
        
    except Exception as e:
        logger.error(f"❌ Error procesando respuesta AvaGraphBot: {e}")
        return {
            'success': False,
            'response': f'Error interno procesando respuesta: {str(e)}',
            'metadata': {
                'processing_error': str(e),
                'processing_timestamp': datetime.now().isoformat()
            }
        }

# 🔧 MODIFICAR el endpoint handle_chat para incluir imágenes de usuario
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def handle_chat():
    """Endpoint principal de chat con AvaGraphBot"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        logger.info("=" * 70)
        logger.info("🚀 NUEVA SOLICITUD DE CHAT (AVAGRAPHBOT)")
        request_start_time = datetime.now()
        
        # Verificar disponibilidad de AvaGraphBot
        if not AVA_CLASS:
            logger.error("❌ Clase AvaGraphBot no disponible")
            return jsonify({
                'success': False,
                'response': 'El servicio de inteligencia artificial no está disponible. AvaGraphBot no se pudo cargar.',
                'error_code': 'AVAGRAPHBOT_CLASS_UNAVAILABLE'
            }), 503
        
        # Verificar JSON
        if not request.is_json:
            logger.error(f"❌ Content-Type inválido: {request.content_type}")
            return jsonify({
                'success': False,
                'response': 'Content-Type debe ser application/json'
            }), 400
        
        # Obtener datos
        try:
            data = request.get_json()
            logger.info(f"📊 Datos recibidos: {json.dumps({k: v if k != 'fileData' else '[BASE64_DATA]' for k, v in data.items()}, indent=2)}")
        except Exception as json_error:
            logger.error(f"❌ Error parseando JSON: {json_error}")
            return jsonify({
                'success': False,
                'response': 'JSON inválido en la solicitud'
            }), 400
        
        if not data:
            return jsonify({
                'success': False,
                'response': 'Datos JSON requeridos'
            }), 400
        
        # Extraer parámetros
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', data.get('sessionId', data.get('conversationId', f'session_{uuid.uuid4().hex}')))
        
        # 🆕 PROCESAR ARCHIVO ADJUNTO
        user_image_url = None
        image_path_for_ava = None
        
        # Procesar imagen desde base64 (método original)
        if data.get('fileData') and data.get('fileName'):
            try:
                logger.info(f"🖼️ Procesando imagen adjunta desde base64: {data.get('fileName')}")
                user_image_url = process_user_image(data.get('fileData'), data.get('fileName'))
                if user_image_url:
                    logger.info(f"✅ Imagen de usuario guardada: {user_image_url}")
                    # Añadir contexto de imagen al mensaje
                    user_message += f"\n[Imagen adjunta: {data.get('fileName')}]"
            except Exception as img_error:
                logger.error(f"❌ Error procesando imagen desde base64: {img_error}")
        
        # Procesar imagen desde ruta de archivo (método desde route.ts)
        elif data.get('imagePath') and data.get('fileName'):
            try:
                original_filename = data.get('fileName')
                unique_file_path = data.get('imagePath')
                
                logger.info(f"🖼️ Procesando imagen desde ruta única: {unique_file_path}")
                
                # Verificar que el archivo único existe
                if os.path.exists(unique_file_path):
                    logger.info(f"✅ Archivo único encontrado: {unique_file_path}")
                    
                    # Crear copia con nombre original para que el agente la encuentre
                    original_file_path = os.path.join(AVA_SHARED_DIR, original_filename)
                    
                    # Solo copiar si no existe o es diferente
                    if not os.path.exists(original_file_path) or os.path.getmtime(unique_file_path) > os.path.getmtime(original_file_path):
                        import shutil
                        shutil.copy2(unique_file_path, original_file_path)
                        logger.info(f"📋 Archivo copiado para agente: {original_file_path}")
                    
                    image_path_for_ava = original_file_path
                    # Añadir contexto de imagen al mensaje
                    user_message += f"\n[Imagen adjunta: {original_filename}]"
                else:
                    logger.error(f"❌ Archivo único no encontrado: {unique_file_path}")
                    image_path_for_ava = None
            except Exception as img_error:
                logger.error(f"❌ Error procesando imagen desde ruta: {img_error}")
                image_path_for_ava = None
        
        logger.info(f"💬 Mensaje: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
        logger.info(f"🔑 Session ID: {session_id}")
        
        if not user_message:
            return jsonify({
                'success': False,
                'response': 'El mensaje no puede estar vacío'
            }), 400
        
        # Marcar tiempo antes de procesar con AVA
        process_start_time = datetime.now().timestamp()
        
        # Obtener instancia persistente de AvaGraphBot
        logger.info("🧠 Obteniendo instancia persistente de AvaGraphBot...")
        ava_instance = get_or_create_ava_instance(session_id)
        
        if not ava_instance:
            logger.error("❌ No se pudo obtener instancia AvaGraphBot")
            return jsonify({
                'success': False,
                'response': 'No se pudo crear la instancia de inteligencia artificial. El sistema puede estar sobrecargado.',
                'error_code': 'AVAGRAPHBOT_INSTANCE_FAILED'
            }), 503
        
        # Procesar mensaje con AvaGraphBot
        logger.info("🤖 Procesando mensaje con AvaGraphBot...")
        
        # Preparar mensaje para AvaGraphBot incluyendo ruta de imagen si existe
        message_for_ava = user_message
        if image_path_for_ava:
            # Usar el nombre original del archivo que el LLM espera
            original_filename = data.get('fileName', 'imagen.png')
            
            message_for_ava = message_for_ava.replace(f"[Imagen adjunta: {original_filename}]", 
                                                    f"[Imagen adjunta: {original_filename}]")
            
            # Agregar instrucciones simples usando solo el nombre original
            message_for_ava += f"\n\n🔍 ANÁLISIS DE IMAGEN REQUERIDO:"
            message_for_ava += f"\n- Archivo disponible: {original_filename}"
            message_for_ava += f"\n- Usar herramienta: vision"
            message_for_ava += f"\n- Parámetro: image_path = '{original_filename}'"
            message_for_ava += f"\n- ⚠️ IMPORTANTE: Usar exactamente este nombre de archivo"
            
            logger.info(f"📎 Enviando instrucciones con nombre original: {original_filename}")
            logger.info(f"📁 Archivo copiado en: {image_path_for_ava}")
        
        try:
            result = ava_instance.chat(message_for_ava)
            processing_time = datetime.now().timestamp() - process_start_time
            
            logger.info(f"✅ AvaGraphBot procesó en {processing_time:.2f} segundos")
            logger.info(f"📤 Resultado crudo: {result}")
            
        except Exception as ava_error:
            logger.error(f"❌ Error en AvaGraphBot: {ava_error}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return jsonify({
                'success': False,
                'response': 'Error procesando tu mensaje con AvaGraphBot. Por favor, intenta con una pregunta diferente.',
                'error_code': 'AVAGRAPHBOT_PROCESSING_ERROR',
                'error_details': str(ava_error)
            }), 500
        
        # Procesar respuesta
        logger.info("🔄 Procesando respuesta de AvaGraphBot...")
        processed_response = process_ava_response(result, user_message)
        
        # Detectar imagen generada por AvaGraphBot
        generated_image_url = detect_new_generated_image(process_start_time)
        
        # Construir respuesta final
        total_time = datetime.now().timestamp() - request_start_time.timestamp()
        
        final_response = {
            'success': processed_response['success'],
            'response': processed_response['response'],
            'responseText': processed_response['response'],
            'session_id': session_id,
            'conversationId': session_id,
            'timestamp': datetime.now().isoformat(),
            'agentName': 'AvaGraphBot',
            'metadata': {
                **processed_response.get('metadata', {}),
                'processing_time_seconds': round(processing_time, 3),
                'total_time_seconds': round(total_time, 3),
                'memory_preserved': True,
                'session_active': session_id in ava_instances,
                'bot_type': 'AvaGraphBot',
                'raw_ava_result': result
            }
        }
        
        # 🆕 AGREGAR IMAGEN DE USUARIO A LA RESPUESTA
        if user_image_url:
            final_response['userImageUrl'] = user_image_url
            final_response['userImageAlt'] = f"Imagen subida: {data.get('fileName', 'imagen.png')}"
            final_response['metadata']['user_image_processed'] = True
            logger.info(f"🖼️ Imagen de usuario incluida en respuesta: {user_image_url}")
        
        # Agregar URL de imagen generada por AvaGraphBot si existe
        if generated_image_url:
            final_response['imageUrl'] = generated_image_url
            final_response['imageAlt'] = "Imagen generada por AvaGraphBot"
            final_response['metadata']['generated_image'] = True
            logger.info(f"🎨 Imagen generada incluida: {generated_image_url}")
        
        logger.info(f"✅ Respuesta exitosa: {len(final_response['response'])} caracteres")
        logger.info(f"🧠 Memoria preservada para sesión: {session_id}")
        logger.info(f"⏱️ Tiempo total: {total_time:.3f} segundos")
        logger.info("=" * 70)
        
        return jsonify(final_response)
        
    except Exception as critical_error:
        logger.error(f"❌ ERROR CRÍTICO: {critical_error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'response': 'Error interno del servidor.',
            'error_code': 'CRITICAL_ERROR',
            'timestamp': datetime.now().isoformat()
        }), 500

# 🆕 FUNCIÓN PARA PROCESAR IMÁGENES DE USUARIO
def process_user_image(file_data: str, filename: str) -> Optional[str]:
    """Procesar imagen enviada por el usuario"""
    try:
        # Decodificar base64
        if file_data.startswith('data:'):
            file_data = file_data.split(',')[1]
        
        image_bytes = base64.b64decode(file_data)
        
        # Generar nombre único
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_filename = secure_filename(filename)
        unique_filename = f"user_{timestamp}_{uuid.uuid4().hex[:8]}_{safe_filename}"
        
        # Guardar en directorio de imágenes de usuario
        image_path = USER_IMAGES_DIR / unique_filename
        
        # Verificar que es una imagen válida
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()  # Verificar integridad
            
            # Reabrir para guardar (después de verify() no se puede usar)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convertir a RGB si es necesario
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Guardar imagen
            image.save(image_path, format='PNG', optimize=True)
            
            # Retornar URL accesible
            image_url = f"http://localhost:5001/user-images/{unique_filename}"
            logger.info(f"✅ Imagen de usuario guardada: {image_path}")
            return image_url
            
        except Exception as img_error:
            logger.error(f"❌ Error validando imagen: {img_error}")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error procesando imagen de usuario: {e}")
        return None

# 🔧 MODIFICAR LA FUNCIÓN detect_new_generated_image para ser más específica
def detect_new_generated_image(timestamp_before: float) -> Optional[str]:
    """Detectar imagen generada por AvaGraphBot después del timestamp"""
    try:
        if not GENERATED_IMAGES_DIR.exists():
            logger.info("📁 Directorio de imágenes generadas no existe")
            return None
        
        current_time = datetime.now().timestamp()
        latest_image = None
        latest_time = timestamp_before
        
        # Buscar la imagen más reciente después del timestamp
        for image_file in GENERATED_IMAGES_DIR.glob("*.png"):
            if image_file.is_file():
                file_time = image_file.stat().st_mtime
                
                # Solo imágenes generadas después del timestamp y en ventana de 120 segundos
                if file_time > timestamp_before and (current_time - file_time) < 120:
                    if file_time > latest_time:
                        latest_time = file_time
                        latest_image = image_file
        
        if latest_image:
            image_url = f"http://localhost:5001/images/{latest_image.name}"
            logger.info(f"🖼️ Nueva imagen AvaGraphBot detectada: {image_url}")
            return image_url
        else:
            logger.info("🔍 No se detectaron nuevas imágenes generadas por AvaGraphBot")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error detectando imagen generada: {e}")
        return None

# IMPORTAR AVAGRAPHBOT AL INICIAR
logger.info("=" * 60)
logger.info("🚀 IMPORTANDO AVAGRAPHBOT...")
logger.info("=" * 60)

AVA_MODULE, AVA_CLASS = import_ava_graph_bot()

if AVA_MODULE and AVA_CLASS:
    logger.info(f"✅ AvaGraphBot listo: {AVA_CLASS.__name__}")
else:
    logger.error("❌ AvaGraphBot no disponible")

# ENDPOINTS

@app.route('/')
def index():
    """Endpoint principal de información"""
    return jsonify({
        "service": "AgenteAVA Chat Webhook (AvaGraphBot)",
        "version": "2.4",
        "status": "running",
        "port": 5001,
        "ava_status": {
            "module_loaded": AVA_MODULE is not None,
            "class_available": AVA_CLASS is not None,
            "class_name": AVA_CLASS.__name__ if AVA_CLASS else None,
            "file_exists": (AVA_BOT_DIR / "ava_graph_bot.py").exists()
        },
        "bot_type": "AvaGraphBot",
        "active_sessions": len(ava_instances),
        "memory_preserved": True,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """Estado de salud del servicio"""
    try:
        directories_ok = all([
            AVA_SHARED_DIR.exists(),
            GENERATED_IMAGES_DIR.exists(),
            CHAT_UPLOADS_DIR.exists()
        ])
        
        # Test de creación de instancia
        test_instance_ok = False
        if AVA_CLASS:
            try:
                test_instance = create_ava_instance("health_test")
                if test_instance:
                    test_instance_ok = True
                    # Cleanup test instance
                    try:
                        test_instance.shutdown()
                    except:
                        pass
            except Exception as e:
                logger.warning(f"Test instance creation failed: {e}")
        
        return jsonify({
            "service": "AgenteAVA Chat Webhook (AvaGraphBot)",
            "status": "healthy",
            "port": 5001,
            "ava_available": AVA_CLASS is not None,
            "ava_class_name": AVA_CLASS.__name__ if AVA_CLASS else None,
            "test_instance_creation": test_instance_ok,
            "directories_ok": directories_ok,
            "active_sessions": len(ava_instances),
            "memory_preserved": True,
            "system_info": {
                "base_dir": str(BASE_DIR),
                "ava_bot_dir": str(AVA_BOT_DIR),
                "python_path_includes_ava": str(AVA_BOT_DIR) in sys.path
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "service": "AgenteAVA Chat Webhook",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/chat/test')
def test_ava():
    """Probar AvaGraphBot"""
    try:
        if not AVA_CLASS:
            return jsonify({
                "success": False,
                "message": "Clase AvaGraphBot no disponible",
                "ava_module_loaded": AVA_MODULE is not None,
                "timestamp": datetime.now().isoformat()
            }), 503
        
        # Crear instancia temporal de prueba
        test_session = f'test_{uuid.uuid4().hex[:8]}'
        logger.info(f"🧪 Creando instancia de prueba: {test_session}")
        
        ava_instance = get_or_create_ava_instance(test_session)
        
        if not ava_instance:
            return jsonify({
                "success": False,
                "message": "No se pudo crear instancia de prueba",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # Ejecutar chat de prueba
        try:
            test_message = "Hola, confirma que estás funcionando correctamente"
            logger.info(f"📨 Enviando mensaje de prueba: {test_message}")
            
            result = ava_instance.chat(test_message)
            logger.info(f"📨 Resultado de prueba: {result}")
            
            processed = process_ava_response(result, test_message)
            
            # Obtener status de la instancia
            try:
                status = ava_instance.get_status()
            except:
                status = {"status_error": "No se pudo obtener status"}
            
            # Limpiar instancia temporal
            try:
                ava_instance.shutdown()
            except:
                pass
            
            if test_session in ava_instances:
                del ava_instances[test_session]
            
            return jsonify({
                "success": processed.get('success', False),
                "message": "Prueba de AvaGraphBot completada",
                "test_response_preview": processed.get('response', '')[:200] + "..." if len(processed.get('response', '')) > 200 else processed.get('response', ''),
                "test_successful": processed.get('success', False),
                "instance_status": status,
                "raw_result": result,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as chat_error:
            logger.error(f"❌ Error en chat de prueba: {chat_error}")
            return jsonify({
                "success": False,
                "message": f"Error ejecutando chat de prueba: {str(chat_error)}",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error en test: {e}")
        return jsonify({
            "success": False,
            "message": f"Error en test: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500



# SERVIR ARCHIVOS
@app.route('/images/<filename>')
def serve_generated_image(filename):
    """Servir imágenes generadas por AvaGraphBot"""
    try:
        return send_from_directory(GENERATED_IMAGES_DIR, filename)
    except FileNotFoundError:
        return jsonify({"error": "Imagen no encontrada"}), 404

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    """Servir archivos subidos"""
    try:
        return send_from_directory(CHAT_UPLOADS_DIR, filename)
    except FileNotFoundError:
        return jsonify({"error": "Archivo no encontrado"}), 404

@app.route('/user-images/<filename>')
def serve_user_image(filename):
    """Servir imágenes de usuario"""
    try:
        return send_from_directory(USER_IMAGES_DIR, filename)
    except FileNotFoundError:
        return jsonify({"error": "Imagen no encontrada"}), 404

@app.route('/user-uploads/<filename>')
def serve_user_upload(filename):
    """Servir imágenes públicas de user-uploads"""
    try:
        public_uploads_dir = AVA_SHARED_DIR  # Debe ser ava_bot/shared_files
        return send_from_directory(public_uploads_dir, filename)
    except FileNotFoundError:
        return jsonify({"error": "Imagen no encontrada"}), 404

# ENDPOINT DE STATUS DE INSTANCIAS
@app.route('/api/chat/sessions')
def get_active_sessions():
    """Obtener información de sesiones activas"""
    try:
        sessions_info = {}
        
        for session_id, instance in ava_instances.items():
            try:
                status = instance.get_status()
                sessions_info[session_id] = {
                    "session_id": session_id[:16] + "...",  # Ocultar ID completo
                    "status": status,
                    "active": True
                }
            except Exception as e:
                sessions_info[session_id] = {
                    "session_id": session_id[:16] + "...",
                    "error": str(e),
                    "active": False
                }
        
        return jsonify({
            "total_sessions": len(ava_instances),
            "sessions": sessions_info,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# MANEJO DE ERRORES
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"❌ 404 - Endpoint no encontrado: {request.url}")
    return jsonify({
        "error": "Endpoint no encontrado",
        "requested_url": request.url,
        "method": request.method
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ Error 500: {error}")
    return jsonify({
        "error": "Error interno del servidor",
        "timestamp": datetime.now().isoformat()
    }), 500

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 INICIANDO WEBHOOK CHAT AGENTEAVA (AVAGRAPHBOT)")
    print("=" * 80)
    
    # Crear directorios
    create_directories()
    
    # Información del sistema
    print(f"\n📊 ESTADO DEL SISTEMA:")
    print(f"  📁 Directorio base: {BASE_DIR}")
    print(f"  📁 Directorio AVA: {AVA_BOT_DIR}")
    print(f"  🤖 Módulo AVA: {'✅' if AVA_MODULE else '❌'}")
    print(f"  🎯 Clase AVA: {'✅' if AVA_CLASS else '❌'}")
    if AVA_CLASS:
        print(f"  📋 Clase: {AVA_CLASS.__name__}")
    print(f"  🧠 Memoria persistente: ✅ ACTIVADA")
    print(f"  📡 Puerto: 5001")
    print(f"  🤖 Bot: AvaGraphBot")
    
    # Test de creación de instancia
    if AVA_CLASS:
        print(f"\n🧪 PROBANDO CREACIÓN DE INSTANCIA...")
        try:
            test_instance = create_ava_instance("startup_test")
            if test_instance:
                print("✅ INSTANCIA AVAGRAPHBOT CREADA EXITOSAMENTE")
                try:
                    status = test_instance.get_status()
                    print(f"📊 Status: {status}")
                    test_instance.shutdown()
                except Exception as e:
                    print(f"⚠️ Warning obteniendo status: {e}")
            else:
                print("❌ NO SE PUDO CREAR INSTANCIA AVAGRAPHBOT")
        except Exception as e:
            print(f"❌ ERROR EN TEST: {e}")
    
    print(f"\n📡 ENDPOINTS DISPONIBLES:")
    print("  GET  /                     - Información del servicio")
    print("  GET  /health               - Estado de salud")
    print("  POST /api/chat             - Chat con AvaGraphBot")
    print("  GET  /api/chat/test        - Prueba de AvaGraphBot")
    print("  GET  /api/chat/sessions    - Sesiones activas")
    print("  GET  /images/<filename>    - Imágenes generadas")
    
    print(f"\n🧪 PRUEBAS RÁPIDAS:")
    print("  curl http://localhost:5001/health")
    print("  curl http://localhost:5001/api/chat/test")
    
    print(f"\n⚡ CARACTERÍSTICAS AVAGRAPHBOT:")
    print("  ✅ Instancias persistentes por sesión")
    print("  ✅ Servidor gRPC interno con herramientas")
    print("  ✅ Cliente MCP para tools avanzados")
    print("  ✅ Grafo de estado conversacional")
    print("  ✅ Detección de imágenes generadas")
    
    print("\n" + "=" * 80)
    
    if not AVA_MODULE or not AVA_CLASS:
        print("⚠️  ATENCIÓN: AvaGraphBot no completamente disponible")
        print("   Verifica dependencias: grpc, langchain, mcp_server, etc.")
    else:
        print("🎉 AVAGRAPHBOT COMPLETAMENTE OPERATIVO")
        print("   Memoria persistente activada")
        print("   Listo para conversaciones inteligentes avanzadas")
    
    print(f"\n🎯 Presiona Ctrl+C para detener el servidor")
    print("=" * 80)
    
    try:
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print(f"\n👋 Servidor detenido por el usuario")
        print(f"📊 Sesiones activas al cierre: {len(ava_instances)}")
        
        # Cleanup instancias
        for session_id, instance in ava_instances.items():
            try:
                instance.shutdown()
                print(f"🧹 Sesión {session_id[:8]}... cerrada")
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error crítico iniciando servidor: {e}")
        print(f"\n❌ ERROR CRÍTICO: {e}")
        raise