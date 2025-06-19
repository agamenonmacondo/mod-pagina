import sys
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import importlib.util
from werkzeug.utils import secure_filename
import traceback
import json
import glob
import shutil


app = Flask(__name__)
CORS(app)

# Configuración de directorios
BASE_DIR = Path(__file__).parent
PUBLIC_DIR = BASE_DIR / "public"
PUBLIC_NEWS_DIR = PUBLIC_DIR / "news" 
PUBLIC_IMAGES_DIR = PUBLIC_DIR / "images"

# Crear directorios si no existen
PUBLIC_DIR.mkdir(exist_ok=True)
PUBLIC_NEWS_DIR.mkdir(exist_ok=True)
PUBLIC_IMAGES_DIR.mkdir(exist_ok=True)

# RUTAS Y CONFIGURACIÓN
BASE_DIR = Path(r"c:\Users\h\Downloads\pagina ava")
AVA_SHARED_DIR = BASE_DIR / "ava_bot" / "shared_files"
GENERATED_IMAGES_DIR = BASE_DIR / "ava_bot" / "generated_images"
NEWS_DIR = BASE_DIR / "ava_bot_news" / "generated_news"
PUBLIC_NEWS_DIR = BASE_DIR / "public" / "news"
PUBLIC_IMAGES_DIR = BASE_DIR / "public" / "images"

def create_directories():
    """Crear carpetas necesarias"""
    for directory in [AVA_SHARED_DIR, GENERATED_IMAGES_DIR, NEWS_DIR, PUBLIC_NEWS_DIR, PUBLIC_IMAGES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

create_directories()

def has_generated_new_image(time_before):
    """Validación simple de imagen generada"""
    if not GENERATED_IMAGES_DIR.exists():
        return None
    
    current_time = datetime.now().timestamp()
    
    for img in GENERATED_IMAGES_DIR.glob('*.png'):
        file_time = img.stat().st_mtime
        
        # Solo imágenes generadas después de la llamada y en los últimos 10 segundos
        if file_time > time_before and (current_time - file_time) < 10:
            return f"http://localhost:5000/webhook/generated-image/{img.name}"
    
    return None

def create_fresh_ava_instance():
    """Crear una nueva instancia de AVA"""
    try:
        # Limpiar módulos previos
        modules_to_remove = [name for name in sys.modules.keys() if 'ava_graph_bot' in name]
        for module_name in modules_to_remove:
            del sys.modules[module_name]
        
        # Cambiar directorio
        original_cwd = os.getcwd()
        ava_dir = str(BASE_DIR / "ava_bot")
        os.chdir(ava_dir)
        
        try:
            # Importar AVA
            ava_path = BASE_DIR / "ava_bot" / "ava_graph_bot.py"
            spec = importlib.util.spec_from_file_location("ava_graph_bot", ava_path)
            ava_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ava_module)
            
            return ava_module.AvaGraphBot()
            
        finally:
            os.chdir(original_cwd)
            
    except Exception as e:
        print(f"❌ ERROR CREANDO AVA: {e}")
        return None

def generate_daily_news():
    """Generar noticias diarias - versión corregida"""
    try:
        print("🚀 Iniciando generación de noticias...")
        
        # Verificar que existe el directorio de noticias
        news_module_dir = BASE_DIR / "ava_bot_news"
        if not news_module_dir.exists():
            print(f"❌ Directorio no encontrado: {news_module_dir}")
            return {"success": False, "error": "Directorio ava_bot_news no existe"}
        
        # Verificar que existe el archivo del módulo
        news_module_path = news_module_dir / "ava_graph_news.py"
        if not news_module_path.exists():
            print(f"❌ Archivo no encontrado: {news_module_path}")
            return {"success": False, "error": "ava_graph_news.py no existe"}
        
        # Agregar el directorio al path de Python
        import sys
        news_module_str = str(news_module_dir)
        if news_module_str not in sys.path:
            sys.path.insert(0, news_module_str)
        
        # Cambiar directorio temporalmente
        original_cwd = os.getcwd()
        os.chdir(str(news_module_dir))
        
        try:
            # Importar dinámicamente el módulo
            import importlib.util
            spec = importlib.util.spec_from_file_location("ava_graph_news", news_module_path)
            news_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(news_module)
            
            # Ejecutar la función de generación
            print("📰 Generando noticias...")
            results = news_module.generate_multiple_news(count=3)
            
            # Copiar archivos y crear índice
            copy_to_public_directory()
            create_news_index()
            
            print(f"✅ Generación completada: {len(results) if results else 0} noticias")
            
            return {
                "success": True,
                "generated_at": datetime.now().isoformat(),
                "news_count": len(results) if results else 0,
                "message": "Noticias generadas exitosamente"
            }
            
        finally:
            # Restaurar directorio original
            os.chdir(original_cwd)
            
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return {"success": False, "error": f"Error importando módulo: {str(e)}"}
    except Exception as e:
        print(f"❌ Error general: {e}")
        return {"success": False, "error": f"Error generando noticias: {str(e)}"}

def copy_to_public_directory():
    """Copiar archivos al directorio público"""
    try:
        # Copiar JSONs más recientes
        json_files = glob.glob(str(NEWS_DIR / "*.json"))
        recent_jsons = sorted(json_files, key=os.path.getctime, reverse=True)[:3]
        
        for json_file in recent_jsons:
            filename = os.path.basename(json_file)
            shutil.copy2(json_file, PUBLIC_NEWS_DIR / filename)
            print(f"📄 JSON copiado: {filename}")
        
        # Copiar imágenes más recientes desde generated_images
        image_files = glob.glob(str(GENERATED_IMAGES_DIR / "*.png"))
        recent_images = sorted(image_files, key=os.path.getctime, reverse=True)[:3]
        
        for image_file in recent_images:
            filename = os.path.basename(image_file)
            # Copiar a directorio público
            shutil.copy2(image_file, PUBLIC_IMAGES_DIR / filename)
            print(f"🖼️ Imagen copiada: {filename}")
            
        # También buscar imágenes con nombres específicos de noticias
        news_image_patterns = [
            "ava_generated_*.png",
            "news_*.png", 
            "generated_*.png"
        ]
        
        for pattern in news_image_patterns:
            pattern_files = glob.glob(str(GENERATED_IMAGES_DIR / pattern))
            for img_file in pattern_files:
                filename = os.path.basename(img_file)
                shutil.copy2(img_file, PUBLIC_IMAGES_DIR / filename) 
                print(f"🎯 Imagen específica copiada: {filename}")
                
    except Exception as e:
        print(f"❌ Error copiando archivos: {e}")

def create_news_index():
    """Crear índice de noticias con imágenes correctas"""
    try:
        json_files = glob.glob(str(PUBLIC_NEWS_DIR / "*.json"))
        news_index = []
        
        for json_file in sorted(json_files, reverse=True):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    news_data = json.load(f)
                
                # Buscar imagen correspondiente
                topic_key = news_data.get('topic_key', 'default')
                
                # Buscar imágenes disponibles
                possible_images = [
                    f"ava_generated_{topic_key}.png",
                    f"news_{topic_key}.png",
                    f"generated_{topic_key}.png",
                    "ava_generated_default.png"
                ]
                
                image_url = None
                for img_name in possible_images:
                    if (PUBLIC_IMAGES_DIR / img_name).exists():
                        image_url = f"/images/{img_name}"
                        break
                
                # Si no hay imagen específica, usar la más reciente
                if not image_url:
                    recent_imgs = sorted(PUBLIC_IMAGES_DIR.glob("*.png"), key=os.path.getctime, reverse=True)
                    if recent_imgs:
                        image_url = f"/images/{recent_imgs[0].name}"
                
                news_item = {
                    "id": os.path.basename(json_file).replace('.json', ''),
                    "topic": topic_key,
                    "generated_at": news_data.get('generated_at'),
                    "quality_score": news_data.get('quality_score', 1),
                    "content_length": news_data.get('content_length', 0),
                    "title": extract_title(news_data.get('content', '')),
                    "subtitle": extract_subtitle(news_data.get('content', '')),
                    "preview": extract_preview(news_data.get('content', '')),
                    "file_url": f"/news/{os.path.basename(json_file)}",
                    "image_url": image_url or "/images/default.png"  # Fallback
                }
                
                news_index.append(news_item)
                
            except Exception as e:
                print(f"❌ Error procesando {json_file}: {e}")
                continue
        
        index_data = {
            "generated_at": datetime.now().isoformat(),
            "total_news": len(news_index),
            "news": news_index
        }
        
        with open(PUBLIC_NEWS_DIR / "index.json", 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print(f"📋 Índice creado: {len(news_index)} noticias con imágenes")
        
    except Exception as e:
        print(f"❌ Error creando índice: {e}")

def extract_title(content):
    for line in content.split('\n'):
        if line.startswith('TÍTULO:'):
            return line.replace('TÍTULO:', '').strip()
    return "Sin título"

def extract_subtitle(content):
    for line in content.split('\n'):
        if line.startswith('SUBTÍTULO:'):
            return line.replace('SUBTÍTULO:', '').strip()
    return "Sin subtítulo"

def extract_preview(content):
    lines = content.split('\n')
    content_started = False
    content_lines = []
    
    for line in lines:
        if line.startswith('CONTENIDO:'):
            content_started = True
            continue
        if content_started and line.strip():
            if line.startswith(('DATOS_DE_BÚSQUEDA:', 'IMAGEN:', 'METADATA:')):
                break
            content_lines.append(line.strip())
    
    preview = ' '.join(content_lines)
    return preview[:200] + "..." if len(preview) > 200 else preview

@app.route('/webhook/chat', methods=['POST'])
def webhook_chat():
    """Webhook para texto"""
    try:
        print(f"\n💬 TEXTO - {datetime.now().strftime('%H:%M:%S')}")
        
        if request.content_type != 'application/json':
            return jsonify({'success': False, 'response': 'JSON requerido'}), 400
        
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        print(f"💬 MENSAJE: '{user_message}'")
        
        # Marcar tiempo antes de AVA
        time_before_ava = datetime.now().timestamp()
        
        # Crear AVA
        ava_instance = create_fresh_ava_instance()
        if not ava_instance:
            return jsonify({'success': False, 'response': 'AVA no disponible'}), 500
        
        # Procesar con AVA
        result = ava_instance.chat(user_message)
        print(f"✅ AVA RESPONDIÓ")
        
        if isinstance(result, dict):
            response_text = result.get('message', result.get('response', str(result)))
        else:
            response_text = str(result)
        
        # Verificar imagen nueva
        image_url = has_generated_new_image(time_before_ava)
        
        response_data = {
            'success': True,
            'response': response_text,
            'session_id': session_id
        }
        
        if image_url:
            response_data['imageUrl'] = image_url
            print(f"📤 CON IMAGEN")
        else:
            print(f"📤 SIN IMAGEN")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({'success': False, 'response': 'Error procesando'}), 500

@app.route('/webhook/image-upload', methods=['POST'])
def webhook_image():
    """Webhook para imágenes"""
    try:
        print(f"\n📸 IMAGEN - {datetime.now().strftime('%H:%M:%S')}")
        
        user_message = request.form.get('message', '')
        session_id = request.form.get('session_id', 'default')
        uploaded_file = request.files.get('file')
        
        if not uploaded_file:
            return jsonify({'success': False, 'response': 'Archivo requerido'}), 400
        
        # Guardar archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upload_{timestamp}.{uploaded_file.filename.split('.')[-1]}"
        file_path = AVA_SHARED_DIR / filename
        uploaded_file.save(str(file_path))
        
        # Procesar con AVA
        time_before_ava = datetime.now().timestamp()
        message_for_ava = f'Analiza la imagen: "{file_path}" - {user_message}'
        
        ava_instance = create_fresh_ava_instance()
        if not ava_instance:
            return jsonify({'success': False, 'response': 'AVA no disponible'}), 500
        
        result = ava_instance.chat(message_for_ava)
        print(f"✅ AVA RESPONDIÓ")
        
        if isinstance(result, dict):
            response_text = result.get('message', result.get('response', str(result)))
        else:
            response_text = str(result)
        
        # Verificar imagen generada
        generated_image_url = has_generated_new_image(time_before_ava)
        uploaded_image_url = f"http://localhost:5000/webhook/shared-file/{filename}"
        
        response_data = {
            'success': True,
            'response': response_text,
            'session_id': session_id,
            'uploadedImageUrl': uploaded_image_url
        }
        
        if generated_image_url:
            response_data['imageUrl'] = generated_image_url
            print(f"📤 CON IMAGEN GENERADA")
        else:
            print(f"📤 SIN IMAGEN GENERADA")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({'success': False, 'response': 'Error procesando imagen'}), 500

@app.route('/api/news', methods=['GET'])
def api_get_news():
    """API para obtener noticias"""
    try:
        print("📰 GET /api/news - Solicitud recibida")
        
        # Buscar archivos de noticias
        if not PUBLIC_NEWS_DIR.exists():
            PUBLIC_NEWS_DIR.mkdir(parents=True, exist_ok=True)
        
        news_files = [f for f in PUBLIC_NEWS_DIR.glob("*.json") if f.name != "index.json"]
        news_list = []
        
        print(f"📁 Encontrados {len(news_files)} archivos de noticias")
        
        # Si no hay archivos, crear datos de muestra
        if len(news_files) == 0:
            print("📝 No hay noticias, creando datos de muestra...")
            create_sample_news()
            news_files = [f for f in PUBLIC_NEWS_DIR.glob("*.json") if f.name != "index.json"]
        
        for news_file in sorted(news_files, reverse=True):
            try:
                with open(news_file, 'r', encoding='utf-8') as f:
                    news_data = json.load(f)
                
                content = news_data.get('content', '')
                lines = content.split('\n') if content else []
                
                title = "Noticia de IA"
                subtitle = "Generado por AgenteAVA"
                preview = content[:300] + "..." if len(content) > 300 else content
                
                # Parsear contenido estructurado
                for line in lines:
                    line = line.strip()
                    if line.startswith('TÍTULO:'):
                        title = line.replace('TÍTULO:', '').strip()
                    elif line.startswith('SUBTÍTULO:'):
                        subtitle = line.replace('SUBTÍTULO:', '').strip()
                    elif line.startswith('CONTENIDO:'):
                        content_text = line.replace('CONTENIDO:', '').strip()
                        preview = content_text[:300] + "..." if len(content_text) > 300 else content_text
                
                news_item = {
                    "id": news_data.get('id', news_file.stem),
                    "topic": news_data.get('topic_key', 'ai_news'),
                    "title": title,
                    "subtitle": subtitle,
                    "preview": preview,
                    "generated_at": news_data.get('generated_at', datetime.now().isoformat()),
                    "quality_score": news_data.get('quality_score', 1),
                    "content_length": len(content),
                    "image_url": "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=600&h=400",
                    "file_url": f"/news/{news_file.name}"
                }
                
                news_list.append(news_item)
                print(f"✅ Procesada: {title[:50]}...")
                
            except Exception as e:
                print(f"❌ Error procesando {news_file}: {e}")
                continue
        
        response_data = {
            "generated_at": datetime.now().isoformat(),
            "total_news": len(news_list),
            "news": news_list
        }
        
        print(f"📤 Enviando {len(news_list)} noticias")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error en /api/news: {e}")
        return jsonify({
            "generated_at": datetime.now().isoformat(),
            "total_news": 0,
            "news": [],
            "error": str(e)
        }), 500

# ✅ FUNCIÓN PARA CREAR NOTICIAS DE MUESTRA
def create_sample_news():
    """Crear noticias de muestra"""
    try:
        sample_data = [
            {
                "id": "sample_1",
                "topic_key": "openai_news", 
                "generated_at": datetime.now().isoformat(),
                "quality_score": 3,
                "content_length": 1200,
                "content": """TÍTULO: ChatGPT-4 Turbo revoluciona la IA conversacional
SUBTÍTULO: OpenAI presenta mejoras significativas en velocidad y precisión
CONTENIDO: OpenAI ha lanzado ChatGPT-4 Turbo, una versión mejorada que promete respuestas más rápidas y precisas. Esta nueva iteración incluye una ventana de contexto ampliada que permite conversaciones más largas y coherentes, manteniendo el hilo de la conversación durante sesiones extendidas."""
            },
            {
                "id": "sample_2",
                "topic_key": "google_ai",
                "generated_at": datetime.now().isoformat(),
                "quality_score": 2,
                "content_length": 1000,
                "content": """TÍTULO: Google Gemini Pro ahora disponible para desarrolladores
SUBTÍTULO: Nueva API abre posibilidades para integración empresarial
CONTENIDO: Google ha lanzado la API de Gemini Pro, permitiendo a los desarrolladores integrar las capacidades avanzadas de IA de Google en sus aplicaciones. Esta herramienta promete competir directamente con GPT-4 en tareas de procesamiento de lenguaje natural."""
            },
            {
                "id": "sample_3",
                "topic_key": "ai_ethics",
                "generated_at": datetime.now().isoformat(),
                "quality_score": 3,
                "content_length": 1500,
                "content": """TÍTULO: La ética en IA: nuevos marcos regulatorios en Europa
SUBTÍTULO: La Unión Europea establece directrices para el desarrollo responsable
CONTENIDO: La Unión Europea ha establecido nuevas directrices para el desarrollo ético de la inteligencia artificial, enfocándose en la transparencia, responsabilidad y protección de datos. Estas regulaciones impactarán significativamente cómo las empresas tecnológicas desarrollan y despliegan sus sistemas de IA."""
            }
        ]
        
        for news in sample_data:
            filename = f"{news['id']}.json"
            filepath = PUBLIC_NEWS_DIR / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(news, f, ensure_ascii=False, indent=2)
                
        print(f"✅ Creadas {len(sample_data)} noticias de muestra")
        return len(sample_data)
        
    except Exception as e:
        print(f"❌ Error creando noticias: {e}")
        return 0

# ✅ RUTA PARA CREAR DATOS DE MUESTRA MANUALMENTE
@app.route('/webhook/create-sample', methods=['GET'])
def create_sample_endpoint():
    """Crear datos de muestra manualmente"""
    try:
        count = create_sample_news()
        return jsonify({
            "success": True,
            "created": count,
            "message": f"Se crearon {count} noticias de muestra"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ✅ RUTA DE ESTADO
@app.route('/webhook/status', methods=['GET'])
def webhook_status():
    """Estado del webhook"""
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "directories": {
            "public_news_exists": PUBLIC_NEWS_DIR.exists(),
            "public_images_exists": PUBLIC_IMAGES_DIR.exists()
        },
        "file_counts": {
            "news_files": len(list(PUBLIC_NEWS_DIR.glob("*.json"))) if PUBLIC_NEWS_DIR.exists() else 0,
            "image_files": len(list(PUBLIC_IMAGES_DIR.glob("*.png"))) if PUBLIC_IMAGES_DIR.exists() else 0
        }
    })

# ✅ SERVIR ARCHIVOS DE NOTICIAS
@app.route('/news/<filename>')
def serve_news(filename):
    """Servir archivos de noticias"""
    try:
        return send_from_directory(PUBLIC_NEWS_DIR, filename)
    except:
        return jsonify({"error": "Archivo no encontrado"}), 404

if __name__ == '__main__':
    print("🚀 Iniciando AgenteAVA Webhook Server...")
    print("📍 Servidor disponible en: http://localhost:5000")
    print("📰 API de noticias: http://localhost:5000/api/news")
    print("🔍 Estado: http://localhost:5000/webhook/status")
    
    app.run(debug=True, host='0.0.0.0', port=5000)