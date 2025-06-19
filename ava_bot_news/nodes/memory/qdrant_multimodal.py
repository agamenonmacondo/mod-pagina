import json
import numpy as np
from PIL import Image
import io
import base64
import uuid
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
from sentence_transformers import SentenceTransformer

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct, 
        Filter, FieldCondition, MatchValue
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

logger = logging.getLogger(__name__)

class QdrantMultimodalMemory:
    """🧠 Memoria multimodal inteligente con Qdrant - Reemplazo directo de Redis"""
    
    def __init__(self, host="localhost", port=6333, collection_prefix="ava_bot"):
        self.collection_prefix = collection_prefix
        
        if not QDRANT_AVAILABLE:
            raise ImportError("Qdrant client not installed. Run: pip install qdrant-client")
        
        try:
            # Conectar a Qdrant (local o cloud)
            self.client = QdrantClient(host=host, port=port)
            
            # Inicializar modelo de embeddings para texto
            self.text_encoder = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Crear colecciones necesarias
            self._init_collections()
            
            logger.info(f"✅ Qdrant Multimodal Memory initialized at {host}:{port}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise
    
    def _generate_point_id(self, user_id: str, key: str, content_hash: str = None) -> str:
        """🔑 Generar UUID válido para Qdrant"""
        # Crear string único basado en user_id + key + hash opcional
        unique_string = f"{user_id}_{key}"
        if content_hash:
            unique_string += f"_{content_hash}"
        
        # Generar UUID determinístico basado en el string
        namespace = uuid.UUID('12345678-1234-5678-1234-123456789abc')
        return str(uuid.uuid5(namespace, unique_string))
    
    def _init_collections(self):
        """🔧 Inicializar colecciones de Qdrant"""
        collections = [
            ("text", 384),      # all-MiniLM-L6-v2 dimensions
            ("vectors", 768),   # Vectores personalizados (configurable)
            ("images", 512)     # Para embeddings de imágenes
        ]
        
        for collection_type, vector_size in collections:
            collection_name = f"{self.collection_prefix}_{collection_type}"
            
            try:
                # Verificar si la colección existe
                collections_info = self.client.get_collections()
                existing_names = [col.name for col in collections_info.collections]
                
                if collection_name not in existing_names:
                    # Crear colección
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=vector_size,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"✅ Created collection: {collection_name}")
                else:
                    logger.info(f"✅ Collection exists: {collection_name}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Issue with collection {collection_name}: {e}")
    
    # --- Texto (reemplazo directo de Redis) ---
    def store_text(self, user_id: str, key: str, text: str):
        """Almacena texto asociado a un usuario con búsqueda semántica."""
        try:
            # Generar embedding del texto
            embedding = self.text_encoder.encode(text).tolist()
            
            # Crear hash del contenido para ID único
            content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            
            # Generar UUID válido
            point_id = self._generate_point_id(user_id, key, content_hash)
            
            point = PointStruct(
                id=point_id,  # Ahora es UUID válido
                vector=embedding,
                payload={
                    "user_id": user_id,
                    "key": key,
                    "text": text,
                    "type": "text",
                    "timestamp": datetime.now().isoformat(),
                    "text_length": len(text),
                    "content_hash": content_hash
                }
            )
            
            # Insertar en Qdrant
            self.client.upsert(
                collection_name=f"{self.collection_prefix}_text",
                points=[point]
            )
            
            logger.debug(f"📝 Stored text: {key} for user {user_id} with ID {point_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store text: {e}")
            raise

    def get_text(self, user_id: str, key: str) -> Optional[str]:
        """Recupera texto almacenado (equivalente a Redis)."""
        try:
            # Buscar por user_id y key exactos
            results = self.client.scroll(
                collection_name=f"{self.collection_prefix}_text",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                        FieldCondition(key="key", match=MatchValue(value=key))
                    ]
                ),
                limit=1
            )
            
            if results[0]:  # results = (points, next_page_offset)
                return results[0][0].payload["text"]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get text: {e}")
            return None

    # --- Vectores ---
    def store_vector(self, user_id: str, key: str, vector: np.ndarray):
        """Almacena vectores con dimensiones flexibles."""
        try:
            # Convertir a lista si es numpy array
            if isinstance(vector, np.ndarray):
                vector_list = vector.tolist()
            else:
                vector_list = vector
            
            # Redimensionar si es necesario para la colección
            if len(vector_list) != 768:
                # Padding o truncado según sea necesario
                if len(vector_list) < 768:
                    vector_list.extend([0.0] * (768 - len(vector_list)))
                else:
                    vector_list = vector_list[:768]
            
            # Generar UUID válido
            vector_hash = hashlib.md5(str(vector_list).encode()).hexdigest()[:8]
            point_id = self._generate_point_id(user_id, key, vector_hash)
            
            point = PointStruct(
                id=point_id,
                vector=vector_list,
                payload={
                    "user_id": user_id,
                    "key": key,
                    "type": "vector",
                    "original_dimensions": len(vector.tolist() if isinstance(vector, np.ndarray) else vector),
                    "timestamp": datetime.now().isoformat(),
                    "vector_hash": vector_hash
                }
            )
            
            self.client.upsert(
                collection_name=f"{self.collection_prefix}_vectors",
                points=[point]
            )
            
            logger.debug(f"🔢 Stored vector: {key} for user {user_id} with ID {point_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store vector: {e}")
            raise

    def get_vector(self, user_id: str, key: str) -> Optional[np.ndarray]:
        """Recupera vectores."""
        try:
            results = self.client.scroll(
                collection_name=f"{self.collection_prefix}_vectors",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                        FieldCondition(key="key", match=MatchValue(value=key))
                    ]
                ),
                limit=1
            )
            
            if results[0]:
                vector_data = results[0][0].vector
                original_dims = results[0][0].payload.get("original_dimensions", len(vector_data))
                
                # Restaurar dimensiones originales
                if original_dims < len(vector_data):
                    vector_data = vector_data[:original_dims]
                
                return np.array(vector_data)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get vector: {e}")
            return None

    # --- Imágenes ---
    def store_image(self, user_id: str, key: str, image: Image.Image):
        """Almacena imágenes con embedding visual."""
        try:
            # Convertir imagen a base64 para almacenamiento
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            
            # Generar embedding visual simple (basado en estadísticas de imagen)
            img_array = np.array(image.resize((32, 32)))
            visual_features = [
                float(img_array.mean()),  # Brillo promedio
                float(img_array.std()),   # Varianza
                float(img_array.max()),   # Valor máximo
                float(img_array.min()),   # Valor mínimo
            ]
            
            # Extender a 512 dimensiones con características derivadas
            visual_embedding = []
            for i in range(512):
                if i < len(visual_features):
                    visual_embedding.append(visual_features[i])
                else:
                    # Generar características sintéticas basadas en las reales
                    base_idx = i % len(visual_features)
                    synthetic_feature = visual_features[base_idx] * (0.1 * (i // len(visual_features)))
                    visual_embedding.append(float(synthetic_feature))
            
            # Generar UUID válido
            img_hash = hashlib.md5(img_base64.encode()).hexdigest()[:8]
            point_id = self._generate_point_id(user_id, key, img_hash)
            
            point = PointStruct(
                id=point_id,
                vector=visual_embedding,
                payload={
                    "user_id": user_id,
                    "key": key,
                    "type": "image",
                    "image_data": img_base64,
                    "width": image.width,
                    "height": image.height,
                    "format": image.format or "PNG",
                    "timestamp": datetime.now().isoformat(),
                    "image_hash": img_hash
                }
            )
            
            self.client.upsert(
                collection_name=f"{self.collection_prefix}_images",
                points=[point]
            )
            
            logger.debug(f"🖼️ Stored image: {key} for user {user_id} with ID {point_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to store image: {e}")
            raise

    def get_image(self, user_id: str, key: str) -> Optional[Image.Image]:
        """Recupera imágenes."""
        try:
            results = self.client.scroll(
                collection_name=f"{self.collection_prefix}_images",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                        FieldCondition(key="key", match=MatchValue(value=key))
                    ]
                ),
                limit=1
            )
            
            if results[0]:
                img_base64 = results[0][0].payload["image_data"]
                img_bytes = base64.b64decode(img_base64)
                return Image.open(io.BytesIO(img_bytes))
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get image: {e}")
            return None

    # --- Funcionalidades avanzadas (mejores que Redis) ---
    def search_similar_texts(self, user_id: str, query: str, limit: int = 5, threshold: float = 0.7) -> List[Dict]:
        """🔍 Búsqueda semántica de textos similares."""
        try:
            # Generar embedding de la consulta
            query_embedding = self.text_encoder.encode(query).tolist()
            
            # Buscar textos similares
            results = self.client.search(
                collection_name=f"{self.collection_prefix}_text",
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=limit,
                score_threshold=threshold
            )
            
            return [
                {
                    "key": result.payload["key"],
                    "text": result.payload["text"],
                    "score": result.score,
                    "timestamp": result.payload["timestamp"]
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"❌ Failed to search similar texts: {e}")
            return []

    def search_similar_images(self, user_id: str, reference_image: Image.Image, limit: int = 3) -> List[Dict]:
        """🖼️ Búsqueda de imágenes similares visualmente."""
        try:
            # Generar embedding de la imagen de referencia
            img_array = np.array(reference_image.resize((32, 32)))
            ref_features = [
                float(img_array.mean()),
                float(img_array.std()),
                float(img_array.max()),
                float(img_array.min()),
            ]
            
            # Extender embedding
            ref_embedding = []
            for i in range(512):
                if i < len(ref_features):
                    ref_embedding.append(ref_features[i])
                else:
                    base_idx = i % len(ref_features)
                    synthetic_feature = ref_features[base_idx] * (0.1 * (i // len(ref_features)))
                    ref_embedding.append(float(synthetic_feature))
            
            # Buscar imágenes similares
            results = self.client.search(
                collection_name=f"{self.collection_prefix}_images",
                query_vector=ref_embedding,
                query_filter=Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                ),
                limit=limit
            )
            
            return [
                {
                    "key": result.payload["key"],
                    "score": result.score,
                    "width": result.payload["width"],
                    "height": result.payload["height"],
                    "timestamp": result.payload["timestamp"]
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"❌ Failed to search similar images: {e}")
            return []

    # --- Utils (compatibilidad con Redis) ---
    def clear_user_data(self, user_id: str):
        """Borra todos los datos de un usuario."""
        try:
            collections = ["text", "vectors", "images"]
            
            for collection_type in collections:
                collection_name = f"{self.collection_prefix}_{collection_type}"
                
                # Buscar todos los puntos del usuario
                results = self.client.scroll(
                    collection_name=collection_name,
                    scroll_filter=Filter(
                        must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                    ),
                    limit=10000  # Límite alto para obtener todos
                )
                
                # Extraer IDs para eliminar
                point_ids = [point.id for point in results[0]]
                
                if point_ids:
                    self.client.delete(
                        collection_name=collection_name,
                        points_selector=point_ids
                    )
                    logger.info(f"🧹 Deleted {len(point_ids)} points from {collection_name}")
            
            logger.info(f"✅ Cleared all data for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear user data: {e}")
            raise

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """📊 Estadísticas del usuario."""
        try:
            stats = {
                "user_id": user_id,
                "text_count": 0,
                "vector_count": 0,
                "image_count": 0,
                "total_points": 0
            }
            
            collections = ["text", "vectors", "images"]
            
            for collection_type in collections:
                collection_name = f"{self.collection_prefix}_{collection_type}"
                
                try:
                    # Contar puntos del usuario usando scroll
                    results = self.client.scroll(
                        collection_name=collection_name,
                        scroll_filter=Filter(
                            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
                        ),
                        limit=10000,  # Alto para contar todos
                        with_payload=False,
                        with_vectors=False
                    )
                    
                    count = len(results[0])
                    stats[f"{collection_type}_count"] = count
                    stats["total_points"] += count
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error counting {collection_type}: {e}")
                    stats[f"{collection_type}_count"] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get user stats: {e}")
            return {"error": str(e)}

    def ping(self) -> bool:
        """🏓 Verificar conexión (compatibilidad con Redis)."""
        try:
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"❌ Ping failed: {e}")
            return False