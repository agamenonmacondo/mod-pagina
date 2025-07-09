#!/usr/bin/env python3
"""
🧪 Script de prueba para verificar la memoria vectorial en Docker
"""

import sys
import os
import time
import requests
from datetime import datetime

def test_qdrant_connection():
    """Probar conexión a Qdrant"""
    print("🔍 Probando conexión a Qdrant...")
    
    # URLs a probar
    qdrant_urls = []
    
    # Si estamos en Docker
    if os.environ.get('QDRANT_HOST'):
        qdrant_urls.append(f"http://{os.environ.get('QDRANT_HOST')}:6333")
    
    # URLs locales
    qdrant_urls.extend([
        "http://localhost:6333",
        "http://127.0.0.1:6333"
    ])
    
    for url in qdrant_urls:
        try:
            print(f"  🔄 Probando {url}...")
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ Qdrant disponible en {url}")
                return url
            else:
                print(f"  ❌ Error {response.status_code} en {url}")
        except Exception as e:
            print(f"  ❌ Error conectando a {url}: {str(e)[:50]}")
    
    print("  ⚠️ Qdrant no disponible")
    return None

def test_memory_system():
    """Probar el sistema de memoria"""
    print("\n🧠 Probando sistema de memoria...")
    
    try:
        # Importar después de configurar el path
        sys.path.append('/app/ava_bot')
        from ava_graph_multimodal import MultiModalMemory
        
        memory = MultiModalMemory()
        print("  ✅ MultiModalMemory inicializada")
        
        # Estado de prueba
        test_state = {
            "user_id": "test_docker",
            "session_id": "docker_session_001",
            "messages": ["¿Funciona la memoria en Docker?", "Sí, funciona correctamente"],
            "conversation_history": [],
            "execution_plan": {"step1": "test_memory"},
            "plan_status": {"step1": "completed"},
            "tool_to_execute": None,
            "tool_arguments": {},
            "tool_result": "Memoria funcionando en Docker",
            "available_tools": {"memory_test": {}},
            "node": "memory_test",
            "timestamp": datetime.now(),
            "error_message": None,
            "context_memory": {"test_mode": True}
        }
        
        # Guardar estado
        point_id = memory.guardar_agent_state(test_state)
        print(f"  ✅ Estado guardado: {point_id}")
        
        # Buscar estados similares
        query_state = {
            "user_id": "test_docker",
            "messages": ["¿La memoria funciona?"],
            "conversation_history": [],
            "execution_plan": {},
            "plan_status": {},
            "context_memory": {}
        }
        
        estados = memory.buscar_estados_similares(query_state, limite=1)
        if estados:
            print(f"  ✅ Búsqueda funcionando: {len(estados)} resultado(s)")
            print(f"      Similitud: {estados[0]['similarity_score']:.3f}")
        else:
            print("  ⚠️ No se encontraron estados similares")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error en memoria: {e}")
        return False

def main():
    """Función principal"""
    print("🐳 VERIFICANDO MEMORIA VECTORIAL EN DOCKER")
    print("=" * 50)
    
    # Esperar un momento para que los servicios se inicialicen
    print("⏳ Esperando inicialización de servicios...")
    time.sleep(5)
    
    # 1. Probar conexión a Qdrant
    qdrant_url = test_qdrant_connection()
    
    # 2. Probar sistema de memoria
    if qdrant_url:
        memory_ok = test_memory_system()
    else:
        print("⚠️ Saltando prueba de memoria - Qdrant no disponible")
        memory_ok = False
    
    # Resumen
    print(f"\n📊 RESUMEN DE PRUEBAS:")
    print(f"  🔗 Qdrant: {'✅' if qdrant_url else '❌'}")
    print(f"  🧠 Memoria: {'✅' if memory_ok else '❌'}")
    
    if qdrant_url and memory_ok:
        print(f"\n🎉 ¡MEMORIA VECTORIAL FUNCIONANDO EN DOCKER!")
    else:
        print(f"\n⚠️ Algunos componentes necesitan atención")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
