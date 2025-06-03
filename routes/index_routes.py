from flask import Blueprint, render_template
import logging

logger = logging.getLogger(__name__)
index_bp = Blueprint('index', __name__)

@index_bp.route('/')
def index():
    """Página principal"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error cargando index.html: {str(e)}")
        return f"Error cargando template index.html: {str(e)}"

@index_bp.route('/about')
def about():
    """Página sobre nosotros"""
    return """
    <h1>Sobre AVA</h1>
    <p>AVA es un sistema de agentes virtuales avanzados.</p>
    <a href="/">🔙 Volver al inicio</a>
    """

@index_bp.route('/contact')
def contact():
    """Página de contacto"""
    return """
    <h1>Contacto</h1>
    <p>Para más información, contacta con nosotros.</p>
    <a href="/">🔙 Volver al inicio</a>
    """

@index_bp.route('/services')
def services():
    """Página de servicios"""
    return """
    <h1>Servicios</h1>
    <p>Ofrecemos servicios de inteligencia artificial.</p>
    <a href="/">🔙 Volver al inicio</a>
    """

@index_bp.route('/info')
def info():
    """Mostrar información de configuración"""
    from flask import current_app
    import os
    
    templates_exist = os.path.exists(current_app.template_folder)
    static_exist = os.path.exists(current_app.static_folder)
    
    # Listar templates disponibles
    templates_list = []
    if templates_exist:
        try:
            templates_list = [f for f in os.listdir(current_app.template_folder) if f.endswith('.html')]
        except Exception as e:
            templates_list = [f'Error listando templates: {str(e)}']
    
    # Obtener todas las rutas disponibles
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint != 'static':
            methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
            routes.append(f"{rule.rule} [{methods}] -> {rule.endpoint}")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Información de la Aplicación</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #121212; color: #f0f0f0; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .success {{ background-color: rgba(46, 204, 113, 0.2); color: #2ecc71; }}
            .error {{ background-color: rgba(231, 76, 60, 0.2); color: #e74c3c; }}
            ul {{ list-style-type: none; padding: 0; }}
            li {{ padding: 5px; margin: 2px 0; background-color: #1e1e1e; }}
            a {{ text-decoration: none; color: #FFD700; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>🤖 Información de la Aplicación Flask AVA</h1>
        
        <h2>📁 Configuración:</h2>
        <ul>
            <li><strong>Templates folder:</strong> {current_app.template_folder}</li>
            <li><strong>Static folder:</strong> {current_app.static_folder}</li>
        </ul>
        
        <h2>✅ Estado:</h2>
        <div class="status {'success' if templates_exist else 'error'}">
            <strong>Templates:</strong> {'✅ Encontrado' if templates_exist else '❌ No encontrado'}
        </div>
        <div class="status {'success' if static_exist else 'error'}">
            <strong>Static:</strong> {'✅ Encontrado' if static_exist else '❌ No encontrado'}
        </div>
        
        <h2>📄 Templates ({len(templates_list)}):</h2>
        <ul>
            {''.join([f'<li>📄 {template}</li>' for template in templates_list])}
        </ul>
        
        <h2>🛣️ Rutas disponibles:</h2>
        <ul>
            {''.join([f'<li>🔗 {route}</li>' for route in routes])}
        </ul>
        
        <h2>🔗 Enlaces de prueba:</h2>
        <ul>
            <li><a href="/">🏠 Página principal</a></li>
            <li><a href="/noticias">📰 Noticias</a></li>
            <li><a href="/login">🔐 Login</a></li>
            <li><a href="/register">📝 Registro</a></li>
            <li><a href="/dashboard">📊 Dashboard</a></li>
            <li><a href="/chat">💬 Chat</a></li>
            <li><a href="/api/test">🔧 API Test</a></li>
        </ul>
        
        <hr>
        <p><small>Aplicación Flask AVA - Puerto 8080 - Admin: admin/admin123</small></p>
    </body>
    </html>
    """

# Manejo de errores
@index_bp.errorhandler(404)
def not_found(error):
    return """
    <h1>❌ Página no encontrada</h1>
    <p>La página que buscas no existe.</p>
    <a href="/info">🔙 Volver a información</a>
    """, 404

@index_bp.errorhandler(500)
def internal_error(error):
    return """
    <h1>💥 Error interno del servidor</h1>
    <p>Algo salió mal en el servidor.</p>
    <a href="/info">🔙 Volver a información</a>
    """, 500