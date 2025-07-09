import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from ava_graph_state import AgentState
from dotenv import load_dotenv

load_dotenv()

class ShortContextMemory:
    """Clase para recuperar contexto resumido SOLO de Supabase"""
    
    def __init__(self):
        self.supabase = None
        self._initialize_supabase()
    
    def _initialize_supabase(self):
        """Inicializar conexión a Supabase - REQUERIDO"""
        try:
            from supabase import create_client
            url = os.getenv('SUPABASE_URL')
            key = os.getenv('SUPABASE_SERVICE_KEY')
            
            if not url or not key:
                print("❌ Variables de entorno de Supabase faltantes")
                print(f"   SUPABASE_URL: {'✅ OK' if url else '❌ FALTANTE'}")
                print(f"   SUPABASE_SERVICE_KEY: {'✅ OK' if key else '❌ FALTANTE'}")
                raise Exception("Credenciales de Supabase no configuradas")
            
            self.supabase = create_client(url, key)
            print("✅ ShortContextMemory conectado a Supabase")
            
        except Exception as e:
            print(f"❌ Error conectando a Supabase: {e}")
            raise Exception("Supabase es requerido para el funcionamiento")
    
    def enrich_state_with_context(self, state: AgentState) -> AgentState:
        """Modificar el state agregando contexto de mensajes resumidos"""
        session_id = state.get("session_id")
        if not session_id:
            print("⚠️ No session_id encontrado, generando uno nuevo")
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            state["session_id"] = session_id
        
        print(f"🔍 Cargando contexto desde Supabase para session: {session_id}")
        archived_context = self._get_archived_context(session_id)
        recent_summaries = self._get_recent_summaries(session_id)
        print(f"   📊 Contexto archivado: {len(archived_context)} mensajes")
        print(f"   📋 Resúmenes recientes: {len(recent_summaries)} encontrados")
        
        # MODIFICAR STATE CON CONTEXTO EXTENDIDO
        state["archived_context"] = archived_context
        state["conversation_summaries"] = recent_summaries
        state["has_extended_memory"] = bool(archived_context or recent_summaries)
        
        # CREAR CONTEXTO ENRIQUECIDO PARA EL AGENTE CONVERSACIONAL
        if archived_context or recent_summaries:
            enriched_context = self._create_enriched_context(archived_context, recent_summaries)
            state["enriched_conversation_context"] = enriched_context
            print(f"✅ State enriquecido con contexto híbrido")
        else:
            print("⚠️ No se encontró contexto previo")
        
        return state
    
    def _get_archived_context(self, session_id: str) -> List[Dict]:
        """Extraer mensajes archivados de Supabase"""
        try:
            response = self.supabase.table('conversation_archive') \
                .select('archived_messages, timestamp') \
                .eq('session_id', session_id) \
                .order('created_at', desc=True) \
                .limit(3) \
                .execute()
            
            archived_messages = []
            for row in response.data:
                messages_data = row['archived_messages']
                if isinstance(messages_data, list):
                    for msg in messages_data:
                        msg["archive_timestamp"] = row['timestamp']
                        archived_messages.append(msg)
            
            print(f"   📥 Mensajes archivados cargados: {len(archived_messages)}")
            return archived_messages[-10:]  # Últimos 10 mensajes
            
        except Exception as e:
            print(f"❌ Error cargando contexto archivado: {e}")
            return []
    
    def _get_recent_summaries(self, session_id: str) -> List[Dict]:
        """Extraer resúmenes recientes de Supabase"""
        try:
            response = self.supabase.table('summaries') \
                .select('structured_data, llm_summary, timestamp') \
                .eq('session_id', session_id) \
                .order('created_at', desc=True) \
                .limit(5) \
                .execute()
            
            summaries = []
            for row in response.data:
                summaries.append({
                    "structured_data": row['structured_data'],
                    "llm_summary": row['llm_summary'],
                    "timestamp": row['timestamp']
                })
            
            print(f"   📋 Resúmenes cargados: {len(summaries)}")
            return summaries
            
        except Exception as e:
            print(f"❌ Error cargando resúmenes: {e}")
            return []
    
    def save_archived_context(self, session_id: str, messages: List[Dict]) -> bool:
        """Guardar contexto archivado en Supabase"""
        try:
            data = {
                'session_id': session_id,
                'archived_messages': messages,
                'timestamp': datetime.now().isoformat(),
            }
            
            response = self.supabase.table('conversation_archive').insert(data).execute()
            success = bool(response.data)
            
            if success:
                print(f"✅ Contexto archivado guardado: {len(messages)} mensajes")
            else:
                print("❌ Error guardando contexto archivado")
                
            return success
            
        except Exception as e:
            print(f"❌ Error en save_archived_context: {e}")
            return False
    
    def save_summary(self, session_id: str, structured_data: Dict, llm_summary: str) -> bool:
        """Guardar resumen en Supabase"""
        try:
            data = {
                'session_id': session_id,
                'structured_data': structured_data,
                'llm_summary': llm_summary,
                'timestamp': datetime.now().isoformat(),
            }
            
            print(f"💾 Guardando resumen en Supabase...")
            print(f"   🆔 Session: {session_id}")
            print(f"   📝 Resumen: {llm_summary[:50]}...")
            
            response = self.supabase.table('summaries').insert(data).execute()
            success = bool(response.data)
            
            if success:
                print(f"✅ Resumen guardado exitosamente")
                # Verificar que se guardó
                verify = self.supabase.table('summaries').select('id').eq('session_id', session_id).execute()
                print(f"   📊 Total resúmenes para esta sesión: {len(verify.data)}")
            else:
                print("❌ Error: respuesta vacía de Supabase")
                
            return success
            
        except Exception as e:
            print(f"❌ Error en save_summary: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_enriched_context(self, archived_messages: List[Dict], summaries: List[Dict]) -> str:
        """Crear contexto enriquecido para el agente conversacional"""
        context_parts = []
        
        # CONTEXTO DE RESÚMENES
        if summaries:
            context_parts.append("CONTEXTO PREVIO DE LA CONVERSACIÓN:")
            for summary in summaries[:2]:
                structured = summary.get("structured_data", {})
                context_parts.append(f"- {structured.get('conversation_context', 'Contexto no disponible')}")
                
                specific_data = structured.get("specific_data", {})
                if specific_data.get("urls"):
                    context_parts.append(f"  Enlaces relevantes: {', '.join(specific_data['urls'][:2])}")
                if specific_data.get("prices"):
                    context_parts.append(f"  Precios mencionados: {', '.join(specific_data['prices'][:2])}")
        
        # CONTEXTO DE MENSAJES ARCHIVADOS
        if archived_messages:
            context_parts.append("\nMENSAJES ANTERIORES RELEVANTES:")
            user_messages = [msg for msg in archived_messages if "Human" in msg.get("type", "")]
            for msg in user_messages[-2:]:
                content_preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                context_parts.append(f"- Usuario dijo: {content_preview}")
        
        return "\n".join(context_parts)

# NODO PARA EL GRAFO
def create_context_memory_node():
    """Nodo que enriquece el state con memoria de contexto desde Supabase"""
    
    def context_memory_node(state: AgentState) -> AgentState:
        print("🧠 Context Memory Node iniciando con Supabase...")
        context_memory = ShortContextMemory()
        enriched_state = context_memory.enrich_state_with_context(state)
        enriched_state["node"] = "conversational"
        return enriched_state
    
    return context_memory_node

# FUNCIÓN DE TEST DIRECTO
def test_supabase_memory():
    """Test directo del sistema de memoria con Supabase"""
    print("🧪 PROBANDO MEMORIA CON SUPABASE")
    print("=" * 40)
    
    try:
        memory = ShortContextMemory()
        
        # Test de guardado
        session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        structured_data = {
            "conversation_context": "Test directo de memoria con Supabase",
            "key_topics": ["test", "memoria", "supabase"],
            "specific_data": {
                "test_type": "direct_memory_test",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        llm_summary = "Test directo de guardado en memoria híbrida"
        
        # Guardar
        success = memory.save_summary(session_id, structured_data, llm_summary)
        
        if success:
            print("✅ Test de guardado exitoso")
            
            # Test de carga
            summaries = memory._get_recent_summaries(session_id)
            if summaries:
                print(f"✅ Test de carga exitoso: {len(summaries)} resúmenes encontrados")
                return True
            else:
                print("❌ Test de carga falló")
                return False
        else:
            print("❌ Test de guardado falló")
            return False
            
    except Exception as e:
        print(f"❌ Error en el test: {e}")
        return False

if __name__ == "__main__":
    test_supabase_memory()