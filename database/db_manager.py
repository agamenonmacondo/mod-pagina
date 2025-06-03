import sqlite3
import uuid
import logging
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect('instance/users.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializar base de datos - Solo usuarios y autenticación"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            last_login TEXT,
            profile_image TEXT,
            phone TEXT,
            company TEXT,
            role TEXT DEFAULT 'user'
        )
    ''')
    
    # Tabla de sesiones de usuario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tabla de intentos de login
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_attempts (
            id TEXT PRIMARY KEY,
            username TEXT,
            ip_address TEXT,
            success INTEGER DEFAULT 0,
            attempted_at TEXT NOT NULL,
            user_agent TEXT
        )
    ''')
    
    # Crear usuarios por defecto
    _create_default_users(cursor)
    
    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada correctamente")

def _create_default_users(cursor):
    """Crear usuarios admin y demo por defecto"""
    # Usuario admin
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        admin_id = str(uuid.uuid4())
        password_hash = generate_password_hash('admin123')
        
        cursor.execute('''
            INSERT INTO users (
                id, username, email, password, first_name, last_name, 
                is_admin, is_active, created_at, role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            admin_id, 'admin', 'admin@ava.com', password_hash, 
            'Administrador', 'Sistema', 1, 1, 
            datetime.now().isoformat(), 'admin'
        ))
        logger.info("Usuario admin creado - username: admin, password: admin123")
    
    # Usuario demo
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'demo'")
    if cursor.fetchone()[0] == 0:
        demo_id = str(uuid.uuid4())
        password_hash = generate_password_hash('demo123')
        
        cursor.execute('''
            INSERT INTO users (
                id, username, email, password, first_name, last_name, 
                is_admin, is_active, created_at, role
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            demo_id, 'demo', 'demo@ava.com', password_hash, 
            'Usuario', 'Demo', 0, 1, 
            datetime.now().isoformat(), 'user'
        ))
        logger.info("Usuario demo creado - username: demo, password: demo123")

def log_login_attempt(username, ip_address, success, user_agent=None):
    """Registrar intento de login para seguridad"""
    try:
        conn = get_db_connection()
        attempt_id = str(uuid.uuid4())
        
        conn.execute('''
            INSERT INTO login_attempts (id, username, ip_address, success, attempted_at, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            attempt_id, username, ip_address, 
            1 if success else 0, datetime.now().isoformat(), user_agent
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error registrando intento de login: {e}")

def create_user_session(user_id, ip_address, user_agent=None):
    """Crear sesión de usuario"""
    try:
        conn = get_db_connection()
        session_id = str(uuid.uuid4())
        session_token = str(uuid.uuid4())
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        
        conn.execute('''
            INSERT INTO user_sessions (
                id, user_id, session_token, ip_address, user_agent, 
                created_at, expires_at, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id, user_id, session_token, ip_address, user_agent,
            datetime.now().isoformat(), expires_at, 1
        ))
        
        conn.commit()
        conn.close()
        return session_token
    except Exception as e:
        logger.error(f"Error creando sesión: {e}")
        return None