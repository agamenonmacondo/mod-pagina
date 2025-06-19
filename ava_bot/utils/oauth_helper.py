import os
import json
import logging
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

def get_google_credentials_from_env(scopes):
    """Obtener credenciales Google desde variables de entorno"""
    
    # Cargar .env si existe
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("✅ Variables .env cargadas")
    except ImportError:
        logger.info("ℹ️ python-dotenv no disponible")
    
    # Verificar variables requeridas
    required_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET', 
        'GOOGLE_ACCESS_TOKEN',
        'GOOGLE_REFRESH_TOKEN'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Variables OAuth faltantes: {missing_vars}")
        return None
    
    try:
        # Crear credenciales desde env vars
        creds = Credentials(
            token=os.getenv('GOOGLE_ACCESS_TOKEN'),
            refresh_token=os.getenv('GOOGLE_REFRESH_TOKEN'),
            token_uri=os.getenv('GOOGLE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            scopes=scopes
        )
        
        # Refrescar si es necesario
        if creds.expired and creds.refresh_token:
            logger.info("🔄 Refrescando token OAuth...")
            creds.refresh(Request())
            logger.info("✅ Token OAuth refrescado")
        
        logger.info("✅ Credenciales OAuth desde env vars")
        return creds
        
    except Exception as e:
        logger.error(f"❌ Error creando credenciales: {e}")
        return None

def get_google_credentials_from_files(scopes):
    """Método legacy: credenciales desde archivos JSON"""
    
    # Buscar token.json en ubicaciones comunes
    possible_paths = [
        Path(__file__).parent.parent / 'token.json',
        Path('token.json'),
        Path('llmpagina/ava_bot/token.json')
    ]
    
    token_path = None
    for path in possible_paths:
        if path.exists():
            token_path = path
            break
    
    if not token_path:
        logger.error("❌ token.json no encontrado")
        return None
    
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        
        logger.info("✅ Credenciales desde archivos")
        return creds
        
    except Exception as e:
        logger.error(f"❌ Error cargando desde archivos: {e}")
        return None

def get_google_credentials(scopes):
    """Función principal: env vars primero, luego archivos"""
    
    # 1. PRIORIDAD: Variables de entorno
    creds = get_google_credentials_from_env(scopes)
    if creds:
        return creds
    
    # 2. FALLBACK: Archivos JSON
    logger.info("🔄 Env vars no disponibles, intentando archivos...")
    creds = get_google_credentials_from_files(scopes)
    if creds:
        return creds
    
    # 3. ERROR: Sin credenciales
    logger.error("❌ No hay credenciales OAuth disponibles")
    raise Exception("Credenciales OAuth no disponibles. Configura variables de entorno o archivos JSON.")