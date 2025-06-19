import os
import sys

def fix_protobuf_imports():
    """Corrige automáticamente las importaciones en los archivos protobuf generados"""
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    grpc_file = os.path.join(current_dir, 'ava_bot_pb2_grpc.py')
    
    if not os.path.exists(grpc_file):
        print("❌ Archivo ava_bot_pb2_grpc.py no encontrado")
        return False
    
    # Leer el archivo
    with open(grpc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar y reemplazar la línea problemática
    old_import = "import ava_bot_pb2 as ava__bot__pb2"
    new_import = """try:
    import ava_bot_pb2 as ava__bot__pb2
except ImportError:
    from . import ava_bot_pb2 as ava__bot__pb2"""
    
    if old_import in content and new_import not in content:
        content = content.replace(old_import, new_import)
        
        # Escribir el archivo corregido
        with open(grpc_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Importaciones corregidas en ava_bot_pb2_grpc.py")
        return True
    else:
        print("ℹ️ Las importaciones ya están corregidas")
        return True

if __name__ == "__main__":
    fix_protobuf_imports()