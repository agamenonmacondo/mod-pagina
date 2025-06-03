from flask import Flask
from routes.index_routes import index_bp
from routes.auth_routes import auth_bp
from routes.news_routes import news_bp
from routes.dashboard_routes import dashboard_bp
from routes.api_routes import api_bp
from routes.chat_routes import chat_bp
from database.db_manager import init_db
from utils.template_filters import register_filters
from utils.context_processors import register_context_processors
import logging
import os
import threading
import time
import atexit

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# ✅ VARIABLE GLOBAL PARA CONTROLAR INICIALIZACIÓN
ava_initialized = False

def init_ava_on_startup():
    """Inicializar AVA en background al arrancar el servidor"""
    global ava_initialized
    
    if ava_initialized:
        return
    
    try:
        logger.info("🚀 Iniciando AVA Bot en background...")
        
        # Esperar un poco a que Flask termine de inicializarse
        time.sleep(3)
        
        # ✅ CORREGIR IMPORTACIÓN - La función se llama start_ava, no start_ava_script
        from routes.chat_routes import start_ava
        
        # Intentar inicializar AVA
        success = start_ava()
        
        if success:
            logger.info("✅ AVA Bot inicializado correctamente al startup")
            ava_initialized = True
        else:
            logger.warning("⚠️ AVA Bot no se pudo inicializar al startup")
            
    except Exception as e:
        logger.error(f"❌ Error inicializando AVA al startup: {e}")

def cleanup_ava():
    """Limpiar recursos de AVA al cerrar"""
    try:
        # ✅ CORREGIR IMPORTACIÓN - Usar alias para evitar conflicto de nombres
        from routes.chat_routes import cleanup_ava as cleanup_ava_chat
        cleanup_ava_chat()
        logger.info("🧹 Recursos de AVA limpiados")
    except Exception as e:
        logger.error(f"❌ Error limpiando AVA: {e}")

# ✅ CREAR APLICACIÓN DE FORMA SIMPLE
app = Flask(__name__, 
           template_folder='llmpagina/templates',
           static_folder='llmpagina/static')

# Configuración básica
app.config['SECRET_KEY'] = 'clave-secreta-temporal'

# Registrar filtros y procesadores
register_filters(app)
register_context_processors(app)

# ✅ REGISTRAR BLUEPRINTS CON MEJOR MANEJO DE ERRORES
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
        logger.info(f"✅ Blueprint {name} registrado exitosamente")
        successfully_registered.append(name)
        
    except Exception as e:
        logger.error(f"❌ Error registrando {name}: {e}")
        failed_blueprints.append((name, str(e)))
        
        # ✅ ANÁLISIS ESPECÍFICO DE ERRORES
        if "overwriting an existing endpoint function" in str(e):
            logger.error(f"💡 {name}: Hay rutas duplicadas. Revisar endpoints.")
        elif "BuildError" in str(e):
            logger.error(f"💡 {name}: Error de construcción de URL. Revisar url_for().")
        elif "ImportError" in str(e):
            logger.error(f"💡 {name}: Error de importación. Revisar imports.")

# Inicializar base de datos
try:
    init_db()
    logger.info("✅ Base de datos inicializada")
except Exception as e:
    logger.error(f"❌ Error inicializando base de datos: {e}")

if __name__ == '__main__':
    # Crear directorios necesarios
    os.makedirs('logs', exist_ok=True)
    
    logger.info("🤖 Aplicación AVA iniciada")
    logger.info(f"📁 Templates: {app.template_folder}")
    logger.info(f"🎨 Static: {app.static_folder}")
    
    # ✅ MOSTRAR RESUMEN DE BLUEPRINTS
    print(f"\n📊 Blueprints registrados: {len(successfully_registered)}")
    for bp in successfully_registered:
        print(f"   ✅ {bp}")
    
    if failed_blueprints:
        print(f"\n❌ Blueprints fallidos: {len(failed_blueprints)}")
        for bp_name, error in failed_blueprints:
            print(f"   ❌ {bp_name}: {error[:100]}...")
    
    # ✅ SOLO INICIALIZAR AVA SI CHAT_BP ESTÁ REGISTRADO
    if 'chat_bp' in successfully_registered:
        ava_thread = threading.Thread(target=init_ava_on_startup, daemon=True)
        ava_thread.start()
        logger.info("🚀 AVA Bot se iniciará en background...")
    else:
        logger.warning("⚠️ Chat blueprint no registrado - AVA no se iniciará")
    
    # ✅ REGISTRAR CLEANUP AL CERRAR
    atexit.register(cleanup_ava)
    
    # ✅ MOSTRAR RUTAS DISPONIBLES (SOLO LAS QUE FUNCIONAN)
    print("\n🔗 Rutas disponibles:")
    route_count = 0
    chat_routes = []
    
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
            route_count += 1
            print(f"   • {rule.rule} [{methods}] -> {rule.endpoint}")
            
            # Recopilar rutas de chat
            if 'chat' in rule.rule.lower():
                chat_routes.append(f"{rule.rule} [{methods}]")
    
    print(f"\n📊 Total de rutas: {route_count}")
    
    # ✅ MOSTRAR RUTAS DE CHAT SI EXISTEN
    if chat_routes:
        print("\n💬 Rutas de Chat:")
        for route in chat_routes:
            print(f"   • {route}")
    else:
        print("\n⚠️ No se encontraron rutas de chat")
    
    # ✅ MOSTRAR ENLACES IMPORTANTES
    print("\n🌐 Enlaces importantes:")
    print("   • Aplicación principal: http://localhost:8080/")
    print("   • Dashboard: http://localhost:8080/dashboard")
    
    # Solo mostrar si están disponibles
    if 'news_bp' in successfully_registered:
        print("   • Noticias: http://localhost:8080/noticias")
    if 'chat_bp' in successfully_registered:
        print("   • API Chat Status: http://localhost:8080/api/chat/status")
        print("   • API Chat Debug: http://localhost:8080/api/chat/debug")
    
    # Ejecutar aplicación
    try:
        app.run(host='0.0.0.0', port=8080, debug=True)
    except Exception as e:
        logger.error(f"❌ Error ejecutando aplicación: {e}")