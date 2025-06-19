"""Cliente MCP global independiente - SIN importaciones circulares"""

# ✅ VARIABLES GLOBALES SIMPLIFICADAS
_global_ava_client = None

def set_global_ava_client(client):
    """Establecer cliente MCP global para los nodos"""
    global _global_ava_client
    _global_ava_client = client

def get_global_ava_client():
    """Obtener cliente MCP global desde los nodos"""
    global _global_ava_client
    return _global_ava_client

def cleanup_global_client():
    """Limpiar cliente global"""
    global _global_ava_client
    if _global_ava_client:
        try:
            _global_ava_client.cleanup()
        except:
            pass
    _global_ava_client = None