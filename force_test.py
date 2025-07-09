import os
import sys
from dotenv import load_dotenv

def force_test():
    """Test que fuerza la recarga de variables de entorno"""
    print("🔄 FORZANDO RECARGA DE VARIABLES DE ENTORNO")
    print("=" * 50)
    
    # 1. Limpiar variables existentes
    for key in list(os.environ.keys()):
        if key.startswith('SUPABASE'):
            print(f"🗑️ Limpiando: {key}")
            del os.environ[key]
    
    # 2. Forzar recarga del archivo .env
    load_dotenv(override=True)
    
    # 3. Verificar variables cargadas
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    print(f"🔗 URL después de recarga: {url}")
    print(f"🔑 KEY: {key[:20]}..." if key else "❌ No configurada")
    
    # 4. Verificar URL correcta
    correct_url = "https://tvpvfzjnarjrravihmfq.supabase.co"
    if url == correct_url:
        print("✅ URL es correcta después de recarga")
    else:
        print(f"❌ URL sigue incorrecta. Esperado: {correct_url}")
        return False
    
    # 5. Test de DNS
    import socket
    try:
        socket.gethostbyname('tvpvfzjnarjrravihmfq.supabase.co')
        print("✅ DNS resuelve correctamente")
    except Exception as e:
        print(f"❌ DNS falla: {e}")
        return False
    
    # 6. Test de Supabase con ESQUEMA REAL
    try:
        from supabase import create_client, Client
        
        supabase: Client = create_client(url, key)
        print("✅ Cliente Supabase creado")
        
        return test_real_schema(supabase)
        
    except ImportError:
        print("❌ Supabase no instalado. Ejecuta: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_real_schema(supabase):
    """Test con el esquema REAL de la tabla"""
    print("\n🔍 PROBANDO CON ESQUEMA REAL...")
    
    try:
        # ✅ TEST 1: LECTURA CON ESQUEMA REAL
        print("📖 Test de lectura...")
        response = supabase.table('conversation_archive').select('*').limit(5).execute()
        print(f"✅ CONECTADO! Registros encontrados: {len(response.data)}")
        
        if response.data:
            print("📄 ESTRUCTURA REAL CONFIRMADA:")
            sample_record = response.data[0]
            print(f"   Columnas: {list(sample_record.keys())}")
            print(f"   Ejemplo: {sample_record}")
        
        # ✅ TEST 2: INSERCIÓN CON ESQUEMA REAL
        print("\n📝 Test de inserción...")
        from datetime import datetime
        
        # Datos según el esquema REAL
        test_data = {
            'session_id': 'test_real_schema',
            'archived_messages': {
                'messages': [
                    {
                        'role': 'human',
                        'content': 'Test con esquema real',
                        'timestamp': datetime.now().isoformat()
                    }
                ],
                'summary': 'Test de conexión con esquema correcto'
            },
            'timestamp': datetime.now().isoformat()
        }
        
        insert_response = supabase.table('conversation_archive').insert(test_data).execute()
        print("✅ Inserción exitosa con esquema real")
        print(f"   Datos insertados: {insert_response.data}")
        
        # ✅ TEST 3: ACTUALIZACIÓN
        print("\n✏️ Test de actualización...")
        update_data = {
            'archived_messages': {
                'messages': [
                    {
                        'role': 'human', 
                        'content': 'Test con esquema real - ACTUALIZADO',
                        'timestamp': datetime.now().isoformat()
                    }
                ],
                'summary': 'Test actualizado correctamente'
            }
        }
        
        update_response = supabase.table('conversation_archive').update(update_data).eq('session_id', 'test_real_schema').execute()
        print("✅ Actualización exitosa")
        
        # ✅ TEST 4: CONSULTA ESPECÍFICA
        print("\n🔍 Test de consulta específica...")
        query_response = supabase.table('conversation_archive').select('session_id, archived_messages').eq('session_id', 'test_real_schema').execute()
        
        if query_response.data:
            print("✅ Consulta específica exitosa")
            print(f"   Datos recuperados: {query_response.data[0]}")
        
        # ✅ TEST 5: LIMPIEZA
        print("\n🗑️ Test de eliminación...")
        delete_response = supabase.table('conversation_archive').delete().eq('session_id', 'test_real_schema').execute()
        print("✅ Eliminación exitosa")
        
        # ✅ TEST 6: VERIFICAR TABLA SUMMARIES
        print("\n📋 Verificando tabla summaries...")
        try:
            summaries_response = supabase.table('summaries').select('*').limit(3).execute()
            print(f"✅ Tabla summaries existe - {len(summaries_response.data)} registros")
            
            if summaries_response.data:
                print("📄 Esquema de summaries:")
                print(f"   Columnas: {list(summaries_response.data[0].keys())}")
        except Exception as e:
            print(f"⚠️ Error en tabla summaries: {e}")
        
        print("\n🎉 ¡TODAS LAS OPERACIONES CRUD FUNCIONAN CON ESQUEMA REAL!")
        return True
        
    except Exception as e:
        print(f"❌ Error con esquema real: {e}")
        return False

def show_integration_next_steps():
    """Mostrar próximos pasos para integración"""
    print("\n" + "=" * 60)
    print("🎯 PRÓXIMOS PASOS PARA INTEGRACIÓN:")
    print("=" * 60)
    print("✅ Conexión a Supabase: FUNCIONANDO")
    print("✅ Esquema de tabla: IDENTIFICADO")
    print("✅ Operaciones CRUD: FUNCIONANDO")
    print()
    print("📝 AHORA NECESITAS:")
    print("1. Actualizar ava_memory.py para usar el esquema real:")
    print("   - Usar 'archived_messages' (jsonb) en lugar de 'content'")
    print("   - Adaptar estructura de datos")
    print()
    print("2. Estructura de datos correcta:")
    print("   {")
    print("     'session_id': 'id_de_sesion',")
    print("     'archived_messages': {")
    print("       'messages': [lista_de_mensajes],")
    print("       'summary': 'resumen_opcional'")
    print("     },")
    print("     'timestamp': 'fecha_iso'")
    print("   }")
    print()
    print("💡 ¿Quieres que actualice ava_memory.py con el esquema correcto?")
    print("=" * 60)

if __name__ == "__main__":
    success = force_test()
    if success:
        print("\n🎯 RESULTADO: ¡COMPLETAMENTE EXITOSO!")
        show_integration_next_steps()
    else:
        print("\n🎯 RESULTADO: ERROR")