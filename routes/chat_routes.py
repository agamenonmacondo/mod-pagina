from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import subprocess
import logging
import time
import os
import json
import re
import sys
import threading  # ✅ AGREGAR ESTA LÍNEA
import atexit     # ✅ AGREGAR ESTA LÍNEA
from pathlib import Path

# Configurar Blueprint
chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

# Variables globales para proceso AVA
ava_process = None
ava_bot_path = None
llm_instance = None  # ✅ AGREGAR ESTA LÍNEA

def find_ava_script():
    """Encuentra el script principal de AVA automáticamente"""
    try:
        base_path = Path(__file__).parent.parent
        logger.info(f"🔍 Buscando AVA desde: {base_path}")
        
        # Ubicaciones posibles del script
        possible_locations = [
            base_path / 'llmpagina' / 'ava_bot' / 'llm_mcp_integration.py',
            base_path / 'ava_bot' / 'llm_mcp_integration.py',
            base_path / 'llm_mcp_integration.py'
        ]
        
        for script_path in possible_locations:
            if script_path.exists():
                working_dir = script_path.parent
                logger.info(f"✅ Script AVA encontrado: {script_path}")
                logger.info(f"📁 Directorio de trabajo: {working_dir}")
                return working_dir, script_path
        
        logger.error("❌ Script AVA no encontrado en ninguna ubicación")
        return None, None
        
    except Exception as e:
        logger.error(f"❌ Error buscando script AVA: {e}")
        return None, None

def get_python_executable():
    """Obtiene el ejecutable de Python correcto"""
    # Usar el mismo que está funcionando
    venv_python = Path(__file__).parent.parent / 'venv' / 'Scripts' / 'python.exe'
    
    if venv_python.exists():
        logger.info(f"✅ Usando Python del venv: {venv_python}")
        return str(venv_python)
    else:
        logger.info(f"⚠️ Venv no encontrado, usando sys.executable: {sys.executable}")
        return sys.executable

def start_ava():
    """Inicia el proceso AVA de forma limpia"""
    global ava_process, ava_bot_path
    
    try:
        logger.info("🚀 Iniciando AVA...")
        
        # Encontrar script
        ava_bot_path, script_path = find_ava_script()
        if not script_path:
            logger.error("❌ No se encontró el script AVA")
            return False
        
        # Terminar proceso anterior si existe
        if ava_process and ava_process.poll() is None:
            logger.info("🔄 Terminando proceso AVA anterior...")
            ava_process.terminate()
            try:
                ava_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                ava_process.kill()
            ava_process = None
        
        # Configurar entorno
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONPATH'] = str(ava_bot_path)
        
        # Iniciar proceso
        python_exe = get_python_executable()
        logger.info(f"🐍 Ejecutando: {python_exe} {script_path}")
        
        ava_process = subprocess.Popen(
            [python_exe, str(script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=0,
            cwd=str(ava_bot_path),
            env=env
        )
        
        # Esperar inicialización
        logger.info("⏳ Esperando inicialización...")
        start_time = time.time()
        init_lines = []
        
        while time.time() - start_time < 30:  # 30 segundos timeout
            if ava_process.poll() is not None:
                logger.error("❌ Proceso AVA terminó durante inicialización")
                return False
            
            try:
                line = ava_process.stdout.readline()
                if line:
                    clean_line = line.strip()
                    init_lines.append(clean_line)
                    
                    # Log seguro (sin unicode problemático)
                    try:
                        logger.info(f"📥 AVA: {clean_line}")
                    except UnicodeEncodeError:
                        ascii_line = clean_line.encode('ascii', errors='ignore').decode('ascii')
                        logger.info(f"📥 AVA: {ascii_line}")
                    
                    # Buscar indicadores de éxito
                    success_indicators = [
                        "Ava lista",
                        "herramientas listas",
                        "HERRAMIENTAS CARGADAS",
                        "AVA Bot listo"
                    ]
                    
                    if any(indicator in clean_line for indicator in success_indicators):
                        logger.info("🎉 AVA inicializado exitosamente!")
                        time.sleep(2)  # Tiempo para estabilización
                        return True
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.warning(f"⚠️ Error leyendo inicialización: {e}")
                break
        
        # Verificar si sigue vivo
        if ava_process and ava_process.poll() is None:
            logger.info("✅ AVA parece estar funcionando")
            return True
        else:
            logger.error("❌ AVA falló en inicialización")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error iniciando AVA: {e}")
        return False

def send_message_to_ava(message):
    """Envía mensaje a AVA y obtiene respuesta - CORRIGIENDO CAPTURA DE HERRAMIENTAS"""
    global ava_process
    
    if not ava_process or ava_process.poll() is not None:
        logger.error("❌ Proceso AVA no disponible")
        return None
    
    try:
        logger.info(f"📤 Enviando mensaje real: '{message}'")
        
        # Enviar mensaje
        message_to_send = f"{message}\n"
        ava_process.stdin.write(message_to_send)
        ava_process.stdin.flush()
        time.sleep(0.5)
        
        # Variables para captura
        response_lines = []
        start_time = time.time()
        timeout = 60  # Timeout más largo para herramientas
        final_response = None
        message_processed = False
        tool_executed = False
        
        logger.info("📥 Iniciando lectura de respuesta...")
        
        while time.time() - start_time < timeout:
            if ava_process.poll() is not None:
                logger.error("❌ Proceso AVA terminó")
                break
            
            try:
                line = ava_process.stdout.readline()
                if line:
                    clean_line = line.strip()
                    if clean_line:
                        response_lines.append(clean_line)
                        logger.info(f"📥 AVA línea: {clean_line}")
                        
                        # ✅ VERIFICAR QUE AVA PROCESÓ NUESTRO MENSAJE
                        if f"👤 Usuario: {message}" in clean_line or f"💬 Tú: 👤 {message}" in clean_line:
                            message_processed = True
                            logger.info(f"✅ AVA procesó nuestro mensaje")
                            continue
                        
                        # ✅ DETECTAR EJECUCIÓN DE HERRAMIENTAS
                        if "🎯 Ejecutando herramienta:" in clean_line:
                            tool_name = clean_line.split("🎯 Ejecutando herramienta:", 1)[1].strip()
                            logger.info(f"🔧 AVA está ejecutando herramienta: {tool_name}")
                            tool_executed = True
                            continue
                        
                        # ✅ DETECTAR FINALIZACIÓN DE HERRAMIENTA
                        if "✅ Resultado:" in clean_line and tool_executed:
                            logger.info("✅ Herramienta completada, esperando respuesta final...")
                            continue
                        
                        # ✅ IGNORAR LLM RESPONSE SI HAY HERRAMIENTAS EJECUTÁNDOSE
                        if "🧠 LLM Response:" in clean_line:
                            response_part = clean_line.split("🧠 LLM Response:", 1)[1].strip()
                            
                            # ✅ SI ES UN JSON DE HERRAMIENTA, NO LO TOMAR COMO RESPUESTA FINAL
                            if response_part.startswith('{"use_tool":'):
                                logger.info(f"🔧 LLM Response es comando de herramienta, esperando ejecución...")
                                continue
                            else:
                                # ✅ ES UNA RESPUESTA REAL DESPUÉS DE EJECUTAR HERRAMIENTAS
                                if tool_executed and message_processed:
                                    final_response = response_part
                                    logger.info(f"✅ RESPUESTA LLM FINAL (post-herramienta): {final_response}")
                                    time.sleep(2)  # Esperar un poco más para imágenes
                                    break
                                elif not tool_executed and message_processed:
                                    final_response = response_part
                                    logger.info(f"✅ RESPUESTA LLM DIRECTA: {final_response}")
                                    time.sleep(2)
                                    break
                        
                        # ✅ RESPUESTA DIRECTA DE AVA - CAPTURA INMEDIATA
                        elif "🤖 Ava:" in clean_line:
                            response_part = clean_line.split("🤖 Ava:", 1)[1].strip()
                            if len(response_part) > 10:  # Reducir requisito mínimo
                                final_response = response_part
                                logger.info(f"✅ RESPUESTA AVA CAPTURADA: {final_response}")
                                time.sleep(1)  # Reducir espera
                                break
                        
                        # ✅ DETECTAR PROCESAMIENTO DE MENSAJE
                        elif "🎯 Intención detectada:" in clean_line:
                            logger.info(f"🎯 AVA detectó intención")
                            message_processed = True
                        elif "🤖 Procesando con" in clean_line:
                            logger.info(f"🤖 AVA está procesando")
                            message_processed = True
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.warning(f"⚠️ Error leyendo: {e}")
                break
        
        # ✅ PROCESAR RESPUESTA FINAL
        if final_response:
            clean_response = clean_final_response(final_response)
            
            # ✅ BUSCAR IMÁGENES GENERADAS
            image_info = detect_image_generation(response_lines)
            
            if image_info:
                logger.info(f"🖼️ Imagen detectada: {image_info}")
                return {
                    'text': clean_response,
                    'image_generated': True,
                    'image_filename': image_info['filename'],
                    'image_url': f"/api/chat/image/{image_info['filename']}"
                }
            else:
                logger.info(f"✅ Respuesta final procesada: {clean_response}")
                return clean_response
        
        # ✅ FALLBACK MEJORADO
        logger.warning("⚠️ No se encontró respuesta final válida")
        
        # Buscar la última respuesta de AVA que no sea repetitiva
        for line in reversed(response_lines[-10:]):
            if ("🤖 Ava:" in line and 
                len(line) > 30 and
                not "¡Hola! 😊" in line and
                not "iniciado la conversación" in line):
                
                response_part = line.split("🤖 Ava:", 1)[1].strip()
                clean_response = clean_final_response(response_part)
                
                if len(clean_response) > 15:
                    logger.info(f"✅ RESPUESTA FALLBACK: {clean_response}")
                    
                    # Buscar imagen también en fallback
                    image_info = detect_image_generation(response_lines)
                    if image_info:
                        return {
                            'text': clean_response,
                            'image_generated': True,
                            'image_filename': image_info['filename'],
                            'image_url': f"/api/chat/image/{image_info['filename']}"
                        }
                    return clean_response
        
        logger.error(f"❌ No se obtuvo respuesta válida para: '{message}'")
        logger.error(f"📝 Tool executed: {tool_executed}, Message processed: {message_processed}")
        logger.error(f"📝 Últimas líneas: {response_lines[-5:] if response_lines else 'ninguna'}")
        
        return f"Procesé tu solicitud pero no pude capturar la respuesta completa. ¿Podrías intentar de nuevo?"
            
    except Exception as e:
        logger.error(f"❌ Error en comunicación: {e}")
        return f"Error comunicando con AVA: {str(e)}"

def clean_final_response(response_text):
    """Limpia la respuesta final - VERSIÓN MEJORADA"""
    try:
        if not response_text:
            return ""
        
        # Limpiar caracteres de encoding problemáticos
        clean_response = response_text
        
        # Mapeo de caracteres problemáticos
        char_fixes = {
            'Â¡': '¡', 'Ã³': 'ó', 'Ã±': 'ñ', 'Ã¡': 'á', 
            'Ã©': 'é', 'Ã­': 'í', 'Ãº': 'ú', 'Â¿': '¿'
        }
        
        for bad_char, good_char in char_fixes.items():
            clean_response = clean_response.replace(bad_char, good_char)
        
        # Remover patrones de log que se colaron
        patterns_to_remove = [
            r'INFO:.*?:',
            r'DEBUG:.*?:',
            r'WARNING:.*?:',
            r'🔍.*?:',
            r'📥 AVA:',
            r'📤.*?:',
            r'⏰.*?:',
            r'🧠 LLM Response:',
            r'🎯.*?:',
            r'Analizando respuesta LLM:',
            r'No se pudo extraer.*?',
            r'Intención detectada:.*?',
            r'Usuario:.*?',
            r'Contexto actual:.*?'
        ]
        
        for pattern in patterns_to_remove:
            clean_response = re.sub(pattern, '', clean_response, flags=re.IGNORECASE)
        
        # Limpiar espacios extra y saltos de línea
        clean_response = ' '.join(clean_response.split())
        
        # Remover caracteres de control residuales
        clean_response = ''.join(char for char in clean_response if ord(char) >= 32 or char in '\n\t')
        
        return clean_response.strip()
        
    except Exception as e:
        logger.error(f"❌ Error limpiando respuesta: {e}")
        return str(response_text).strip() if response_text else ""

def detect_image_generation(lines):
    """Detecta generación de imagen - VERSIÓN MEJORADA"""
    try:
        for line in lines:
            line_lower = line.lower()
            
            # Patrones de imagen generada
            image_patterns = [
                r'imagen guardada en:?\s*([a-zA-Z0-9_\-]+\.png)',
                r'imagen generada:?\s*([a-zA-Z0-9_\-]+\.png)',
                r'filepath[:\s]*.*?([a-zA-Z0-9_\-]+\.png)',
                r'guardada en.*?([a-zA-Z0-9_\-]+\.png)',
                r'saved.*?([a-zA-Z0-9_\-]+\.png)'
            ]
            
            for pattern in image_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    filename = match.group(1)
                    logger.info(f"🖼️ Imagen detectada: {filename}")
                    return {
                        'filename': filename,
                        'path': line,
                        'detected_pattern': pattern
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error detectando imagen: {e}")
        return None

def find_image_directories():
    """Encuentra directorios donde pueden estar las imágenes generadas"""
    base_path = Path(__file__).parent.parent
    
    possible_dirs = [
        base_path / 'llmpagina' / 'ava_bot' / 'generated_images',
        base_path / 'ava_bot' / 'generated_images',
        base_path / 'generated_images',
        base_path / 'static' / 'generated',
        base_path / 'llmpagina' / 'ava_bot' / 'tools' / 'generated_images'
    ]
    
    existing_dirs = []
    for dir_path in possible_dirs:
        if dir_path.exists():
            existing_dirs.append(dir_path)
    
    return existing_dirs

def cleanup_ava():
    """Limpia el proceso AVA"""
    global ava_process
    
    if ava_process:
        try:
            if ava_process.poll() is None:
                ava_process.terminate()
                try:
                    ava_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    ava_process.kill()
            ava_process = None
            logger.info("🧹 Proceso AVA limpiado")
        except Exception as e:
            logger.error(f"⚠️ Error limpiando AVA: {e}")

# ✅ ENDPOINTS DE LA API - SOLO UNA DEFINICIÓN DE CADA UNO

@chat_bp.route('/api/chat/status', methods=['GET'])
def chat_status():
    """Estado del chat AVA"""
    global ava_process
    
    is_running = ava_process is not None and ava_process.poll() is None
    
    return jsonify({
        'ava_status': 'running' if is_running else 'stopped',
        'timestamp': datetime.now().isoformat(),
        'process_id': ava_process.pid if is_running else None
    })

@chat_bp.route('/api/chat/message', methods=['POST'])
def chat_message():
    """Enviar mensaje a AVA - VERSIÓN DEPURADA COMPLETA"""
    try:
        logger.info(f"📥 Request recibida: {request.method} {request.path}")
        
        # Obtener datos JSON
        data = request.get_json()
        if not data:
            logger.error("❌ No se recibieron datos JSON")
            return jsonify({'error': 'Datos JSON requeridos'}), 400
        
        logger.info(f"📦 Datos recibidos: {data}")
        
        if 'message' not in data:
            logger.error("❌ Campo 'message' no encontrado")
            return jsonify({'error': 'Campo message requerido'}), 400
        
        message = data['message'].strip()
        if not message:
            logger.error("❌ Mensaje vacío")
            return jsonify({'error': 'Mensaje no puede estar vacío'}), 400
        
        logger.info(f"📝 Mensaje a procesar: '{message}'")
        
        # Verificar estado de AVA
        global ava_process
        
        if not ava_process or ava_process.poll() is not None:
            logger.warning("⚠️ AVA no disponible - intentando reiniciar...")
            
            restart_success = start_ava()
            if not restart_success:
                logger.error("❌ No se pudo reiniciar AVA")
                return jsonify({
                    'success': False,
                    'response': 'AVA está temporalmente fuera de línea. Por favor, presiona "Reiniciar AVA".',
                    'status': 'offline',
                    'action_needed': 'restart'
                })
        
        # ✅ ENVIAR MENSAJE Y CAPTURAR RESPUESTA
        logger.info(f"📤 Enviando a AVA: '{message}'")
        start_time = time.time()
        
        response = send_message_to_ava(message)
        
        processing_time = time.time() - start_time
        logger.info(f"⏱️ Tiempo de procesamiento: {processing_time:.2f}s")
        logger.info(f"📥 Respuesta recibida de send_message_to_ava: {response}")
        logger.info(f"📥 Tipo de respuesta: {type(response)}")
        
        # ✅ PROCESAR RESPUESTA CON LOGGING DETALLADO
        if response:
            if isinstance(response, dict):
                # Respuesta con imagen
                logger.info("🖼️ Respuesta tipo dict (imagen detectada)")
                response_json = {
                    'success': True,
                    'response': response.get('text', ''),
                    'image_generated': response.get('image_generated', False),
                    'image_url': response.get('image_url'),
                    'image_filename': response.get('image_filename'),
                    'status': 'success',
                    'processing_time': processing_time,
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"📤 Enviando respuesta JSON (imagen): {response_json}")
                return jsonify(response_json)
            else:
                # Respuesta de texto simple
                logger.info("📝 Respuesta tipo string (texto simple)")
                response_json = {
                    'success': True,
                    'response': str(response),
                    'image_generated': False,
                    'status': 'success',
                    'processing_time': processing_time,
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"📤 Enviando respuesta JSON (texto): {response_json}")
                return jsonify(response_json)
        else:
            # No se obtuvo respuesta
            logger.error("❌ No se obtuvo respuesta de AVA")
            error_response = {
                'success': False,
                'response': 'No pude procesar tu mensaje. AVA puede estar ocupado procesando otra solicitud.',
                'status': 'no_response',
                'action_needed': 'retry'
            }
            logger.info(f"📤 Enviando respuesta de error: {error_response}")
            return jsonify(error_response)
        
    except Exception as e:
        logger.error(f"❌ Error en chat_message: {e}")
        import traceback
        logger.error(f"📋 Traceback completo: {traceback.format_exc()}")
        error_response = {
            'success': False,
            'response': 'Error interno del servidor. Por favor, intenta de nuevo.',
            'status': 'error',
            'error_details': str(e)
        }
        return jsonify(error_response), 500

@chat_bp.route('/api/chat/image/<filename>')
def serve_image(filename):
    """Servir imágenes generadas por AVA"""
    try:
        # Buscar imagen en directorios posibles
        image_dirs = find_image_directories()
        
        for img_dir in image_dirs:
            image_path = img_dir / filename
            if image_path.exists():
                logger.info(f"🖼️ Sirviendo imagen: {image_path}")
                return send_file(str(image_path), mimetype='image/png')
        
        logger.warning(f"⚠️ Imagen no encontrada: {filename}")
        return jsonify({'error': 'Imagen no encontrada'}), 404
        
    except Exception as e:
        logger.error(f"❌ Error sirviendo imagen: {e}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/restart', methods=['POST'])
def restart_ava():
    """Reiniciar AVA manualmente"""
    try:
        logger.info("🔄 Reiniciando AVA...")
        
        # Limpiar proceso actual
        cleanup_ava()
        
        # Iniciar nuevo proceso
        success = start_ava()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'AVA reiniciado exitosamente',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error reiniciando AVA'
            })
        
    except Exception as e:
        logger.error(f"❌ Error reiniciando AVA: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/api/chat/test', methods=['POST'])
def test_ava():
    """Probar conexión con AVA"""
    try:
        test_message = "hola"
        response = send_message_to_ava(test_message)
        
        if response:
            return jsonify({
                'success': True,
                'test_message': test_message,
                'response': response,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'AVA no respondió'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/api/chat/debug', methods=['GET'])
def debug_info():
    """Información de debug del sistema"""
    try:
        global ava_process, ava_bot_path
        
        debug_info = {
            'timestamp': datetime.now().isoformat(),
            'ava_process': {
                'exists': ava_process is not None,
                'pid': ava_process.pid if ava_process else None,
                'poll_status': ava_process.poll() if ava_process else None,
                'running': ava_process is not None and ava_process.poll() is None
            },
            'paths': {
                'ava_bot_path': str(ava_bot_path) if ava_bot_path else None,
                'script_found': False,
                'python_executable': get_python_executable()
            },
            'system': {
                'python_version': sys.version,
                'cwd': os.getcwd(),
                'env_vars': {
                    'PYTHONIOENCODING': os.environ.get('PYTHONIOENCODING'),
                    'GROQ_API_KEY': 'SET' if os.environ.get('GROQ_API_KEY') else 'NOT_SET'
                }
            }
        }
        
        # Verificar si encontramos el script
        working_dir, script_path = find_ava_script()
        if script_path:
            debug_info['paths']['script_found'] = True
            debug_info['paths']['script_path'] = str(script_path)
            debug_info['paths']['working_dir'] = str(working_dir)
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@chat_bp.route('/api/chat/memory-debug')
def memory_debug():
    """Debug del sistema de memoria"""
    try:
        global llm_instance
        
        if not llm_instance:
            return jsonify({'error': 'AVA no inicializada'})
        
        debug_info = {
            'memory_file': llm_instance.memory_file,
            'memory_file_exists': os.path.exists(llm_instance.memory_file),
            'email': llm_instance.current_user_email,
            'conversation_count': len(llm_instance.conversation_history),
            'user_info_fields': len(llm_instance.user_info),
            'user_info': llm_instance.user_info,
            'last_5_messages': llm_instance.conversation_history[-5:] if llm_instance.conversation_history else [],
            'context_summary': llm_instance._get_context_summary()
        }
        
        # Verificar archivo de memoria
        if os.path.exists(llm_instance.memory_file):
            try:
                with open(llm_instance.memory_file, 'r', encoding='utf-8') as f:
                    file_content = json.load(f)
                debug_info['memory_file_content'] = {
                    'conversation_history_count': len(file_content.get('conversation_history', [])),
                    'last_updated': file_content.get('last_updated'),
                    'session_count': file_content.get('session_count', 0)
                }
            except Exception as e:
                debug_info['memory_file_error'] = str(e)
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': str(e)})

@chat_bp.route('/api/chat/memory-reset', methods=['POST'])
def memory_reset():
    """Resetear memoria (solo para debugging)"""
    try:
        global llm_instance
        
        if not llm_instance:
            return jsonify({'error': 'AVA no inicializada'})
        
        # Limpiar memoria
        llm_instance.conversation_history = []
        llm_instance.user_info = {}
        llm_instance.current_user_email = None
        
        # Guardar estado limpio
        llm_instance._save_memory()
        
        return jsonify({
            'success': True,
            'message': 'Memoria reseteada correctamente'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

# ✅ INICIALIZACIÓN AUTOMÁTICA - SOLO UNA VEZ
def init_ava_on_startup():
    """Inicializa AVA automáticamente al cargar la aplicación"""
    try:
        logger.info("🚀 Iniciando AVA en background...")
        success = start_ava()
        if success:
            logger.info("✅ AVA iniciado exitosamente")
        else:
            logger.warning("⚠️ AVA no se pudo inicializar al startup")
    except Exception as e:
        logger.error(f"❌ Error iniciando AVA al startup: {e}")

# Inicializar cuando se importa el módulo
startup_thread = threading.Thread(target=init_ava_on_startup)
startup_thread.daemon = True
startup_thread.start()

# Cleanup al salir
atexit.register(cleanup_ava)

@chat_bp.route('/api/chat/test-direct', methods=['POST'])
def test_direct_response():
    """Test directo para debug - envía respuesta sin procesar AVA"""
    try:
        data = request.get_json()
        message = data.get('message', 'test')
        
        # Respuesta de prueba directa
        test_response = {
            'success': True,
            'response': f'Test directo funcionando! Recibí: "{message}"',
            'image_generated': False,
            'status': 'test_success',
            'timestamp': datetime.now().isoformat(),
            'test_mode': True
        }
        
        logger.info(f"📤 TEST: Enviando respuesta directa: {test_response}")
        return jsonify(test_response)
        
    except Exception as e:
        logger.error(f"❌ Error en test directo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/api/chat/test-ava-direct', methods=['POST'])
def test_ava_direct():
    """Test directo de AVA - bypass completo"""
    try:
        data = request.get_json()
        message = data.get('message', 'hola')
        
        logger.info(f"🧪 TEST AVA DIRECTO: {message}")
        
        # Verificar AVA
        global ava_process
        if not ava_process or ava_process.poll() is not None:
            return jsonify({
                'success': False,
                'response': 'AVA no está ejecutándose',
                'status': 'offline'
            })
        
        # Enviar mensaje directo
        try:
            ava_process.stdin.write(f"{message}\n")
            ava_process.stdin.flush()
            logger.info("📤 Mensaje enviado a AVA")
            
            # Leer respuesta con timeout corto
            timeout = 10
            collected_lines = []
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                if ava_process.poll() is not None:
                    break
                
                line = ava_process.stdout.readline()
                if line:
                    clean_line = line.strip()
                    collected_lines.append(clean_line)
                    logger.info(f"📥 AVA DIRECTO: {clean_line}")
                    
                    # Buscar respuesta
                    if "🧠 LLM Response:" in clean_line:
                        response_part = clean_line.split("🧠 LLM Response:", 1)[1].strip()
                        return jsonify({
                            'success': True,
                            'response': response_part,
                            'image_generated': False,
                            'status': 'direct_success',
                            'lines_collected': len(collected_lines),
                            'timestamp': datetime.now().isoformat()
                        })
                    elif "🤖 Ava:" in clean_line:
                        response_part = clean_line.split("🤖 Ava:", 1)[1].strip()
                        return jsonify({
                            'success': True,
                            'response': response_part,
                            'image_generated': False,
                            'status': 'direct_success_alt',
                            'lines_collected': len(collected_lines),
                            'timestamp': datetime.now().isoformat()
                        })
                else:
                    time.sleep(0.1)
            
            return jsonify({
                'success': False,
                'response': 'Timeout esperando respuesta de AVA',
                'status': 'timeout',
                'lines_collected': len(collected_lines),
                'all_lines': collected_lines[-10:]  # Últimas 10 líneas
            })
            
        except Exception as e:
            logger.error(f"❌ Error comunicando con AVA: {e}")
            return jsonify({
                'success': False,
                'response': f'Error de comunicación: {str(e)}',
                'status': 'communication_error'
            })
            
    except Exception as e:
        logger.error(f"❌ Error en test AVA directo: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

