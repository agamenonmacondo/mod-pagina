import os
import sys
import base64
import hashlib
from datetime import datetime
from pathlib import Path
import json
from PIL import Image
import sqlite3
import time
import platform

# ✅ RUTAS SIMPLIFICADAS Y ROBUSTAS
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent

class SQLiteMemoryManager:
    """Sistema de memoria SQLite mejorado - SIN DEPENDENCIA DE JSON"""
    
    def __init__(self):
        self.db_path = self._get_universal_db_path()
        self.images_dir = current_dir / "stored_images"
        self.images_dir.mkdir(exist_ok=True)
        self.init_database()
        print(f"🗃️ SQLiteMemoryManager inicializado. DB: {self.db_path}")
        print(f"🖼️ Directorio de imágenes: {self.images_dir}")
    
    def _get_universal_db_path(self) -> Path:
        """Detecta automáticamente la ruta correcta según el entorno"""
        
        # 1. Variable de entorno (máxima prioridad)
        if db_path_env := os.getenv("MEMORY_DB_PATH"):
            return Path(db_path_env)
        
        # 2. Detectar Azure/Cloud
        if self._is_cloud_environment():
            # Usar directorio temporal writable
            return Path("/tmp/ava_memory.db")
        
        # 3. Desarrollo local (tu caso actual)
        current_dir = Path(__file__).parent
        return current_dir / "memory.db"
    
    def _is_cloud_environment(self) -> bool:
        """Detecta si está en cloud/contenedor"""
        return (
            # Azure indicators
            os.getenv("WEBSITE_SITE_NAME") or
            os.getenv("FUNCTIONS_WORKER_RUNTIME") or
            # Docker indicators
            os.path.exists("/.dockerenv") or
            # Linux + /app directory (contenedor típico)
            (platform.system() == "Linux" and os.path.exists("/app"))
        )
    
    def init_database(self):
        """Inicializar la base de datos - SINTAXIS CORREGIDA"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Tabla principal multimodal
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS memory_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        entry_type TEXT NOT NULL,
                        content TEXT,
                        response TEXT,
                        metadata TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Tabla especializada para archivos
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS file_attachments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        memory_entry_id INTEGER,
                        original_path TEXT,
                        stored_path TEXT,
                        filename TEXT,
                        file_hash TEXT UNIQUE,
                        file_size INTEGER,
                        dimensions TEXT,
                        format TEXT,
                        description TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (memory_entry_id) REFERENCES memory_entries(id)
                    )
                ''')
                
                # Índices para optimización
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_user_timestamp 
                    ON memory_entries(user_id, timestamp DESC)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_content_search 
                    ON memory_entries(user_id, entry_type, content)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_file_hash 
                    ON file_attachments(file_hash)
                ''')
                
                print("✅ Base de datos SQLite inicializada con índices optimizados")
                
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")
    
    def add_message(self, user_id, message, response=None):
        """Agregar mensaje de texto a SQLite - OPTIMIZADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO memory_entries (user_id, entry_type, content, response)
                    VALUES (?, 'message', ?, ?)
                ''', (user_id, message, response))
                
                # ✅ SINTAXIS CORREGIDA: Usar LIMIT con subquery
                conn.execute('''
                    DELETE FROM memory_entries 
                    WHERE user_id = ? AND entry_type = 'message' 
                    AND id NOT IN (
                        SELECT id FROM memory_entries 
                        WHERE user_id = ? AND entry_type = 'message'
                        ORDER BY timestamp DESC 
                        LIMIT 10
                    )
                ''', (user_id, user_id))
                
                print(f"💬 Mensaje agregado a SQLite para {user_id}")
                return True
                
        except Exception as e:
            print(f"❌ Error agregando mensaje a SQLite: {e}")
            return False
    
    def add_image(self, user_id, image_path, description=""):
        """Agregar imagen a SQLite - ERROR CORREGIDO"""
        try:
            image_path = Path(image_path)
            
            if not image_path.exists():
                print(f"❌ Imagen no encontrada: {image_path}")
                return False
            
            # Verificar imagen válida
            try:
                with Image.open(image_path) as img:
                    width, height = img.size
                    format = img.format
                    print(f"🖼️ Imagen válida: {width}x{height} {format}")
            except Exception as e:
                print(f"❌ No es una imagen válida: {e}")
                return False
            
            # Generar hash único
            with open(image_path, 'rb') as f:
                image_data = f.read()
                image_hash = hashlib.md5(image_data).hexdigest()
            
            # Verificar si ya existe
            with sqlite3.connect(self.db_path) as conn:
                existing = conn.execute('''
                    SELECT fa.stored_path FROM file_attachments fa
                    JOIN memory_entries me ON fa.memory_entry_id = me.id
                    WHERE me.user_id = ? AND fa.file_hash = ?
                ''', (user_id, image_hash)).fetchone()
                
                if existing:
                    print(f"♻️ Imagen ya existe para {user_id}: {existing[0]}")
                    # Actualizar timestamp de la entrada existente
                    conn.execute('''
                        UPDATE memory_entries SET timestamp = CURRENT_TIMESTAMP
                        WHERE id IN (
                            SELECT me.id FROM memory_entries me
                            JOIN file_attachments fa ON me.id = fa.memory_entry_id
                            WHERE me.user_id = ? AND fa.file_hash = ?
                        )
                    ''', (user_id, image_hash))
                    return True
            
            # Copiar imagen si no existe
            stored_image_path = self.images_dir / f"{user_id}_{image_hash}_{image_path.name}"
            
            if not stored_image_path.exists():
                with open(image_path, 'rb') as src, open(stored_image_path, 'wb') as dst:
                    dst.write(src.read())
                print(f"📁 Imagen copiada a: {stored_image_path}")
            
            # Guardar en base de datos con transacción
            with sqlite3.connect(self.db_path) as conn:
                # Insertar entrada principal
                cursor = conn.execute('''
                    INSERT INTO memory_entries (user_id, entry_type, metadata)
                    VALUES (?, 'image', ?)
                ''', (user_id, json.dumps({'description': description})))
                
                memory_entry_id = cursor.lastrowid
                
                # Insertar detalles del archivo
                conn.execute('''
                    INSERT INTO file_attachments 
                    (memory_entry_id, original_path, stored_path, filename, file_hash, 
                     file_size, dimensions, format, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (memory_entry_id, str(image_path), str(stored_image_path), 
                      image_path.name, image_hash, len(image_data), 
                      f"{width}x{height}", format, description))
                
                # ✅ LIMPIAR IMÁGENES ANTIGUAS - SINTAXIS CORREGIDA
                # Primero obtener IDs de entradas antiguas
                old_entries = conn.execute('''
                    SELECT me.id, fa.stored_path FROM memory_entries me
                    JOIN file_attachments fa ON me.id = fa.memory_entry_id
                    WHERE me.user_id = ? AND me.entry_type = 'image'
                    ORDER BY me.timestamp ASC
                ''', (user_id,)).fetchall()
                
                # Si hay más de 10, eliminar las más antiguas
                if len(old_entries) > 10:
                    entries_to_remove = old_entries[:-10]  # Mantener las últimas 10
                    
                    for entry_id, old_path in entries_to_remove:
                        # Eliminar archivo físico
                        old_file_path = Path(old_path)
                        if old_file_path.exists():
                            old_file_path.unlink()
                            print(f"🗑️ Imagen antigua eliminada: {old_file_path}")
                        
                        # Eliminar registros
                        conn.execute('DELETE FROM file_attachments WHERE memory_entry_id = ?', (entry_id,))
                        conn.execute('DELETE FROM memory_entries WHERE id = ?', (entry_id,))
                    
                    print(f"🧹 Limpieza: {len(entries_to_remove)} imágenes antiguas eliminadas")
                
                print(f"🖼️ Imagen guardada en SQLite para {user_id}")
                return True
                
        except Exception as e:
            print(f"❌ Error agregando imagen a SQLite: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def search_messages(self, user_id, query, limit=5):
        """Búsqueda en SQLite con indexación optimizada"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                results = conn.execute('''
                    SELECT content, response, timestamp FROM memory_entries
                    WHERE user_id = ? AND entry_type = 'message' 
                    AND (content LIKE ? OR response LIKE ?)
                    ORDER BY timestamp DESC LIMIT ?
                ''', (user_id, f'%{query}%', f'%{query}%', limit)).fetchall()
                
                # Convertir a formato compatible
                formatted_results = []
                for content, response, timestamp in results:
                    formatted_results.append({
                        'message': content,
                        'response': response,
                        'timestamp': timestamp
                    })
                
                return formatted_results
                
        except Exception as e:
            print(f"❌ Error buscando mensajes en SQLite: {e}")
            return []
    
    def search_images(self, user_id, query="", limit=5):
        """Buscar imágenes en SQLite - OPTIMIZADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if query:
                    results = conn.execute('''
                        SELECT me.metadata, fa.* FROM memory_entries me
                        JOIN file_attachments fa ON me.id = fa.memory_entry_id
                        WHERE me.user_id = ? AND me.entry_type = 'image'
                        AND (fa.description LIKE ? OR fa.filename LIKE ?)
                        ORDER BY me.timestamp DESC LIMIT ?
                    ''', (user_id, f'%{query}%', f'%{query}%', limit)).fetchall()
                else:
                    results = conn.execute('''
                        SELECT me.metadata, fa.* FROM memory_entries me
                        JOIN file_attachments fa ON me.id = fa.memory_entry_id
                        WHERE me.user_id = ? AND me.entry_type = 'image'
                        ORDER BY me.timestamp DESC LIMIT ?
                    ''', (user_id, limit)).fetchall()
                
                # Formatear resultados
                formatted_results = []
                for row in results:
                    if len(row) >= 11:  # Verificar que tenga todos los campos
                        metadata = row[0]
                        mem_id, orig_path, stored_path, filename, file_hash, file_size, dims, format, desc, timestamp = row[1:11]
                        
                        formatted_results.append({
                            'type': 'image',
                            'original_path': orig_path,
                            'stored_path': stored_path,
                            'filename': filename,
                            'description': desc,
                            'hash': file_hash,
                            'size': file_size,
                            'dimensions': dims,
                            'format': format,
                            'timestamp': timestamp
                        })
                
                return formatted_results
                
        except Exception as e:
            print(f"❌ Error buscando imágenes en SQLite: {e}")
            return []
    
    def get_stats(self, user_id):
        """Obtener estadísticas del usuario desde SQLite - OPTIMIZADO"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Contar total de entradas
                total_count = conn.execute('''
                    SELECT COUNT(*) FROM memory_entries WHERE user_id = ?
                ''', (user_id,)).fetchone()[0]
                
                # Obtener última entrada con detalles
                last_entry = conn.execute('''
                    SELECT me.entry_type, me.content, me.response, me.timestamp, me.metadata,
                           fa.filename, fa.description, fa.dimensions, fa.format
                    FROM memory_entries me
                    LEFT JOIN file_attachments fa ON me.id = fa.memory_entry_id
                    WHERE me.user_id = ? 
                    ORDER BY me.timestamp DESC LIMIT 1
                ''', (user_id,)).fetchone()
                
                if last_entry:
                    entry_type, content, response, timestamp, metadata, filename, description, dimensions, format = last_entry
                    
                    if entry_type == 'image':
                        last_message = {
                            'type': entry_type,
                            'filename': filename,
                            'description': description,
                            'dimensions': dimensions,
                            'format': format,
                            'timestamp': timestamp
                        }
                    else:
                        last_message = {
                            'type': entry_type,
                            'message': content,
                            'response': response,
                            'timestamp': timestamp
                        }
                else:
                    last_message = None
                    timestamp = None
                
                return {
                    'total_messages': total_count,
                    'user_id': user_id,
                    'last_message': last_message,
                    'last_timestamp': timestamp
                }
                
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas de SQLite: {e}")
            return {
                'total_messages': 0,
                'user_id': user_id,
                'last_message': None,
                'error': str(e)
            }

    def migrate_from_json(self, json_file_path):
        """Migrar datos existentes del JSON a SQLite"""
        try:
            json_path = Path(json_file_path)
            if not json_path.exists():
                print(f"📝 No hay archivo JSON para migrar: {json_path}")
                return False
            
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            print(f"🔄 Migrando {len(json_data)} usuarios del JSON a SQLite...")
            
            with sqlite3.connect(self.db_path) as conn:
                for user_id, entries in json_data.items():
                    print(f"👤 Migrando usuario: {user_id} ({len(entries)} entradas)")
                    
                    for entry in entries:
                        if entry.get('type') == 'image':
                            # Migrar imagen
                            cursor = conn.execute('''
                                INSERT INTO memory_entries (user_id, entry_type, metadata, timestamp)
                                VALUES (?, 'image', ?, ?)
                            ''', (user_id, json.dumps({'description': entry.get('description', '')}), entry.get('timestamp')))
                            
                            memory_entry_id = cursor.lastrowid
                            
                            # Insertar detalles del archivo
                            conn.execute('''
                                INSERT INTO file_attachments 
                                (memory_entry_id, original_path, stored_path, filename, file_hash, 
                                 file_size, dimensions, format, description, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (memory_entry_id, entry.get('original_path'), entry.get('stored_path'),
                                  entry.get('filename'), entry.get('hash'), entry.get('size'),
                                  entry.get('dimensions'), entry.get('format'), entry.get('description'),
                                  entry.get('timestamp')))
                        else:
                            # Migrar mensaje de texto
                            conn.execute('''
                                INSERT INTO memory_entries (user_id, entry_type, content, response, timestamp)
                                VALUES (?, 'message', ?, ?, ?)
                            ''', (user_id, entry.get('message'), entry.get('response'), entry.get('timestamp')))
            
            # Hacer backup del JSON original
            backup_path = json_path.with_suffix('.json.backup')
            json_path.rename(backup_path)
            print(f"✅ Migración completada. JSON respaldado en: {backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error migrando JSON a SQLite: {e}")
            return False

class MemoryAdapter:
    """Adaptador para el sistema de memoria - SOLO SQLITE"""
    
    def __init__(self):
        try:
            self.memory_manager = SQLiteMemoryManager()
            self.backend_type = "SQLite"
            
            # Migrar datos JSON existentes si existen
            json_file = current_dir / "memory_data.json"
            if json_file.exists():
                print("🔄 Detectado archivo JSON existente, migrando a SQLite...")
                self.memory_manager.migrate_from_json(json_file)
            
            print("✅ MemoryAdapter inicializado con backend SQLite puro")
                
        except Exception as e:
            print(f"❌ Error inicializando MemoryAdapter: {e}")
            self.memory_manager = None
            self.backend_type = "None"
    
    def process(self, params):
        """Procesar operaciones de memoria - SOLO SQLITE"""
        try:
            if not self.memory_manager:
                return {
                    "success": False,
                    "message": "❌ Memory manager no disponible"
                }
            
            user_id = params.get('user_id', 'default_user')
            action = params.get('action', 'get_stats')
            
            print(f"🧠 Procesando memoria [SQLite] - User: {user_id}, Action: {action}")
            
            if action == 'get_stats':
                stats = self.memory_manager.get_stats(user_id)
                return {
                    "success": True,
                    "action": "estadísticas",
                    "backend": self.backend_type,
                    "data": stats,
                    "message": f"📊 Estadísticas obtenidas [SQLite] para {user_id}: {stats['total_messages']} entradas"
                }
            
            elif action == 'add_message':
                message = params.get('message', '').strip()
                response = params.get('response', '').strip()
                
                if not message:
                    return {
                        "success": False,
                        "message": "❌ Mensaje vacío no se puede guardar"
                    }
                
                success = self.memory_manager.add_message(user_id, message, response)
                if success:
                    return {
                        "success": True,
                        "action": "mensaje agregado",
                        "backend": self.backend_type,
                        "message": f"💾 Mensaje guardado [SQLite] para {user_id}"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ Error guardando mensaje en SQLite"
                    }
            
            elif action == 'search':
                query = params.get('query', '').strip()
                if not query:
                    return {
                        "success": False,
                        "message": "❌ Query de búsqueda vacío"
                    }
                
                results = self.memory_manager.search_messages(user_id, query)
                return {
                    "success": True,
                    "action": "búsqueda",
                    "backend": self.backend_type,
                    "results": results,
                    "count": len(results),
                    "message": f"🔍 Encontrados {len(results)} resultados [SQLite] para '{query}'"
                }
            
            elif action == 'add_image':
                image_path = params.get('image_path', '').strip()
                description = params.get('description', '').strip()
                
                if not image_path:
                    return {
                        "success": False,
                        "message": "❌ Ruta de imagen requerida"
                    }
                
                success = self.memory_manager.add_image(user_id, image_path, description)
                if success:
                    return {
                        "success": True,
                        "action": "imagen agregada",
                        "backend": self.backend_type,
                        "message": f"🖼️ Imagen guardada [SQLite] para {user_id}: {Path(image_path).name}"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"❌ Error guardando imagen en SQLite"
                    }
            
            elif action == 'search_images':
                query = params.get('query', '').strip()
                
                results = self.memory_manager.search_images(user_id, query)
                return {
                    "success": True,
                    "action": "búsqueda de imágenes",
                    "backend": self.backend_type,
                    "results": results,
                    "count": len(results),
                    "message": f"🖼️ Encontradas {len(results)} imágenes [SQLite] para '{query}'"
                }
            
            else:
                return {
                    "success": False,
                    "message": f"❌ Acción no reconocida: {action}"
                }
                
        except Exception as e:
            error_msg = f"❌ Error en MemoryAdapter.process [SQLite]: {str(e)}"
            print(error_msg)
            return {
                "success": False,
                "message": error_msg
            }

# ✅ FUNCIÓN DE TESTING SQLITE PURO
def test_sqlite_memory():
    """Test del sistema SQLite puro"""
    print("🗃️ Probando Sistema SQLite Puro...")
    print("=" * 60)
    
    adapter = MemoryAdapter()
    
    test_user = "sqlite_test_user"
    
    # Test 1: Estadísticas iniciales
    print("\n📋 TEST 1: Estadísticas iniciales")
    result1 = adapter.process({
        'user_id': test_user,
        'action': 'get_stats'
    })
    print(f"📊 Resultado: {result1}")
    
    # Test 2: Agregar mensajes
    print("\n📋 TEST 2: Agregar 5 mensajes")
    for i in range(5):
        result = adapter.process({
            'user_id': test_user,
            'action': 'add_message',
            'message': f'Mensaje SQLite {i+1}',
            'response': f'Respuesta SQLite {i+1}'
        })
        print(f"💬 Mensaje {i+1}: {result['success']}")
    
    # Test 3: Búsqueda
    print("\n📋 TEST 3: Búsqueda de mensajes")
    result3 = adapter.process({
        'user_id': test_user,
        'action': 'search',
        'query': 'SQLite'
    })
    print(f"🔍 Resultado búsqueda: {result3}")
    
    # Test 4: Agregar imagen
    print("\n📋 TEST 4: Agregar imagen")
    test_image_path = r"C:\Users\h\Downloads\ChatGPT Image 1 may 2025, 05_44_25 a.m..png"
    
    if Path(test_image_path).exists():
        result4 = adapter.process({
            'user_id': test_user,
            'action': 'add_image',
            'image_path': test_image_path,
            'description': 'Imagen de prueba SQLite puro'
        })
        print(f"🖼️ Resultado imagen: {result4}")
        
        # Test 5: Buscar imágenes
        print("\n📋 TEST 5: Buscar imágenes")
        result5 = adapter.process({
            'user_id': test_user,
            'action': 'search_images',
            'query': 'SQLite'
        })
        print(f"🔍 Resultado búsqueda imágenes: {result5}")
    else:
        print(f"⚠️ Imagen de prueba no encontrada: {test_image_path}")
    
    # Test 6: Estadísticas finales
    print("\n📋 TEST 6: Estadísticas finales")
    result6 = adapter.process({
        'user_id': test_user,
        'action': 'get_stats'
    })
    print(f"📊 Estadísticas finales: {result6}")
    
    print("\n✅ Tests SQLite completados")

if __name__ == "__main__":
    # Solo test SQLite - SIN JSON
    test_sqlite_memory()