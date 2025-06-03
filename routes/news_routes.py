from flask import Blueprint, render_template, jsonify, current_app, send_from_directory, redirect, url_for, abort
from datetime import datetime, timedelta
from pathlib import Path
import threading
import logging
import json
import subprocess
import time
import os
import sys  # ✅ AGREGAR IMPORT FALTANTE

logger = logging.getLogger(__name__)
news_bp = Blueprint('news', __name__)

# Variables globales para control del flujo SEO
last_seo_execution = None  # ✅ NOMBRE CORRECTO
seo_execution_interval = timedelta(hours=12)  # 2 veces al día
seo_lock = threading.Lock()

# ✅ VARIABLE PARA CONTROLAR EJECUCIÓN AUTOMÁTICA
auto_seo_enabled = True
last_check_time = None

def get_seo_paths():
    """Obtener rutas del sistema SEO"""
    base_dir = Path(__file__).parent.parent
    seo_dir = base_dir / 'llmpagina' / 'ava_seo'
    
    return {
        'workflow_script': seo_dir / 'seo_workflow.py',
        'output_dir': seo_dir / 'output',
        'articulos_dir': seo_dir / 'output' / 'articulos',
        'seo_json_dir': seo_dir / 'output' / 'seo_json',
        'static_dir': seo_dir / 'output' / 'static',
        'results_dir': seo_dir / 'results',
        'latest_articles': seo_dir / 'results' / 'latest_articles.json',
        'latest_results': seo_dir / 'results' / 'latest_results.json'
    }

def create_default_image():
    """Crear imagen por defecto si no existe"""
    try:
        static_images_dir = Path(__file__).parent.parent / 'llmpagina' / 'static' / 'images'
        static_images_dir.mkdir(parents=True, exist_ok=True)
        
        default_image_path = static_images_dir / 'default-article.png'
        
        if not default_image_path.exists():
            try:
                from PIL import Image, ImageDraw, ImageFont
                
                img = Image.new('RGB', (600, 400), color='#1c1c1c')
                draw = ImageDraw.Draw(img)
                
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except:
                    font = ImageFont.load_default()
                
                text1 = "AVA"
                bbox1 = draw.textbbox((0, 0), text1, font=font)
                text1_width = bbox1[2] - bbox1[0]
                x1 = (600 - text1_width) // 2
                y1 = 150
                draw.text((x1, y1), text1, fill='#FFD700', font=font)
                
                try:
                    font2 = ImageFont.truetype("arial.ttf", 24)
                except:
                    font2 = ImageFont.load_default()
                
                text2 = "Artículo de IA"
                bbox2 = draw.textbbox((0, 0), text2, font=font2)
                text2_width = bbox2[2] - bbox2[0]
                x2 = (600 - text2_width) // 2
                y2 = 220
                draw.text((x2, y2), text2, fill='#FFD700', font=font2)
                
                img.save(default_image_path)
                logger.info(f"✅ Imagen PNG por defecto creada: {default_image_path}")
                
            except ImportError:
                create_basic_png_fallback()
            except Exception as e:
                logger.error(f"Error creando imagen PNG: {e}")
                create_basic_png_fallback()
        
    except Exception as e:
        logger.error(f"Error en create_default_image: {e}")

def create_basic_png_fallback():
    """Crear PNG básico sin librerías externas"""
    try:
        static_images_dir = Path(__file__).parent.parent / 'llmpagina' / 'static' / 'images'
        static_images_dir.mkdir(parents=True, exist_ok=True)
        default_image_path = static_images_dir / 'default-article.png'
        
        if not default_image_path.exists():
            png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            
            with open(default_image_path, 'wb') as f:
                f.write(png_data)
                
            logger.info(f"✅ PNG básico creado: {default_image_path}")
            
    except Exception as e:
        logger.error(f"Error creando PNG básico: {e}")

def find_corresponding_image(article_data, static_dir, app_context=None):
    """Buscar imagen correspondiente al artículo específico"""
    try:
        article_title = article_data.get('title', '')
        run_id = article_data.get('run_id', '')
        filename = article_data.get('filename', '')
        
        logger.info(f"🔍 Buscando imagen para:")
        logger.info(f"   📝 Título: {article_title}")
        logger.info(f"   🆔 Run ID: {run_id}")
        logger.info(f"   📄 Filename: {filename}")
        
        if not static_dir.exists():
            logger.warning(f"⚠️ Directorio no existe: {static_dir}")
            return get_fallback_image(article_title, app_context)
        
        # MÉTODO 1: Buscar por archivo de metadata específico
        image_from_metadata = find_image_by_metadata_safe(article_data, static_dir)
        if image_from_metadata and image_from_metadata.get('exists'):
            logger.info(f"✅ Imagen encontrada por metadata: {image_from_metadata.get('filename', 'N/A')}")
            return build_image_response(image_from_metadata, article_title, 'metadata_title', app_context)
        
        # MÉTODO 2: Buscar por run_id
        if run_id:
            image_from_run_id = find_image_by_run_id_safe(run_id, static_dir)
            if image_from_run_id and image_from_run_id.get('exists'):
                logger.info(f"✅ Imagen encontrada por run_id: {image_from_run_id.get('filename', 'N/A')}")
                return build_image_response(image_from_run_id, article_title, 'run_id', app_context)
        
        # MÉTODO 3: Buscar por título
        image_from_title = find_image_by_title_safe(article_title, static_dir)
        if image_from_title and image_from_title.get('exists'):
            logger.info(f"✅ Imagen encontrada por título: {image_from_title.get('filename', 'N/A')}")
            return build_image_response(image_from_title, article_title, 'title_pattern', app_context)
        
        # MÉTODO 4: Fallback
        logger.warning(f"⚠️ No se encontró imagen específica para: {article_title}")
        return get_fallback_image(article_title, app_context)
        
    except Exception as e:
        logger.error(f"Error buscando imagen: {e}")
        return get_fallback_image(article_data.get('title', 'Artículo'), app_context)

def find_image_by_metadata_safe(article_data, static_dir):
    """Buscar imagen usando archivos de metadata"""
    try:
        article_title = article_data.get('title', '')
        filename = article_data.get('filename', '')
        
        metadata_files = list(static_dir.glob('*_metadata.json'))
        
        for metadata_file in metadata_files:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                metadata_title = metadata.get('article_title', '')
                metadata_article_file = metadata.get('article_file', '')
                image_filename = metadata.get('image_filename', '')
                
                # Verificar coincidencia exacta por título
                if metadata_title and article_title and metadata_title.strip().lower() == article_title.strip().lower():
                    image_path = static_dir / image_filename
                    if image_path.exists():
                        logger.info(f"📋 Coincidencia por título en metadata: {metadata_file.name}")
                        return {
                            "image_path": image_path,
                            "filename": image_filename,
                            "exists": True,
                            "metadata": metadata
                        }
                
                # Verificar coincidencia por archivo
                if metadata_article_file and filename and metadata_article_file in filename:
                    image_path = static_dir / image_filename
                    if image_path.exists():
                        logger.info(f"📋 Coincidencia por archivo en metadata: {metadata_file.name}")
                        return {
                            "image_path": image_path,
                            "filename": image_filename,
                            "exists": True,
                            "metadata": metadata
                        }
                        
            except Exception as e:
                logger.error(f"Error leyendo metadata {metadata_file}: {e}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error en find_image_by_metadata_safe: {e}")
        return None

def find_image_by_run_id_safe(run_id, static_dir):
    """Buscar imagen por run_id exacto"""
    try:
        png_files = list(static_dir.glob('*.png'))
        
        for png_file in png_files:
            png_name = png_file.stem.lower()
            run_id_clean = run_id.lower().replace('.json', '')
            
            # Verificar coincidencia exacta del run_id
            if run_id_clean in png_name or png_name in run_id_clean:
                # Verificar que sea una coincidencia significativa
                if len(run_id_clean) > 10 and run_id_clean[:15] in png_name:
                    logger.info(f"🆔 Coincidencia por run_id: {png_file.name}")
                    return {
                        "image_path": png_file,
                        "filename": png_file.name,
                        "exists": True
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"Error en find_image_by_run_id_safe: {e}")
        return None

def find_image_by_title_safe(article_title, static_dir):
    """Buscar imagen por título del artículo"""
    try:
        # Limpiar título para comparación
        title_clean = article_title.lower()
        for char in [':', '?', '¿', '¡', '!', '"', "'", ',', '.', ';', '(', ')', '[', ']', '{', '}']:
            title_clean = title_clean.replace(char, '')
        
        # Generar patrones de búsqueda más específicos
        words = title_clean.split()
        if len(words) >= 3:
            # Usar las primeras 3-4 palabras para mayor precisión
            pattern_words = words[:4]
        else:
            pattern_words = words
        
        patterns = [
            '_'.join(pattern_words),
            '-'.join(pattern_words),
            ''.join(pattern_words),
        ]
        
        # Solo usar patrones suficientemente largos
        patterns = [p for p in patterns if len(p) > 8]
        
        png_files = list(static_dir.glob('*.png'))
        
        for png_file in png_files:
            png_name = png_file.stem.lower()
            
            for pattern in patterns:
                # Verificar coincidencia significativa
                if len(pattern) > 8 and pattern in png_name:
                    logger.info(f"📝 Coincidencia por título: {png_file.name} (patrón: {pattern})")
                    return {
                        "image_path": png_file,
                        "filename": png_file.name,
                        "exists": True
                    }
        
        return None
        
    except Exception as e:
        logger.error(f"Error en find_image_by_title_safe: {e}")
        return None

def build_image_response(image_data, article_title, source, app_context=None):
    """Construir respuesta de imagen de forma segura"""
    try:
        if not image_data or not image_data.get('exists', False):
            logger.warning(f"⚠️ Imagen no existe para: {article_title}")
            return get_fallback_image(article_title, app_context)
        
        filename = image_data.get('filename', '')
        if filename:
            try:
                # Intentar construir URL con url_for
                if app_context:
                    with app_context:
                        web_path = url_for('static', filename=f'seo_images/{filename}')
                else:
                    # Fallback a ruta manual
                    web_path = f'/static/seo_images/{filename}'
                
                return {
                    "original_path": image_data.get('original_path', ''),
                    "web_path": web_path,
                    "article_title": article_title,
                    "timestamp": datetime.now().isoformat(),
                    "exists": True,
                    "is_fallback": False,
                    "source": source,
                    "filename": filename
                }
                
            except Exception as url_error:
                logger.error(f"❌ Error construyendo URL para imagen: {url_error}")
                # Usar ruta manual como fallback
                web_path = f'/static/seo_images/{filename}'
                
                return {
                    "original_path": image_data.get('original_path', ''),
                    "web_path": web_path,
                    "article_title": article_title,
                    "timestamp": datetime.now().isoformat(),
                    "exists": True,
                    "is_fallback": False,
                    "source": source,
                    "filename": filename
                }
        else:
            logger.warning(f"⚠️ No hay filename para imagen de: {article_title}")
            return get_fallback_image(article_title, app_context)
            
    except Exception as e:
        logger.error(f"❌ Error construyendo respuesta de imagen: {e}")
        return get_fallback_image(article_title, app_context)

def get_fallback_image(article_title, app_context=None):
    """Obtener imagen por defecto del sistema"""
    create_default_image()
    
    try:
        # Si tenemos contexto de aplicación, usar url_for
        if app_context:
            with app_context:
                web_path = url_for('static', filename='images/default-article.png')
        else:
            # Sin contexto, construir URL manualmente
            web_path = '/static/images/default-article.png'
        
        return {
            "original_path": "",
            "web_path": web_path,
            "article_title": article_title,
            "timestamp": datetime.now().isoformat(),
            "exists": False,
            "is_fallback": True,
            "source": "fallback"
        }
    except Exception as e:
        logger.error(f"Error en get_fallback_image: {e}")
        return {
            "original_path": "",
            "web_path": "/static/images/default-article.png",
            "article_title": article_title,
            "timestamp": datetime.now().isoformat(),
            "exists": False,
            "is_fallback": True,
            "source": "fallback"
        }

def should_execute_seo():
    """Verificar si debe ejecutarse el flujo SEO - VERSIÓN CORREGIDA"""
    global last_seo_execution, last_check_time
    
    # ✅ EVITAR VERIFICACIONES CONSTANTES
    current_time = datetime.now()
    
    # Si acabamos de verificar (últimos 5 minutos), no verificar de nuevo
    if last_check_time and (current_time - last_check_time) < timedelta(minutes=5):
        return False
    
    last_check_time = current_time
    
    # Si nunca se ha ejecutado, ejecutar una vez
    if last_seo_execution is None:
        logger.info("🔄 Primera ejecución SEO programada")
        return True
    
    # Verificar si han pasado 12 horas
    time_since_last = current_time - last_seo_execution
    should_run = time_since_last >= seo_execution_interval
    
    if should_run:
        logger.info(f"🔄 Han pasado {time_since_last.total_seconds()/3600:.1f} horas desde la última ejecución SEO")
    else:
        remaining_time = seo_execution_interval - time_since_last
        logger.info(f"⏳ Faltan {remaining_time.total_seconds()/3600:.1f} horas para próxima ejecución SEO")
    
    return should_run

def check_and_run_seo():
    """Verificar y ejecutar SEO si es necesario - VERSIÓN CORREGIDA"""
    global auto_seo_enabled, last_seo_execution  # ✅ Asegurar que la variable esté declarada
    
    if not auto_seo_enabled:
        return
    
    try:
        current_time = datetime.now()
        
        if should_execute_seo():
            logger.info("🚀 INICIANDO ejecución automática del flujo SEO")
            logger.info(f"⏰ Hora actual: {current_time.strftime('%H:%M:%S')}")
            logger.info(f"📅 Fecha: {current_time.strftime('%Y-%m-%d')}")
            threading.Thread(target=execute_seo_workflow, daemon=True).start()
        else:
            # ✅ CORRECCIÓN: Cambiar "last_seeo_execution" por "last_seo_execution"
            if last_seo_execution:
                time_until_next = seo_execution_interval - (current_time - last_seo_execution)  # ✅ CORREGIDO
                hours_remaining = time_until_next.total_seconds() / 3600
                
                # Solo loggear si faltan menos de 1 hora o es un intervalo específico
                if hours_remaining < 1 or current_time.minute in [0, 30]:
                    logger.info(f"⏳ Próxima ejecución SEO en: {hours_remaining:.1f} horas")
            else:
                logger.info("⏳ Primera ejecución SEO pendiente")
                
    except Exception as e:
        logger.error(f"❌ Error en check_and_run_seo: {e}")

def execute_seo_workflow():
    """Ejecutar el flujo de trabajo SEO en segundo plano - VERSIÓN ÚNICA"""
    global last_seo_execution
    
    with seo_lock:
        try:
            start_time = datetime.now()
            logger.info(f"🚀 INICIO ejecución SEO - {start_time.strftime('%H:%M:%S')}")
            
            paths = get_seo_paths()
            workflow_script = paths['workflow_script']
            
            if not workflow_script.exists():
                logger.error(f"❌ Script SEO no encontrado: {workflow_script}")
                return False
            
            for dir_path in [paths['output_dir'], paths['articulos_dir'], 
                           paths['seo_json_dir'], paths['static_dir'], paths['results_dir']]:
                dir_path.mkdir(parents=True, exist_ok=True)
            
            logger.info("📋 Ejecutando script SEO...")
            
            result = subprocess.run([
                sys.executable, str(workflow_script)
            ], capture_output=True, text=True, timeout=1800)
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            if result.returncode == 0:
                logger.info(f"✅ Flujo SEO completado exitosamente en {duration.total_seconds():.1f}s")
                logger.info(f"🕐 Finalizado a las: {end_time.strftime('%H:%M:%S')}")
                last_seo_execution = end_time
                update_results_files()
                
                # Log de próxima ejecución
                next_execution = last_seo_execution + seo_execution_interval
                logger.info(f"⏰ Próxima ejecución programada: {next_execution.strftime('%H:%M:%S')}")
                
                return True
            else:
                logger.error(f"❌ Error ejecutando flujo SEO: {result.stderr}")
                logger.info(f"📋 Salida del script: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("⏰ Timeout ejecutando flujo SEO (30 minutos)")
            return False
        except Exception as e:
            logger.error(f"💥 Excepción ejecutando flujo SEO: {e}")
            return False

def update_results_files():
    """Actualizar archivos de resultados agregando los nuevos artículos"""
    try:
        paths = get_seo_paths()
        articulos_dir = paths['articulos_dir']
        static_dir = paths['static_dir']
        latest_articles_file = paths['latest_articles']
        latest_results_file = paths['latest_results']
        
        existing_results = []
        if latest_results_file.exists():
            try:
                with open(latest_results_file, 'r', encoding='utf-8') as f:
                    existing_results = json.load(f)
            except Exception as e:
                logger.error(f"Error cargando resultados existentes: {e}")
        
        new_articles = []
        if articulos_dir.exists():
            for article_file in articulos_dir.glob('*.json'):
                try:
                    with open(article_file, 'r', encoding='utf-8') as f:
                        article_data = json.load(f)
                    
                    run_id = article_file.stem
                    
                    # Agregar información adicional para búsqueda de imagen
                    article_data['filename'] = article_file.name
                    article_data['run_id'] = run_id
                    
                    # Buscar imagen específica para este artículo SIN contexto Flask
                    image_data = find_corresponding_image(article_data, static_dir, app_context=None)
                    
                    result_entry = {
                        "run_id": run_id,
                        "article": article_data,
                        "image": image_data,
                        "timestamp": article_data.get('generated_at', datetime.now().isoformat())
                    }
                    
                    if not any(r.get('run_id') == run_id for r in existing_results):
                        new_articles.append(result_entry)
                        logger.info(f"➕ Nuevo artículo agregado: {run_id}")
                        logger.info(f"   🖼️ Imagen: {image_data.get('source', 'N/A')} - {image_data.get('web_path', 'N/A')}")
                        
                except Exception as e:
                    logger.error(f"Error procesando artículo {article_file}: {e}")
        
        all_results = new_articles + existing_results
        all_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        all_results = all_results[:20]
        
        with open(latest_results_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        latest_6 = all_results[:6]
        with open(latest_articles_file, 'w', encoding='utf-8') as f:
            json.dump(latest_6, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📝 Actualizados archivos de resultados: {len(new_articles)} nuevos artículos")
        
    except Exception as e:
        logger.error(f"Error actualizando archivos de resultados: {e}")

# ✅ REEMPLAZAR LA FUNCIÓN DUPLICADA CON ESTA VERSIÓN ÚNICA
def load_articles_from_latest_results():
    """Cargar artículos desde latest_results.json - VERSIÓN CORREGIDA"""
    try:
        paths = get_seo_paths()
        latest_results_file = paths['latest_results']
        
        logger.info(f"📂 Cargando artículos desde: {latest_results_file}")
        
        if not latest_results_file.exists():
            logger.warning(f"⚠️ Archivo no existe: {latest_results_file}")
            return []
        
        # Leer archivo JSON
        with open(latest_results_file, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
        
        if not results_data:
            logger.warning("⚠️ No hay datos en latest_results.json")
            return []
        
        logger.info(f"📄 Encontrados {len(results_data)} resultados en el archivo")
        
        # Procesar artículos - ✅ SOLO LOS ÚLTIMOS 6
        articles = []
        for i, result in enumerate(results_data[:6]):  # ✅ SOLO LOS PRIMEROS 6
            try:
                # Extraer datos del artículo
                article_data = result.get('article', {})
                image_data = result.get('image', {})
                
                # ✅ VERIFICAR QUE TENGA TÍTULO
                title = article_data.get('title', '')
                if not title:
                    logger.warning(f"⚠️ Artículo {i+1} sin título, saltando...")
                    continue
                
                # ✅ CREAR OBJETO ARTÍCULO PROCESADO COMO DICCIONARIO
                processed_article = {
                    'title': title,
                    'content': article_data.get('content', ''),
                    'excerpt': article_data.get('content', '')[:300] + '...' if len(article_data.get('content', '')) > 300 else article_data.get('content', ''),
                    'meta_description': article_data.get('meta_description', ''),
                    'keywords': article_data.get('keywords', []),
                    'references': article_data.get('references', []),
                    'generated_at': article_data.get('generated_at', datetime.now().isoformat()),
                    'run_id': result.get('run_id', ''),
                    'filename': article_data.get('filename', ''),
                    'source_topics': article_data.get('source_topics', []),
                    'model_used': article_data.get('model_used', 'llama3-70b-8192'),
                    
                    # Datos de imagen
                    'image_path': image_data.get('web_path', '/static/images/default-article.png'),
                    'image_exists': image_data.get('exists', False),
                    'image_filename': image_data.get('filename', ''),
                    'has_image': image_data.get('exists', False),
                    
                    # Timestamp para ordenar
                    'timestamp': result.get('timestamp', datetime.now().isoformat())
                }
                
                articles.append(processed_article)
                logger.debug(f"✅ Procesado artículo: {processed_article['title'][:50]}...")
                
            except Exception as e:
                logger.error(f"❌ Error procesando artículo {i+1}: {e}")
                continue
        
        logger.info(f"✅ Procesados {len(articles)} artículos exitosamente")
        
        # Ordenar por fecha (más recientes primero)
        articles.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return articles
        
    except Exception as e:
        logger.error(f"❌ Error cargando artículos: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return []

@news_bp.route('/noticias')
def noticias():
    """Página principal de noticias - VERSIÓN CORREGIDA FINAL"""
    try:
        logger.info("📰 Cargando página de noticias...")
        
        # Verificar y ejecutar SEO si es necesario
        check_and_run_seo()
        
        # ✅ CARGAR ARTÍCULOS DESDE latest_results.json (SOLO LOS ÚLTIMOS 6)
        articles = load_articles_from_latest_results()
        
        if not articles:
            logger.warning("⚠️ No se encontraron artículos")
            return render_template('noticias.html',
                                 articles=[],
                                 current_time=datetime.now(),
                                 total_articles=0,
                                 error_message="No hay artículos disponibles en este momento.")
        
        logger.info(f"📰 Mostrando {len(articles)} artículos en la página")
        
        return render_template('noticias.html',
                             articles=articles,
                             current_time=datetime.now(),
                             total_articles=len(articles))
        
    except Exception as e:
        logger.error(f"❌ Error en ruta noticias: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        
        return render_template('noticias.html',
                             articles=[],
                             current_time=datetime.now(),
                             total_articles=0,
                             error_message="Error cargando noticias. Por favor, intenta más tarde.")

@news_bp.route('/articulo/<article_id>')
def ver_articulo(article_id):
    """Ver un artículo específico - VERSIÓN CORREGIDA"""
    try:
        logger.info(f"📖 Solicitando artículo: {article_id}")
        
        # Cargar todos los artículos desde latest_results.json
        articles = load_articles_from_latest_results()
        
        if not articles:
            logger.warning("⚠️ No se encontraron artículos")
            abort(404)
        
        # Buscar el artículo específico por run_id
        article_data = None
        for art in articles:
            if art.get('run_id') == article_id:
                article_data = art
                break
        
        if not article_data:
            logger.warning(f"⚠️ Artículo no encontrado: {article_id}")
            abort(404)
        
        logger.info(f"✅ Artículo encontrado: {article_data.get('title', 'Sin título')}")
        
        # ✅ RESTRUCTURAR DATOS PARA EL TEMPLATE
        article_for_template = {
            'article': {
                'title': article_data.get('title', ''),
                'content': article_data.get('content', ''),
                'meta_description': article_data.get('meta_description', ''),
                'keywords': article_data.get('keywords', []),
                'references': article_data.get('references', []),
                'generated_at': article_data.get('generated_at', '')
            },
            'image': {
                'web_path': article_data.get('image_path', '/static/images/default-article.png'),
                'timestamp': article_data.get('timestamp', ''),
                'exists': article_data.get('image_exists', False)
            },
            'run_id': article_data.get('run_id', '')
        }
        
        # ✅ RENDERIZAR CON ESTRUCTURA CORRECTA
        return render_template('public_article.html', 
                             article=article_for_template,
                             current_time=datetime.now())
        
    except Exception as e:
        logger.error(f"❌ Error cargando artículo {article_id}: {e}")
        abort(500)

@news_bp.route('/api/noticias')
def api_noticias():
    """API para obtener noticias en formato JSON"""
    try:
        articles = load_articles_from_latest_results()
        
        return jsonify({
            'success': True,
            'total': len(articles),
            'articles': articles  # Todos los artículos (máximo 6)
        })
        
    except Exception as e:
        logger.error(f"❌ Error en API noticias: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'articles': []
        }), 500

# ✅ RUTA PARA SERVIR IMÁGENES SEO
@news_bp.route('/static/seo_images/<filename>')
def serve_seo_image(filename):
    """Servir imágenes SEO generadas"""
    try:
        paths = get_seo_paths()
        static_dir = paths['static_dir']
        
        image_path = static_dir / filename
        
        if not image_path.exists():
            logger.warning(f"⚠️ Imagen SEO no encontrada: {filename}")
            # Retornar imagen por defecto
            default_image = Path(__file__).parent.parent / 'static' / 'images' / 'default-article.png'
            if default_image.exists():
                return send_from_directory(str(default_image.parent), 'default-article.png')
            else:
                abort(404)
        
        logger.info(f"🖼️ Sirviendo imagen SEO: {filename}")
        return send_from_directory(str(static_dir), filename)
        
    except Exception as e:
        logger.error(f"❌ Error sirviendo imagen SEO {filename}: {e}")
        abort(500)