import os
from dotenv import load_dotenv

load_dotenv()

def quick_test():
    """Test rápido de conexión a Supabase"""
    print("🧪 TEST RÁPIDO DE SUPABASE")
    print("=" * 40)
    
    # Verificar variables
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    print(f"🔗 URL: {url}")
    print(f"🔑 KEY: {key[:20]}..." if key else "❌ No configurada")
    
    if not url or not key:
        print("❌ Variables faltantes en .env")
        return False
    
    try:
        from supabase import create_client, Client
        
        # Crear cliente
        supabase: Client = create_client(url, key)
        print("✅ Cliente creado exitosamente")
        
        # Test de conexión
        response = supabase.table('conversation_archive').select('*').limit(1).execute()
        print(f"✅ CONECTADO! Registros encontrados: {len(response.data)}")
        
        # Test de inserción
        from datetime import datetime
        test_data = {
            'session_id': 'test_quick',
            'message_type': 'system',
            'content': 'Test de conexión rápida',
            'created_at': datetime.now().isoformat()
        }
        
        insert_response = supabase.table('conversation_archive').insert(test_data).execute()
        print("✅ Inserción exitosa")
        
        # Limpiar
        supabase.table('conversation_archive').delete().eq('session_id', 'test_quick').execute()
        print("✅ Limpieza completada")
        
        print("🎉 TODO FUNCIONA PERFECTAMENTE!")
        return True
        
    except ImportError:
        print("❌ Supabase no instalado. Ejecuta: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    quick_test()