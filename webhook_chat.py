import sys
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS, cross_origin
import importlib.util
from werkzeug.utils import secure_filename
import traceback
import json
import uuid

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

# ✅ CONFIGURACIÓN DE DIRECTORIOS (igual que webhook_server.py)
BASE_DIR = Path(r"c:\Users\h\Downloads\pagina ava")
AVA_SHARED_DIR = BASE_DIR / "ava_bot" / "shared_files"
GENERATED_IMAGES_DIR = BASE_DIR / "ava_bot" / "generated_images"
CHAT_UPLOADS_DIR = BASE_DIR / "chat_uploads"
CHAT_LOGS_DIR = BASE_DIR / "chat_logs"

def create_directories():
    """Crear carpetas necesarias"""
    for directory in [AVA_SHARED_DIR, GENERATED_IMAGES_DIR, CHAT_UPLOADS_DIR, CHAT_LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

create_directories()

print(f"💬 Webhook CHAT con AgenteAVA iniciado")
print(f"🤖 Directorio AVA: {BASE_DIR / 'ava_bot'}")
print(f"📁 Directorio uploads: {CHAT_UPLOADS_DIR}")
print(f"🖼️ Directorio imágenes: {GENERATED_IMAGES_DIR}")

# ✅ FUNCIÓN CORREGIDA PARA IMPORTAR AVA (usando la lógica del webhook_server.py)
def has_generated_new_image(time_before):
    """Validación simple de imagen generada"""
    if not GENERATED_IMAGES_DIR.exists():
        return None
    
    current_time = datetime.now().timestamp()
    
    for img in GENERATED_IMAGES_DIR.glob('*.png'):
        file_time = img.stat().st_mtime
        
        # Solo imágenes generadas después de la llamada y en los últimos 10 segundos
        if file_time > time_before and (current_time - file_time) < 10:
            return f"http://localhost:5001/images/{img.name}"
    
    return None

def create_fresh_ava_instance():
    """Crear una nueva instancia de AVA - MÉTODO CORREGIDO"""
    try:
        print("🔄 Creando instancia de AgenteAVA...")
        
        # ✅ LIMPIAR MÓDULOS PREVIOS (igual que webhook_server.py)
        modules_to_remove = [name for name in sys.modules.keys() if 'ava_graph_bot' in name]
        for module_name in modules_to_remove:
            del sys.modules[module_name]
        
        # ✅ AGREGAR EL DIRECTORIO AVA_BOT AL PATH DE PYTHON
        ava_bot_dir = str(BASE_DIR / "ava_bot")
        if ava_bot_dir not in sys.path:
            sys.path.insert(0, ava_bot_dir)
            print(f"📁 Agregado al PATH: {ava_bot_dir}")
        
        # ✅ CAMBIAR DIRECTORIO DE TRABAJO (igual que webhook_server.py)
        original_cwd = os.getcwd()
        os.chdir(ava_bot_dir)
        print(f"📂 Cambiado a directorio: {ava_bot_dir}")
        
        try:
            # ✅ IMPORTAR AVA (igual que webhook_server.py)
            ava_path = BASE_DIR / "ava_bot" / "ava_graph_bot.py"
            if not ava_path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {ava_path}")
            
            spec = importlib.util.spec_from_file_location("ava_graph_bot", ava_path)
            ava_module = importlib.util.module_from_spec(spec)
            
            print("🔧 Ejecutando módulo AgenteAVA...")
            spec.loader.exec_module(ava_module)
            
            print("✅ AgenteAVA cargado exitosamente")
            return ava_module.AvaGraphBot()
            
        finally:
            # ✅ RESTAURAR DIRECTORIO ORIGINAL
            os.chdir(original_cwd)
            print(f"📂 Restaurado directorio: {original_cwd}")
            
    except Exception as e:
        print(f"❌ ERROR CREANDO AVA: {e}")
        traceback.print_exc()
        return None

def log_conversation(session_id, user_message, ai_response, file_info=None):
    """Guardar conversación en logs"""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_message": user_message,
            "ai_response": ai_response,
            "file_info": file_info
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
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"❌ Error guardando log: {e}")

# ✅ ENDPOINT PRINCIPAL DE CHAT (usando la misma lógica que webhook_server.py)
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
@cross_origin()
def handle_chat():
    """Endpoint principal para chat con AgenteAVA - MÉTODO CORREGIDO"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        print(f"\n💬 CHAT REQUEST - {datetime.now().strftime('%H:%M:%S')}")
        print(f"Content-Type: {request.content_type}")
        
        # ✅ MANEJAR FORMDATA (archivos) - igual que webhook_server.py
        if request.content_type and 'multipart/form-data' in request.content_type:
            return handle_file_chat()
        
        # ✅ MANEJAR JSON (texto) - igual que webhook_server.py
        if request.content_type != 'application/json':
            return jsonify({'success': False, 'response': 'JSON requerido'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No se recibieron datos"}), 400
        
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', f'session_{uuid.uuid4().hex}')
        
        if not user_message:
            return jsonify({"success": False, "error": "Mensaje vacío"}), 400
        
        print(f"💭 MENSAJE: '{user_message}'")
        
        # ✅ MARCAR TIEMPO ANTES DE AVA (para detectar imágenes generadas)
        time_before_ava = datetime.now().timestamp()
        
        # ✅ CREAR INSTANCIA DE AVA
        ava_instance = create_fresh_ava_instance()
        if not ava_instance:
            return jsonify({
                'success': False, 
                'response': 'AgenteAVA no está disponible en este momento. Por favor, intenta más tarde.'
            }), 500
        
        # ✅ PROCESAR CON AGENTEAVA (igual que webhook_server.py)
        print("🤖 Procesando con AgenteAVA...")
        result = ava_instance.chat(user_message)
        print(f"✅ AVA RESPONDIÓ")
        
        # Extraer respuesta
        if isinstance(result, dict):
            response_text = result.get('message', result.get('response', str(result)))
        else:
            response_text = str(result)
        
        # ✅ VERIFICAR SI SE GENERÓ UNA IMAGEN
        generated_image_url = has_generated_new_image(time_before_ava)
        
        # Preparar respuesta
        response_data = {
            'success': True,
            'response': response_text,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        if generated_image_url:
            response_data['imageUrl'] = generated_image_url
            print(f"📸 CON IMAGEN: {generated_image_url}")
        else:
            print(f"📤 SIN IMAGEN")
        
        # Guardar en logs
        log_conversation(session_id, user_message, response_text)
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ ERROR EN CHAT: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'response': 'Error procesando mensaje. Por favor, intenta de nuevo.',
            'error': str(e)
        }), 500

def handle_file_chat():
    """Manejar chat con archivos usando AgenteAVA - MÉTODO CORREGIDO"""
    try:
        print(f"\n📁 FILE CHAT - {datetime.now().strftime('%H:%M:%S')}")
        
        user_message = request.form.get('message', '').strip()
        session_id = request.form.get('session_id', f'session_{uuid.uuid4().hex}')
        uploaded_file = request.files.get('file')
        
        if not uploaded_file:
            return jsonify({'success': False, 'response': 'Archivo requerido'}), 400
        
        # ✅ GUARDAR ARCHIVO EN SHARED_FILES (igual que webhook_server.py)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = uploaded_file.filename.split('.')[-1] if '.' in uploaded_file.filename else 'bin'
        filename = f"chat_upload_{timestamp}.{file_extension}"
        file_path = AVA_SHARED_DIR / filename
        uploaded_file.save(str(file_path))
        
        print(f"📁 Archivo guardado: {filename}")
        
        # ✅ CREAR MENSAJE PARA AVA (igual que webhook_server.py)
        time_before_ava = datetime.now().timestamp()
        
        if user_message:
            message_for_ava = f'Analiza el archivo: "{file_path}" - {user_message}'
        else:
            message_for_ava = f'Analiza el archivo: "{file_path}"'
        
        print(f"🤖 Enviando a AgenteAVA: {message_for_ava}")
        
        # ✅ PROCESAR CON AGENTEAVA
        ava_instance = create_fresh_ava_instance()
        if not ava_instance:
            return jsonify({
                'success': False, 
                'response': 'AgenteAVA no está disponible para procesar archivos.'
            }), 500
        
        result = ava_instance.chat(message_for_ava)
        print(f"✅ AVA PROCESÓ EL ARCHIVO")
        
        # Extraer respuesta
        if isinstance(result, dict):
            response_text = result.get('message', result.get('response', str(result)))
        else:
            response_text = str(result)
        
        # ✅ VERIFICAR IMAGEN GENERADA
        generated_image_url = has_generated_new_image(time_before_ava)
        uploaded_file_url = f"http://localhost:5001/uploads/{filename}"
        
        # Preparar respuesta
        response_data = {
            'success': True,
            'response': response_text,
            'session_id': session_id,
            'uploadedImageUrl': uploaded_file_url,
            'timestamp': datetime.now().isoformat()
        }
        
        if generated_image_url:
            response_data['imageUrl'] = generated_image_url
            print(f"📸 CON IMAGEN GENERADA: {generated_image_url}")
        else:
            print(f"📤 SIN IMAGEN GENERADA")
        
        # Guardar en logs
        file_info = {
            "filename": filename,
            "original_name": uploaded_file.filename,
            "file_type": file_extension,
            "file_size": os.path.getsize(file_path)
        }
        log_conversation(session_id, user_message or "Archivo subido", response_text, file_info)
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ ERROR EN FILE CHAT: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'response': 'Error procesando archivo.',
            'error': str(e)
        }), 500

# ✅ SERVIR ARCHIVOS (igual que webhook_server.py)
@app.route('/images/<filename>')
@cross_origin()
def serve_generated_image(filename):
    """Servir imágenes generadas por AgenteAVA"""
    try:
        return send_from_directory(GENERATED_IMAGES_DIR, filename)
    except Exception as e:
        print(f"❌ Error sirviendo imagen {filename}: {e}")
        return jsonify({"error": "Imagen no encontrada"}), 404

@app.route('/uploads/<filename>')
@cross_origin()
def serve_uploaded_file(filename):
    """Servir archivos subidos por usuarios"""
    try:
        return send_from_directory(AVA_SHARED_DIR, filename)
    except Exception as e:
        print(f"❌ Error sirviendo archivo {filename}: {e}")
        return jsonify({"error": "Archivo no encontrado"}), 404

# ✅ ENDPOINTS DE INFORMACIÓN Y DEBUG
@app.route('/health')
@cross_origin()
def health():
    """Estado del servicio de chat"""
    try:
        # Verificar si AgenteAVA está disponible
        ava_available = False
        error_msg = None
        try:
            test_ava = create_fresh_ava_instance()
            ava_available = test_ava is not None
        except Exception as e:
            error_msg = str(e)
        
        return jsonify({
            "service": "AgenteAVA Chat Service", 
            "status": "running",
            "port": 5001,
            "ava_available": ava_available,
            "ava_error": error_msg,
            "capabilities": [
                "text_chat_with_ava", 
                "file_upload_analysis", 
                "image_generation",
                "multimodal_processing"
            ],
            "directories": {
                "ava_bot_exists": (BASE_DIR / "ava_bot").exists(),
                "ava_graph_bot_exists": (BASE_DIR / "ava_bot" / "ava_graph_bot.py").exists(),
                "shared_files_exists": AVA_SHARED_DIR.exists(),
                "generated_images_exists": GENERATED_IMAGES_DIR.exists()
            },
            "path_info": {
                "base_dir": str(BASE_DIR),
                "ava_bot_in_path": str(BASE_DIR / "ava_bot") in sys.path
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "service": "AgenteAVA Chat Service",
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/chat/test')
@cross_origin()
def test_ava():
    """Probar conexión con AgenteAVA"""
    try:
        print("🧪 Probando conexión con AgenteAVA...")
        ava_instance = create_fresh_ava_instance()
        if ava_instance:
            result = ava_instance.chat("Hola, ¿estás funcionando?")
            return jsonify({
                "success": True,
                "ava_available": True,
                "test_response": str(result),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "ava_available": False,
                "error": "No se pudo crear instancia de AgenteAVA"
            }), 500
    except Exception as e:
        print(f"❌ Error en test: {e}")
        return jsonify({
            "success": False,
            "ava_available": False,
            "error": str(e)
        }), 500

@app.route('/api/chat/history/<session_id>')
@cross_origin()
def get_chat_history(session_id):
    """Obtener historial de chat"""
    try:
        today = datetime.now().strftime('%Y%m%d')
        log_file = CHAT_LOGS_DIR / f"chat_{today}.json"
        
        if not log_file.exists():
            return jsonify({"history": []})
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_logs = json.load(f)
        
        session_logs = [log for log in all_logs if log.get('session_id') == session_id]
        
        return jsonify({"history": session_logs})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 WEBHOOK DE CHAT CON AGENTEAVA - Puerto 5001")
    print("📡 Endpoints disponibles:")
    print("   POST /api/chat - Chat con AgenteAVA (texto y archivos)")
    print("   GET  /images/<filename> - Imágenes generadas por AVA")
    print("   GET  /uploads/<filename> - Archivos subidos")
    print("   GET  /api/chat/test - Probar conexión con AVA")
    print("   GET  /health - Estado del servicio")
    print("   GET  /api/chat/history/<session> - Historial")
    print(f"\n🤖 AgenteAVA: {(BASE_DIR / 'ava_bot' / 'ava_graph_bot.py').exists()}")
    print(f"📁 PATH incluye ava_bot: {str(BASE_DIR / 'ava_bot') in sys.path}")
    app.run(host='0.0.0.0', port=5001, debug=True)