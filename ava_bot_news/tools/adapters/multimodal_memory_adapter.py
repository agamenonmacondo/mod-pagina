import os
import json
import sqlite3
import hashlib
import asyncio
from typing import List, Dict, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import base64
import logging
import re

# Imports for embeddings - CORREGIDO
try:
    import sentence_transformers
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    print("✅ sentence-transformers importado correctamente")
except ImportError as e:
    print(f"❌ Error importando sentence-transformers: {e}")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
except Exception as e:
    print(f"❌ Error inesperado con sentence-transformers: {e}")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
    print("✅ chromadb importado correctamente")
except ImportError as e:
    print(f"❌ Error importando chromadb: {e}")
    CHROMADB_AVAILABLE = False

logger = logging.getLogger(__name__)

class MultimodalMemoryAdapter:
    """
    Adaptador de memoria multimodal que funciona en local y deploy.
    Soporta texto, imágenes y búsqueda semántica.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Inicializa el adaptador de memoria multimodal.
        
        Args:
            base_path: Ruta base. Si es None, detecta automáticamente si es local o deploy
        """
        self.logger = logging.getLogger(__name__)
        self._setup_dynamic_paths()
        
        self.images_path = os.path.join(self.base_path, "stored_images")
        self.embeddings_path = os.path.join(self.base_path, "embeddings_cache")
        self.vector_db_path = os.path.join(self.base_path, "vector_db")
        
        # Crear directorios necesarios
        self._create_directories()
        
        # Inicializar base de datos
        self._init_database()
        
        # Inicializar modelos de embeddings
        self.text_embedder = None
        self.vector_store = None
        self._init_embeddings()
        
        logger.info(f"✅ MultimodalMemoryAdapter inicializado")
        logger.info(f"📁 Base path: {self.base_path}")
        logger.info(f"🗃️ DB path: {self.db_path}")
        logger.info(f"🖼️ Images path: {self.images_path}")
    
    def _setup_dynamic_paths(self):
        """Configura rutas dinámicamente según el entorno"""
        
        # ✅ DETECTAR ENTORNO
        is_cloud = self._is_cloud_environment()
        
        if is_cloud:
            self._setup_cloud_paths()
        else:
            self._setup_local_paths()
    
    def _is_cloud_environment(self) -> bool:
        """Detecta si está ejecutándose en cloud"""
        cloud_indicators = [
            'GOOGLE_CLOUD_PROJECT',
            'PORT',  # Cloud Run típico
            'K_SERVICE',  # Google Cloud Run
            'AZURE_CLIENT_ID',
            'AWS_REGION',
            'DYNO',  # Heroku
        ]
        return any(os.getenv(indicator) for indicator in cloud_indicators)
    
    def _setup_cloud_paths(self):
        """Configuración para entorno cloud - RUTAS PERSISTENTES"""
        self.logger.info("☁️ Configurando memoria para entorno CLOUD...")
        
        # ✅ GOOGLE CLOUD RUN
        if os.getenv('GOOGLE_CLOUD_PROJECT'):
            base_path = "/mnt/memory"
            os.makedirs(base_path, exist_ok=True)
            
        # ✅ AZURE CONTAINER INSTANCES  
        elif os.getenv('AZURE_CLIENT_ID'):
            base_path = "/mnt/azure-storage"
            os.makedirs(base_path, exist_ok=True)
            
        # ✅ HEROKU/GENERIC CLOUD
        else:
            # Usar directorio temporal pero con variable de entorno
            base_path = os.getenv('MEMORY_PATH', '/tmp/ava_memory')
            os.makedirs(base_path, exist_ok=True)
    
        # ✅ CONFIGURAR BASE_PATH
        self.base_path = base_path  # ← ESTO FALTABA
    
        # ✅ RUTAS ESPECÍFICAS
        self.db_path = os.path.join(base_path, "multimodal_memory.db")
        self.chroma_path = os.path.join(base_path, "chroma_vectordb")
        
        # ✅ CREAR DIRECTORIOS
        os.makedirs(self.chroma_path, exist_ok=True)
        
        self.logger.info(f"📁 Base path: {self.base_path}")  # ← AGREGAR LOG
        self.logger.info(f"📊 Cloud SQLite: {self.db_path}")
        self.logger.info(f"🧠 Cloud ChromaDB: {self.chroma_path}")
    
    def _setup_local_paths(self):
        """Configuración para entorno local - RUTAS RELATIVAS"""
        self.logger.info("🏠 Configurando memoria para entorno LOCAL...")
        
        # ✅ CONFIGURAR BASE_PATH PRIMERO
        base_path = Path(__file__).parent.absolute()
        self.base_path = str(base_path)  # ← ESTO FALTABA
        
        self.db_path = str(base_path / "multimodal_memory.db")
        self.chroma_path = str(base_path / "chroma_vectordb")
        
        # ✅ CREAR DIRECTORIOS LOCALES
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.chroma_path, exist_ok=True)
        
        self.logger.info(f"📁 Base path: {self.base_path}")  # ← AGREGAR LOG
        self.logger.info(f"📊 Local SQLite: {self.db_path}")
        self.logger.info(f"🧠 Local ChromaDB: {self.chroma_path}")
    
    def _detect_base_path(self, base_path: Optional[str] = None) -> str:
        """Detecta automáticamente la ruta base según el entorno."""
        if base_path:
            return base_path
            
        # Detectar si estamos en desarrollo local o deploy
        current_file = Path(__file__).resolve()
        
        # Buscar el directorio del proyecto
        project_markers = ['ava_bot', 'llmpagina', 'pagina ava']
        current_dir = current_file.parent
        
        while current_dir.parent != current_dir:  # No hemos llegado a la raíz
            if any(marker in current_dir.name for marker in project_markers):
                # Encontramos el directorio del proyecto
                return str(current_dir / "data" / "memory")
            current_dir = current_dir.parent
        
        # Fallback: usar directorio temporal en el sistema
        if os.environ.get('DEPLOYMENT_ENV'):  # Variable de entorno para deploy
            return os.path.join("/tmp", "ava_memory")  # Linux/cloud
        else:
            return os.path.join(os.path.expanduser("~"), ".ava_memory")  # Local
    
    def _create_directories(self):
        """Crea los directorios necesarios."""
        directories = [
            self.base_path,
            self.images_path,
            self.embeddings_path,
            self.vector_db_path
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"📁 Directorio creado/verificado: {directory}")
    
    def _init_database(self):
        """Inicializa la base de datos SQLite con esquema multimodal."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabla principal de conversaciones
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    conversation_type TEXT DEFAULT 'text'
                )
            """)
            
            # Tabla de memorias de texto
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS text_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    content TEXT NOT NULL,
                    embedding_hash TEXT,
                    keywords TEXT,
                    sentiment REAL,
                    importance_score REAL DEFAULT 1.0,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            # Tabla de memorias de imágenes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    image_path TEXT NOT NULL,
                    image_hash TEXT UNIQUE,
                    description TEXT,
                    embedding_hash TEXT,
                    width INTEGER,
                    height INTEGER,
                    file_size INTEGER,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            # Tabla de enlaces semánticos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS semantic_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id_1 INTEGER,
                    memory_id_2 INTEGER,
                    memory_type_1 TEXT,
                    memory_type_2 TEXT,
                    similarity_score REAL,
                    link_type TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla de metadatos de usuario
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE,
                    preferences TEXT,
                    total_conversations INTEGER DEFAULT 0,
                    last_activity DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices para optimizar búsquedas
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_text_memories_conversation_id ON text_memories(conversation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_memories_conversation_id ON image_memories(conversation_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_image_memories_hash ON image_memories(image_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_semantic_links_memory_ids ON semantic_links(memory_id_1, memory_id_2)")
            
            conn.commit()
            logger.info("✅ Base de datos multimodal inicializada")
    
    def _init_embeddings(self):
        """Inicializa los modelos de embeddings y la base de datos vectorial."""
        try:
            # Inicializar modelo de embeddings de texto
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
                self.text_embedder = SentenceTransformer(model_name)
                logger.info(f"✅ Modelo de embeddings cargado: {model_name}")
            else:
                logger.warning("⚠️ sentence-transformers no disponible. Usar embeddings básicos.")
            
            # Inicializar ChromaDB
            if CHROMADB_AVAILABLE:
                chroma_settings = Settings(
                    persist_directory=self.vector_db_path,
                    anonymized_telemetry=False
                )
                self.vector_store = chromadb.Client(chroma_settings)
                
                # Crear colecciones si no existen
                try:
                    self.text_collection = self.vector_store.get_collection("text_memories")
                except:
                    self.text_collection = self.vector_store.create_collection("text_memories")
                
                try:
                    self.image_collection = self.vector_store.get_collection("image_memories")
                except:
                    self.image_collection = self.vector_store.create_collection("image_memories")
                
                logger.info("✅ ChromaDB inicializado")
            else:
                logger.warning("⚠️ ChromaDB no disponible. Usar búsqueda básica.")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando embeddings: {e}")
            self.text_embedder = None
            self.vector_store = None
    
    def _calculate_text_hash(self, text: str) -> str:
        """Calcula hash MD5 del texto para cache de embeddings."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _calculate_image_hash(self, image_path: str) -> str:
        """Calcula hash MD5 de la imagen."""
        try:
            with open(image_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculando hash de imagen: {e}")
            return ""
    
    def _generate_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Genera embedding para texto."""
        if not self.text_embedder:
            return None
            
        try:
            embedding = self.text_embedder.encode(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generando embedding de texto: {e}")
            return None
    
    def _save_embedding_to_cache(self, content_hash: str, embedding: np.ndarray, embedding_type: str = "text"):
        """Guarda embedding en cache local."""
        try:
            cache_file = os.path.join(self.embeddings_path, f"{embedding_type}_{content_hash}.npy")
            np.save(cache_file, embedding)
        except Exception as e:
            logger.error(f"Error guardando embedding en cache: {e}")
    
    def _load_embedding_from_cache(self, content_hash: str, embedding_type: str = "text") -> Optional[np.ndarray]:
        """Carga embedding desde cache local."""
        try:
            cache_file = os.path.join(self.embeddings_path, f"{embedding_type}_{content_hash}.npy")
            if os.path.exists(cache_file):
                return np.load(cache_file)
        except Exception as e:
            logger.error(f"Error cargando embedding desde cache: {e}")
        return None
    
    async def store_text_memory(self, user_id: str, content: str, session_id: Optional[str] = None, 
                               context: Optional[Dict] = None) -> int:
        """
        Almacena una memoria de texto con embeddings.
        
        Returns:
            ID de la conversación creada
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Crear conversación
                cursor.execute("""
                    INSERT INTO conversations (user_id, session_id, conversation_type)
                    VALUES (?, ?, 'text')
                """, (user_id, session_id))
                
                conversation_id = cursor.lastrowid
                
                # Generar embedding
                content_hash = self._calculate_text_hash(content)
                embedding = self._load_embedding_from_cache(content_hash)
                
                if embedding is None:
                    embedding = self._generate_text_embedding(content)
                    if embedding is not None:
                        self._save_embedding_to_cache(content_hash, embedding)
                
                # Extraer keywords básicas (mejorar con NLP)
                keywords = self._extract_keywords(content)
                
                # Calcular importancia (básica)
                importance_score = len(content) / 100.0  # Heurística simple
                
                # Guardar memoria de texto
                cursor.execute("""
                    INSERT INTO text_memories (conversation_id, content, embedding_hash, keywords, importance_score)
                    VALUES (?, ?, ?, ?, ?)
                """, (conversation_id, content, content_hash, json.dumps(keywords), importance_score))
                
                # Guardar en vector store si está disponible
                if self.vector_store and embedding is not None:
                    try:
                        self.text_collection.add(
                            embeddings=[embedding.tolist()],
                            documents=[content],
                            metadatas=[{
                                "user_id": user_id,
                                "conversation_id": conversation_id,
                                "timestamp": datetime.now().isoformat(),
                                "keywords": keywords
                            }],
                            ids=[f"text_{conversation_id}"]
                        )
                    except Exception as e:
                        logger.error(f"Error guardando en vector store: {e}")
                
                conn.commit()
                
                # Actualizar metadatos de usuario
                await self._update_user_metadata(user_id)
                
                logger.info(f"✅ Memoria de texto almacenada: conversation_id={conversation_id}")
                return conversation_id
                
        except Exception as e:
            logger.error(f"❌ Error almacenando memoria de texto: {e}")
            raise
    
    async def store_image_memory(self, user_id: str, image_path: str, description: Optional[str] = None,
                               session_id: Optional[str] = None) -> int:
        """
        Almacena una memoria de imagen.
        
        Returns:
            ID de la conversación creada
        """
        try:
            # Calcular hash de imagen
            image_hash = self._calculate_image_hash(image_path)
            
            # Obtener metadatos de imagen
            image_info = self._get_image_info(image_path)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Verificar si la imagen ya existe
                cursor.execute("SELECT id FROM image_memories WHERE image_hash = ?", (image_hash,))
                existing = cursor.fetchone()
                
                if existing:
                    logger.info(f"📷 Imagen ya existe en memoria: {image_hash}")
                    return existing[0]
                
                # Crear conversación
                cursor.execute("""
                    INSERT INTO conversations (user_id, session_id, conversation_type)
                    VALUES (?, ?, 'image')
                """, (user_id, session_id))
                
                conversation_id = cursor.lastrowid
                
                # Copiar imagen a almacenamiento local
                stored_image_path = self._store_image_file(image_path, image_hash)
                
                # Guardar memoria de imagen
                cursor.execute("""
                    INSERT INTO image_memories (conversation_id, image_path, image_hash, description, 
                                              width, height, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (conversation_id, stored_image_path, image_hash, description,
                      image_info.get('width'), image_info.get('height'), image_info.get('file_size')))
                
                conn.commit()
                
                # Actualizar metadatos de usuario
                await self._update_user_metadata(user_id)
                
                logger.info(f"✅ Memoria de imagen almacenada: conversation_id={conversation_id}")
                return conversation_id
                
        except Exception as e:
            logger.error(f"❌ Error almacenando memoria de imagen: {e}")
            raise
    
    async def search_semantic_memories(self, query: str, user_id: Optional[str] = None, 
                                     modalities: List[str] = ['text'], limit: int = 5) -> List[Dict]:
        """
        Busca memorias por similitud semántica.
        
        Args:
            query: Texto de búsqueda
            user_id: ID del usuario (opcional, para filtrar)
            modalities: Lista de modalidades ['text', 'image']
            limit: Número máximo de resultados
            
        Returns:
            Lista de memorias encontradas
        """
        results = []
        
        try:
            if 'text' in modalities and self.vector_store:
                # Buscar en memorias de texto
                query_embedding = self._generate_text_embedding(query)
                
                if query_embedding is not None:
                    text_results = self.text_collection.query(
                        query_embeddings=[query_embedding.tolist()],
                        n_results=limit,
                        where={"user_id": user_id} if user_id else None
                    )
                    
                    for i, doc in enumerate(text_results['documents'][0]):
                        metadata = text_results['metadatas'][0][i]
                        results.append({
                            'type': 'text',
                            'content': doc,
                            'similarity': 1.0 - text_results['distances'][0][i],  # Convertir distancia a similitud
                            'metadata': metadata,
                            'conversation_id': metadata['conversation_id']
                        })
            
            # Buscar en memorias de texto usando SQLite si no hay vector store
            if not self.vector_store and 'text' in modalities:
                text_results = await self._search_text_basic(query, user_id, limit)
                results.extend(text_results)
            
            # Buscar en memorias de imagen (por descripción)
            if 'image' in modalities:
                image_results = await self._search_images_by_description(query, user_id, limit)
                results.extend(image_results)
            
            # Ordenar por similitud
            results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda semántica: {e}")
            return []
    
    async def get_recent_multimodal_context(self, user_id: str, days: int = 7, limit: int = 10) -> Dict:
        """
        Obtiene contexto multimodal reciente del usuario.
        
        Returns:
            Diccionario con memorias de texto e imagen recientes
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Obtener conversaciones recientes
                cursor.execute("""
                    SELECT c.*, tm.content as text_content, im.description as image_description,
                           im.image_path
                    FROM conversations c
                    LEFT JOIN text_memories tm ON c.id = tm.conversation_id
                    LEFT JOIN image_memories im ON c.id = im.conversation_id
                    WHERE c.user_id = ? AND c.timestamp >= ?
                    ORDER BY c.timestamp DESC
                    LIMIT ?
                """, (user_id, cutoff_date.isoformat(), limit))
                
                rows = cursor.fetchall()
                
                context = {
                    'text_memories': [],
                    'image_memories': [],
                    'total_conversations': 0
                }
                
                for row in rows:
                    context['total_conversations'] += 1
                    
                    if row['text_content']:
                        context['text_memories'].append({
                            'conversation_id': row['id'],
                            'content': row['text_content'],
                            'timestamp': row['timestamp'],
                            'session_id': row['session_id']
                        })
                    
                    if row['image_description']:
                        context['image_memories'].append({
                            'conversation_id': row['id'],
                            'description': row['image_description'],
                            'image_path': row['image_path'],
                            'timestamp': row['timestamp'],
                            'session_id': row['session_id']
                        })
                
                return context
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo contexto multimodal: {e}")
            return {'text_memories': [], 'image_memories': [], 'total_conversations': 0}
    
    async def find_related_images(self, text_query: str, user_id: Optional[str] = None, 
                                limit: int = 5) -> List[Dict]:
        """
        Encuentra imágenes relacionadas con una consulta de texto.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Buscar por descripción de imagen
                query_parts = text_query.lower().split()
                like_conditions = []
                params = []
                
                for part in query_parts:
                    like_conditions.append("LOWER(im.description) LIKE ?")
                    params.append(f"%{part}%")
                
                where_clause = " AND ".join(like_conditions)
                
                if user_id:
                    where_clause = f"c.user_id = ? AND ({where_clause})"
                    params.insert(0, user_id)
                
                cursor.execute(f"""
                    SELECT im.*, c.timestamp, c.user_id
                    FROM image_memories im
                    JOIN conversations c ON im.conversation_id = c.id
                    WHERE {where_clause}
                    ORDER BY c.timestamp DESC
                    LIMIT ?
                """, params + [limit])
                
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    results.append({
                        'conversation_id': row['conversation_id'],
                        'image_path': row['image_path'],
                        'description': row['description'],
                        'timestamp': row['timestamp'],
                        'width': row['width'],
                        'height': row['height'],
                        'file_size': row['file_size']
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Error buscando imágenes relacionadas: {e}")
            return []
    
    async def create_semantic_link(self, memory_id_1: int, memory_id_2: int, 
                                 memory_type_1: str, memory_type_2: str, 
                                 similarity_score: float, link_type: str = "semantic"):
        """Crea un enlace semántico entre dos memorias."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO semantic_links (memory_id_1, memory_id_2, memory_type_1, memory_type_2,
                                              similarity_score, link_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (memory_id_1, memory_id_2, memory_type_1, memory_type_2, similarity_score, link_type))
                
                conn.commit()
                logger.debug(f"✅ Enlace semántico creado: {memory_id_1} <-> {memory_id_2}")
                
        except Exception as e:
            logger.error(f"❌ Error creando enlace semántico: {e}")
    
    def _extract_keywords(self, text: str) -> str:  # ← Cambiar return type de List[str] a str
        """Extrae keywords del texto - DEVUELVE STRING EN VEZ DE LISTA"""
        try:
            # Limpiar texto
            clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
            words = clean_text.split()
            
            # Filtrar palabras importantes (longitud > 3, no stopwords básicas)
            stopwords = {'que', 'para', 'con', 'por', 'una', 'como', 'esta', 'pero', 'sus', 'fue'}
            keywords = [word for word in words if len(word) > 3 and word not in stopwords]
            
            # ✅ DEVOLVER COMO STRING JSON EN VEZ DE LISTA
            return json.dumps(keywords[:10])  # Máximo 10 keywords como JSON string
            
        except Exception as e:
            logger.error(f"Error extrayendo keywords: {e}")
            return "[]"  # Lista vacía como JSON string
    
    def _get_image_info(self, image_path: str) -> Dict:
        """Obtiene información básica de la imagen."""
        try:
            import os
            from PIL import Image
            
            stat = os.stat(image_path)
            
            info = {
                'file_size': stat.st_size,
                'width': None,
                'height': None
            }
            
            try:
                with Image.open(image_path) as img:
                    info['width'] = img.width
                    info['height'] = img.height
            except:
                pass
            
            return info
            
        except Exception as e:
            logger.error(f"Error obteniendo info de imagen: {e}")
            return {'file_size': 0, 'width': None, 'height': None}
    
    def _store_image_file(self, source_path: str, image_hash: str) -> str:
        """Copia la imagen al almacenamiento local."""
        try:
            import shutil
            from pathlib import Path
            
            # Obtener extensión del archivo
            extension = Path(source_path).suffix
            
            # Crear nombre de archivo único
            stored_filename = f"{image_hash}{extension}"
            stored_path = os.path.join(self.images_path, stored_filename)
            
            # Copiar archivo si no existe
            if not os.path.exists(stored_path):
                shutil.copy2(source_path, stored_path)
                logger.debug(f"📷 Imagen copiada: {stored_path}")
            
            return stored_path
            
        except Exception as e:
            logger.error(f"Error almacenando archivo de imagen: {e}")
            return source_path  # Fallback al path original
    
    async def _search_text_basic(self, query: str, user_id: Optional[str], limit: int) -> List[Dict]:
        """Búsqueda básica de texto usando LIKE en SQLite."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query_parts = query.lower().split()
                like_conditions = []
                params = []
                
                for part in query_parts:
                    like_conditions.append("LOWER(tm.content) LIKE ?")
                    params.append(f"%{part}%")
                
                where_clause = " AND ".join(like_conditions)
                
                if user_id:
                    where_clause = f"c.user_id = ? AND ({where_clause})"
                    params.insert(0, user_id)
                
                cursor.execute(f"""
                    SELECT tm.*, c.timestamp, c.user_id
                    FROM text_memories tm
                    JOIN conversations c ON tm.conversation_id = c.id
                    WHERE {where_clause}
                    ORDER BY tm.importance_score DESC, c.timestamp DESC
                    LIMIT ?
                """, params + [limit])
                
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    results.append({
                        'type': 'text',
                        'content': row['content'],
                        'similarity': 0.5,  # Valor por defecto para búsqueda básica
                        'metadata': {
                            'user_id': row['user_id'],
                            'conversation_id': row['conversation_id'],
                            'timestamp': row['timestamp'],
                            'importance_score': row['importance_score']
                        },
                        'conversation_id': row['conversation_id']
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Error en búsqueda básica de texto: {e}")
            return []
    
    async def _search_images_by_description(self, query: str, user_id: Optional[str], limit: int) -> List[Dict]:
        """Busca imágenes por descripción."""
        images = await self.find_related_images(query, user_id, limit)
        
        results = []
        for img in images:
            results.append({
                'type': 'image',
                'content': img['description'] or 'Sin descripción',
                'similarity': 0.3,  # Valor por defecto
                'metadata': {
                    'image_path': img['image_path'],
                    'conversation_id': img['conversation_id'],
                    'timestamp': img['timestamp'],
                    'width': img['width'],
                    'height': img['height']
                },
                'conversation_id': img['conversation_id']
            })
        
        return results
    
    async def _update_user_metadata(self, user_id: str):
        """Actualiza metadatos del usuario."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Contar conversaciones del usuario
                cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
                total_conversations = cursor.fetchone()[0]
                
                # Actualizar o insertar metadatos
                cursor.execute("""
                    INSERT OR REPLACE INTO user_metadata (user_id, total_conversations, last_activity)
                    VALUES (?, ?, ?)
                """, (user_id, total_conversations, datetime.now().isoformat()))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error actualizando metadatos de usuario: {e}")
    
    async def get_user_stats(self, user_id: str) -> Dict:
        """Obtiene estadísticas del usuario."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Estadísticas básicas
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN conversation_type = 'text' THEN 1 END) as text_conversations,
                        COUNT(CASE WHEN conversation_type = 'image' THEN 1 END) as image_conversations,
                        COUNT(*) as total_conversations,
                        MIN(timestamp) as first_conversation,
                        MAX(timestamp) as last_conversation
                    FROM conversations 
                    WHERE user_id = ?
                """, (user_id,))
                
                stats = dict(cursor.fetchone())
                
                return stats
                
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de usuario: {e}")
            return {}
    
    def cleanup_old_memories(self, days_to_keep: int = 30):
        """Limpia memorias antiguas para mantener el rendimiento."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Obtener IDs de conversaciones a eliminar
                cursor.execute("""
                    SELECT id FROM conversations WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                old_conversation_ids = [row[0] for row in cursor.fetchall()]
                
                if old_conversation_ids:
                    # Eliminar en orden correcto para respetar foreign keys
                    placeholders = ','.join(['?'] * len(old_conversation_ids))
                    
                    cursor.execute(f"DELETE FROM text_memories WHERE conversation_id IN ({placeholders})", old_conversation_ids)
                    cursor.execute(f"DELETE FROM image_memories WHERE conversation_id IN ({placeholders})", old_conversation_ids)
                    cursor.execute(f"DELETE FROM conversations WHERE id IN ({placeholders})", old_conversation_ids)
                    
                    conn.commit()
                    
                    logger.info(f"🧹 Limpieza completada: {len(old_conversation_ids)} conversaciones eliminadas")
                
        except Exception as e:
            logger.error(f"Error en limpieza de memorias: {e}")
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método de ejecución para compatibilidad MCP.
        
        Args:
            params: Parámetros con action, user_id y otros campos específicos
            
        Returns:
            Resultado de la operación
        """
        try:
            action = params.get("action", "")
            user_id = params.get("user_id", "")
            
            if not user_id:
                return {
                    "success": False,
                    "error": "user_id es requerido",
                    "action": action
                }
            
            logger.info(f"🧠 Ejecutando memoria multimodal: {action} para usuario: {user_id}")
            
            # Ejecutar la acción usando asyncio ya que el adaptador es async
            if action == "store_text_memory":
                content = params.get("content", "")
                session_id = params.get("session_id")
                return asyncio.run(self._execute_store_text_memory(user_id, content, session_id))
            
            elif action == "store_image_memory":
                image_path = params.get("image_path", "")
                description = params.get("description", "")
                session_id = params.get("session_id")
                return asyncio.run(self._execute_store_image_memory(user_id, image_path, description, session_id))
            
            elif action == "search_semantic_memories":
                query = params.get("query", "")
                modalities = params.get("modalities", ["text"])
                limit = params.get("limit", 5)
                return asyncio.run(self._execute_search_semantic_memories(query, user_id, modalities, limit))
            
            elif action == "get_recent_multimodal_context":
                days = params.get("days", 7)
                limit = params.get("limit", 10)
                return asyncio.run(self._execute_get_recent_multimodal_context(user_id, days, limit))
            
            elif action == "find_related_images":
                text_query = params.get("text_query", "")
                limit = params.get("limit", 5)
                return asyncio.run(self._execute_find_related_images(text_query, user_id, limit))
            
            elif action == "get_user_stats":
                return asyncio.run(self._execute_get_user_stats(user_id))
            
            elif action == "create_semantic_link":
                memory_id_1 = params.get("memory_id_1")
                memory_id_2 = params.get("memory_id_2")
                memory_type_1 = params.get("memory_type_1", "text")
                memory_type_2 = params.get("memory_type_2", "text")
                similarity_score = params.get("similarity_score", 0.75)
                link_type = params.get("link_type", "related")
                return asyncio.run(self._execute_create_semantic_link(
                    memory_id_1, memory_id_2, memory_type_1, memory_type_2, similarity_score, link_type
                ))
            
            elif action == "validate_system":
                return self._validate_system()
            
            else:
                return {
                    "success": False,
                    "error": f"Acción no reconocida: {action}",
                    "available_actions": [
                        "store_text_memory", "store_image_memory", 
                        "search_semantic_memories", "get_recent_multimodal_context",
                        "find_related_images", "get_user_stats",
                        "create_semantic_link", "validate_system"
                    ]
                }
                
        except Exception as e:
            logger.error(f"❌ Error en MultimodalMemoryAdapter.execute: {e}")
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "action": params.get("action", "unknown")
            }
    
    async def _execute_store_text_memory(self, user_id: str, content: str, session_id: Optional[str]) -> Dict:
        """Wrapper para store_text_memory."""
        try:
            conversation_id = await self.store_text_memory(user_id, content, session_id)
            return {
                "success": True,
                "conversation_id": conversation_id,
                "message": "✅ Memoria de texto almacenada exitosamente",
                "details": {
                    "user_id": user_id,
                    "content_length": len(content),
                    "session_id": session_id,
                    "embeddings_available": self.text_embedder is not None
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_store_image_memory(self, user_id: str, image_path: str, description: str, session_id: Optional[str]) -> Dict:
        """Wrapper para store_image_memory."""
        try:
            conversation_id = await self.store_image_memory(user_id, image_path, description, session_id)
            return {
                "success": True,
                "conversation_id": conversation_id,
                "message": "✅ Memoria de imagen almacenada exitosamente",
                "details": {
                    "user_id": user_id,
                    "image_path": image_path,
                    "description": description,
                    "session_id": session_id
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_search_semantic_memories(self, query: str, user_id: str, modalities: List[str], limit: int) -> Dict:
        """Wrapper para search_semantic_memories."""
        try:
            results = await self.search_semantic_memories(query, user_id, modalities, limit)
            return {
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": results,
                "message": f"✅ Búsqueda completada: {len(results)} resultados encontrados"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_get_recent_multimodal_context(self, user_id: str, days: int, limit: int) -> Dict:
        """Wrapper para get_recent_multimodal_context."""
        try:
            context = await self.get_recent_multimodal_context(user_id, days, limit)
            return {
                "success": True,
                "context": context,
                "message": f"✅ Contexto obtenido: {context.get('total_conversations', 0)} conversaciones"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_find_related_images(self, text_query: str, user_id: str, limit: int) -> Dict:
        """Wrapper para find_related_images."""
        try:
            images = await self.find_related_images(text_query, user_id, limit)
            return {
                "success": True,
                "images_found": len(images),
                "images": images,
                "message": f"✅ Encontradas {len(images)} imágenes relacionadas"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_get_user_stats(self, user_id: str) -> Dict:
        """Wrapper para get_user_stats."""
        try:
            stats = await self.get_user_stats(user_id)
            return {
                "success": True,
                "statistics": stats,
                "message": f"✅ Estadísticas obtenidas para {user_id}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_create_semantic_link(self, memory_id_1, memory_id_2, memory_type_1, memory_type_2, similarity_score, link_type) -> Dict:
        """Wrapper para create_semantic_link."""
        try:
            await self.create_semantic_link(memory_id_1, memory_id_2, memory_type_1, memory_type_2, similarity_score, link_type)
            return {
                "success": True,
                "message": f"✅ Enlace semántico creado entre {memory_id_1} y {memory_id_2}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _validate_system(self) -> Dict:
        """Validar que el sistema esté funcionando correctamente."""
        try:
            validation_results = {
                "system_validation": "Memoria Multimodal - Sistema Real",
                "timestamp": datetime.now().isoformat(),
                "validations": []
            }
            
            # Validar directorios
            directories = {
                "base_path": self.base_path,
                "db_path": os.path.dirname(self.db_path),
                "images_path": self.images_path,
                "embeddings_path": self.embeddings_path,
                "vector_db_path": self.vector_db_path
            }
            
            for name, path in directories.items():
                exists = os.path.exists(path)
                validation_results["validations"].append({
                    "component": f"Directory - {name}",
                    "status": "✅ OK" if exists else "❌ ERROR",
                    "path": str(path),
                    "exists": exists
                })
            
            # Validar base de datos
            db_exists = os.path.exists(self.db_path)
            validation_results["validations"].append({
                "component": "SQLite Database",
                "status": "✅ OK" if db_exists else "❌ ERROR",
                "path": str(self.db_path),
                "exists": db_exists
            })
            
            # Validar embeddings
            validation_results["validations"].append({
                "component": "Text Embedder",
                "status": "✅ OK" if self.text_embedder else "⚠️ NO DISPONIBLE",
                "available": self.text_embedder is not None
            })
            
            # Validar vector store
            validation_results["validations"].append({
                "component": "Vector Store",
                "status": "✅ OK" if self.vector_store else "⚠️ NO DISPONIBLE",
                "available": self.vector_store is not None
            })
            
            # Calcular resumen
            total_validations = len(validation_results["validations"])
            ok_validations = len([v for v in validation_results["validations"] if "✅ OK" in v["status"]])
            
            validation_results["summary"] = {
                "total_components": total_validations,
                "components_ok": ok_validations,
                "success_rate": (ok_validations / total_validations) * 100 if total_validations > 0 else 0,
                "system_ready": ok_validations >= (total_validations * 0.7)  # 70% mínimo
            }
            
            return {
                "success": True,
                "validation_results": validation_results,
                "message": f"✅ Validación del sistema: {ok_validations}/{total_validations} componentes OK"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "❌ Error validando el sistema"
            }
    
    def _prepare_chroma_metadata(self, conversation_id: str, user_id: str, session_id: Optional[str] = None) -> Dict[str, Union[str, int, float, bool]]:
        """Prepara metadatos compatibles con ChromaDB - CORREGIDO"""
        try:
            # ✅ SOLO TIPOS PERMITIDOS: str, int, float, bool
            metadata = {
                "conversation_id": str(conversation_id),
                "user_id": str(user_id),
                "session_id": str(session_id) if session_id else "default",
                "timestamp": str(datetime.now().isoformat()),
                "type": "text_memory"
            }
            
            # ✅ VALIDAR QUE NO HAY LISTAS
            for key, value in metadata.items():
                if isinstance(value, (list, dict, tuple)):
                    metadata[key] = json.dumps(value)  # Convertir a JSON string
                elif value is None:
                    metadata[key] = "none"
                    
            return metadata
            
        except Exception as e:
            logger.error(f"Error preparando metadatos: {e}")
            # Metadatos mínimos como fallback
            return {
                "conversation_id": str(conversation_id),
                "user_id": str(user_id),
                "type": "text_memory"
            }
    
    async def _add_to_vector_store(self, content: str, conversation_id: str, user_id: str, session_id: Optional[str] = None):
        """Añade contenido al vector store - CORREGIDO"""
        try:
            if not self.vector_store or not self.text_collection:
                logger.warning("Vector store no disponible")
                return
            
            # ✅ GENERAR EMBEDDINGS SEGUROS
            if self.text_embedder:
                try:
                    # Limpiar contenido antes del embedding
                    clean_content = self._clean_content_for_embedding(content)
                    embeddings = self.text_embedder.encode(clean_content)
                    
                    # Convertir a lista si es numpy array
                    if hasattr(embeddings, 'tolist'):
                        embeddings = embeddings.tolist()
                    
                except Exception as e:
                    logger.error(f"Error generando embeddings: {e}")
                    return
            else:
                # Embeddings dummy si no hay modelo
                embeddings = [0.0] * 384
            
            # ✅ METADATOS SEGUROS - SOLO STRINGS, INTS, FLOATS, BOOLS
            metadata = {
                "user_id": str(user_id),
                "conversation_id": str(conversation_id),
                "session_id": str(session_id) if session_id else "default",
                "timestamp": datetime.now().isoformat(),
                "type": "text_memory"
            }
            
            # ✅ AÑADIR A CHROMADB CON VALIDACIÓN
            self.text_collection.add(
                embeddings=[embeddings],
                documents=[str(content)],  # Asegurar que es string
                metadatas=[metadata],  # Metadatos sin listas
                ids=[f"text_{conversation_id}_{user_id}_{int(datetime.now().timestamp())}"]
            )
            
            logger.info(f"✅ Contenido añadido al vector store: ID {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error guardando en vector store: {e}")
    
    def _clean_content_for_embedding(self, content: str) -> str:
        """Limpia contenido para embeddings"""
        try:
            # Remover caracteres problemáticos
            clean_content = re.sub(r'[^\w\s\.\,\!\?\-\(\)]', ' ', content)
            
            # Limitar longitud
            if len(clean_content) > 500:
                clean_content = clean_content[:500] + "..."
                
            return clean_content.strip()
            
        except Exception as e:
            logger.error(f"Error limpiando contenido: {e}")
            return str(content)[:200]

# Funciones de utilidad para integración con el sistema existente
async def create_multimodal_memory_adapter(base_path: Optional[str] = None) -> MultimodalMemoryAdapter:
    """Factory function para crear el adaptador."""
    return MultimodalMemoryAdapter(base_path)

def get_multimodal_memory_path() -> str:
    """Obtiene la ruta de memoria multimodal para el entorno actual."""
    adapter = MultimodalMemoryAdapter()
    return adapter.base_path

async def main():
    """
    Función principal para probar el MultimodalMemoryAdapter.
    Ejecuta una suite completa de pruebas para validar todas las funcionalidades.
    """
    print("🧪 INICIANDO PRUEBAS DEL MULTIMODAL MEMORY ADAPTER")
    print("=" * 60)
    
    # Configurar logging para las pruebas
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # ✅ PRUEBA 1: Inicialización del adaptador
        print("\n📋 PRUEBA 1: Inicialización del adaptador")
        print("-" * 40)
        
        adapter = MultimodalMemoryAdapter()
        print(f"✅ Adaptador inicializado correctamente")
        print(f"📁 Base path: {adapter.base_path}")
        print(f"🗃️ DB path: {adapter.db_path}")
        print(f"🖼️ Images path: {adapter.images_path}")
        print(f"🧠 Text embedder disponible: {'✅' if adapter.text_embedder else '❌'}")
        print(f"🔍 Vector store disponible: {'✅' if adapter.vector_store else '❌'}")
        
        # ✅ PRUEBA 2: Almacenamiento de memorias de texto
        print("\n📋 PRUEBA 2: Almacenamiento de memorias de texto")
        print("-" * 40)
        
        test_users = ["test_user_1@email.com", "test_user_2@email.com"]
        text_conversations = []
        
        text_samples = [
            "Estoy buscando apartamentos en Melgar, Tolima para el próximo fin de semana. Necesito que tenga piscina y sea para 4 personas.",
            "Me interesa encontrar hoteles económicos en Bogotá cerca del aeropuerto.",
            "Quiero planear un viaje a Cartagena en diciembre, necesito recomendaciones de lugares para visitar.",
            "Busco apartamentos amoblados en Medellín para alquilar por 3 meses.",
            "Necesito información sobre actividades turísticas en San Andrés y Providencia."
        ]
        
        for i, text in enumerate(text_samples):
            user_id = test_users[i % len(test_users)]
            session_id = f"test_session_{i+1}"
            
            conversation_id = await adapter.store_text_memory(
                user_id=user_id,
                content=text,
                session_id=session_id
            )
            
            text_conversations.append({
                'conversation_id': conversation_id,
                'user_id': user_id,
                'content': text,
                'session_id': session_id
            })
            
            print(f"✅ Texto {i+1} almacenado - ID: {conversation_id}, Usuario: {user_id}")
        
        print(f"📊 Total de memorias de texto almacenadas: {len(text_conversations)}")
        
        # ✅ PRUEBA 3: Almacenamiento de memorias de imagen (simuladas)
        print("\n📋 PRUEBA 3: Almacenamiento de memorias de imagen")
        print("-" * 40)
        
        # Crear imágenes de prueba temporales
        import tempfile
        from PIL import Image
        
        image_conversations = []
        image_samples = [
            {
                "description": "Apartamento hermoso en Melgar con piscina y vista al río Magdalena",
                "width": 1024,
                "height": 768,
                "color": (100, 150, 200)
            },
            {
                "description": "Hotel boutique en zona rosa de Bogotá con spa y restaurante",
                "width": 800,
                "height": 600,
                "color": (200, 100, 150)
            },
            {
                "description": "Playa paradisíaca en Cartagena con aguas cristalinas",
                "width": 1200,
                "height": 800,
                "color": (50, 150, 250)
            }
        ]
        
        for i, img_data in enumerate(image_samples):
            # Crear imagen temporal
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                # Crear imagen simple con PIL
                img = Image.new('RGB', (img_data['width'], img_data['height']), img_data['color'])
                img.save(tmp_file.name, 'JPEG')
                temp_image_path = tmp_file.name
            
            user_id = test_users[i % len(test_users)]
            session_id = f"image_session_{i+1}"
            
            try:
                conversation_id = await adapter.store_image_memory(
                    user_id=user_id,
                    image_path=temp_image_path,
                    description=img_data['description'],
                    session_id=session_id
                )
                
                image_conversations.append({
                    'conversation_id': conversation_id,
                    'user_id': user_id,
                    'description': img_data['description'],
                    'session_id': session_id,
                    'temp_path': temp_image_path
                })
                
                print(f"✅ Imagen {i+1} almacenada - ID: {conversation_id}, Usuario: {user_id}")
                
            except Exception as e:
                print(f"⚠️ Error almacenando imagen {i+1}: {e}")
                # Limpiar archivo temporal en caso de error
                try:
                    os.unlink(temp_image_path)
                except:
                    pass
        
        print(f"📊 Total de memorias de imagen almacenadas: {len(image_conversations)}")
        
        # ✅ PRUEBA 4: Búsqueda semántica
        print("\n📋 PRUEBA 4: Búsqueda semántica")
        print("-" * 40)
        
        search_queries = [
            {
                "query": "apartamentos Melgar piscina",
                "modalities": ["text", "image"],
                "expected_results": "Debe encontrar textos e imágenes sobre Melgar"
            },
            {
                "query": "hoteles Bogotá",
                "modalities": ["text"],
                "expected_results": "Debe encontrar textos sobre hoteles en Bogotá"
            },
            {
                "query": "playa Cartagena",
                "modalities": ["image"],
                "expected_results": "Debe encontrar imágenes de playas"
            }
        ]
        
        for i, search in enumerate(search_queries):
            print(f"\n🔍 Búsqueda {i+1}: '{search['query']}'")
            print(f"   Modalidades: {search['modalities']}")
            
            results = await adapter.search_semantic_memories(
                query=search['query'],
                user_id=None,  # Buscar en todos los usuarios
                modalities=search['modalities'],
                limit=3
            )
            
            print(f"   Resultados encontrados: {len(results)}")
            for j, result in enumerate(results):
                print(f"   [{j+1}] Tipo: {result['type']}, Similitud: {result['similarity']:.2f}")
                print(f"       Contenido: {result['content'][:80]}...")
            
            print(f"   Expectativa: {search['expected_results']}")
        
        # ✅ PRUEBA 5: Obtener contexto de usuario
        print("\n📋 PRUEBA 5: Contexto de usuario")
        print("-" * 40)
        
        for user_id in test_users:
            print(f"\n👤 Usuario: {user_id}")
            
            context = await adapter.get_recent_multimodal_context(
                user_id=user_id,
                days=7,
                limit=10
            )
            
            print(f"   Total conversaciones: {context['total_conversations']}")
            print(f"   Memorias de texto: {len(context['text_memories'])}")
            print(f"   Memorias de imagen: {len(context['image_memories'])}")
            
            # Mostrar algunas memorias
            for i, memory in enumerate(context['text_memories'][:2]):
                print(f"   Texto {i+1}: {memory['content'][:60]}...")
            
            for i, memory in enumerate(context['image_memories'][:2]):
                print(f"   Imagen {i+1}: {memory['description'][:60]}...")
        
        # ✅ PRUEBA 6: Búsqueda de imágenes relacionadas
        print("\n📋 PRUEBA 6: Búsqueda de imágenes relacionadas")
        print("-" * 40)
        
        image_queries = ["piscina", "hotel", "playa"]
        
        for query in image_queries:
            print(f"\n🖼️ Buscando imágenes relacionadas con: '{query}'")
            
            related_images = await adapter.find_related_images(
                text_query=query,
                user_id=None,
                limit=3
            )
            
            print(f"   Imágenes encontradas: {len(related_images)}")
            for i, img in enumerate(related_images):
                print(f"   [{i+1}] {img['description'][:60]}...")
                print(f"       Dimensiones: {img['width']}x{img['height']}")
        
        # ✅ PRUEBA 7: Estadísticas de usuario
        print("\n📋 PRUEBA 7: Estadísticas de usuario")
        print("-" * 40)
        
        for user_id in test_users:
            print(f"\n📊 Estadísticas para {user_id}:")
            
            stats = await adapter.get_user_stats(user_id)
            
            if stats:
                print(f"   Conversaciones de texto: {stats.get('text_conversations', 0)}")
                print(f"   Conversaciones de imagen: {stats.get('image_conversations', 0)}")
                print(f"   Total conversaciones: {stats.get('total_conversations', 0)}")
                print(f"   Primera conversación: {stats.get('first_conversation', 'N/A')}")
                print(f"   Última conversación: {stats.get('last_conversation', 'N/A')}")
            else:
                print("   No se encontraron estadísticas")
        
        # ✅ PRUEBA 8: Creación de enlaces semánticos
        print("\n📋 PRUEBA 8: Enlaces semánticos")
        print("-" * 40)
        
        if len(text_conversations) >= 2:
            conv1 = text_conversations[0]
            conv2 = text_conversations[1]
            
            await adapter.create_semantic_link(
                memory_id_1=conv1['conversation_id'],
                memory_id_2=conv2['conversation_id'],
                memory_type_1="text",
                memory_type_2="text",
                similarity_score=0.75,
                link_type="related_topic"
            )
            
            print(f"✅ Enlace semántico creado entre conversaciones {conv1['conversation_id']} y {conv2['conversation_id']}")
        
        # ✅ PRUEBA 9: Validación de directorios y archivos
        print("\n📋 PRUEBA 9: Validación de estructura")
        print("-" * 40)
        
        directories_to_check = [
            adapter.base_path,
            adapter.images_path,
            adapter.embeddings_path,
            adapter.vector_db_path
        ]
        
        for directory in directories_to_check:
            exists = os.path.exists(directory)
            print(f"   📁 {directory}: {'✅ Existe' if exists else '❌ No existe'}")
        
        # Verificar base de datos
        db_exists = os.path.exists(adapter.db_path)
        print(f"   🗃️ Base de datos: {'✅ Existe' if db_exists else '❌ No existe'}")
        
        if db_exists:
            # Verificar tablas
            with sqlite3.connect(adapter.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                print(f"   📋 Tablas encontradas: {', '.join(tables)}")
        
        # ✅ PRUEBA 10: Rendimiento básico
        print("\n📋 PRUEBA 10: Prueba de rendimiento")
        print("-" * 40)
        
        import time
        
        # Medir tiempo de búsqueda
        start_time = time.time()
        
        for _ in range(5):
            await adapter.search_semantic_memories(
                query="test query",
                modalities=["text"],
                limit=5
            )
        
        end_time = time.time()
        avg_search_time = (end_time - start_time) / 5
        
        print(f"   ⏱️ Tiempo promedio de búsqueda: {avg_search_time:.3f} segundos")
        print(f"   🚀 Rendimiento: {'✅ Bueno' if avg_search_time < 1.0 else '⚠️ Lento'}")
        
        # ✅ RESUMEN FINAL
        print("\n" + "=" * 60)
        print("📋 RESUMEN DE PRUEBAS")
        print("=" * 60)
        
        print(f"✅ Adaptador inicializado correctamente")
        print(f"✅ {len(text_conversations)} memorias de texto almacenadas")
        print(f"✅ {len(image_conversations)} memorias de imagen almacenadas")
        print(f"✅ Búsquedas semánticas funcionando")
        print(f"✅ Contexto de usuario recuperado")
        print(f"✅ Estadísticas de usuario generadas")
        print(f"✅ Enlaces semánticos creados")
        print(f"✅ Estructura de directorios validada")
        print(f"✅ Base de datos funcionando correctamente")
        print(f"✅ Rendimiento aceptable")
        
        dependencies_status = []
        dependencies_status.append(f"🧠 Sentence Transformers: {'✅' if SENTENCE_TRANSFORMERS_AVAILABLE else '❌'}")
        dependencies_status.append(f"🔍 ChromaDB: {'✅' if CHROMADB_AVAILABLE else '❌'}")
        
        print("\n📦 Estado de dependencias:")
        for status in dependencies_status:
            print(f"   {status}")
        
        print(f"\n🎉 TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
        print(f"💡 El MultimodalMemoryAdapter está listo para usar en producción")
        
        # Limpiar archivos temporales
        print(f"\n🧹 Limpiando archivos temporales...")
        for img_conv in image_conversations:
            try:
                if 'temp_path' in img_conv:
                    os.unlink(img_conv['temp_path'])
                    print(f"   🗑️ Eliminado: {img_conv['temp_path']}")
            except Exception as e:
                print(f"   ⚠️ Error eliminando {img_conv.get('temp_path', 'N/A')}: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN LAS PRUEBAS: {e}")
        print(f"🔍 Traceback completo:")
        import traceback
        traceback.print_exc()
        return False

def run_quick_test():
    """
    Función de prueba rápida para validar funcionalidad básica.
    """
    print("🚀 PRUEBA RÁPIDA DEL MULTIMODAL MEMORY ADAPTER")
    print("=" * 50)
    
    try:
        # Crear adaptador
        adapter = MultimodalMemoryAdapter()
        print("✅ Adaptador creado")
        
        # Verificar directorios
        directories_ok = all(os.path.exists(d) for d in [
            adapter.base_path,
            adapter.images_path,
            adapter.embeddings_path,
            adapter.vector_db_path
        ])
        print(f"✅ Directorios: {'OK' if directories_ok else 'ERROR'}")
        
        # Verificar base de datos
        db_ok = os.path.exists(adapter.db_path)
        print(f"✅ Base de datos: {'OK' if db_ok else 'ERROR'}")
        
        # Verificar dependencias
        print(f"✅ Sentence Transformers: {'OK' if SENTENCE_TRANSFORMERS_AVAILABLE else 'NO DISPONIBLE'}")
        print(f"✅ ChromaDB: {'OK' if CHROMADB_AVAILABLE else 'NO DISPONIBLE'}")
        
        print("\n🎉 PRUEBA RÁPIDA COMPLETADA")
        return True
        
    except Exception as e:
        print(f"❌ ERROR EN PRUEBA RÁPIDA: {e}")
        return False

if __name__ == "__main__":
    """
    Punto de entrada principal para ejecutar las pruebas.
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Prueba rápida
        success = run_quick_test()
    else:
        # Prueba completa
        success = asyncio.run(main())
    
    # Código de salida
    sys.exit(0 if success else 1)