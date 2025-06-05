from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Configuración
    app.config['SECRET_KEY'] = 'tu-clave-secreta-aqui'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # 🔥 CREAR CARPETA UPLOADS AL INICIO
    from pathlib import Path
    uploads_dir = Path(app.root_path) / 'static' / 'images' / 'uploads'
    uploads_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Carpeta uploads creada: {uploads_dir}")
    
    # Registrar blueprints
    from routes.chat_routes import chat_bp
    app.register_blueprint(chat_bp)
    
    return app