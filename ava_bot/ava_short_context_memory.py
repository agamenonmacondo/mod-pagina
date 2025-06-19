import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from ava_graph_state import AgentState

class ShortContextMemory:
    """Clase para recuperar contexto resumido de la base de datos y modificar el state"""
    
    def __init__(self, db_path: str = "summary.db"):
        self.db_path = db_path
    
    def enrich_state_with_context(self, state: AgentState) -> AgentState:
        """Modificar el state agregando contexto de mensajes resumidos"""
        try:
            session_id = state.get("session_id")
            if not session_id:
                return state
            
            # ✅ EXTRAER CONTEXTO RESUMIDO DE LA DB
            archived_context = self._get_archived_context(session_id)
            recent_summaries = self._get_recent_summaries(session_id)
            
            # ✅ MODIFICAR STATE CON CONTEXTO EXTENDIDO
            state["archived_context"] = archived_context
            state["conversation_summaries"] = recent_summaries
            state["has_extended_memory"] = bool(archived_context or recent_summaries)
            
            # ✅ CREAR CONTEXTO ENRIQUECIDO PARA EL AGENTE CONVERSACIONAL
            if archived_context or recent_summaries:
                enriched_context = self._create_enriched_context(archived_context, recent_summaries)
                state["enriched_conversation_context"] = enriched_context
            
            print(f"✅ State enriquecido con contexto de {len(recent_summaries)} resúmenes")
            return state
            
        except Exception as e:
            print(f"❌ Error enriqueciendo state: {e}")
            return state
    
    def _get_archived_context(self, session_id: str) -> List[Dict]:
        """Extraer mensajes archivados de la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT archived_messages, timestamp FROM conversation_archive
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 3
            ''', (session_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            archived_messages = []
            for row in results:
                messages_data = json.loads(row[0])
                for msg in messages_data:
                    msg["archive_timestamp"] = row[1]
                    archived_messages.append(msg)
            
            return archived_messages[-10:]  # Últimos 10 mensajes archivados
            
        except Exception as e:
            print(f"Error obteniendo mensajes archivados: {e}")
            return []
    
    def _get_recent_summaries(self, session_id: str) -> List[Dict]:
        """Extraer resúmenes recientes de la sesión"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT structured_data, llm_summary, timestamp FROM summaries
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 5
            ''', (session_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            summaries = []
            for row in results:
                try:
                    structured_data = json.loads(row[0])
                    summaries.append({
                        "structured_data": structured_data,
                        "llm_summary": row[1],
                        "timestamp": row[2]
                    })
                except:
                    continue
            
            return summaries
            
        except Exception as e:
            print(f"Error obteniendo resúmenes: {e}")
            return []
    
    def _create_enriched_context(self, archived_messages: List[Dict], summaries: List[Dict]) -> str:
        """Crear contexto enriquecido para el agente conversacional"""
        try:
            context_parts = []
            
            # ✅ CONTEXTO DE RESÚMENES
            if summaries:
                context_parts.append("CONTEXTO PREVIO DE LA CONVERSACIÓN:")
                for summary in summaries[:2]:  # Últimos 2 resúmenes
                    structured = summary.get("structured_data", {})
                    context_parts.append(f"- {structured.get('conversation_context', 'Contexto no disponible')}")
                    
                    # Datos específicos importantes
                    specific_data = structured.get("specific_data", {})
                    if specific_data.get("urls"):
                        context_parts.append(f"  Enlaces relevantes: {', '.join(specific_data['urls'][:2])}")
                    if specific_data.get("prices"):
                        context_parts.append(f"  Precios mencionados: {', '.join(specific_data['prices'][:2])}")
            
            # ✅ CONTEXTO DE MENSAJES ARCHIVADOS (solo los más relevantes)
            if archived_messages:
                context_parts.append("\nMENSAJES ANTERIORES RELEVANTES:")
                user_messages = [msg for msg in archived_messages if "Human" in msg.get("type", "")]
                for msg in user_messages[-2:]:  # Últimos 2 mensajes del usuario
                    content_preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                    context_parts.append(f"- Usuario dijo: {content_preview}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"Error creando contexto enriquecido: {e}")
            return "Contexto no disponible"

# ✅ NODO PARA EL GRAFO
def create_context_memory_node():
    """Nodo que enriquece el state con memoria de contexto"""
    
    def context_memory_node(state: AgentState) -> AgentState:
        # ✅ CREAR INSTANCIA DE MEMORIA DE CONTEXTO
        context_memory = ShortContextMemory()
        
        # ✅ ENRIQUECER STATE CON CONTEXTO DE LA DB
        enriched_state = context_memory.enrich_state_with_context(state)
        
        # ✅ MARCAR SIGUIENTE NODO
        enriched_state["node"] = "conversational"
        
        return enriched_state
    
    return context_memory_node