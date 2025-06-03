import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash
import uuid
from datetime import datetime

def migrate_users_to_correct_db():
    """Migrar usuarios de ava_users.db a instance/users.db con password_hash"""
    
    old_db = Path("ava_users.db")
    new_db = Path("instance/users.db")
    
    if not old_db.exists():
        print("❌ ava_users.db no encontrada")
        return False
    
    if not new_db.exists():
        print("❌ instance/users.db no encontrada")
        return False
    
    # Conectar a ambas bases de datos
    old_conn = sqlite3.connect(old_db)
    old_conn.row_factory = sqlite3.Row
    
    new_conn = sqlite3.connect(new_db)
    new_conn.row_factory = sqlite3.Row
    
    try:
        # ✅ 1. Obtener usuarios de la DB antigua
        old_users = old_conn.execute("""
            SELECT id, username, email, password, first_name, last_name,
                   is_admin, is_active, created_at, last_login, role
            FROM users
        """).fetchall()
        
        print(f"📊 Usuarios encontrados en ava_users.db: {len(old_users)}")
        
        # ✅ 2. Limpiar la DB nueva (mantener solo structure)
        new_conn.execute("DELETE FROM users")
        new_conn.commit()
        print("🧹 instance/users.db limpiada")
        
        # ✅ 3. Migrar cada usuario
        migrated = 0
        for user in old_users:
            try:
                # Convertir password a password_hash
                password_value = user['password'] or '123456'  # Default si está vacío
                
                # Si ya parece un hash, usar tal como está
                if password_value.startswith(('pbkdf2:sha256', 'scrypt:')):
                    password_hash = password_value
                    print(f"  📋 {user['username']}: Copiando hash existente")
                else:
                    # Si es texto plano, hashear
                    password_hash = generate_password_hash(password_value)
                    print(f"  🔐 {user['username']}: Hasheando contraseña '{password_value}'")
                
                # Usar ID existente o generar nuevo UUID si está vacío
                user_id = user['id'] if user['id'] else str(uuid.uuid4())
                
                # Insertar en nueva DB con password_hash
                new_conn.execute("""
                    INSERT INTO users (
                        id, username, email, password_hash, first_name, last_name,
                        is_admin, is_active, created_at, last_login, role
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    user['username'],
                    user['email'] or f"{user['username']}@ava.local",
                    password_hash,
                    user['first_name'] or '',
                    user['last_name'] or '',
                    user['is_admin'] or 0,
                    user['is_active'] or 1,
                    user['created_at'] or datetime.now().isoformat(),
                    user['last_login'],
                    user['role'] or 'user'
                ))
                
                migrated += 1
                
            except Exception as e:
                print(f"  ❌ Error migrando {user['username']}: {e}")
        
        new_conn.commit()
        print(f"✅ {migrated} usuarios migrados exitosamente")
        
        # ✅ 4. Verificar migración
        verify_migration(new_conn)
        
        # ✅ 5. Renombrar DB antigua para backup
        backup_old_database()
        
        return True
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        old_conn.close()
        new_conn.close()

def verify_migration(conn):
    """Verificar que la migración fue exitosa"""
    
    users = conn.execute("""
        SELECT username, password_hash, is_admin, email
        FROM users
    """).fetchall()
    
    print(f"\n👥 USUARIOS MIGRADOS ({len(users)} total):")
    print("=" * 60)
    
    for user in users:
        has_hash = "✅ SÍ" if user['password_hash'] else "❌ NO"
        is_admin = "✅ SÍ" if user['is_admin'] else "❌ NO"
        print(f"👤 {user['username']}")
        print(f"   📧 Email: {user['email']}")
        print(f"   🔐 Password Hash: {has_hash}")
        print(f"   🛡️ Admin: {is_admin}")
        print()

def backup_old_database():
    """Hacer backup de la base de datos antigua"""
    
    old_db = Path("ava_users.db")
    backup_db = Path("ava_users_backup.db")
    
    try:
        if old_db.exists():
            # Copiar a backup
            import shutil
            shutil.copy2(old_db, backup_db)
            print(f"💾 Backup creado: {backup_db}")
            
            # Renombrar original
            old_db.rename("ava_users_OLD.db")
            print(f"📁 DB antigua renombrada a: ava_users_OLD.db")
            
    except Exception as e:
        print(f"⚠️ Error creando backup: {e}")

def update_db_manager():
    """Actualizar db_manager.py para usar instance/users.db"""
    
    db_manager_path = Path("database/db_manager.py")
    
    if not db_manager_path.exists():
        print("⚠️ database/db_manager.py no encontrado")
        return
    
    try:
        # Leer contenido actual
        with open(db_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar y reemplazar la ruta de la DB
        old_patterns = [
            'ava_users.db',
            '"ava_users.db"',
            "'ava_users.db'"
        ]
        
        new_db_path = 'instance/users.db'
        
        updated = False
        for pattern in old_patterns:
            if pattern in content:
                content = content.replace(pattern, f'"{new_db_path}"')
                updated = True
                print(f"🔄 Reemplazado: {pattern} → {new_db_path}")
        
        if updated:
            # Escribir contenido actualizado
            with open(db_manager_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ db_manager.py actualizado")
        else:
            print("ℹ️ db_manager.py no necesita cambios")
            
    except Exception as e:
        print(f"❌ Error actualizando db_manager.py: {e}")

def test_login_after_migration():
    """Probar login después de la migración"""
    from werkzeug.security import check_password_hash
    
    db_path = Path("instance/users.db")
    
    if not db_path.exists():
        print("❌ instance/users.db no encontrada")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        users = conn.execute("""
            SELECT username, password_hash 
            FROM users 
            WHERE is_active = 1
        """).fetchall()
        
        print(f"\n🧪 PROBANDO LOGIN PARA {len(users)} USUARIOS:")
        print("=" * 50)
        
        working_logins = []
        
        for user in users:
            if user['password_hash']:
                # Probar contraseñas comunes
                test_passwords = ['123456', 'admin', user['username'], 'password']
                
                for pwd in test_passwords:
                    if check_password_hash(user['password_hash'], pwd):
                        working_logins.append((user['username'], pwd))
                        print(f"✅ {user['username']} / {pwd} - FUNCIONA")
                        break
                else:
                    print(f"❌ {user['username']} - Contraseña no detectada")
            else:
                print(f"⚠️ {user['username']} - Sin password_hash")
        
        if working_logins:
            print(f"\n🎉 CREDENCIALES QUE FUNCIONAN:")
            for username, password in working_logins:
                print(f"   👤 {username} / {password}")
        
        return len(working_logins) > 0
        
    except Exception as e:
        print(f"❌ Error probando login: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔄 MIGRACIÓN DE BASE DE DATOS AVA")
    print("=" * 50)
    
    # 1. Migrar usuarios
    print("1️⃣ Migrando usuarios de ava_users.db a instance/users.db...")
    if migrate_users_to_correct_db():
        
        # 2. Actualizar db_manager
        print("\n2️⃣ Actualizando configuración...")
        update_db_manager()
        
        # 3. Probar login
        print("\n3️⃣ Probando funcionalidad de login...")
        if test_login_after_migration():
            print("\n🎉 ¡MIGRACIÓN EXITOSA!")
            print("\n🚀 Ahora ejecuta: python app.py")
            print("🔑 Usa las credenciales mostradas arriba")
        else:
            print("\n⚠️ Migración completada pero revisar credenciales")
    else:
        print("\n❌ Error en migración")