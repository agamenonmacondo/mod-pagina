import sqlite3
import os
from pathlib import Path

def find_all_databases():
    """Buscar todas las bases de datos posibles"""
    
    search_paths = [
        ".",
        "instance",
        "database", 
        "llmpagina",
        "llmpagina/database"
    ]
    
    found_dbs = []
    
    for search_path in search_paths:
        path = Path(search_path)
        if path.exists():
            # Buscar archivos .db
            for db_file in path.glob("*.db"):
                found_dbs.append(db_file)
    
    print("🔍 BASES DE DATOS ENCONTRADAS:")
    if found_dbs:
        for db in found_dbs:
            print(f"   📁 {db}")
            
            # Verificar contenido
            try:
                conn = sqlite3.connect(db)
                conn.row_factory = sqlite3.Row
                
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = [t['name'] for t in tables]
                print(f"      📋 Tablas: {table_names}")
                
                if 'users' in table_names:
                    columns = conn.execute("PRAGMA table_info(users)").fetchall()
                    column_names = [c['name'] for c in columns]
                    print(f"      📊 Columnas users: {column_names}")
                    
                    user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()
                    print(f"      👥 Usuarios: {user_count['count']}")
                
                conn.close()
                
            except Exception as e:
                print(f"      ❌ Error leyendo: {e}")
            
            print()
    else:
        print("   ❌ No se encontraron bases de datos")
    
    return found_dbs

def get_active_database_path():
    """Obtener la ruta de la base de datos que usa la aplicación"""
    
    # Importar el db_manager para ver qué ruta usa
    try:
        import sys
        sys.path.append('.')
        
        from database.db_manager import get_db_connection
        
        # Intentar obtener una conexión y ver la ruta
        conn = get_db_connection()
        
        # SQLite tiene un comando para obtener la ruta de la base de datos
        db_path = conn.execute("PRAGMA database_list").fetchone()
        conn.close()
        
        print(f"🎯 BASE DE DATOS ACTIVA: {db_path}")
        return db_path
        
    except Exception as e:
        print(f"❌ Error obteniendo DB activa: {e}")
        return None

if __name__ == "__main__":
    print("🔍 DIAGNÓSTICO COMPLETO DE BASE DE DATOS")
    print("=" * 50)
    
    # 1. Buscar todas las bases de datos
    found_dbs = find_all_databases()
    
    # 2. Ver cuál usa la aplicación
    print("\n🎯 VERIFICANDO BASE DE DATOS ACTIVA:")
    active_db = get_active_database_path()
    
    # 3. Crear directorio instance si no existe
    instance_dir = Path("instance")
    if not instance_dir.exists():
        print(f"\n📁 Creando directorio: {instance_dir}")
        instance_dir.mkdir()
    
    print(f"\n📂 Directorio instance existe: {instance_dir.exists()}")