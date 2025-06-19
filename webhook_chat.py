import sys
import os
import json
import uuid
import logging
import traceback
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS, cross_origin
from werkzeug.utils import secure_filename
import base64
from PIL import Image
import io

# ✅ CONFIGURACIÓN DE LOGGING AVANZADO
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('webhook_chat.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://192.168.0.5:3000"])

# ✅ CONFIGURACIÓN DE DIRECTORIOS MEJORADA
BASE_DIR = Path(r"c:\Users\h\Downloads\pagina ava")
AVA_SHARED_DIR = BASE_DIR / "ava_bot" / "shared_files"
GENERATED_IMAGES_DIR = BASE_DIR / "ava_bot" / "generated_images"
CHAT_UPLOADS_DIR = BASE_DIR / "chat_uploads"
CHAT_LOGS_DIR = BASE_DIR / "chat_logs"
USER_IMAGES_DIR = BASE_DIR / "user_images"  # Nueva carpeta para imágenes de usuario
PROCESSED_IMAGES_DIR = BASE_DIR / "processed_images"  # Nueva carpeta para imágenes procesadas

# Configuración de archivos permitidos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'pdf', 'txt', 'docx', 'mp3', 'wav', 'mp4', 'avi'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def create_directories():
    """Crear todas las carpetas necesarias"""
    directories = [
        AVA_SHARED_DIR, GENERATED_IMAGES_DIR, CHAT_UPLOADS_DIR, 
        CHAT_LOGS_DIR, USER_IMAGES_DIR, PROCESSED_IMAGES_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Directorio verificado: {directory}")

create_directories()

logger.info("💬 Webhook CHAT Avanzado con AgenteAVA iniciado")
logger.info(f"🤖 Directorio AVA: {BASE_DIR / 'ava_bot'}")
logger.info(f"📁 Directorio uploads: {CHAT_UPLOADS_DIR}")
logger.info(f"🖼️ Directorio imágenes generadas: {GENERATED_IMAGES_DIR}")
logger.info(f"👤 Directorio imágenes usuario: {USER_IMAGES_DIR}")

def create_fresh_ava_instance():
    """Crear una nueva instancia de AVA con manejo de errores mejorado"""
    try:
        logger.info("🤖 Iniciando creación de nueva instancia AVA...")
        
        # Limpiar módulos previos para evitar conflictos
        modules_to_remove = [name for name in sys.modules.keys() if 'ava_graph_bot' in name]
        for module_name in modules_to_remove:
            del sys.modules[module_name]
            logger.debug(f"🧹 Módulo limpiado: {module_name}")
        
        logger.info(f"🧹 Limpiados {len(modules_to_remove)} módulos previos")
        
        # Agregar el directorio AVA_BOT al PATH de Python
        ava_bot_dir = str(BASE_DIR / "ava_bot")
        if ava_bot_dir not in sys.path:
            sys.path.insert(0, ava_bot_dir)
            logger.info(f"📁 Agregado al PATH: {ava_bot_dir}")
        
        # Guardar directorio original y cambiar
        original_cwd = os.getcwd()
        os.chdir(ava_bot_dir)
        logger.info(f"📂 Cambiado a directorio: {ava_bot_dir}")
        
        try:
            # Verificar que existe el archivo principal
            ava_path = BASE_DIR / "ava_bot" / "ava_graph_bot.py"
            if not ava_path.exists():
                raise FileNotFoundError(f"Archivo ava_graph_bot.py no encontrado en: {ava_path}")
            
            logger.info(f"📄 Cargando módulo desde: {ava_path}")
            
            # Importar dinámicamente el módulo AVA
            spec = importlib.util.spec_from_file_location("ava_graph_bot", ava_path)
            if spec is None:
                raise ImportError("No se pudo crear spec para ava_graph_bot")
            
            ava_module = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                raise ImportError("No se pudo obtener loader para ava_graph_bot")
            
            spec.loader.exec_module(ava_module)
            logger.info("✅ Módulo AVA cargado exitosamente")
            
            # Verificar que la clase existe
            if not hasattr(ava_module, 'AvaGraphBot'):
                raise AttributeError("Clase AvaGraphBot no encontrada en el módulo")
            
            # Crear instancia
            ava_instance = ava_module.AvaGraphBot()
            logger.info("🤖 Instancia AvaGraphBot creada")
            
            # Verificar que tiene el método chat
            if not hasattr(ava_instance, 'chat'):
                raise AttributeError("La instancia AVA no tiene método 'chat'")
            
            logger.info("✅ Instancia AVA completamente funcional")
            return ava_instance
            
        except Exception as e:
            logger.error(f"❌ Error durante importación/creación: {str(e)}")
            raise
        finally:
            # Restaurar directorio original
            os.chdir(original_cwd)
            logger.debug(f"📂 Restaurado directorio original: {original_cwd}")
            
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO CREANDO AVA: {str(e)}")
        logger.error(f"❌ Traceback completo:\n{traceback.format_exc()}")
        return None

def process_llm_response(result: Any, user_message: str = "") -> Dict[str, Any]:
    """Procesar respuesta del LLM de manera más robusta"""
    try:
        logger.info(f"🔄 Procesando respuesta LLM (tipo: {type(result).__name__})")
        
        response_data = {
            'success': True,
            'response': '',
            'metadata': {
                'processing_timestamp': datetime.now().isoformat(),
                'input_type': type(result).__name__,
                'user_message_length': len(user_message)
            },
            'debug_info': {
                'raw_type': str(type(result)),
                'has_content': bool(result)
            }
        }
        
        # Caso 1: Respuesta es un diccionario
        if isinstance(result, dict):
            logger.info("📊 Procesando respuesta tipo diccionario")
            
            # Buscar texto de respuesta en diferentes campos posibles
            response_fields = ['message', 'response', 'content', 'text', 'answer', 'output']
            response_text = None
            
            for field in response_fields:
                if field in result and result[field]:
                    response_text = str(result[field])
                    logger.info(f"📝 Texto encontrado en campo: {field}")
                    break
            
            if not response_text:
                # Si no hay campos específicos, convertir todo el dict
                response_text = json.dumps(result, ensure_ascii=False, indent=2)
                logger.warning("⚠️ No se encontró campo de texto específico, usando JSON completo")
            
            response_data['response'] = response_text
            response_data['metadata'].update({
                'source_field': next((field for field in response_fields if field in result), 'full_dict'),
                'dict_keys': list(result.keys()),
                'has_image': any(key in result for key in ['image', 'image_url', 'imageUrl']),
                'has_metadata': 'metadata' in result
            })
            
            # Extraer metadatos adicionales si existen
            for meta_field in ['confidence', 'model_used', 'tokens_used', 'processing_time']:
                if meta_field in result:
                    response_data['metadata'][meta_field] = result[meta_field]
                    
        # Caso 2: Respuesta es una lista
        elif isinstance(result, list):
            logger.info(f"📋 Procesando respuesta tipo lista ({len(result)} elementos)")
            
            if result:
                response_text = '\n'.join(str(item) for item in result if item)
                response_data['response'] = response_text
                response_data['metadata']['list_length'] = len(result)
                response_data['metadata']['non_empty_items'] = len([item for item in result if item])
            else:
                response_data['response'] = "El modelo devolvió una lista vacía"
                response_data['success'] = False
                
        # Caso 3: Respuesta es string
        elif isinstance(result, str):
            logger.info("📝 Procesando respuesta tipo string")
            
            if result.strip():
                response_data['response'] = result.strip()
                response_data['metadata']['text_length'] = len(result)
                response_data['metadata']['word_count'] = len(result.split())
            else:
                response_data['response'] = "El modelo devolvió una cadena vacía"
                response_data['success'] = False
                
        # Caso 4: Respuesta booleana o numérica
        elif isinstance(result, (bool, int, float)):
            logger.info(f"🔢 Procesando respuesta tipo {type(result).__name__}")
            response_data['response'] = str(result)
            response_data['metadata']['numeric_value'] = result
            
        # Caso 5: Respuesta None
        elif result is None:
            logger.warning("⚠️ Respuesta es None")
            response_data['response'] = "El modelo no generó respuesta"
            response_data['success'] = False
            
        # Caso 6: Otros tipos
        else:
            logger.warning(f"❓ Tipo de respuesta desconocido: {type(result)}")
            response_data['response'] = str(result)
            response_data['metadata']['converted_from'] = type(result).__name__
            response_data['debug_info']['raw_preview'] = str(result)[:200]
        
        # Validaciones finales
        if not response_data['response']:
            response_data['response'] = "El modelo no generó una respuesta válida"
            response_data['success'] = False
            logger.warning("⚠️ Respuesta final vacía")
        else:
            logger.info(f"✅ Respuesta procesada exitosamente: {len(response_data['response'])} caracteres")
        
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error procesando respuesta LLM: {str(e)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        return {
            'success': False,
            'response': f'Error interno procesando respuesta del modelo: {str(e)}',
            'metadata': {
                'error': str(e),
                'error_type': type(e).__name__,
                'processing_timestamp': datetime.now().isoformat()
            },
            'debug_info': {
                'raw_result_preview': str(result)[:500] if result else 'None',
                'raw_result_type': str(type(result))
            }
        }

def has_generated_new_image(timestamp_before: float) -> Optional[str]:
    """Detectar si se generó una nueva imagen después del timestamp dado - MEJORADO"""
    try:
        if not GENERATED_IMAGES_DIR.exists():
            logger.debug("📁 Directorio de imágenes generadas no existe")
            return None
        
        current_time = datetime.now().timestamp()
        
        # Buscar imágenes generadas después del timestamp
        for image_file in GENERATED_IMAGES_DIR.glob("*.png"):
            file_time = image_file.stat().st_mtime
            
            # Solo imágenes generadas después de la llamada y en los últimos 30 segundos
            if file_time > timestamp_before and (current_time - file_time) < 30:
                image_url = f"http://localhost:5001/images/{image_file.name}"
                logger.info(f"🖼️ Nueva imagen detectada: {image_url}")
                return image_url
        
        # También buscar en otros formatos
        for ext in ['jpg', 'jpeg', 'gif', 'webp']:
            for image_file in GENERATED_IMAGES_DIR.glob(f"*.{ext}"):
                file_time = image_file.stat().st_mtime
                if file_time > timestamp_before and (current_time - file_time) < 30:
                    image_url = f"http://localhost:5001/images/{image_file.name}"
                    logger.info(f"🖼️ Nueva imagen detectada ({ext}): {image_url}")
                    return image_url
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error detectando nueva imagen: {str(e)}")
        return None

def allowed_file(filename):
    """Verificar si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image_file(file_data: bytes, filename: str) -> Dict[str, Any]:
    """Validar archivo de imagen y obtener información"""
    try:
        # Verificar que es una imagen válida
        image = Image.open(io.BytesIO(file_data))
        
        return {
            'valid': True,
            'format': image.format,
            'size': image.size,
            'mode': image.mode,
            'file_size': len(file_data),
            'filename': filename
        }
    except Exception as e:
        logger.error(f"❌ Error validando imagen {filename}: {str(e)}")
        return {
            'valid': False,
            'error': str(e),
            'filename': filename
        }

def process_base64_image(base64_data: str, filename: str) -> Optional[str]:
    """Procesar imagen en base64 y guardarla"""
    try:
        # Extraer datos de la imagen base64
        if ',' in base64_data:
            header, data = base64_data.split(',', 1)
        else:
            data = base64_data
        
        # Decodificar base64
        image_data = base64.b64decode(data)
        
        # Validar imagen
        validation = validate_image_file(image_data, filename)
        if not validation['valid']:
            logger.error(f"❌ Imagen base64 inválida: {validation['error']}")
            return None
        
        # Generar nombre único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = validation.get('format', 'png').lower()
        unique_filename = f"user_image_{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Guardar en directorio de usuario
        file_path = USER_IMAGES_DIR / unique_filename
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        logger.info(f"💾 Imagen base64 guardada: {unique_filename}")
        logger.info(f"📏 Tamaño: {validation['size']}, Formato: {validation['format']}")
        
        return f"http://localhost:5001/user-images/{unique_filename}"
        
    except Exception as e:
        logger.error(f"❌ Error procesando imagen base64: {str(e)}")
        return None

def log_conversation(session_id: str, user_message: str, ai_response: str, 
                    file_info: Optional[Dict] = None, image_info: Optional[Dict] = None):
    """Guardar conversación en logs con información de archivos e imágenes"""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_message": user_message,
            "ai_response": ai_response[:1000] + "..." if len(ai_response) > 1000 else ai_response,  # Limitar tamaño
            "file_info": file_info,
            "image_info": image_info,
            "metadata": {
                "message_length": len(user_message),
                "response_length": len(ai_response),
                "has_file": file_info is not None,
                "has_image": image_info is not None
            }
        }
        
        log_file = CHAT_LOGS_DIR / f"chat_{datetime.now().strftime('%Y%m%d')}.json"
        
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        # Mantener solo los últimos 1000 logs por día
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
            
        logger.debug(f"📝 Conversación guardada en log: {log_file}")
            
    except Exception as e:
        logger.error(f"❌ Error guardando log: {e}")

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
@cross_origin()
def handle_chat():
    """Endpoint principal para chat con AgenteAVA - MEJORADO"""
    if request.method == 'OPTIONS':
        return '', 200
    
    request_start_time = datetime.now()
    logger.info(f"\n💬 === NUEVA SOLICITUD CHAT === {request_start_time.strftime('%H:%M:%S')} ===")
    
    try:
        logger.info(f"Content-Type: {request.content_type}")
        
        # Manejar FormData (archivos)
        if request.content_type and 'multipart/form-data' in request.content_type:
            return handle_file_chat()
        
        # Validar Content-Type para JSON
        if request.content_type != 'application/json':
            logger.warning(f"❌ Content-Type inválido: {request.content_type}")
            return jsonify({
                'success': False,
                'response': 'Content-Type debe ser application/json'
            }), 400
        
        # Obtener y validar datos JSON
        try:
            data = request.get_json()
        except Exception as json_error:
            logger.error(f"❌ Error parseando JSON: {str(json_error)}")
            return jsonify({
                'success': False,
                'response': 'JSON inválido en la solicitud'
            }), 400
        
        if not data:
            logger.warning("❌ Datos JSON vacíos")
            return jsonify({
                'success': False,
                'response': 'Datos JSON requeridos'
            }), 400
        
        # Extraer parámetros
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', data.get('sessionId', f'session_{uuid.uuid4().hex}'))
        conversation_id = data.get('conversationId', session_id)
        has_file = data.get('hasFile', False)
        file_data = data.get('fileData', '')
        file_name = data.get('fileName', '')
        
        # Logging de parámetros
        logger.info(f"📝 Mensaje: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
        logger.info(f"🔑 Session ID: {session_id}")
        logger.info(f"💬 Conversation ID: {conversation_id}")
        logger.info(f"📎 Tiene archivo: {has_file}")
        if has_file:
            logger.info(f"📄 Archivo: {file_name}")
        
        # Validar que hay mensaje
        if not user_message:
            logger.warning("❌ Mensaje vacío")
            return jsonify({
                'success': False,
                'response': 'El mensaje no puede estar vacío'
            }), 400
        
        # Marcar tiempo antes de crear AVA
        ava_creation_start = datetime.now().timestamp()
        
        # Procesar imagen base64 si existe
        user_image_url = None
        image_info = None
        if has_file and file_data and file_name:
            logger.info("🖼️ Procesando imagen base64...")
            user_image_url = process_base64_image(file_data, file_name)
            if user_image_url:
                image_info = {
                    "uploaded_image_url": user_image_url,
                    "original_filename": file_name,
                    "processed_at": datetime.now().isoformat()
                }
                logger.info(f"✅ Imagen procesada: {user_image_url}")
            else:
                logger.warning("⚠️ No se pudo procesar la imagen base64")
        
        # Crear instancia fresca de AVA
        logger.info("🤖 Creando instancia AVA...")
        ava_instance = create_fresh_ava_instance()
        
        if not ava_instance:
            logger.error("❌ No se pudo crear instancia AVA")
            return jsonify({
                'success': False,
                'response': 'El servicio de inteligencia artificial no está disponible temporalmente. Por favor, intenta nuevamente en unos momentos.',
                'error_code': 'AVA_INSTANCE_FAILED'
            }), 503
        
        ava_creation_time = datetime.now().timestamp() - ava_creation_start
        logger.info(f"✅ Instancia AVA creada en {ava_creation_time:.2f} segundos")
        
        # Preparar mensaje para AVA (incluir información de imagen si existe)
        message_for_ava = user_message
        if user_image_url:
            # Guardar también en shared_files para que AVA pueda acceder
            try:
                # Copiar imagen a shared_files
                user_image_path = USER_IMAGES_DIR / user_image_url.split('/')[-1]
                shared_image_path = AVA_SHARED_DIR / user_image_url.split('/')[-1]
                
                if user_image_path.exists():
                    import shutil
                    shutil.copy2(user_image_path, shared_image_path)
                    message_for_ava = f'Analiza esta imagen: "{shared_image_path}" - {user_message}'
                    logger.info(f"📋 Mensaje para AVA con imagen: {message_for_ava[:100]}...")
            except Exception as copy_error:
                logger.error(f"❌ Error copiando imagen a shared_files: {copy_error}")
        
        # Procesar mensaje con AVA
        logger.info("🧠 Enviando mensaje a AVA para procesamiento...")
        llm_start_time = datetime.now().timestamp()
        
        try:
            result = ava_instance.chat(message_for_ava)
            llm_processing_time = datetime.now().timestamp() - llm_start_time
            
            logger.info(f"✅ AVA procesó el mensaje en {llm_processing_time:.2f} segundos")
            logger.debug(f"🔍 Resultado crudo (primeros 200 chars): {str(result)[:200]}")
            
        except Exception as ava_error:
            logger.error(f"❌ Error en procesamiento AVA: {str(ava_error)}")
            logger.error(f"❌ Traceback AVA:\n{traceback.format_exc()}")
            
            return jsonify({
                'success': False,
                'response': 'Error procesando tu mensaje con la inteligencia artificial. Por favor, intenta con una pregunta diferente.',
                'error_code': 'AVA_PROCESSING_FAILED',
                'error_details': str(ava_error) if app.debug else None
            }), 500
        
        # Procesar respuesta del LLM
        logger.info("🔄 Procesando respuesta del LLM...")
        processed_response = process_llm_response(result, user_message)
        
        # Detectar si se generó nueva imagen
        generated_image_url = has_generated_new_image(ava_creation_start)
        
        # Construir respuesta final
        total_processing_time = datetime.now().timestamp() - request_start_time.timestamp()
        
        final_response = {
            'success': processed_response['success'],
            'responseText': processed_response['response'],  # Para compatibilidad con frontend
            'response': processed_response['response'],      # Formato estándar
            'session_id': session_id,
            'conversationId': conversation_id,
            'timestamp': datetime.now().isoformat(),
            'agentName': 'AgenteAVA',
            'metadata': {
                **processed_response.get('metadata', {}),
                'processing_times': {
                    'total_seconds': round(total_processing_time, 3),
                    'ava_creation_seconds': round(ava_creation_time, 3),
                    'llm_processing_seconds': round(llm_processing_time, 3)
                },
                'request_info': {
                    'had_file': has_file,
                    'had_user_image': user_image_url is not None,
                    'message_length': len(user_message),
                    'timestamp': request_start_time.isoformat()
                }
            }
        }
        
        # Agregar URLs de imágenes
        if user_image_url:
            final_response['uploadedImageUrl'] = user_image_url
            final_response['metadata']['user_image_processed'] = True
            logger.info(f"👤 Imagen de usuario incluida: {user_image_url}")
        
        if generated_image_url:
            final_response['imageUrl'] = generated_image_url
            final_response['metadata']['generated_image'] = True
            logger.info(f"🖼️ Imagen generada por AVA incluida: {generated_image_url}")
        
        # Guardar en logs
        log_conversation(
            session_id, 
            user_message, 
            processed_response['response'],
            image_info=image_info
        )
        
        # Logging de respuesta exitosa
        response_length = len(final_response['response'])
        logger.info(f"📤 Respuesta lista: {response_length} caracteres")
        logger.info(f"⏱️ Tiempo total de procesamiento: {total_processing_time:.3f} segundos")
        logger.info(f"✅ === SOLICITUD COMPLETADA EXITOSAMENTE ===\n")
        
        return jsonify(final_response)
        
    except Exception as critical_error:
        total_time = datetime.now().timestamp() - request_start_time.timestamp()
        logger.error(f"❌ ERROR CRÍTICO EN WEBHOOK: {str(critical_error)}")
        logger.error(f"❌ Tiempo hasta error: {total_time:.3f} segundos")
        logger.error(f"❌ Traceback completo:\n{traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'response': 'Ha ocurrido un error interno en el servidor. Nuestro equipo ha sido notificado.',
            'error_code': 'CRITICAL_SERVER_ERROR',
            'timestamp': datetime.now().isoformat(),
            'error_details': str(critical_error) if app.debug else None
        }), 500

def handle_file_chat():
    """Manejar chat con archivos usando AgenteAVA - MEJORADO"""
    try:
        logger.info(f"\n📁 === FILE CHAT === {datetime.now().strftime('%H:%M:%S')} ===")
        
        user_message = request.form.get('message', '').strip()
        session_id = request.form.get('session_id', f'session_{uuid.uuid4().hex}')
        uploaded_file = request.files.get('file')
        
        if not uploaded_file:
            return jsonify({
                'success': False, 
                'response': 'Archivo requerido para esta solicitud'
            }), 400
        
        # Validar archivo
        if not allowed_file(uploaded_file.filename):
            return jsonify({
                'success': False,
                'response': f'Tipo de archivo no permitido. Extensiones permitidas: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Verificar tamaño
        uploaded_file.seek(0, 2)  # Ir al final del archivo
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)  # Volver al inicio
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'response': f'Archivo demasiado grande. Tamaño máximo: {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400
        
        # Generar nombre único y seguro
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = secure_filename(uploaded_file.filename)
        file_extension = original_filename.split('.')[-1] if '.' in original_filename else 'bin'
        unique_filename = f"upload_{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Guardar en múltiples ubicaciones para compatibilidad
        shared_file_path = AVA_SHARED_DIR / unique_filename
        upload_file_path = CHAT_UPLOADS_DIR / unique_filename
        
        # Leer datos del archivo
        file_data = uploaded_file.read()
        
        # Guardar archivo
        with open(shared_file_path, 'wb') as f:
            f.write(file_data)
        with open(upload_file_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"📁 Archivo guardado: {unique_filename} ({file_size} bytes)")
        
        # Información del archivo
        file_info = {
            "filename": unique_filename,
            "original_name": original_filename,
            "file_type": file_extension,
            "file_size": file_size,
            "uploaded_at": datetime.now().isoformat(),
            "is_image": file_extension.lower() in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']
        }
        
        # Si es imagen, validar y procesar
        uploaded_file_url = f"http://localhost:5001/uploads/{unique_filename}"
        if file_info['is_image']:
            validation = validate_image_file(file_data, original_filename)
            if validation['valid']:
                file_info['image_info'] = {
                    'format': validation['format'],
                    'size': validation['size'],
                    'mode': validation['mode']
                }
                logger.info(f"🖼️ Imagen válida: {validation['size']}, formato: {validation['format']}")
            else:
                logger.warning(f"⚠️ Imagen inválida: {validation['error']}")
        
        # Marcar tiempo antes de AVA
        time_before_ava = datetime.now().timestamp()
        
        # Preparar mensaje para AVA
        if user_message:
            message_for_ava = f'Analiza el archivo: "{shared_file_path}" - {user_message}'
        else:
            message_for_ava = f'Analiza el archivo: "{shared_file_path}"'
        
        logger.info(f"🤖 Enviando a AgenteAVA: {message_for_ava[:100]}...")
        
        # Crear instancia y procesar con AgenteAVA
        ava_instance = create_fresh_ava_instance()
        if not ava_instance:
            return jsonify({
                'success': False,
                'response': 'AgenteAVA no está disponible para procesar archivos.',
                'error_code': 'AVA_INSTANCE_FAILED'
            }), 503
        
        # Procesar con AVA
        try:
            result = ava_instance.chat(message_for_ava)
            logger.info("✅ AVA procesó el archivo exitosamente")
        except Exception as ava_error:
            logger.error(f"❌ Error procesando archivo con AVA: {str(ava_error)}")
            return jsonify({
                'success': False,
                'response': 'Error procesando el archivo con la inteligencia artificial.',
                'error_code': 'AVA_FILE_PROCESSING_FAILED'
            }), 500
        
        # Procesar respuesta
        processed_response = process_llm_response(result, user_message)
        
        # Verificar imagen generada por AVA
        generated_image_url = has_generated_new_image(time_before_ava)
        
        # Preparar respuesta
        response_data = {
            'success': processed_response['success'],
            'response': processed_response['response'],
            'responseText': processed_response['response'],  # Compatibilidad
            'session_id': session_id,
            'uploadedImageUrl': uploaded_file_url,
            'timestamp': datetime.now().isoformat(),
            'agentName': 'AgenteAVA',
            'metadata': {
                **processed_response.get('metadata', {}),
                'file_info': file_info,
                'uploaded_file_url': uploaded_file_url
            }
        }
        
        if generated_image_url:
            response_data['imageUrl'] = generated_image_url
            response_data['metadata']['generated_image'] = True
            logger.info(f"🖼️ Imagen generada por AVA: {generated_image_url}")
        
        # Guardar en logs
        log_conversation(
            session_id, 
            user_message or "Archivo subido", 
            processed_response['response'], 
            file_info=file_info
        )
        
        logger.info(f"✅ === ARCHIVO PROCESADO EXITOSAMENTE ===\n")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"❌ ERROR EN FILE CHAT: {e}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'response': 'Error procesando archivo. Por favor, intenta nuevamente.',
            'error_code': 'FILE_PROCESSING_ERROR',
            'error_details': str(e) if app.debug else None
        }), 500

# ✅ ENDPOINTS PARA SERVIR ARCHIVOS - MEJORADOS
@app.route('/images/<filename>')
@cross_origin()
def serve_generated_image(filename):
    """Servir imágenes generadas por AgenteAVA"""
    try:
        logger.debug(f"📤 Sirviendo imagen generada: {filename}")
        return send_from_directory(GENERATED_IMAGES_DIR, filename)
    except FileNotFoundError:
        logger.warning(f"❌ Imagen generada no encontrada: {filename}")
        return jsonify({"error": "Imagen no encontrada"}), 404
    except Exception as e:
        logger.error(f"❌ Error sirviendo imagen generada {filename}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/uploads/<filename>')
@cross_origin()
def serve_uploaded_file(filename):
    """Servir archivos subidos por usuarios"""
    try:
        logger.debug(f"📤 Sirviendo archivo subido: {filename}")
        return send_from_directory(CHAT_UPLOADS_DIR, filename)
    except FileNotFoundError:
        logger.warning(f"❌ Archivo subido no encontrado: {filename}")
        return jsonify({"error": "Archivo no encontrado"}), 404
    except Exception as e:
        logger.error(f"❌ Error sirviendo archivo subido {filename}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/user-images/<filename>')
@cross_origin()
def serve_user_image(filename):
    """Servir imágenes de usuario procesadas desde base64"""
    try:
        logger.debug(f"📤 Sirviendo imagen de usuario: {filename}")
        return send_from_directory(USER_IMAGES_DIR, filename)
    except FileNotFoundError:
        logger.warning(f"❌ Imagen de usuario no encontrada: {filename}")
        return jsonify({"error": "Imagen no encontrada"}), 404
    except Exception as e:
        logger.error(f"❌ Error sirviendo imagen de usuario {filename}: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

# ✅ ENDPOINTS DE DIAGNÓSTICO Y ESTADO - MEJORADOS
@app.route('/api/chat/status', methods=['GET'])
@cross_origin()
def llm_status():
    """Verificar estado y salud del LLM"""
    try:
        logger.info("🔍 Iniciando verificación de estado LLM...")
        status_start_time = datetime.now().timestamp()
        
        # Intentar crear instancia
        ava_instance = create_fresh_ava_instance()
        
        if not ava_instance:
            return jsonify({
                'status': 'unhealthy',
                'llm_available': False,
                'error': 'No se pudo crear instancia AVA',
                'timestamp': datetime.now().isoformat(),
                'check_duration_seconds': datetime.now().timestamp() - status_start_time
            }), 503
        
        # Probar con mensaje simple
        test_message = "Hola, confirma que estás funcionando correctamente."
        logger.info(f"🧪 Probando LLM con mensaje: '{test_message}'")
        
        try:
            test_result = ava_instance.chat(test_message)
            processed = process_llm_response(test_result, test_message)
            
            check_duration = datetime.now().timestamp() - status_start_time
            
            logger.info(f"✅ Verificación LLM completada en {check_duration:.3f} segundos")
            
            return jsonify({
                'status': 'healthy',
                'llm_available': True,
                'test_successful': processed['success'],
                'test_response_length': len(processed['response']),
                'test_response_preview': processed['response'][:100],
                'check_duration_seconds': round(check_duration, 3),
                'timestamp': datetime.now().isoformat(),
                'service': 'AVA Chat Webhook Enhanced',
                'version': '2.0'
            })
            
        except Exception as test_error:
            logger.error(f"❌ Error en prueba LLM: {str(test_error)}")
            return jsonify({
                'status': 'partial',
                'llm_available': True,
                'test_successful': False,
                'error': f'AVA creado pero falló en prueba: {str(test_error)}',
                'timestamp': datetime.now().isoformat()
            }), 503
            
    except Exception as e:
        logger.error(f"❌ Error crítico verificando LLM: {str(e)}")
        return jsonify({
            'status': 'error',
            'llm_available': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/health')
@cross_origin()
def health():
    """Estado completo del servicio de chat"""
    try:
        # Verificar AVA
        ava_available = False
        ava_error = None
        try:
            test_ava = create_fresh_ava_instance()
            ava_available = test_ava is not None
        except Exception as e:
            ava_error = str(e)
        
        # Verificar directorios
        directories_status = {
            "ava_bot_exists": (BASE_DIR / "ava_bot").exists(),
            "ava_graph_bot_exists": (BASE_DIR / "ava_bot" / "ava_graph_bot.py").exists(),
            "shared_files_exists": AVA_SHARED_DIR.exists(),
            "generated_images_exists": GENERATED_IMAGES_DIR.exists(),
            "user_images_exists": USER_IMAGES_DIR.exists(),
            "chat_uploads_exists": CHAT_UPLOADS_DIR.exists(),
            "chat_logs_exists": CHAT_LOGS_DIR.exists()
        }
        
        # Contar archivos en directorios
        file_counts = {}
        for dir_name, dir_path in [
            ("generated_images", GENERATED_IMAGES_DIR),
            ("user_images", USER_IMAGES_DIR),
            ("chat_uploads", CHAT_UPLOADS_DIR),
            ("shared_files", AVA_SHARED_DIR)
        ]:
            try:
                file_counts[dir_name] = len(list(dir_path.glob("*"))) if dir_path.exists() else 0
            except:
                file_counts[dir_name] = -1
        
        return jsonify({
            "service": "AgenteAVA Chat Service Enhanced",
            "version": "2.0",
            "status": "running",
            "port": 5001,
            "ava_available": ava_available,
            "ava_error": ava_error,
            "capabilities": [
                "text_chat_with_ava",
                "file_upload_analysis",
                "image_generation",
                "multimodal_processing",
                "base64_image_processing",
                "advanced_logging",
                "conversation_history"
            ],
            "directories": directories_status,
            "file_counts": file_counts,
            "path_info": {
                "base_dir": str(BASE_DIR),
                "ava_bot_in_path": str(BASE_DIR / "ava_bot") in sys.path
            },
            "allowed_file_types": list(ALLOWED_EXTENSIONS),
            "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Error en health check: {str(e)}")
        return jsonify({
            "service": "AgenteAVA Chat Service Enhanced",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/chat/test')
@cross_origin()
def test_ava():
    """Probar conexión con AgenteAVA"""
    try:
        logger.info("🧪 Iniciando prueba de conexión con AgenteAVA...")
        ava_instance = create_fresh_ava_instance()
        if ava_instance:
            result = ava_instance.chat("Hola, ¿estás funcionando correctamente?")
            processed = process_llm_response(result, "Prueba de funcionamiento")
            return jsonify({
                "success": True,
                "ava_available": True,
                "test_response": processed['response'][:200],
                "response_length": len(processed['response']),
                "processing_successful": processed['success'],
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "ava_available": False,
                "error": "No se pudo crear instancia de AgenteAVA"
            }), 500
    except Exception as e:
        logger.error(f"❌ Error en test: {e}")
        return jsonify({
            "success": False,
            "ava_available": False,
            "error": str(e)
        }), 500

@app.route('/api/chat/debug', methods=['POST'])
@cross_origin()
def debug_ava():
    """Debug del LLM con mensaje personalizado"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400
        
        test_message = data.get('message', 'Mensaje de prueba para debug')
        include_raw = data.get('include_raw', False)
        
        logger.info(f"🐛 Iniciando debug AVA con mensaje: '{test_message}'")
        debug_start_time = datetime.now().timestamp();
        
        # Crear instancia
        ava_instance = create_fresh_ava_instance()
        if not ava_instance:
            return jsonify({
                'error': 'No se pudo crear instancia AVA para debug',
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # Procesar mensaje
        try:
            result = ava_instance.chat(test_message)
            processed = process_llm_response(result, test_message)
            
            debug_duration = datetime.now().timestamp() - debug_start_time;
            
            debug_response = {
                'debug_info': {
                    'input_message': test_message,
                    'processing_successful': processed['success'],
                    'response_preview': processed['response'][:200],
                    'response_length': len(processed['response']),
                    'processing_time_seconds': round(debug_duration, 3),
                    'raw_result_type': type(result).__name__,
                    'metadata': processed.get('metadata', {}),
                    'timestamp': datetime.now().isoformat()
                },
                'full_response': processed['response'] if processed['success'] else None
            }
            
            # Incluir resultado crudo si se solicita
            if include_raw:
                debug_response['raw_result'] = {
                    'data': str(result)[:1000],  # Limitar tamaño
                    'type': str(type(result)),
                    'length': len(str(result))
                }
            
            logger.info(f"✅ Debug completado en {debug_duration:.3f} segundos")
            return jsonify(debug_response)
            
        except Exception as debug_error:
            logger.error(f"❌ Error en debug AVA: {str(debug_error)}")
            return jsonify({
                'error': f'Error procesando mensaje de debug: {str(debug_error)}',
                'debug_info': {
                    'input_message': test_message,
                    'error_type': type(debug_error).__name__,
                    'timestamp': datetime.now().isoformat()
                }
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error crítico en debug: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat/history/<session_id>')
@cross_origin()
def get_chat_history(session_id):
    """Obtener historial de chat mejorado"""
    try:
        today = datetime.now().strftime('%Y%m%d')
        log_file = CHAT_LOGS_DIR / f"chat_{today}.json"
        
        if not log_file.exists():
            return jsonify({"history": [], "session_id": session_id, "date": today})
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_logs = json.load(f)
        
        session_logs = [log for log in all_logs if log.get('session_id') == session_id]
        
        return jsonify({
            "history": session_logs,
            "session_id": session_id,
            "date": today,
            "total_messages": len(session_logs),
            "has_files": any(log.get('file_info') for log in session_logs),
            "has_images": any(log.get('image_info') for log in session_logs)
        })
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("🚀 WEBHOOK DE CHAT AVANZADO CON AGENTEAVA - Puerto 5001")
    logger.info("📡 Endpoints disponibles:")
    logger.info("   POST /api/chat - Chat con AgenteAVA (texto, archivos, imágenes base64)")
    logger.info("   GET  /images/<filename> - Imágenes generadas por AVA")
    logger.info("   GET  /uploads/<filename> - Archivos subidos")
    logger.info("   GET  /user-images/<filename> - Imágenes de usuario procesadas")
    logger.info("   GET  /api/chat/test - Probar conexión con AVA")
    logger.info("   GET  /api/chat/status - Estado del LLM")
    logger.info("   POST /api/chat/debug - Debug del LLM")
    logger.info("   GET  /health - Estado completo del servicio")
    logger.info("   GET  /api/chat/history/<session> - Historial de conversación")
    logger.info(f"\n🤖 AgenteAVA disponible: {(BASE_DIR / 'ava_bot' / 'ava_graph_bot.py').exists()}")
    logger.info(f"📁 PATH incluye ava_bot: {str(BASE_DIR / 'ava_bot') in sys.path}")
    logger.info(f"📏 Tamaño máximo de archivo: {MAX_FILE_SIZE // (1024*1024)}MB")
    logger.info(f"📋 Tipos de archivo permitidos: {', '.join(ALLOWED_EXTENSIONS)}")
    logger.info("=" * 60)
    
    app.run(host='0.0.0.0', port=5001, debug=True)