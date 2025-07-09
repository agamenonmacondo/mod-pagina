# Configuración para memoria vectorial en Docker
import os

def get_qdrant_config():
    """Obtener configuración de Qdrant basada en el entorno"""
    
    # Si estamos en Docker, usar el nombre del servicio
    if os.environ.get('QDRANT_HOST'):
        return {
            "host": os.environ.get('QDRANT_HOST', 'vector-db'),
            "port": int(os.environ.get('QDRANT_PORT', 6333)),
            "url": os.environ.get('QDRANT_URL', f"http://{os.environ.get('QDRANT_HOST', 'vector-db')}:6333")
        }
    
    # Configuración local para desarrollo
    return {
        "host": "localhost",
        "port": 6333,
        "url": "http://localhost:6333"
    }

def get_memory_config():
    """Configuración completa para la memoria vectorial"""
    qdrant_config = get_qdrant_config()
    
    return {
        "qdrant": qdrant_config,
        "collection_name": "ava_memory",
        "embedding_model": "all-MiniLM-L6-v2",
        "vector_size": 384,
        "timeout": 60,
        "fallback_to_memory": True
    }
