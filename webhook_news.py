from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS, cross_origin
from pathlib import Path
import json
from datetime import datetime, timedelta
import os
import threading
import time
import subprocess
import sys

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

# Configuración
BASE_DIR = Path(__file__).parent
GENERATED_NEWS_DIR = BASE_DIR / "ava_bot_news" / "generated_news"
GENERATED_IMAGES_DIR = Path("c:/Users/h/Downloads/pagina ava/ava_bot/generated_images")

# Scripts path
NEWS_GENERATOR_SCRIPT = BASE_DIR / "ava_bot_news" / "ava_graph_news.py"

# Cache y estado
cached_news = []
cache_timestamp = None
auto_refresh_active = True

print(f"📰 Webhook NEWS con auto-generación iniciado")
print(f"📁 Directorio noticias: {GENERATED_NEWS_DIR}")
print(f"🖼️ Directorio imágenes: {GENERATED_IMAGES_DIR}")
print(f"🤖 Script generador: {NEWS_GENERATOR_SCRIPT}")

class AutoNewsManager:
    """Administrador que ejecuta el script ava_graph_news.py automáticamente"""
    
    def __init__(self):
        self.running = True
        self.last_check = None
        self.last_generation = None
        
    def log(self, message):
        """Log con timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    def get_last_news_timestamp(self):
        """Obtener timestamp de última noticia"""
        if not GENERATED_NEWS_DIR.exists():
            return None
            
        json_files = list(GENERATED_NEWS_DIR.glob("compiled_news_*.json"))
        if not json_files:
            return None
        
        archivo_reciente = max(json_files, key=lambda x: x.stat().st_mtime)
        
        try:
            with open(archivo_reciente, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            timestamp_collection = datos.get('collection_info', {}).get('generated_at')
            if timestamp_collection:
                return datetime.fromisoformat(timestamp_collection.replace('Z', '+00:00'))
        except:
            pass
        
        return None
    
    def needs_generation(self):
        """Verificar si necesita generar (24 horas)"""
        last_news = self.get_last_news_timestamp()
        
        if not last_news:
            return True, "No hay noticias previas"
        
        now = datetime.now()
        hours_passed = (now - last_news).total_seconds() / 3600
        
        if hours_passed >= 24:
            return True, f"Han pasado {hours_passed:.1f} horas"
        else:
            return False, f"Faltan {24 - hours_passed:.1f} horas"
    
    def execute_news_generator(self):
        """Ejecutar el script ava_graph_news.py directamente"""
        try:
            self.log("🚀 Ejecutando ava_graph_news.py...")
            
            # Ejecutar el script con input automático
            process = subprocess.Popen([
                'python', str(NEWS_GENERATOR_SCRIPT)
            ], 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            cwd=str(BASE_DIR / "ava_bot_news")
            )
            
            # Enviar comandos automáticos al script
            input_commands = "multiple\nquit\n"
            stdout, stderr = process.communicate(input=input_commands, timeout=600)
            
            if process.returncode == 0:
                self.log("✅ Script ejecutado exitosamente")
                self.log(f"📊 Output: {stdout[-200:]}")  # Últimas 200 chars
                self.last_generation = datetime.now()
                
                # Esperar a que se escriban los archivos
                time.sleep(3)
                
                # Actualizar cache
                actualizar_cache()
                
                return True
            else:
                self.log(f"❌ Error ejecutando script:")
                self.log(f"STDERR: {stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("❌ Timeout ejecutando script (>10 min)")
            process.kill()
            return False
        except Exception as e:
            self.log(f"❌ Error ejecutando script: {e}")
            return False
    
    def auto_check_loop(self):
        """Loop de verificación automática"""
        while self.running and auto_refresh_active:
            try:
                self.last_check = datetime.now()
                
                # Verificar si necesita generar
                needs, reason = self.needs_generation()
                self.log(f"🔍 Verificación: {reason}")
                
                if needs:
                    self.log("🚨 Ejecutando generación automática...")
                    self.execute_news_generator()
                
                # Actualizar cache cada verificación
                actualizar_cache()
                
                # Esperar 1 hora antes de la próxima verificación
                time.sleep(3600)
                
            except Exception as e:
                self.log(f"❌ Error en verificación automática: {e}")
                time.sleep(300)  # Esperar 5 minutos en caso de error
    
    def force_generation(self):
        """Forzar ejecución del script"""
        self.log("🔨 Ejecución forzada del script")
        return self.execute_news_generator()
    
    def get_status(self):
        """Obtener status completo"""
        last_news = self.get_last_news_timestamp()
        needs, reason = self.needs_generation()
        
        return {
            "manager_running": self.running,
            "script_path": str(NEWS_GENERATOR_SCRIPT),
            "script_exists": NEWS_GENERATOR_SCRIPT.exists(),
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_generation": self.last_generation.isoformat() if self.last_generation else None,
            "last_news_timestamp": last_news.isoformat() if last_news else None,
            "needs_generation": needs,
            "reason": reason
        }

# Instancia global del manager
news_manager = AutoNewsManager()

def encontrar_imagen_por_timestamp(timestamp_noticia, topic_key):
    """Buscar imagen por timestamp exacto"""
    if not GENERATED_IMAGES_DIR.exists():
        return None
        
    archivos_meta = list(GENERATED_IMAGES_DIR.glob("*_meta.json"))
    
    try:
        fecha_noticia = datetime.fromisoformat(timestamp_noticia.replace('Z', '+00:00'))
    except:
        return None
    
    mejor_match = None
    menor_diferencia = float('inf')
    
    for meta_file in archivos_meta:
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
            
            filename = meta_data.get('filename', '')
            generated_at = meta_data.get('generated_at', '')
            
            if not generated_at or not filename:
                continue
            
            fecha_imagen = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
            diferencia_segundos = abs((fecha_imagen - fecha_noticia).total_seconds())
            
            if diferencia_segundos < menor_diferencia and diferencia_segundos <= 7200:
                menor_diferencia = diferencia_segundos
                mejor_match = filename
        except:
            continue
    
    return mejor_match

def extraer_titulo_del_contenido(contenido):
    """Extraer título del contenido"""
    lineas = contenido.split('\n')
    
    for linea in lineas:
        linea = linea.strip()
        if linea.startswith('TÍTULO:'):
            return linea.replace('TÍTULO:', '').strip().strip('"')
        elif linea.startswith('# '):
            return linea.replace('# ', '').strip()
    
    for linea in lineas:
        linea = linea.strip()
        if len(linea) > 20 and not linea.startswith(('===', '###', 'FECHA:', 'FUENTES:')):
            return linea[:80] + "..." if len(linea) > 80 else linea
    
    return "Noticia de IA Generada"

def extraer_subtitulo_del_contenido(contenido):
    """Extraer subtítulo del contenido"""
    lineas = contenido.split('\n')
    
    for linea in lineas:
        linea = linea.strip()
        if linea.startswith('SUBTÍTULO:'):
            return linea.replace('SUBTÍTULO:', '').strip().strip('"')
    
    return "Generado por AgenteAVA con IA avanzada"

def crear_preview_inteligente(contenido):
    """Crear preview del contenido"""
    lineas = contenido.split('\n')
    
    for linea in lineas:
        linea = linea.strip()
        if (len(linea) > 100 and 
            not linea.startswith(('===', '###', 'TÍTULO:', 'SUBTÍTULO:', 'FECHA:', 'FUENTES:'))):
            return linea[:280] + "..." if len(linea) > 280 else linea
    
    return contenido.strip()[:300] + "..."

def cargar_noticias_optimizado():
    """Cargar noticias con detección de imágenes por timestamp"""
    if not GENERATED_NEWS_DIR.exists():
        return []
        
    json_files = list(GENERATED_NEWS_DIR.glob("compiled_news_*.json"))
    
    if not json_files:
        return []
    
    archivo_reciente = max(json_files, key=lambda x: x.stat().st_mtime)
    
    try:
        with open(archivo_reciente, 'r', encoding='utf-8') as f:
            datos_compilados = json.load(f)
    except:
        return []
    
    noticias_procesadas = []
    articulos = datos_compilados.get('news_articles', [])
    
    for articulo in articulos:
        contenido = articulo.get('content', '')
        titulo = extraer_titulo_del_contenido(contenido)
        subtitulo = extraer_subtitulo_del_contenido(contenido)
        
        timestamp_noticia = articulo.get('generated_at', '')
        topic_key = articulo.get('topic_key', 'ai_general')
        
        imagen_filename = encontrar_imagen_por_timestamp(timestamp_noticia, topic_key)
        imagen_url = f"http://localhost:5000/images/{imagen_filename}" if imagen_filename else None
        
        preview = crear_preview_inteligente(contenido)
        
        noticia_procesada = {
            "id": articulo.get('id'),
            "topic": topic_key,
            "title": titulo,
            "subtitle": subtitulo,
            "preview": preview,
            "full_content": contenido,
            "generated_at": timestamp_noticia,
            "quality_score": articulo.get('quality_score'),
            "content_length": articulo.get('content_length'),
            "image_url": imagen_url,
            "topic_name": articulo.get('topic_name')
        }
        
        noticias_procesadas.append(noticia_procesada)
    
    return noticias_procesadas

def actualizar_cache():
    """Actualizar cache de noticias"""
    global cached_news, cache_timestamp
    
    cached_news = cargar_noticias_optimizado()
    cache_timestamp = datetime.now()
    
    print(f"✅ Cache actualizado: {len(cached_news)} noticias")

# Endpoints
@app.route('/api/news', methods=['GET'])
@cross_origin()
def get_news():
    """Obtener noticias con cache"""
    global cached_news, cache_timestamp
    
    if not cached_news or not cache_timestamp or (datetime.now() - cache_timestamp).seconds > 3600:
        actualizar_cache()
    
    return jsonify({
        "service": "AVA News Service",
        "generated_at": datetime.now().isoformat(),
        "total_news": len(cached_news),
        "news": cached_news,
        "cache_timestamp": cache_timestamp.isoformat() if cache_timestamp else None
    })

@app.route('/api/news/refresh', methods=['GET'])
@cross_origin()
def force_refresh():
    """Forzar actualización del cache"""
    actualizar_cache()
    return jsonify({
        "status": "success",
        "message": "Cache actualizado",
        "timestamp": datetime.now().isoformat(),
        "total_news": len(cached_news)
    })

@app.route('/api/news/status', methods=['GET'])
@cross_origin()
def get_news_status():
    """Status completo del sistema"""
    manager_status = news_manager.get_status()
    
    status = {
        "webhook_activo": True,
        "timestamp_actual": datetime.now().isoformat(),
        "cache_timestamp": cache_timestamp.isoformat() if cache_timestamp else None,
        "total_noticias_cache": len(cached_news),
        "auto_manager": manager_status
    }
    
    return jsonify(status)

@app.route('/api/news/force-generate', methods=['POST'])
@cross_origin()
def force_generate():
    """Forzar generación ejecutando el script"""
    
    def ejecutar_script():
        success = news_manager.force_generation()
        if success:
            print("✅ Script ejecutado exitosamente")
        else:
            print("❌ Error ejecutando script")
    
    thread = threading.Thread(target=ejecutar_script, daemon=True)
    thread.start()
    
    return jsonify({
        "status": "success",
        "message": "Script ava_graph_news.py ejecutándose en background",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/images/<filename>')
@cross_origin()
def serve_image(filename):
    """Servir imágenes"""
    try:
        return send_from_directory(str(GENERATED_IMAGES_DIR), filename)
    except:
        return jsonify({"error": "Imagen no encontrada"}), 404

@app.route('/health')
@cross_origin()
def health():
    """Health check"""
    return jsonify({
        "service": "News Service",
        "status": "running",
        "auto_generation": "active",
        "script_execution": "direct",
        "manager_status": news_manager.get_status(),
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Iniciando sistema de ejecución directa de scripts...")
    
    # Verificar que el script existe
    if not NEWS_GENERATOR_SCRIPT.exists():
        print(f"❌ ERROR: No se encuentra el script: {NEWS_GENERATOR_SCRIPT}")
        sys.exit(1)
    
    # Cache inicial
    actualizar_cache()
    
    # Iniciar manager de auto-ejecución
    print("🤖 Iniciando AutoNewsManager con ejecución directa...")
    auto_thread = threading.Thread(target=news_manager.auto_check_loop, daemon=True)
    auto_thread.start()
    
    print("✅ Sistema de ejecución directa activo:")
    print(f"   - Webhook en puerto 5000")
    print(f"   - Script: {NEWS_GENERATOR_SCRIPT}")
    print(f"   - Verificación cada hora")
    print(f"   - Ejecución automática cada 24 horas")
    
    app.run(host='0.0.0.0', port=5000, debug=False)