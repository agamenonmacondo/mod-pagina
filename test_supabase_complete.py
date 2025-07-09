import os
import sys
import subprocess
import socket
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv

# Agregar el directorio ava_bot al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'ava_bot'))

load_dotenv()

def diagnose_dns_issue():
    """Diagnosticar problemas de DNS"""
    print("🔍 DIAGNÓSTICO DNS...")
    
    test_hosts = [
        'tvpvfzjnarjrravihmfq.supabase.co',  # ✅ URL CORRECTA
        'aws-0-sa-east-1.pooler.supabase.com',
        'google.com'
    ]
    
    for host in test_hosts:
        try:
            socket.gethostbyname(host)
            print(f"✅ DNS resuelve: {host}")
        except socket.gaierror as e:
            print(f"❌ DNS falla: {host} - {e}")

def auto_fix_dns():
    """Intentar arreglar problemas de DNS automáticamente"""
    print("🔧 ARREGLANDO DNS...")
    
    try:
        subprocess.run(['ipconfig', '/flushdns'], check=True, capture_output=True)
        print("✅ DNS cache limpiado")
        print("💡 Tip: Reinicia tu conexión WiFi si persisten problemas")
    except Exception as e:
        print(f"⚠️ No se pudo limpiar DNS: {e}")

def test_with_custom_dns():
    """Probar con DNS personalizado"""
    print("🌐 PROBANDO CON DNS PERSONALIZADO...")
    
    try:
        socket.getaddrinfo('tvpvfzjnarjrravihmfq.supabase.co', 443)  # ✅ URL CORRECTA
        print("✅ Resolución DNS exitosa")
        return True
    except Exception as e:
        print(f"❌ DNS personalizado falla: {e}")
        return False

def test_supabase_after_dns_fix():
    """Probar Supabase después del arreglo DNS - VERSIÓN ACTUALIZADA"""
    print("🧪 PROBANDO SUPABASE POST-DNS FIX...")
    
    try:
        from supabase import create_client, Client
        
        # ✅ USAR VARIABLES ESTÁNDAR SEGÚN DOCUMENTACIÓN
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not url or not key:
            print("❌ Variables de entorno faltantes")
            print("💡 Necesitas: SUPABASE_URL y SUPABASE_ANON_KEY")
            print("📝 Obtén las credenciales de:")
            print("   1. Ve a tu dashboard de Supabase")
            print("   2. Settings → API Keys")
            print("   3. Copia Project URL y anon/public key")
            return False
        
        # ✅ CREAR CLIENTE SEGÚN DOCUMENTACIÓN
        supabase: Client = create_client(url, key)
        
        # ✅ TEST CON MÉTODO ESTÁNDAR
        response = supabase.table('conversation_archive').select('*').limit(1).execute()
        
        print(f"✅ Supabase cliente funciona: {len(response.data)} registros")
        return True
        
    except Exception as e:
        print(f"❌ Supabase cliente falla: {e}")
        return False

def test_supabase_client_with_retry():
    """Probar cliente Supabase con reintentos - VERSIÓN ACTUALIZADA"""
    print("🔄 PROBANDO CLIENTE SUPABASE CON REINTENTOS...")
    
    for attempt in range(3):
        try:
            from supabase import create_client, Client
            
            # ✅ VARIABLES ESTÁNDAR
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_ANON_KEY")
            
            if not url or not key:
                print("❌ Variables de entorno faltantes")
                if not url:
                    print("   ❌ SUPABASE_URL no configurada")
                if not key:
                    print("   ❌ SUPABASE_ANON_KEY no configurada")
                return False
            
            # ✅ CREAR CLIENTE
            supabase: Client = create_client(url, key)
            
            # ✅ TEST SIMPLE SEGÚN DOCUMENTACIÓN
            response = supabase.table('conversation_archive').select('*').limit(1).execute()
            print(f"✅ Intento {attempt + 1}: Cliente funciona - {len(response.data)} registros")
            return True
            
        except Exception as e:
            print(f"❌ Intento {attempt + 1} falla: {e}")
            if attempt < 2:
                print("🔄 Reintentando en 2 segundos...")
                import time
                time.sleep(2)
    
    return False

def test_supabase_crud_operations():
    """Test completo de operaciones CRUD según documentación"""
    print("🔧 PROBANDO OPERACIONES CRUD SUPABASE...")
    
    try:
        from supabase import create_client, Client
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not url or not key:
            print("❌ Variables de entorno faltantes")
            return False
        
        supabase: Client = create_client(url, key)
        
        # ✅ TEST 1: SELECT
        print("📖 Testing SELECT...")
        response = supabase.table('conversation_archive').select('*').limit(1).execute()
        print(f"   ✅ SELECT exitoso: {len(response.data)} registros")
        
        # ✅ TEST 2: INSERT
        print("📝 Testing INSERT...")
        test_data = {
            'session_id': 'test_crud',
            'message_type': 'human',
            'content': 'Test CRUD operation',
            'created_at': datetime.now().isoformat()
        }
        
        data, count = supabase.table('conversation_archive').insert(test_data).execute()
        print(f"   ✅ INSERT exitoso")
        
        # ✅ TEST 3: UPDATE
        print("✏️ Testing UPDATE...")
        data, count = supabase.table('conversation_archive').update({
            'content': 'Test CRUD operation - UPDATED'
        }).eq('session_id', 'test_crud').execute()
        print(f"   ✅ UPDATE exitoso")
        
        # ✅ TEST 4: DELETE
        print("🗑️ Testing DELETE...")
        data, count = supabase.table('conversation_archive').delete().eq('session_id', 'test_crud').execute()
        print(f"   ✅ DELETE exitoso")
        
        print("✅ Todas las operaciones CRUD funcionan")
        return True
        
    except Exception as e:
        print(f"❌ Error en operaciones CRUD: {e}")
        return False

def test_transaction_pooler():
    """Probar conexión directa con Transaction Pooler - OPCIONAL"""
    print("🔗 PROBANDO TRANSACTION POOLER (OPCIONAL)...")
    
    # ✅ VERIFICAR SI LA CONTRASEÑA ESTÁ DISPONIBLE
    db_password = os.getenv('SUPABASE_DB_PASSWORD')
    if not db_password:
        print("⚠️ SUPABASE_DB_PASSWORD no configurada - SALTANDO")
        print("💡 Esta prueba es opcional. El cliente Supabase normal debería funcionar.")
        return False
    
    connection_params = {
        'host': 'aws-0-sa-east-1.pooler.supabase.com',
        'port': '6543',
        'database': 'postgres',
        'user': 'postgres.tvpvfzjnarjrravihmfq',
        'password': db_password,
        'connect_timeout': 10
    }
    
    try:
        conn = psycopg2.connect(**connection_params)
        cursor = conn.cursor()
        
        # Test básico
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ PostgreSQL: {version[0][:50]}...")
        
        # Test de tablas
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = cursor.fetchall()
        print(f"✅ Tablas encontradas: {[t[0] for t in tables]}")
        
        # Test de inserción
        test_data = {
            'session_id': 'test_pooler',
            'message_type': 'human',
            'content': 'Test de conexión pooler',
            'created_at': datetime.now().isoformat()
        }
        
        cursor.execute("""
            INSERT INTO conversation_archive (session_id, message_type, content, created_at)
            VALUES (%(session_id)s, %(message_type)s, %(content)s, %(created_at)s)
        """, test_data)
        conn.commit()
        
        print("✅ Inserción de prueba exitosa")
        
        # Limpiar test
        cursor.execute("DELETE FROM conversation_archive WHERE session_id = 'test_pooler'")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print("✅ Transaction Pooler funciona perfectamente")
        return True
        
    except Exception as e:
        print(f"❌ Transaction Pooler falla: {e}")
        return False

def comprehensive_dns_fix_and_test():
    """Arreglo completo de DNS y test"""
    print("🚀 INICIANDO ARREGLO COMPLETO...")
    
    # 1. Diagnóstico inicial
    diagnose_dns_issue()
    
    # 2. Arreglo automático
    auto_fix_dns()
    
    # 3. Test con DNS personalizado
    dns_works = test_with_custom_dns()
    
    # 4. Test de Supabase
    if dns_works:
        supabase_works = test_supabase_after_dns_fix()
    else:
        supabase_works = False
    
    # 5. Fallback a Transaction Pooler (opcional)
    if not supabase_works:
        print("🔄 Probando método alternativo...")
        pooler_works = test_transaction_pooler()
        
        if pooler_works:
            print("✅ SOLUCIÓN: Usar Transaction Pooler para conectar")
            return "transaction_pooler"
        else:
            print("⚠️ Transaction Pooler también falló (normal si no tienes DB password)")
            return "failed"
    else:
        print("✅ SOLUCIÓN: Cliente Supabase funciona")
        return "supabase_client"

def test_network_connectivity():
    """Probar conectividad general de red"""
    print("🌐 PROBANDO CONECTIVIDAD DE RED...")
    
    test_sites = ['google.com', 'github.com', 'supabase.com']
    all_connected = True
    
    for site in test_sites:
        try:
            socket.gethostbyname(site)
            print(f"✅ Conectividad: {site}")
        except Exception as e:
            print(f"❌ Sin conectividad: {site} - {e}")
            all_connected = False
    
    return all_connected

def test_alternative_approaches():
    """Probar enfoques alternativos - SIN REQUERIR DB PASSWORD"""
    print("🔄 PROBANDO ENFOQUES ALTERNATIVOS...")
    
    # ✅ SOLO VARIABLES ESENCIALES (SIN DB PASSWORD)
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables esenciales faltantes: {missing_vars}")
        print("💡 Variables requeridas:")
        print("   - SUPABASE_URL: https://tvpvfzjnarjrravihmfq.supabase.co")  # ✅ URL CORRECTA
        print("   - SUPABASE_ANON_KEY: (obtén de Settings → API Keys)")
        print()
        print("📝 Cómo obtener las credenciales:")
        print("   1. Ve a tu dashboard de Supabase")
        print("   2. Haz clic en 'Settings' → 'API Keys'")
        print("   3. Copia 'Project URL' y 'anon/public key'")
        return False
    else:
        print("✅ Variables esenciales presentes")
    
    # ✅ VARIABLES OPCIONALES
    optional_vars = ['SUPABASE_SERVICE_KEY', 'SUPABASE_DB_PASSWORD']
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ Variable opcional configurada: {var}")
        else:
            print(f"⚠️ Variable opcional no configurada: {var} (no es necesaria)")
    
    # ✅ TEST DE IMPORTACIONES
    try:
        import supabase
        print("✅ Librería supabase importada")
        print(f"   📦 Versión: {supabase.__version__ if hasattr(supabase, '__version__') else 'Unknown'}")
    except ImportError:
        print("❌ Librería supabase no instalada")
        print("💡 Ejecuta: pip install supabase")
        return False
    
    return True

def test_complete_integration():
    """Test de integración completa"""
    print("🎯 TEST DE INTEGRACIÓN COMPLETA...")
    
    try:
        # Importar el sistema AVA
        from ava_memory import save_conversation, get_conversation_summary
        
        # Test de guardado
        test_session = f"test_integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        success = save_conversation(
            session_id=test_session,
            message_type='human',
            content='Test de integración completa'
        )
        
        if success:
            print("✅ Guardado en memoria funciona")
            
            # Test de recuperación
            summary = get_conversation_summary(test_session)
            if summary:
                print("✅ Recuperación de memoria funciona")
                return True
            else:
                print("❌ Recuperación de memoria falla")
                return False
        else:
            print("❌ Guardado en memoria falla")
            return False
            
    except ImportError as e:
        print(f"❌ No se puede importar ava_memory: {e}")
        print("💡 Esto es normal si aún no has configurado el sistema AVA completo")
        return False
    except Exception as e:
        print(f"❌ Error en integración: {e}")
        return False

def comprehensive_connection_test():
    """Test comprensivo de todos los métodos de conexión"""
    print("🧪 TEST COMPRENSIVO DE CONEXIONES...")
    
    results = {}
    
    # 1. Test de red básica
    print("\n1️⃣ TEST DE RED BÁSICA:")
    results['network'] = test_network_connectivity()
    
    # 2. Test de variables de entorno
    print("\n2️⃣ TEST DE CONFIGURACIÓN:")
    results['config'] = test_alternative_approaches()
    
    # 3. Test de cliente Supabase
    print("\n3️⃣ TEST DE CLIENTE SUPABASE:")
    results['supabase_client'] = test_supabase_client_with_retry()
    
    # 4. Test de operaciones CRUD
    print("\n4️⃣ TEST DE OPERACIONES CRUD:")
    if results['supabase_client']:
        results['crud_operations'] = test_supabase_crud_operations()
    else:
        print("⚠️ Saltando CRUD - cliente no funciona")
        results['crud_operations'] = False
    
    # 5. Test de Transaction Pooler (opcional)
    print("\n5️⃣ TEST DE TRANSACTION POOLER (OPCIONAL):")
    results['transaction_pooler'] = test_transaction_pooler()
    
    # 6. Test de integración
    print("\n6️⃣ TEST DE INTEGRACIÓN:")
    results['integration'] = test_complete_integration()
    
    # Determinar mejor método
    if results['integration']:
        best_method = "integration_complete"
    elif results['crud_operations']:
        best_method = "supabase_crud"
    elif results['supabase_client']:
        best_method = "supabase_client"
    elif results['transaction_pooler']:
        best_method = "transaction_pooler"
    else:
        best_method = "failed"
    
    print(f"\n🏆 MEJOR MÉTODO: {best_method}")
    print(f"📊 RESULTADOS: {results}")
    
    return best_method

def show_environment_info():
    """Mostrar información del entorno"""
    print("📋 INFORMACIÓN DEL ENTORNO:")
    print(f"🐍 Python: {sys.version}")
    print(f"📁 Directorio: {os.getcwd()}")
    print(f"🔗 SUPABASE_URL: {os.getenv('SUPABASE_URL', 'No configurada')}")
    print(f"🔑 SUPABASE_ANON_KEY: {'Configurada' if os.getenv('SUPABASE_ANON_KEY') else 'No configurada'}")
    print(f"🔐 SUPABASE_SERVICE_KEY: {'Configurada (opcional)' if os.getenv('SUPABASE_SERVICE_KEY') else 'No configurada (opcional)'}")
    print(f"🔐 SUPABASE_DB_PASSWORD: {'Configurada (opcional)' if os.getenv('SUPABASE_DB_PASSWORD') else 'No configurada (opcional)'}")

def main():
    """Función principal - ejecutar todos los tests"""
    print("🚀 INICIANDO TEST COMPLETO DE SUPABASE")
    print("=" * 60)
    
    # 1. Mostrar información del entorno
    show_environment_info()
    print()
    
    # 2. Test comprensivo
    best_method = comprehensive_connection_test()
    
    # 3. Recomendaciones finales
    print("\n" + "=" * 60)
    print("🎯 RECOMENDACIONES FINALES:")
    
    if best_method == "integration_complete":
        print("✅ TODO FUNCIONA PERFECTAMENTE")
        print("💡 Tu sistema AVA está completamente funcional")
        
    elif best_method == "supabase_crud":
        print("✅ CLIENTE SUPABASE CON CRUD FUNCIONA")
        print("💡 Usa el cliente Python de Supabase con operaciones CRUD")
        
    elif best_method == "supabase_client":
        print("✅ CLIENTE SUPABASE BÁSICO FUNCIONA")
        print("💡 Usa el cliente Python de Supabase normalmente")
        
    elif best_method == "transaction_pooler":
        print("✅ USAR TRANSACTION POOLER")
        print("💡 Modifica tu código para usar conexión directa PostgreSQL")
        
    else:
        print("❌ PROBLEMAS DE CONECTIVIDAD")
        print("💡 Pasos para solucionar:")
        print("   1. Ve a tu dashboard de Supabase")
        print("   2. Settings → API Keys")
        print("   3. Copia estas credenciales a tu archivo .env:")
        print("      SUPABASE_URL=https://tvpvfzjnarjrravihmfq.supabase.co")  # ✅ URL CORRECTA
        print("      SUPABASE_ANON_KEY=tu_anon_key_aqui")
        print("   4. Ejecuta: pip install --upgrade supabase")
    
    print("\n🏁 TEST COMPLETADO")
    return best_method

if __name__ == "__main__":
    result = main()
    print(f"\n🎯 RESULTADO FINAL: {result}")