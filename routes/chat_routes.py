from flask import Blueprint, request, jsonify, send_file
from datetime import datetime
import subprocess
import logging
import time
import os
import sys
import re
from pathlib import Path

# Configurar Blueprint
chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

# Variables globales
ava_process = None
ava_bot_path = None

def find_ava_script():
    """Encuentra el script de AVA en la ruta correcta"""
    base_path = Path(__file__).parent.parent
    
    print("🔍 BÚSQUEDA DE ava_bot.py:")
    print(f"📁 Base path: {base_path}")
    
    # ✅ RUTA EXACTA CONFIRMADA
    script_path = base_path / 'llmpagina' / 'ava_bot' / 'ava_bot.py'
    
    print(f"🎯 Ruta exacta: {script_path}")
    print(f"   Existe: {'✅' if script_path.exists() else '❌'}")
    
    if script_path.exists():
        print(f"   Tamaño: {script_path.stat().st_size} bytes")
        logger.info(f"✅ Script AVA encontrado: {script_path}")
        return script_path.parent, script_path
    else:
        # ✅ BÚSQUEDA ALTERNATIVA SI NO ESTÁ EN LA RUTA PRINCIPAL
        alternative_locations = [
            base_path / 'ava_bot' / 'ava_bot.py',
            base_path / 'ava_bot.py'
        ]
        
        print("🔍 Búsqueda en ubicaciones alternativas:")
        for alt_path in alternative_locations:
            print(f"   {alt_path}: {'✅' if alt_path.exists() else '❌'}")
            if alt_path.exists():
                return alt_path.parent, alt_path
    
    print("❌ Script ava_bot.py no encontrado")
    logger.error("❌ Script ava_bot.py no encontrado")
    return None, None

def get_python_executable():
    """Obtiene Python del venv"""
    venv_python = Path(__file__).parent.parent / 'venv' / 'Scripts' / 'python.exe'
    return str(venv_python) if venv_python.exists() else sys.executable

def start_ava():
    """Inicia AVA con diagnóstico mejorado"""
    global ava_process, ava_bot_path
    
    try:
        print("🔍 DIAGNÓSTICO PARA llmpagina/ava_bot/ava_bot.py:")
        print("=" * 60)
        
        # Paso 1: Encontrar script
        ava_bot_path, script_path = find_ava_script()
        if not script_path:
            print("❌ FALLO: ava_bot.py no encontrado en llmpagina/ava_bot/")
            return False
        
        print(f"✅ Script encontrado: {script_path}")
        
        # Paso 2: Verificar Python
        python_exe = get_python_executable()
        if not Path(python_exe).exists():
            print(f"❌ FALLO: Python no existe: {python_exe}")
            return False
        
        print(f"✅ Python verificado: {python_exe}")
        
        # Paso 3: Verificar API key
        groq_key = os.environ.get('GROQ_API_KEY')
        if not groq_key:
            print("❌ FALLO: GROQ_API_KEY no configurada")
            return False
        
        print(f"✅ GROQ_API_KEY encontrada: {groq_key[:10]}...")
        
        # Paso 4: Terminar proceso anterior
        if ava_process and ava_process.poll() is None:
            print("🔄 Terminando proceso anterior...")
            ava_process.terminate()
            try:
                ava_process.wait(timeout=5)
                print("✅ Proceso anterior terminado")
            except subprocess.TimeoutExpired:
                ava_process.kill()
                print("⚠️ Proceso anterior forzado a terminar")
        
        # Paso 5: Configurar entorno
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONPATH'] = str(ava_bot_path)
        
        # Paso 6: Iniciar proceso
        print("\n🚀 INICIANDO ava_bot.py...")
        
        ava_process = subprocess.Popen(
            [str(python_exe), str(script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=0,
            cwd=str(ava_bot_path),
            env=env
        )
        
        print(f"✅ Proceso iniciado con PID: {ava_process.pid}")
        
        # Paso 7: Monitoreo de inicialización
        print("\n⏳ MONITOREANDO INICIALIZACIÓN...")
        start_time = time.time()
        initialization_timeout = 45
        
        while time.time() - start_time < initialization_timeout:
            if ava_process.poll() is not None:
                stderr_output = ava_process.stderr.read()
                stdout_output = ava_process.stdout.read()
                
                print(f"\n❌ PROCESO TERMINÓ PREMATURAMENTE:")
                print(f"   Código de salida: {ava_process.returncode}")
                
                if stderr_output:
                    print(f"   STDERR: {stderr_output}")
                
                if stdout_output:
                    print(f"   STDOUT: {stdout_output}")
                
                return False
            
            try:
                line = ava_process.stdout.readline()
                if line:
                    clean_line = line.strip()
                    if clean_line:
                        print(f"📋 ava_bot.py: {clean_line}")
                        
                        # Detectar inicialización exitosa
                        success_markers = [
                            "🎯 SISTEMA AVA INICIALIZADO",
                            "💬 ¡Empecemos a conversar!",
                            "✅ Sistema listo",
                            "💬 Escribe tu mensaje:"
                        ]
                        
                        if any(marker in clean_line for marker in success_markers):
                            print("✅ ava_bot.py iniciado correctamente!")
                            return True
                        
                        # Detectar errores críticos
                        error_markers = [
                            "❌ Error:",
                            "GROQ_API_KEY no encontrada", 
                            "FileNotFoundError",
                            "ModuleNotFoundError",
                            "ImportError"
                        ]
                        
                        if any(error in clean_line for error in error_markers):
                            print(f"❌ ERROR CRÍTICO: {clean_line}")
                            return False
                            
            except Exception as e:
                print(f"⚠️ Error leyendo stdout: {e}")
            
            time.sleep(0.5)
        
        # Timeout
        print(f"\n⏰ TIMEOUT ({initialization_timeout}s)")
        if ava_process.poll() is None:
            print("⚠️ Proceso aún activo - asumiendo éxito")
            return True
        else:
            print("❌ Proceso terminó durante timeout")
            return False
            
    except Exception as e:
        print(f"\n💥 EXCEPCIÓN EN start_ava(): {e}")
        import traceback
        traceback.print_exc()
        return False

def detect_image_generation(lines):
    """Detecta generación de imagen - VERSIÓN SIMPLE"""
    try:
        for line in lines:
            # Patrones simples y efectivos
            image_patterns = [
                r'imagen guardada en:?\s*([a-zA-Z0-9_\-]+\.png)',
                r'imagen generada:?\s*([a-zA-Z0-9_\-]+\.png)',
                r'filepath[:\s]*.*?([a-zA-Z0-9_\-]+\.png)',
                r'guardada en.*?([a-zA-Z0-9_\-]+\.png)',
                r'saved.*?([a-zA-Z0-9_\-]+\.png)',
                r'ava_generated_\d{8}_\d{6}\.png'
            ]
            
            for pattern in image_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    filename = match.group(1)
                    logger.info(f"🖼️ Imagen detectada con patrón exitoso: {filename}")
                    return {
                        'filename': filename,
                        'path': line,
                        'detected_pattern': pattern
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error detectando imagen: {e}")
        return None

def send_to_ava(message):
    """Envía mensaje a ava_bot.py - VERSIÓN SIMPLE"""
    global ava_process
    
    if not ava_process or ava_process.poll() is not None:
        logger.error("❌ ava_bot.py no disponible")
        return "AVA no está disponible. Presiona 'Reiniciar AVA'."
    
    try:
        logger.info(f"📤 Enviando a ava_bot.py: {message[:50]}...")
        
        # Enviar mensaje
        ava_process.stdin.write(f"{message}\n")
        ava_process.stdin.flush()
        
        # Variables de captura
        response_parts = []
        all_lines = []
        ava_response_started = False
        
        logger.debug("🔍 Esperando respuesta...")
        
        while True:
            if ava_process.poll() is not None:
                logger.warning("⚠️ Proceso ava_bot.py terminó")
                break
            
            try:
                line = ava_process.stdout.readline()
                if line:
                    clean_line = line.strip()
                    all_lines.append(clean_line)
                    
                    # Detectar fin por marcador
                    if clean_line == "🔚 AVA_RESPONSE_END":
                        logger.debug("🔚 FIN DETECTADO")
                        break
                    
                    # Detectar inicio de respuesta
                    if clean_line.startswith("🤖 Ava: "):
                        ava_response_started = True
                        content = clean_line[7:].strip()
                        if content:
                            response_parts.append(content)
                        continue
                    
                    # Capturar contenido
                    if ava_response_started:
                        # Ignorar logs
                        if any(keyword in clean_line for keyword in [
                            "INFO:httpx:", "INFO:mcp_client:", "INFO:__main__:",
                            "WARNING:", "DEBUG:", "ERROR:", "💬 Mensaje agregado",
                            "HTTP Request:", "🔍 DEBUG:", "📤", "📥", "🎯", "⏳",
                            "✅ LLM respondió", "🔄 Ava está procesando"
                        ]):
                            continue
                        
                        response_parts.append(clean_line)
                
                else:
                    time.sleep(0.01)
                    
            except Exception as e:
                logger.debug(f"⚠️ Error leyendo línea: {e}")
                continue
        
        # Construir respuesta final
        if response_parts:
            while response_parts and response_parts[-1] == "":
                response_parts.pop()
            
            full_response = "\n".join(response_parts).strip()
            logger.info(f"✅ Respuesta capturada: {len(full_response)} chars, {len(response_parts)} líneas")
            
            # Buscar imágenes
            image_info = detect_image_generation(all_lines)
            
            if image_info:
                logger.info(f"🖼️ Imagen detectada: {image_info['filename']}")
                return {
                    'text': full_response,
                    'image_generated': True,
                    'image_filename': image_info['filename'],
                    'image_url': f"/api/chat/image/{image_info['filename']}"
                }
            else:
                logger.info("📝 No se detectaron imágenes")
                return full_response
        
        logger.warning("❌ No se capturó respuesta válida")
        return "No se recibió respuesta válida de AVA."
        
    except Exception as e:
        logger.error(f"❌ Error comunicando con ava_bot.py: {e}")
        return f"Error de comunicación: {str(e)}"

def send_to_ava_unlimited(message):
    """Versión ilimitada para mensajes largos"""
    global ava_process
    
    if not ava_process or ava_process.poll() is not None:
        logger.error("❌ ava_bot.py no disponible")
        return "AVA no está disponible."
    
    try:
        logger.info(f"📤 Enviando (ilimitado): {message[:50]}...")
        
        ava_process.stdin.write(f"{message}\n")
        ava_process.stdin.flush()
        
        response_parts = []
        all_lines = []
        ava_response_started = False
        start_time = time.time()
        timeout = 120
        
        while time.time() - start_time < timeout:
            if ava_process.poll() is not None:
                break
            
            try:
                line = ava_process.stdout.readline()
                if line:
                    clean_line = line.strip()
                    all_lines.append(clean_line)
                    
                    if clean_line == "🔚 AVA_RESPONSE_END":
                        break
                    
                    if clean_line.startswith("🤖 Ava: "):
                        ava_response_started = True
                        content = clean_line[7:].strip()
                        if content:
                            response_parts.append(content)
                        continue
                    
                    if ava_response_started:
                        if any(keyword in clean_line for keyword in [
                            "INFO:", "WARNING:", "DEBUG:", "ERROR:", "💬", "📤", "📥"
                        ]):
                            continue
                        response_parts.append(clean_line)
                
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                continue
        
        if response_parts:
            full_response = "\n".join(response_parts).strip()
            image_info = detect_image_generation(all_lines)
            
            if image_info:
                return {
                    'text': full_response,
                    'image_generated': True,
                    'image_filename': image_info['filename'],
                    'image_url': f"/api/chat/image/{image_info['filename']}"
                }
            return full_response
        
        return "No se recibió respuesta válida."
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return f"Error: {str(e)}"

# ============================================================================
# ENDPOINTS DE LA API - SOLO UNA DEFINICIÓN DE CADA UNO
# ============================================================================

@chat_bp.route('/api/chat/status', methods=['GET'])
def chat_status():
    """Estado del chat AVA"""
    global ava_process
    
    is_running = ava_process is not None and ava_process.poll() is None
    
    return jsonify({
        'ava_status': 'running' if is_running else 'stopped',
        'timestamp': datetime.now().isoformat(),
        'process_id': ava_process.pid if is_running else None,
        'script': 'ava_bot.py'
    })

@chat_bp.route('/api/chat/message', methods=['POST'])
def chat_message():
    """Endpoint principal"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        unlimited_mode = data.get('unlimited', False)
        
        if not message:
            return jsonify({'success': False, 'response': 'Mensaje vacío'}), 400
        
        logger.info(f"📤 Mensaje recibido: {message[:100]}...")
        
        # Verificar ava_bot.py
        global ava_process
        if not ava_process or ava_process.poll() is None:
            logger.info("🚀 Iniciando ava_bot.py...")
            if not start_ava():
                return jsonify({
                    'success': False, 
                    'response': 'Error iniciando AVA.'
                }), 500
        
        # Obtener respuesta
        if unlimited_mode:
            response = send_to_ava_unlimited(message)
        else:
            response = send_to_ava(message)
        
        # Procesar respuesta según tipo
        if isinstance(response, dict) and response.get('image_generated'):
            logger.info(f"🖼️ Respuesta con imagen: {response.get('image_filename')}")
            return jsonify({
                'success': True,
                'response': response.get('text', ''),
                'image_generated': True,
                'image_url': response.get('image_url'),
                'image_filename': response.get('image_filename'),
                'timestamp': datetime.now().isoformat(),
                'source': 'ava_bot.py'
            })
        else:
            logger.info("📝 Respuesta solo texto")
            return jsonify({
                'success': True,
                'response': str(response),
                'image_generated': False,
                'timestamp': datetime.now().isoformat(),
                'source': 'ava_bot.py'
            })
        
    except Exception as e:
        logger.error(f"❌ Error en endpoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'response': 'Error procesando mensaje'
        }), 500

@chat_bp.route('/api/chat/image/<path:image_path>', methods=['GET'])
def get_image(image_path):
    """Servir imágenes - VERSIÓN ACTUALIZADA"""
    try:
        logger.info(f"📷 Solicitando imagen: {image_path}")
        
        base_path = Path(__file__).parent.parent
        
        # 🔥 AGREGAR uploaded images COMO PRIMERA PRIORIDAD
        search_locations = [
            # Prioridad 1: Imágenes subidas por usuarios
            ('uploaded_images', base_path / 'llmpagina' / 'ava_bot' / 'uploaded images' / image_path),
            # Prioridad 2: Imágenes almacenadas por herramientas
            ('stored_images', base_path / 'llmpagina' / 'ava_bot' / 'tools' / 'adapters' / 'stored_images' / image_path),
            # Prioridad 3: Imágenes generadas
            ('generated_images', base_path / 'generated_images' / image_path),
            ('ava_generated', base_path / 'llmpagina' / 'ava_bot' / 'generated_images' / image_path),
        ]
        
        for location_name, location_path in search_locations:
            if location_path.exists():
                logger.info(f"✅ Imagen encontrada en {location_name}: {location_path}")
                
                # Detectar el tipo MIME correcto
                mime_type = 'image/png'  # Default
                if image_path.lower().endswith(('.jpg', '.jpeg')):
                    mime_type = 'image/jpeg'
                elif image_path.lower().endswith('.png'):
                    mime_type = 'image/png'
                elif image_path.lower().endswith('.gif'):
                    mime_type = 'image/gif'
                elif image_path.lower().endswith('.webp'):
                    mime_type = 'image/webp'
                
                return send_file(str(location_path), mimetype=mime_type)
        
        logger.error(f"❌ Imagen no encontrada en ninguna ubicación: {image_path}")
        logger.info("🔍 Ubicaciones buscadas:")
        for location_name, location_path in search_locations:
            logger.info(f"   {location_name}: {location_path} ({'✅' if location_path.exists() else '❌'})")
        
        return jsonify({'error': f'Imagen no encontrada: {image_path}'}), 404
        
    except Exception as e:
        logger.error(f"❌ Error enviando imagen: {e}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/restart', methods=['POST'])
def restart_ava():
    """Reiniciar AVA manualmente"""
    try:
        logger.info("🔄 Reiniciando AVA...")
        
        global ava_process
        if ava_process:
            ava_process.terminate()
            ava_process = None
        
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

@chat_bp.route('/api/chat/debug/images', methods=['GET'])
def debug_images():
    """Debug específico para imágenes"""
    try:
        base_path = Path(__file__).parent.parent
        debug_info = {
            'timestamp': datetime.now().isoformat(),
            'locations': [],
            'recent_images': []
        }
        
        locations = [
            ('stored_images', base_path / 'llmpagina' / 'ava_bot' / 'tools' / 'adapters' / 'stored_images'),
            ('generated_images', base_path / 'generated_images'),
            ('ava_generated', base_path / 'llmpagina' / 'ava_bot' / 'generated_images'),
        ]
        
        for name, path in locations:
            location_info = {
                'name': name,
                'path': str(path),
                'exists': path.exists(),
                'images': []
            }
            
            if path.exists():
                images = list(path.glob('*.png'))
                images.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                for img in images[:10]:
                    location_info['images'].append({
                        'filename': img.name,
                        'size': img.stat().st_size,
                        'modified': datetime.fromtimestamp(img.stat().st_mtime).isoformat(),
                        'url': f'/api/chat/image/{img.name}'
                    })
                    
                    debug_info['recent_images'].append({
                        'filename': img.name,
                        'location': name,
                        'url': f'/api/chat/image/{img.name}',
                        'modified': datetime.fromtimestamp(img.stat().st_mtime).isoformat()
                    })
            
            debug_info['locations'].append(location_info)
        
        debug_info['recent_images'].sort(key=lambda x: x['modified'], reverse=True)
        debug_info['recent_images'] = debug_info['recent_images'][:20]
        
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"❌ Error en debug de imágenes: {e}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/test/image', methods=['POST'])
def test_image_response():
    """Test específico para respuestas con imágenes"""
    try:
        test_response = {
            'success': True,
            'response': 'He generado una imagen de prueba para ti.',
            'image_generated': True,
            'image_filename': 'test_image.png',
            'image_url': '/api/chat/image/test_image.png',
            'timestamp': datetime.now().isoformat(),
            'test_mode': True
        }
        
        logger.info(f"🧪 TEST: Respuesta simulada con imagen: {test_response}")
        return jsonify(test_response)
        
    except Exception as e:
        logger.error(f"❌ Error en test de imagen: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/chat/image-analysis', methods=['POST'])
def analyze_image():
    """Endpoint para análisis de imágenes - RUTA ESTRICTA"""
    try:
        logger.info("📷 === INICIO ANÁLISIS DE IMAGEN ===")
        
        # Verificar que se envió una imagen
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'response': 'No se recibió ninguna imagen'
            }), 400
        
        file = request.files['image']
        message = request.form.get('message', 'Analiza esta imagen que acabo de subir')
        unlimited = request.form.get('unlimited', 'false').lower() == 'true'
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'response': 'Archivo vacío'
            }), 400
        
        # 🔥 OBTENER TAMAÑO DEL ARCHIVO DE FORMA SEGURA
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        logger.info(f"📋 Procesando imagen: {file.filename} ({file.content_type}, {file_size} bytes)")
        
        # 🔥 PASO 1: GUARDAR EN LA RUTA EXACTA QUE YA EXISTE
        import uuid
        import os
        
        file_extension = os.path.splitext(file.filename)[1].lower() or '.png'
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"user_upload_{timestamp}_{uuid.uuid4().hex[:8]}{file_extension}"
        
        # 🔥 RUTA EXACTA Y ESTRICTA - LA QUE YA ESTÁ FUNCIONANDO
        base_path = Path(__file__).parent.parent
        uploaded_images_dir = base_path / 'llmpagina' / 'ava_bot' / 'uploaded images'
        permanent_file_path = uploaded_images_dir / unique_filename
        
        # Guardar el archivo
        file.save(str(permanent_file_path))
        
        # Verificar que se guardó
        if not permanent_file_path.exists():
            return jsonify({'success': False, 'response': 'Error guardando imagen'}), 500
        
        actual_file_size = permanent_file_path.stat().st_size
        logger.info(f"💾 Imagen guardada: {permanent_file_path}")
        logger.info(f"📏 Tamaño: {actual_file_size} bytes")
        
        # 🔥 PASO 2: USAR LA RUTA EXACTA QUE AVA NECESITA
        # Basándose en las imágenes existentes en el attachment:
        # user_upload_20250604_221642_df370cd7.png
        # user_upload_20250604_222416_24f4459d.png
        
        # AVA trabaja desde: c:\Users\h\Downloads\pagina ava\llmpagina\ava_bot\
        # Las imágenes están en: c:\Users\h\Downloads\pagina ava\llmpagina\ava_bot\uploaded images\
        # Por lo tanto, la ruta relativa es: "uploaded images/filename.png"
        
        ava_bot_dir = base_path / 'llmpagina' / 'ava_bot'
        relative_path_for_ava = f"uploaded images/{unique_filename}"
        
        # 🔥 VERIFICACIÓN ESTRICTA DE RUTAS
        logger.info("🔍 === VERIFICACIÓN ESTRICTA DE RUTAS ===")
        logger.info(f"📁 Directorio AVA: {ava_bot_dir}")
        logger.info(f"📁 Directorio imágenes: {uploaded_images_dir}")
        logger.info(f"📄 Archivo guardado: {permanent_file_path}")
        logger.info(f"📄 Archivo existe: {'✅ SÍ' if permanent_file_path.exists() else '❌ NO'}")
        logger.info(f"🎯 Ruta para AVA: {relative_path_for_ava}")
        
        # Verificar desde perspectiva de AVA
        ava_perspective_file = ava_bot_dir / relative_path_for_ava
        logger.info(f"🎯 Ruta completa AVA: {ava_perspective_file}")
        logger.info(f"🎯 AVA puede ver archivo: {'✅ SÍ' if ava_perspective_file.exists() else '❌ NO'}")
        
        # 🔥 PASO 3: MENSAJE PARA AVA CON RUTA EXACTA
        ava_message = f'mira esta imagen "uploaded images/{unique_filename}"'
        
        logger.info("📤 === MENSAJE PARA AVA ===")
        logger.info(f"Ruta enviada: '{relative_path_for_ava}'")
        logger.info(f"Longitud mensaje: {len(ava_message)} caracteres")
        
        # 🔥 PASO 4: VERIFICAR AVA DISPONIBLE
        global ava_process
        if not ava_process or ava_process.poll() is not None:
            logger.info("🚀 Iniciando AVA...")
            if not start_ava():
                return jsonify({
                    'success': False,
                    'response': 'Error iniciando AVA'
                }), 500
            time.sleep(3)
        
        # 🔥 PASO 5: ENVIAR A AVA
        logger.info("📤 Enviando a AVA...")
        
        try:
            if unlimited:
                response = send_to_ava_unlimited(ava_message)
            else:
                response = send_to_ava(ava_message)
            
            logger.info(f"📥 Respuesta de AVA: {str(response)[:150]}...")
            
        except Exception as comm_error:
            logger.error(f"❌ Error comunicación: {comm_error}")
            return jsonify({
                'success': False,
                'response': f'Error comunicación AVA: {str(comm_error)}'
            }), 500
        
        # 🔥 PASO 6: PROCESAR RESPUESTA
        if isinstance(response, dict) and response.get('image_generated'):
            logger.info(f"🖼️ AVA generó imagen: {response.get('image_filename')}")
            return jsonify({
                'success': True,
                'response': response.get('text', 'Análisis completado con imagen'),
                'image_generated': True,
                'image_url': response.get('image_url'),
                'image_filename': response.get('image_filename'),
                'user_image_path': str(permanent_file_path),
                'user_image_filename': unique_filename,
                'user_image_relative_path': relative_path_for_ava,
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'image_with_generated_response'
            })
        else:
            response_text = str(response) if response else "No se pudo analizar la imagen"
            logger.info(f"📝 Respuesta texto: {len(response_text)} caracteres")
            
            return jsonify({
                'success': True,
                'response': response_text,
                'image_generated': False,
                'user_image_path': str(permanent_file_path),
                'user_image_filename': unique_filename,
                'user_image_relative_path': relative_path_for_ava,
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'image_text_analysis'
            })
        
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'response': f'Error procesando imagen: {str(e)}',
            'error_type': 'critical_error',
            'timestamp': datetime.now().isoformat()
        }), 500

