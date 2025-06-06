import os
import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import shutil

logger = logging.getLogger(__name__)

class CloudMemoryManager:
    """Gestor de memoria completo para cloud que maneja TODAS las memorias del proyecto AVA"""
    
    def __init__(self):
        self.is_cloud = self._detect_cloud_environment()
        self.data_path = self._get_data_path()
        self.memory_paths = self._define_memory_paths()
        self._ensure_directories()
        
    def _detect_cloud_environment(self):
        """Detecta si estamos en cloud"""
        cloud_indicators = [
            os.getenv('K_SERVICE'),           # Cloud Run
            os.getenv('GAE_ENV'),             # App Engine
            os.getenv('GOOGLE_CLOUD_PROJECT'), # Google Cloud
            os.getenv('CLOUD_ENV'),           # Variable personalizada
            os.path.exists('/.dockerenv')     # Docker container
        ]
        return any(cloud_indicators)
    
    def _get_data_path(self):
        """Ruta base para datos"""
        if self.is_cloud:
            return '/tmp/ava_data'
        else:
            return 'cloud_data'
    
    def _define_memory_paths(self):
        """Define todas las rutas de memoria del proyecto"""
        return {
            # Base de datos principales
            'users_db': f"{self.data_path}/users.db",
            'memory_db': f"{self.data_path}/memory.db",
            
            # Memoria multimodal específica
            'multimodal_db': f"{self.data_path}/multimodal_memory.db",
            'chroma_vectordb': f"{self.data_path}/chroma_vectordb",
            'embeddings_cache': f"{self.data_path}/embeddings_cache",
            
            # Archivos multimedia
            'stored_images': f"{self.data_path}/stored_images",
            'uploaded_images': f"{self.data_path}/uploaded_images", 
            'generated_images': f"{self.data_path}/generated_images",
            'temp_uploads': f"{self.data_path}/temp_uploads",
            
            # Cache y logs
            'logs': f"{self.data_path}/logs",
            'cache': f"{self.data_path}/cache",
            'sessions': f"{self.data_path}/sessions",
            
            # Configuración
            'config': f"{self.data_path}/config",
            'backups': f"{self.data_path}/backups"
        }
    
    def _ensure_directories(self):
        """Crear TODOS los directorios necesarios"""
        try:
            # Crear directorio base
            os.makedirs(self.data_path, exist_ok=True)
            
            # Crear todos los subdirectorios
            for path_name, path_value in self.memory_paths.items():
                if path_name.endswith('_db'):
                    # Para BD, crear solo el directorio padre
                    os.makedirs(os.path.dirname(path_value), exist_ok=True)
                else:
                    # Para directorios, crear completo
                    os.makedirs(path_value, exist_ok=True)
            
            logger.info(f"✅ Directorios de memoria creados en: {self.data_path}")
            
        except Exception as e:
            logger.error(f"❌ Error creando directorios: {e}")
            raise
    
    def init_users_database(self):
        """Inicializar BD de usuarios"""
        db_path = self.memory_paths['users_db']
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Tabla de usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    is_admin INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    role TEXT DEFAULT 'user',
                    preferences TEXT,
                    profile_image TEXT
                )
            ''')
            
            # Tabla de sesiones de usuario
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Índices
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)')
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ BD usuarios inicializada: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando BD usuarios: {e}")
            return False
    
    def init_memory_database(self):
        """Inicializar BD de memoria estándar"""
        db_path = self.memory_paths['memory_db']
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Tabla de conversaciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    ava_response TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    message_type TEXT DEFAULT 'text',
                    metadata TEXT
                )
            ''')
            
            # Tabla de contexto de usuario
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_context (
                    user_id TEXT PRIMARY KEY,
                    current_context TEXT,
                    conversation_history TEXT,
                    preferences TEXT,
                    last_updated TEXT,
                    context_summary TEXT
                )
            ''')
            
            # Tabla de memoria a corto plazo
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS short_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    expires_at TEXT,
                    memory_type TEXT DEFAULT 'conversation',
                    importance_score REAL DEFAULT 1.0
                )
            ''')
            
            # Índices
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_short_memory_user ON short_term_memory(user_id)')
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ BD memoria estándar inicializada: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando BD memoria: {e}")
            return False
    
    def init_multimodal_database(self):
        """Inicializar BD de memoria multimodal"""
        db_path = self.memory_paths['multimodal_db']
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Tabla principal de memoria multimodal
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS multimodal_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    content_text TEXT,
                    content_data BLOB,
                    file_path TEXT,
                    file_name TEXT,
                    file_size INTEGER,
                    mime_type TEXT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT,
                    tags TEXT,
                    metadata TEXT
                )
            ''')
            
            # Tabla de embeddings/vectores
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id INTEGER NOT NULL,
                    embedding_type TEXT NOT NULL,
                    embedding_vector TEXT NOT NULL,
                    model_used TEXT,
                    dimensions INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (memory_id) REFERENCES multimodal_memories (id)
                )
            ''')
            
            # Tabla de relaciones entre memorias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id_1 INTEGER NOT NULL,
                    memory_id_2 INTEGER NOT NULL,
                    relation_type TEXT NOT NULL,
                    similarity_score REAL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (memory_id_1) REFERENCES multimodal_memories (id),
                    FOREIGN KEY (memory_id_2) REFERENCES multimodal_memories (id)
                )
            ''')
            
            # Tabla de análisis de imágenes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS image_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id INTEGER NOT NULL,
                    analysis_type TEXT NOT NULL,
                    analysis_result TEXT NOT NULL,
                    confidence_score REAL,
                    model_used TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (memory_id) REFERENCES multimodal_memories (id)
                )
            ''')
            
            # Índices para performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_multimodal_user ON multimodal_memories(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_multimodal_type ON multimodal_memories(content_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_multimodal_timestamp ON multimodal_memories(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_embeddings_memory ON memory_embeddings(memory_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_memory1 ON memory_relations(memory_id_1)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_analysis_memory ON image_analysis(memory_id)')
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ BD memoria multimodal inicializada: {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando BD multimodal: {e}")
            return False
    
    def init_vector_database(self):
        """Inicializar base de datos vectorial (ChromaDB)"""
        try:
            chroma_path = self.memory_paths['chroma_vectordb']
            
            # Crear estructura para ChromaDB
            collections_path = f"{chroma_path}/collections"
            os.makedirs(collections_path, exist_ok=True)
            
            # Crear archivo de configuración
            config = {
                "created_at": datetime.now().isoformat(),
                "environment": "cloud" if self.is_cloud else "local",
                "collections": {
                    "user_memories": {
                        "type": "text_embeddings",
                        "model": "all-MiniLM-L6-v2",
                        "dimensions": 384
                    },
                    "image_memories": {
                        "type": "image_embeddings", 
                        "model": "clip-vit-base-patch32",
                        "dimensions": 512
                    },
                    "multimodal_memories": {
                        "type": "multimodal_embeddings",
                        "model": "mixed",
                        "dimensions": 768
                    }
                }
            }
            
            config_path = f"{chroma_path}/config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"✅ BD vectorial inicializada: {chroma_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando BD vectorial: {e}")
            return False
    
    def create_config_files(self):
        """Crear archivos de configuración necesarios"""
        try:
            config_path = self.memory_paths['config']
            
            # Configuración principal
            main_config = {
                "environment": "cloud" if self.is_cloud else "local",
                "data_path": self.data_path,
                "memory_settings": {
                    "max_conversation_history": 100,
                    "short_term_memory_days": 7,
                    "cleanup_old_memories_days": 30,
                    "max_file_size_mb": 16,
                    "supported_image_formats": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
                    "supported_document_formats": [".txt", ".pdf", ".docx", ".md"]
                },
                "embedding_settings": {
                    "text_model": "all-MiniLM-L6-v2",
                    "image_model": "clip-vit-base-patch32",
                    "batch_size": 32,
                    "similarity_threshold": 0.7
                },
                "paths": self.memory_paths,
                "created_at": datetime.now().isoformat()
            }
            
            with open(f"{config_path}/memory_config.json", 'w') as f:
                json.dump(main_config, f, indent=2)
            
            # Archivo de estado del sistema
            status_config = {
                "initialized": True,
                "last_startup": datetime.now().isoformat(),
                "databases_status": {
                    "users_db": "not_checked",
                    "memory_db": "not_checked", 
                    "multimodal_db": "not_checked",
                    "vector_db": "not_checked"
                },
                "cleanup_status": {
                    "last_cleanup": None,
                    "next_cleanup": None
                }
            }
            
            with open(f"{config_path}/system_status.json", 'w') as f:
                json.dump(status_config, f, indent=2)
            
            logger.info("✅ Archivos de configuración creados")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando configuración: {e}")
            return False
    
    def validate_memory_system(self):
        """Validar que todo el sistema de memoria esté funcionando"""
        validation_results = {
            "directories": {},
            "databases": {},
            "config_files": {},
            "permissions": {},
            "total_issues": 0
        }
        
        # Validar directorios
        for name, path in self.memory_paths.items():
            if name.endswith('_db'):
                # Para BD, verificar directorio padre
                parent_dir = os.path.dirname(path)
                exists = os.path.exists(parent_dir)
                writable = os.access(parent_dir, os.W_OK) if exists else False
            else:
                # Para directorios normales
                exists = os.path.exists(path)
                writable = os.access(path, os.W_OK) if exists else False
            
            validation_results["directories"][name] = {
                "exists": exists,
                "writable": writable,
                "path": path
            }
            
            if not exists or not writable:
                validation_results["total_issues"] += 1
        
        # Validar bases de datos
        db_paths = {
            "users_db": self.memory_paths['users_db'],
            "memory_db": self.memory_paths['memory_db'], 
            "multimodal_db": self.memory_paths['multimodal_db']
        }
        
        for db_name, db_path in db_paths.items():
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()
                
                validation_results["databases"][db_name] = {
                    "accessible": True,
                    "tables": tables,
                    "table_count": len(tables)
                }
                
            except Exception as e:
                validation_results["databases"][db_name] = {
                    "accessible": False,
                    "error": str(e)
                }
                validation_results["total_issues"] += 1
        
        # Resultado final
        validation_results["success"] = validation_results["total_issues"] == 0
        validation_results["summary"] = {
            "total_components": len(self.memory_paths) + len(db_paths),
            "issues_found": validation_results["total_issues"],
            "environment": "cloud" if self.is_cloud else "local",
            "data_path": self.data_path
        }
        
        return validation_results
    
    def init_all_memories(self):
        """Inicializar TODAS las memorias del proyecto"""
        logger.info("🧠 Inicializando sistema completo de memoria...")
        
        success_count = 0
        total_operations = 5
        
        # 1. Crear directorios
        try:
            self._ensure_directories()
            success_count += 1
            logger.info("✅ Directorios creados")
        except Exception as e:
            logger.error(f"❌ Error directorios: {e}")
        
        # 2. Inicializar BD usuarios
        if self.init_users_database():
            success_count += 1
        
        # 3. Inicializar BD memoria estándar
        if self.init_memory_database():
            success_count += 1
        
        # 4. Inicializar BD multimodal
        if self.init_multimodal_database():
            success_count += 1
        
        # 5. Crear configuraciones
        if self.create_config_files():
            success_count += 1
        
        # Resultado
        if success_count == total_operations:
            logger.info("🎉 Sistema de memoria inicializado completamente")
            
            # Validar sistema
            validation = self.validate_memory_system()
            if validation["success"]:
                logger.info("✅ Validación del sistema exitosa")
            else:
                logger.warning(f"⚠️ {validation['total_issues']} problemas encontrados en validación")
            
            return True
        else:
            logger.error(f"❌ Solo {success_count}/{total_operations} operaciones exitosas")
            return False
    
    def get_memory_info(self):
        """Obtener información completa del sistema de memoria"""
        info = {
            "environment": "cloud" if self.is_cloud else "local",
            "data_path": self.data_path,
            "paths": self.memory_paths,
            "validation": self.validate_memory_system(),
            "timestamp": datetime.now().isoformat()
        }
        
        return info

# Instancia global
cloud_memory_manager = CloudMemoryManager()

def init_cloud_memory():
    """Función principal para inicializar memoria en cloud"""
    return cloud_memory_manager.init_all_memories()

def get_cloud_memory_info():
    """Obtener información de memoria cloud"""
    return cloud_memory_manager.get_memory_info()