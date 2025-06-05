import os
from pathlib import Path

class ImageConfig:
    """Configuración para almacenamiento de imágenes"""
    
    # 🔥 DIRECTORIO BASE DE LA APLICACIÓN
    BASE_DIR = Path(__file__).parent
    
    # 🔥 USAR LA CARPETA EXISTENTE DE AVA_BOT
    UPLOAD_DIR = BASE_DIR / 'llmpagina' / 'ava_bot' / 'uploaded images'
    
    # 🔥 DIRECTORIO PARA IMÁGENES GENERADAS (MANTENER SEPARADO)
    GENERATED_DIR = BASE_DIR / 'llmpagina' / 'ava_bot' / 'generated_images'
    
    # 🔥 URL BASE PARA SERVIR IMÁGENES
    UPLOAD_URL_PREFIX = '/images/uploads'
    GENERATED_URL_PREFIX = '/images/generated'
    
    # 🔥 CONFIGURACIÓN DE ARCHIVOS
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    
    @classmethod
    def setup_directories(cls):
        """Crear directorios si no existen"""
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        cls.GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        print(f"📁 Directorios configurados:")
        print(f"   📤 Uploads: {cls.UPLOAD_DIR}")
        print(f"   🎨 Generated: {cls.GENERATED_DIR}")
        print(f"   📂 Upload existe: {cls.UPLOAD_DIR.exists()}")
        print(f"   📂 Generated existe: {cls.GENERATED_DIR.exists()}")
    
    @classmethod
    def get_upload_path(cls, filename):
        """Obtener ruta completa para archivo subido"""
        return cls.UPLOAD_DIR / filename
    
    @classmethod
    def get_upload_url(cls, filename):
        """Obtener URL para archivo subido"""
        return f"{cls.UPLOAD_URL_PREFIX}/{filename}"
    
    @classmethod
    def get_generated_path(cls, filename):
        """Obtener ruta completa para imagen generada"""
        return cls.GENERATED_DIR / filename
    
    @classmethod
    def get_generated_url(cls, filename):
        """Obtener URL para imagen generada"""
        return f"{cls.GENERATED_URL_PREFIX}/{filename}"