import sqlite3
import os
from pathlib import Path
from werkzeug.security import generate_password_hash
import uuid
from datetime import datetime

def check_and_fix_database():
    """Verificar y arreglar la estructura de la base de datos"""
    
    # Buscar archivos de base de datos
    possible_db_paths = [
        Path("instance/users.db"),
        Path("users.db"),
        Path("database/users.db"),
        Path("llmpagina/database/users.db")
    ]
    
    db_path = None
    for path in possible_db_paths:
        if path.exists():
            db_path = path
            break
    
    if not db_path:
        print("❌ No se encontró ninguna base de datos")
        print("🔧 Creando nueva base de datos...")
        db_path = Path("instance/users.db")
        db_path.parent.mkdir(exist_ok=True)
    
    print(f"📁 Usando base de datos: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # ✅ 1. Verificar si existe la tabla users
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [table['name'] for table in tables]
        
        print(f"📋 Tablas encontradas: {table_names}")
        
        if 'users' not in table_names:
            print("🔧 Creando tabla users...")
            create_users_table(conn)
        else:
            print("✅ Tabla users existe")
            
            # ✅ 2. Verificar columnas existentes
            columns = conn.execute("PRAGMA table_info(users)").fetchall()
            column_names = [col['name'] for col in columns]
            
            print(f"📊 Columnas actuales: {column_names}")
            
            # ✅ 3. Agregar columna password_hash si no existe
            if 'password_hash' not in column_names:
                print("🔧 Agregando columna password_hash...")
                conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
                conn.commit()
                print("✅ Columna password_hash agregada")
            
            # ✅ 4. Migrar datos si existe columna 'password'
            if 'password' in column_names and 'password_hash' in column_names:
                print("🔄 Migrando datos de password a password_hash...")
                migrate_passwords(conn)
        
        # ✅ 5. Verificar/crear usuario de prueba
        create_test_user_if_not_exists(conn)
        
        # ✅ 6. Mostrar usuarios existentes
        show_all_users(conn)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def create_users_table(conn):
    """Crear tabla users con estructura correcta"""
    conn.execute('''
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            last_login TEXT,
            role TEXT DEFAULT 'user'
        )
    ''')
    conn.commit()
    print("✅ Tabla users creada con estructura correcta")

def migrate_passwords(conn):
    """Migrar contraseñas de 'password' a 'password_hash'"""
    users = conn.execute("""
        SELECT id, username, password, password_hash 
        FROM users 
        WHERE password IS NOT NULL
    """).fetchall()
    
    for user in users:
        if not user['password_hash'] and user['password']:
            password_value = user['password']
            
            # Si ya parece un hash, usarlo tal como está
            if password_value.startswith(('pbkdf2:sha256', 'scrypt:')):
                new_hash = password_value
                print(f"  📋 Copiando hash existente para {user['username']}")
            else:
                # Si es texto plano, hashear
                new_hash = generate_password_hash(password_value)
                print(f"  🔐 Hasheando contraseña para {user['username']}: {password_value}")
            
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, user['id'])
            )
    
    conn.commit()
    print("✅ Migración de contraseñas completada")

def create_test_user_if_not_exists(conn):
    """Crear usuario de prueba si no existe"""
    username = "admin"
    email = "admin@ava.com"
    password = "123456"
    
    # Verificar si ya existe
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (username, email)
    ).fetchone()
    
    if existing:
        print(f"✅ Usuario {username} ya existe")
        return
    
    # Crear usuario
    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)
    
    conn.execute('''
        INSERT INTO users (
            id, username, email, password_hash, first_name, last_name, 
            is_admin, is_active, created_at, role
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, username, email, password_hash, "Admin", "AVA", 
        1, 1, datetime.now().isoformat(), 'admin'
    ))
    
    conn.commit()
    
    print(f"✅ Usuario de prueba creado:")
    print(f"   👤 Usuario: {username}")
    print(f"   📧 Email: {email}")
    print(f"   🔐 Contraseña: {password}")
    print(f"   🛡️ Admin: Sí")

def show_all_users(conn):
    """Mostrar todos los usuarios"""
    users = conn.execute("""
        SELECT id, username, email, password_hash, first_name, last_name, 
               is_admin, is_active, created_at
        FROM users
    """).fetchall()
    
    print(f"\n👥 USUARIOS EN LA BASE DE DATOS ({len(users)} total):")
    print("=" * 70)
    
    for user in users:
        print(f"🆔 ID: {user['id']}")
        print(f"👤 Usuario: {user['username']}")
        print(f"📧 Email: {user['email']}")
        print(f"🔐 Password Hash: {'✅ SÍ' if user['password_hash'] else '❌ NO'}")
        print(f"👨‍💼 Nombre: {user['first_name']} {user['last_name']}")
        print(f"🛡️ Admin: {'✅ SÍ' if user['is_admin'] else '❌ NO'}")
        print(f"✅ Activo: {'✅ SÍ' if user['is_active'] else '❌ NO'}")
        print(f"📅 Creado: {user['created_at']}")
        print("-" * 50)

def test_login_functionality():
    """Probar la funcionalidad de login"""
    from werkzeug.security import check_password_hash
    
    db_path = Path("instance/users.db")
    if not db_path.exists():
        print("❌ Base de datos no encontrada para probar")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Probar con el usuario admin
    user = conn.execute("""
        SELECT username, password_hash 
        FROM users 
        WHERE username = ?
    """, ("admin",)).fetchone()
    
    if user and user['password_hash']:
        test_password = "123456"
        is_valid = check_password_hash(user['password_hash'], test_password)
        
        print(f"\n🧪 PRUEBA DE LOGIN:")
        print(f"👤 Usuario: {user['username']}")
        print(f"🔐 Contraseña: {test_password}")
        print(f"✅ Válida: {'SÍ' if is_valid else 'NO'}")
        
        if is_valid:
            print("🎉 ¡Login funcionará correctamente!")
        else:
            print("❌ Hay un problema con el hash de contraseña")
    else:
        print("❌ No se pudo probar - usuario admin no encontrado")
    
    conn.close()

if __name__ == "__main__":
    print("🔧 REPARADOR DE BASE DE DATOS AVA")
    print("=" * 50)
    
    # ✅ 1. Verificar y arreglar estructura
    print("\n1️⃣ Verificando estructura de base de datos...")
    check_and_fix_database()
    
    # ✅ 2. Probar funcionalidad
    print("\n2️⃣ Probando funcionalidad de login...")
    test_login_functionality()
    
    print("\n✅ Proceso completado")
    print("\n🚀 Ahora puedes ejecutar: python app.py")
    print("🔑 Y usar: admin / 123456 para login")