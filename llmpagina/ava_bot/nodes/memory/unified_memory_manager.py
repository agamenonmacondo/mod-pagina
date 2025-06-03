"""
Manager unificado que orquesta todos los sistemas de memoria
ACTUALIZADO: Incluye Qdrant como backend principal
"""

import logging
import json
import os
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

class UnifiedMemoryManager:
    """
    Manager unificado que orquesta todos los sistemas de memoria
    ACTUALIZADO: Incluye Qdrant como backend principal
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        # ✅ INICIALIZAR THREAD LOCK PRIMERO
        self._thread_lock = threading.RLock()
        
        self.config = config or {
            "use_qdrant": True,      # 🧠 NUEVO: Priorizar Qdrant
            "use_redis": False,      # Desactivar Redis por defecto
            "use_sqlite": True,
            "use_json_fallback": True,
            "qdrant_host": "localhost",  # 🧠 NUEVO
            "qdrant_port": 6333,        # 🧠 NUEVO
            "sqlite_path": "data/memory.db",
            "json_path": "data/memory_backup.json"
        }
        
        # Estados de sistemas
        self.backends = {}
        self.active_backends = []
        self.primary_backend = None
        self.qdrant_memory = None      # 🧠 NUEVO
        self.sqlite_memory = None
        self.json_data = {}
        
        # Inicializar sistemas en orden de prioridad
        self._init_qdrant_memory()      # 🧠 NUEVO: Primera prioridad
        self._init_sqlite_memory()
        self._init_json_memory()
        
        logger.info(f"🧠 Sistemas de memoria activos: {', '.join(self.active_backends)}")
    
    def _init_qdrant_memory(self):
        """🧠 Inicializar Qdrant Memory (sistema principal)"""
        if not self.config.get("use_qdrant", True):
            return
            
        try:
            from nodes.memory.qdrant_multimodal import QdrantMultimodalMemory
            
            self.qdrant_memory = QdrantMultimodalMemory(
                host=self.config.get("qdrant_host", "localhost"),
                port=self.config.get("qdrant_port", 6333)
            )
            
            # Verificar conexión
            if self.qdrant_memory.ping():
                self.active_backends.append("Qdrant Multimodal (Semantic)")
                logger.info("✅ Qdrant Multimodal Memory initialized - Semantic search enabled!")
            else:
                raise ConnectionError("Qdrant ping failed")
                
        except Exception as e:
            logger.warning(f"📝 Qdrant no disponible ({e}), usando fallbacks...")
            self.qdrant_memory = None
    
    def _init_sqlite_memory(self):
        """🗃️ Inicializar SQLite Memory (backup principal)"""
        if not self.config.get("use_sqlite", True):
            return
            
        try:
            from nodes.memory.multimodal_memory import MultimodalMemory
            
            sqlite_path = self.config.get("sqlite_path", "data/memory.db")
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.sqlite_memory = MultimodalMemory(db_path=sqlite_path)
            self.active_backends.append("SQLite Multimodal")
            logger.info("✅ SQLite Memory initialized")
            
        except Exception as e:
            logger.warning(f"⚠️ SQLite no disponible: {e}")
            self.sqlite_memory = None
    
    def _init_json_memory(self):
        """📄 Inicializar JSON Memory (fallback final)"""
        if not self.config.get("use_json_fallback", True):
            return
            
        try:
            json_path = self.config.get("json_path", "data/memory_backup.json")
            Path(json_path).parent.mkdir(parents=True, exist_ok=True)
            
            if Path(json_path).exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.json_data = json.load(f)
            else:
                self.json_data = {
                    "conversations": {},
                    "memories": {},
                    "metadata": {
                        "created": datetime.now().isoformat(),
                        "version": "1.0"
                    }
                }
            
            self.active_backends.append("JSON Backup")
            logger.info("✅ JSON Memory initialized")
            
        except Exception as e:
            logger.error(f"❌ JSON fallback falló: {e}")
    
    def _is_sqlite_safe(self, content: str) -> bool:
        """Verificar si el contenido es seguro para SQLite"""
        try:
            # Verificar caracteres problemáticos
            if not content or len(content.strip()) == 0:
                return False
            
            # Verificar caracteres especiales que pueden causar problemas
            problematic_chars = ['\x00', '\x01', '\x02', '\x03', '\x04']
            if any(char in content for char in problematic_chars):
                return False
            
            # Verificar longitud razonable
            if len(content) > 50000:  # 50KB límite
                return False
            
            return True
            
        except Exception:
            return False

    def store_memory(self, session_id: str, key: str, data: Any, 
                    memory_type: str = "general", tags: List[str] = None, 
                    importance: str = "medium", metadata: Dict = None):
        """💾 Almacenar memoria en todos los backends activos, priorizando Qdrant"""
        
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}
        
        storage_results = {}
        
        # 🧠 QDRANT STORAGE (Primera prioridad - Búsqueda semántica)
        if self.qdrant_memory:
            try:
                # Preparar datos para Qdrant
                if isinstance(data, dict):
                    # Si data es dict (conversación estructurada)
                    text_content = f"{data.get('input', '')} {data.get('response', '')}"
                    if data.get('input') and data.get('response'):
                        text_content = f"Usuario: {data['input']}\nAva: {data['response']}"
                    else:
                        text_content = str(data)
                else:
                    text_content = str(data)
                
                # Almacenar texto con metadata enriquecida
                enhanced_metadata = {
                    "memory_type": memory_type,
                    "tags": tags or [],
                    "importance": importance,
                    "original_data": data,
                    "timestamp": datetime.now().isoformat(),
                    "session_id": session_id,
                    **(metadata or {})
                }
                
                # Usar store_text que incluye embeddings automáticos
                self.qdrant_memory.store_text(session_id, key, text_content)
                
                storage_results["qdrant"] = "success"
                logger.debug(f"✅ Memory stored in Qdrant: {key}")
                
            except Exception as e:
                storage_results["qdrant"] = f"error: {str(e)}"
                logger.warning(f"❌ Failed to store memory in Qdrant: {e}")
        
        # 🗃️ SQLITE MULTIMODAL (con manejo de interfaz corregido)
        if self.sqlite_memory:
            with self._thread_lock:  # ✅ USAR LOCK PARA THREAD SAFETY
                try:
                    # ✅ VERIFICAR THREAD SAFETY
                    if self._is_sqlite_safe():
                        # Usar la lógica de detección de interfaz existente
                        import inspect
                        
                        if hasattr(self.sqlite_memory, 'store_text'):
                            sig = inspect.signature(self.sqlite_memory.store_text)
                            param_names = list(sig.parameters.keys())[1:]  # Excluir 'self'
                            
                            # ✅ USAR INTERFAZ CORRECTA SEGÚN PARÁMETROS
                            if 'value' in param_names:
                                # Interfaz nueva: store_text(key, value, metadata)
                                self.sqlite_memory.store_text(key, data, metadata or {})
                            elif len(param_names) >= 2:
                                # Interfaz antigua: store_text(key, data)
                                self.sqlite_memory.store_text(key, data)
                            else:
                                # Fallback mínimo
                                self.sqlite_memory.store_text(key)
                        
                        storage_results["sqlite"] = "success"
                        logger.debug(f"✅ Stored in SQLite: {key}")
                    else:
                        # ✅ SKIP SQLITE SI ESTAMOS EN THREAD DIFERENTE
                        current_thread = threading.current_thread().ident
                        logger.debug(f"⚠️ Skipping SQLite storage - different thread (original: {self._sqlite_thread_id}, current: {current_thread})")
                        storage_results["sqlite"] = "skipped_different_thread"
                        
                except Exception as e:
                    storage_results["sqlite"] = f"error: {str(e)}"
                    logger.warning(f"❌ Failed to store memory in SQLite: {e}")
        
        # 📄 JSON STORAGE (Fallback simple)
        try:
            if session_id not in self.json_data:
                self.json_data[session_id] = {}
            
            self.json_data[session_id][key] = {
                "data": data,
                "memory_type": memory_type,
                "tags": tags or [],
                "importance": importance,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata
            }
            
            self._save_json_data()
            storage_results["json"] = "success"
            logger.debug(f"✅ Memory stored in JSON: {key}")
            
        except Exception as e:
            storage_results["json"] = f"error: {str(e)}"
            logger.warning(f"❌ Failed to store memory in JSON: {e}")
        
        # Log resultado final
        successful_backends = [k for k, v in storage_results.items() if v == "success"]
        logger.info(f"💾 Stored memory '{key}' in {len(successful_backends)} backends: {successful_backends}")
        
        return storage_results
    
    def search_relevant_memories(self, session_id: str, query: str, 
                               limit: int = 5, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """🔍 Buscar memorias relevantes priorizando Qdrant para búsqueda semántica"""
        
        all_memories = []
        
        # 🧠 QDRANT SEARCH (Primera prioridad - Búsqueda semántica inteligente)
        if self.qdrant_memory:
            try:
                qdrant_memories = self.qdrant_memory.search_similar_texts(
                    session_id, query, limit=limit, threshold=threshold
                )
                
                # Convertir formato de Qdrant al formato estándar
                for qmem in qdrant_memories:
                    all_memories.append({
                        'key': qmem.get('key', 'qdrant_memory'),
                        'content': qmem.get('text', ''),
                        'score': qmem.get('score', 0.0),
                        'source': 'qdrant_semantic',
                        'timestamp': qmem.get('timestamp', ''),
                        'session_id': session_id,
                        'search_type': 'semantic'
                    })
                
                logger.info(f"🧠 Found {len(qdrant_memories)} memories in Qdrant (semantic)")
                
            except Exception as e:
                logger.warning(f"❌ Qdrant search failed: {e}")
        
        # 🗃️ SQLITE SEARCH (Backup)
        if self.sqlite_memory and len(all_memories) < limit:
            try:
                if hasattr(self.sqlite_memory, 'search_relevant_memories'):
                    sqlite_memories = self.sqlite_memory.search_relevant_memories(
                        session_id, query, limit=limit-len(all_memories)
                    )
                else:
                    # Búsqueda básica de texto si no tiene search_relevant_memories
                    sqlite_memories = self._basic_text_search_sqlite(session_id, query, limit-len(all_memories))
                
                # Evitar duplicados por key
                existing_keys = {mem['key'] for mem in all_memories}
                for smem in sqlite_memories:
                    if smem.get('key') not in existing_keys:
                        smem['source'] = 'sqlite'
                        smem['search_type'] = 'text_match'
                        all_memories.append(smem)
                
                logger.debug(f"🗃️ Found {len(sqlite_memories)} memories in SQLite")
                
            except Exception as e:
                logger.warning(f"❌ SQLite search failed: {e}")
        
        # 📄 JSON SEARCH (Fallback final)
        if len(all_memories) < limit:
            try:
                json_memories = self._search_json_memories(session_id, query, limit-len(all_memories))
                
                # Evitar duplicados
                existing_keys = {mem['key'] for mem in all_memories}
                for jmem in json_memories:
                    if jmem.get('key') not in existing_keys:
                        jmem['source'] = 'json'
                        jmem['search_type'] = 'text_match'
                        all_memories.append(jmem)
                
                logger.debug(f"📄 Found {len(json_memories)} memories in JSON")
                
            except Exception as e:
                logger.warning(f"❌ JSON search failed: {e}")
        
        # Ordenar por score (Qdrant scores son más precisos)
        all_memories.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Limitar resultado final
        final_memories = all_memories[:limit]
        
        # Log estadísticas
        sources = {}
        for mem in final_memories:
            source = mem.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        logger.info(f"🔍 Search '{query}' returned {len(final_memories)} memories from: {sources}")
        
        return final_memories
    
    def _search_json_memories(self, session_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """📄 Búsqueda básica en JSON"""
        if session_id not in self.json_data:
            return []
        
        memories = []
        query_lower = query.lower()
        
        for key, memory_data in self.json_data[session_id].items():
            if key == "metadata":  # Skip metadata
                continue
                
            # Búsqueda en contenido
            searchable_content = str(memory_data).lower()
            
            if query_lower in searchable_content:
                # Calcular score básico
                score = searchable_content.count(query_lower) / len(searchable_content.split())
                
                memories.append({
                    'key': key,
                    'content': memory_data,
                    'score': min(score, 1.0),  # Normalizar score
                    'timestamp': memory_data.get('timestamp', ''),
                    'session_id': session_id
                })
        
        # Ordenar por score y limitar
        memories.sort(key=lambda x: x['score'], reverse=True)
        return memories[:limit]
    
    def _basic_text_search_sqlite(self, session_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        """🗃️ Búsqueda básica en SQLite si no tiene búsqueda avanzada"""
        # Implementación básica - en un caso real, esto dependería de tu esquema SQLite
        return []
    
    def get_user_stats(self, session_id: str) -> Dict[str, Any]:
        """📊 Estadísticas de memoria del usuario incluyendo Qdrant"""
        
        stats = {
            'session_id': session_id,
            'total_memories': 0,
            'backends': {},
            'memory_types': {},
            'importance_levels': {},
            'qdrant_stats': {}  # 🧠 NUEVO
        }
        
        # 🧠 QDRANT STATS
        if self.qdrant_memory:
            try:
                qdrant_stats = self.qdrant_memory.get_user_stats(session_id)
                stats['backends']['qdrant'] = qdrant_stats.get('total_points', 0)
                stats['qdrant_stats'] = qdrant_stats
                stats['total_memories'] += qdrant_stats.get('total_points', 0)
                
            except Exception as e:
                logger.warning(f"❌ Error getting Qdrant stats: {e}")
                stats['backends']['qdrant'] = 0
        
        # 🗃️ SQLITE STATS
        if self.sqlite_memory:
            try:
                if hasattr(self.sqlite_memory, 'get_user_stats'):
                    sqlite_stats = self.sqlite_memory.get_user_stats(session_id)
                    stats['backends']['sqlite'] = sqlite_stats.get('total_memories', 0)
                    stats['total_memories'] += sqlite_stats.get('total_memories', 0)
                else:
                    stats['backends']['sqlite'] = 0
                    
            except Exception as e:
                logger.warning(f"❌ Error getting SQLite stats: {e}")
                stats['backends']['sqlite'] = 0
        
        # 📄 JSON STATS
        if session_id in self.json_data:
            json_count = len(self.json_data[session_id]) - (1 if 'metadata' in self.json_data[session_id] else 0)
            stats['backends']['json'] = json_count
            stats['total_memories'] += json_count
        else:
            stats['backends']['json'] = 0
        
        return stats
    
    def clear_user_data(self, session_id: str):
        """🧹 Limpiar datos del usuario en todos los backends"""
        results = {}
        
        # 🧠 CLEAR QDRANT
        if self.qdrant_memory:
            try:
                self.qdrant_memory.clear_user_data(session_id)
                results['qdrant'] = 'cleared'
                logger.info(f"🧹 Cleared Qdrant data for {session_id}")
            except Exception as e:
                results['qdrant'] = f'error: {str(e)}'
                logger.warning(f"❌ Error clearing Qdrant data: {e}")
        
        # 🗃️ CLEAR SQLITE
        if self.sqlite_memory:
            try:
                if hasattr(self.sqlite_memory, 'clear_user_data'):
                    self.sqlite_memory.clear_user_data(session_id)
                results['sqlite'] = 'cleared'
                logger.info(f"🧹 Cleared SQLite data for {session_id}")
            except Exception as e:
                results['sqlite'] = f'error: {str(e)}'
                logger.warning(f"❌ Error clearing SQLite data: {e}")
        
        # 📄 CLEAR JSON
        if session_id in self.json_data:
            try:
                del self.json_data[session_id]
                self._save_json_data()
                results['json'] = 'cleared'
                logger.info(f"🧹 Cleared JSON data for {session_id}")
            except Exception as e:
                results['json'] = f'error: {str(e)}'
                logger.warning(f"❌ Error clearing JSON data: {e}")
        
        return results
    
    def _save_json_data(self):
        """💾 Guardar datos JSON a archivo"""
        try:
            json_path = self.config.get("json_path", "data/memory_backup.json")
            Path(json_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.json_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"❌ Error saving JSON data: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """📊 Estado completo del sistema de memoria con Qdrant"""
        
        status = {
            "active_backends": self.active_backends,
            "systems": {
                "qdrant": {
                    "available": self.qdrant_memory is not None,
                    "healthy": False
                },
                "sqlite": {
                    "available": self.sqlite_memory is not None,
                    "healthy": self.sqlite_memory is not None
                },
                "json": {
                    "available": bool(self.json_data),
                    "healthy": bool(self.json_data)
                }
            },
            "config": self.config,
            "timestamp": datetime.now().isoformat()
        }
        
        # Test Qdrant health
        if self.qdrant_memory:
            try:
                status["systems"]["qdrant"]["healthy"] = self.qdrant_memory.ping()
                
                # Obtener info adicional de Qdrant
                collections_info = {
                    "text_collection": f"ava_bot_text",
                    "vectors_collection": f"ava_bot_vectors", 
                    "images_collection": f"ava_bot_images"
                }
                status["systems"]["qdrant"]["collections"] = collections_info
                
            except Exception as e:
                status["systems"]["qdrant"]["error"] = str(e)
        
        return status

# Instancia global actualizada con Qdrant
unified_memory = UnifiedMemoryManager()

# Función de conveniencia para uso fácil
def get_memory_manager(config: Dict[str, Any] = None) -> UnifiedMemoryManager:
    """Retorna instancia del memory manager con Qdrant integrado"""
    if config:
        return UnifiedMemoryManager(config)
    return unified_memory

# Añadir este método a la clase UnifiedMemoryManager

def retrieve_memory(self, session_id: str = "default", query: str = "", 
                   data_type: str = "all", limit: int = 10,
                   tags: List[str] = None) -> Dict[str, Any]:
    """🔍 Buscar memorias almacenadas en todos los backends"""
    
    try:
        results = {
            "memories": [],
            "total_found": 0,
            "backends_used": [],
            "search_query": query,
            "session_id": session_id
        }
        
        all_memories = []
        
        # 🧠 QDRANT SEARCH (Semantic search)
        if self.qdrant_memory and query:
            try:
                qdrant_results = self.search_memories(query, limit=limit)
                if qdrant_results:
                    for memory in qdrant_results:
                        all_memories.append({
                            "source": "qdrant_semantic",
                            "content": memory.get("text", memory.get("content", "")),
                            "score": memory.get("score", 0.0),
                            "metadata": memory.get("metadata", {}),
                            "timestamp": memory.get("metadata", {}).get("timestamp", "")
                        })
                    results["backends_used"].append("Qdrant Semantic")
            except Exception as e:
                logger.warning(f"❌ Failed to search Qdrant: {e}")
        
        # 🗃️ SQLITE SEARCH (Keyword search)
        if self.sqlite_memory:
            try:
                # Verificar thread safety
                import threading
                current_thread = threading.current_thread().ident
                
                if (hasattr(self, '_sqlite_thread_id') and 
                    current_thread == self._sqlite_thread_id):
                    
                    # Buscar en SQLite si tiene métodos de búsqueda
                    if hasattr(self.sqlite_memory, 'search'):
                        sqlite_results = self.sqlite_memory.search(query, limit=limit)
                        for result in sqlite_results:
                            all_memories.append({
                                "source": "sqlite_keyword",
                                "content": result.get("content", ""),
                                "score": 0.8,  # Score fijo para SQLite
                                "metadata": result.get("metadata", {}),
                                "timestamp": result.get("timestamp", "")
                            })
                        results["backends_used"].append("SQLite Keyword")
                else:
                    logger.debug("⚠️ Skipping SQLite search - different thread")
            except Exception as e:
                logger.warning(f"❌ Failed to search SQLite: {e}")
        
        # 📄 JSON SEARCH (Simple text search)
        if session_id in self.json_data:
            try:
                session_data = self.json_data[session_id]
                query_lower = query.lower() if query else ""
                
                for key, memory in session_data.items():
                    content = str(memory.get("data", "")).lower()
                    
                    # Filtrar por tipo si se especifica
                    if data_type != "all" and memory.get("memory_type") != data_type:
                        continue
                    
                    # Filtrar por tags si se especifica
                    if tags and not any(tag in memory.get("tags", []) for tag in tags):
                        continue
                    
                    # Búsqueda por contenido
                    if not query or query_lower in content:
                        all_memories.append({
                            "source": "json_storage",
                            "content": memory.get("data", ""),
                            "score": 0.6,  # Score fijo para JSON
                            "metadata": memory.get("metadata", {}),
                            "timestamp": memory.get("timestamp", ""),
                            "tags": memory.get("tags", []),
                            "importance": memory.get("importance", "medium")
                        })
                
                if session_id in self.json_data:
                    results["backends_used"].append("JSON Storage")
            except Exception as e:
                logger.warning(f"❌ Failed to search JSON: {e}")
        
        # 🔍 ORDENAR Y LIMITAR RESULTADOS
        # Ordenar por score descendente
        all_memories.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Limitar resultados
        results["memories"] = all_memories[:limit]
        results["total_found"] = len(all_memories)
        
        logger.info(f"🔍 Retrieved {len(results['memories'])} memories from {len(results['backends_used'])} backends")
        return results
        
    except Exception as e:
        logger.error(f"❌ Error retrieving memories: {e}")
        return {
            "memories": [],
            "total_found": 0,
            "backends_used": [],
            "search_query": query,
            "session_id": session_id,
            "error": str(e)
        }