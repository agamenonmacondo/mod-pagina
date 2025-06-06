from flask import Flask, jsonify
from routes.index_routes import index_bp
from routes.auth_routes import auth_bp
from routes.news_routes import news_bp
from routes.dashboard_routes import dashboard_bp
from routes.api_routes import api_bp
from routes.chat_routes import chat_bp
from utils.template_filters import register_filters
from utils.context_processors import register_context_processors
import logging
import os
import threading
import time
import atexit
import sys
from datetime import datetime

# Configuración de logging
if os.getenv('GOOGLE_CLOUD_PROJECT'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# ✅ IMPORTAR MEMORIA CLOUD (INICIALIZACIÓN AUTOMÁTICA)
print("🔄 Importando sistema de memoria...")
try:
    from database.cloud_memory_manager import init_cloud_memory, get_cloud_memory_info, cloud_memory_manager
    CLOUD_MEMORY_AVAILABLE = True
    print("✅ Gestor de memoria cloud importado y pre-inicializado")
    
    # ✅ MOSTRAR INFO DE PRE-INICIALIZACIÓN
    print(f"📁 Ruta de datos: {cloud_memory_manager.data_path}")
    print(f"🌐 Entorno detectado: {'Cloud' if cloud_memory_manager.is_cloud else 'Local'}")
    
except ImportError as e:
    print(f"❌ Error importando memoria cloud: {e}")
    CLOUD_MEMORY_AVAILABLE = False
except Exception as e:
    print(f"❌ Error inesperado importando memoria: {e}")
    CLOUD_MEMORY_AVAILABLE = False

# Variables globales
ava_initialized = False
memory_initialized = False

def detect_environment():
    """Detectar entorno de ejecución"""
    if os.getenv('K_SERVICE') or os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('CLOUD_ENV'):
        return 'cloud'
    else:
        return 'local'

def init_memory_system():
    """Inicializar sistema de memoria completo"""
    global memory_initialized
    
    if memory_initialized:
        logger.info("🧠 Sistema de memoria ya inicializado")
        return True
    
    environment = detect_environment()
    logger.info(f"🧠 Inicializando memoria - Entorno: {environment}")
    
    try:
        if environment == 'cloud' and CLOUD_MEMORY_AVAILABLE:
            logger.info("🌐 Inicializando memoria cloud completa...")
            
            # ✅ EJECUTAR INICIALIZACIÓN COMPLETA
            success = init_cloud_memory()
            
            if success:
                logger.info("✅ Sistema de memoria cloud inicializado completamente")
                
                # ✅ OBTENER Y MOSTRAR INFORMACIÓN
                info = get_cloud_memory_info()
                validation = info.get('validation', {})
                summary = validation.get('summary', {})
                
                logger.info(f"📊 Componentes inicializados: {summary.get('total_components', 0)}")
                logger.info(f"🔍 Problemas encontrados: {summary.get('issues_found', 0)}")
                logger.info(f"📁 Ruta de datos: {info.get('data_path')}")
                
                # ✅ MOSTRAR BASES DE DATOS CREADAS
                db_status = validation.get('databases', {})
                for db_name, db_info in db_status.items():
                    if db_info.get('accessible'):
                        tables = db_info.get('tables', [])
                        logger.info(f"   🗃️ {db_name}: {len(tables)} tablas creadas")
                    else:
                        logger.warning(f"   ⚠️ {db_name}: No accesible")
                
                memory_initialized = True
                return True
            else:
                logger.error("❌ Error inicializando memoria cloud")
                return False
                
        else:
            logger.info("🏠 Inicializando memoria local...")
            try:
                from database.db_manager import init_db
                init_db()
                logger.info("✅ Sistema de memoria local inicializado")
                memory_initialized = True
                return True
            except ImportError:
                logger.warning("⚠️ db_manager no disponible, usando memoria básica")
                memory_initialized = True
                return True
            
    except Exception as e:
        logger.error(f"❌ Error crítico inicializando memoria: {e}")
        import traceback
        traceback.print_exc()
        return False

# ✅ CREAR APLICACIÓN
app = Flask(__name__, 
           template_folder='llmpagina/templates',
           static_folder='llmpagina/static')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'clave-secreta-temporal')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# ✅ REGISTRAR COMPONENTES
try:
    register_filters(app)
    register_context_processors(app)
    logger.info("✅ Filtros y procesadores registrados")
except Exception as e:
    logger.error(f"❌ Error registrando componentes: {e}")

# ✅ REGISTRAR BLUEPRINTS
blueprints_to_register = [
    (index_bp, 'index_bp'),
    (auth_bp, 'auth_bp'), 
    (news_bp, 'news_bp'),
    (dashboard_bp, 'dashboard_bp'),
    (api_bp, 'api_bp'),
    (chat_bp, 'chat_bp')
]

successfully_registered = []
failed_blueprints = []

for blueprint, name in blueprints_to_register:
    try:
        app.register_blueprint(blueprint)
        logger.info(f"✅ Blueprint {name} registrado")
        successfully_registered.append(name)
    except Exception as e:
        logger.error(f"❌ Error registrando {name}: {e}")
        failed_blueprints.append((name, str(e)))

# ✅ ENDPOINTS DE DIAGNÓSTICO
@app.route('/api/memory/status')
def memory_status():
    """Estado del sistema de memoria"""
    if not CLOUD_MEMORY_AVAILABLE:
        return jsonify({
            'status': 'not_available',
            'message': 'Sistema de memoria cloud no disponible',
            'environment': detect_environment()
        }), 503
    
    try:
        info = get_cloud_memory_info()
        return jsonify({
            'status': 'active',
            'memory_info': info,
            'initialized': memory_initialized,
            'environment': detect_environment(),
            'manager_available': CLOUD_MEMORY_AVAILABLE
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'environment': detect_environment()
        }), 500

@app.route('/api/system/health')
def system_health():
    """Estado completo del sistema"""
    return jsonify({
        'status': 'healthy',
        'service': 'ava-bot',
        'environment': detect_environment(),
        'components': {
            'memory_system': memory_initialized,
            'cloud_memory_manager': CLOUD_MEMORY_AVAILABLE,
            'ava_bot': ava_initialized,
            'blueprints_count': len(successfully_registered),
            'blueprints': successfully_registered
        },
        'paths': cloud_memory_manager.memory_paths if CLOUD_MEMORY_AVAILABLE else {},
        'timestamp': datetime.now().isoformat()
    }), 200

# ✅ INICIALIZAR MEMORIA INMEDIATAMENTE
print("\n🚀 Iniciando sistema de memoria...")
memory_success = init_memory_system()

if memory_success:
    print("✅ Sistema de memoria inicializado correctamente")
else:
    print("❌ ADVERTENCIA: Problemas inicializando memoria")

# ✅ FUNCIÓN PARA AVA
def init_ava_on_startup():
    """Inicializar AVA en background"""
    global ava_initialized
    
    if ava_initialized:
        return
    
    try:
        logger.info("🚀 Iniciando AVA Bot...")
        time.sleep(3)
        
        # Verificar que memoria esté lista
        if not memory_initialized:
            logger.warning("⚠️ AVA iniciará sin sistema de memoria completo")
        
        if 'chat_bp' in successfully_registered:
            from routes.chat_routes import start_ava
            success = start_ava()
            
            if success:
                logger.info("✅ AVA Bot inicializado correctamente")
                ava_initialized = True
            else:
                logger.warning("⚠️ AVA Bot no se pudo inicializar")
        else:
            logger.warning("⚠️ Chat blueprint no disponible para AVA")
            
    except Exception as e:
        logger.error(f"❌ Error inicializando AVA: {e}")

if __name__ == '__main__':
    # ✅ CREAR DIRECTORIOS ADICIONALES
    os.makedirs('logs', exist_ok=True)
    
    environment = detect_environment()
    logger.info(f"🤖 AVA iniciado - Entorno: {environment}")
    
    # ✅ MOSTRAR RESUMEN
    print(f"\n📊 Resumen de inicialización:")
    print(f"   🧠 Memoria: {'✅ OK' if memory_initialized else '❌ ERROR'}")
    print(f"   🔧 Cloud Manager: {'✅ OK' if CLOUD_MEMORY_AVAILABLE else '❌ NO'}")
    print(f"   📦 Blueprints: {len(successfully_registered)}/{len(blueprints_to_register)}")
    
    for bp in successfully_registered:
        print(f"      ✅ {bp}")
    
    if failed_blueprints:
        print(f"\n❌ Blueprints fallidos:")
        for bp_name, error in failed_blueprints:
            print(f"      ❌ {bp_name}: {error[:100]}...")
    
    # ✅ INICIALIZAR AVA SI CHAT ESTÁ DISPONIBLE
    if 'chat_bp' in successfully_registered:
        ava_thread = threading.Thread(target=init_ava_on_startup, daemon=True)
        ava_thread.start()
        logger.info("🚀 AVA se iniciará en background...")
    
    # ✅ MOSTRAR ENDPOINTS IMPORTANTES
    print(f"\n🌐 Enlaces importantes:")
    print(f"   • Aplicación: http://localhost:8080/")
    print(f"   • Health: http://localhost:8080/api/system/health")
    print(f"   • Memoria: http://localhost:8080/api/memory/status")
    
    # ✅ EJECUTAR APLICACIÓN
    try:
        port = int(os.environ.get('PORT', 8080))
        debug = (environment != 'cloud')
        
        logger.info(f"🚀 Iniciando servidor en puerto {port}")
        app.run(host='0.0.0.0', port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando aplicación: {e}")
        import traceback
        traceback.print_exc()