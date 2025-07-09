import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from ava_graph_state import AgentState
from ava_graph_multimodal import MultiModalMemory, ShortMemoryContextWithQdrant
import os
from supabase import create_client

class SummaryAgent:
    """Agente especializado en crear resúmenes y guardar en DB"""
    
    def __init__(self, api_key: Optional[str] = None, db_path: str = "summary.db"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.db_path = db_path
        self.llm = None
        self._init_database()
        self._init_llm()
    
    def _init_llm(self):
        """Inicializar LLM para análisis"""
        if self.api_key:
            self.llm = ChatGroq(
                api_key=self.api_key,
                model_name="meta-llama/llama-4-maverick-17b-128e-instruct",
                temperature=0.1,
                max_tokens=2000
            )
        else:
            print("⚠️ GROQ_API_KEY no encontrada - SummaryAgent funcionará en modo básico")
    
    def _init_database(self):
        """Inicializar base de datos con tabla adicional"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla existing summaries
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            summary_type TEXT NOT NULL,
            structured_data TEXT NOT NULL,
            llm_summary TEXT,
            conversation_context TEXT,
            tools_executed TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # ✅ NUEVA TABLA PARA MENSAJES ARCHIVADOS
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            archived_messages TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Base de datos inicializada: {self.db_path}")

    def _generate_json_summary(self, state: AgentState) -> Optional[Dict]:
        """Generar resumen JSON directo usando LLM"""
        if not self.llm:
            return None
        
        try:
            prompt = f"""Analiza este estado de agente conversacional y responde SOLO con JSON válido:

ESTADO DEL AGENTE:
- Mensajes actuales: {len(state.get("messages", []))}
- Historial: {len(state.get("conversation_history", []))}
- Plan ejecutado: {bool(state.get("execution_plan"))}
- Resultados herramientas: {bool(state.get("plan_status", {}).get("results"))}
- Resultado actual: {str(state.get("tool_result", ""))[:200]}

ÚLTIMO MENSAJE USUARIO: {self._get_last_user_message(state)}

RESULTADOS HERRAMIENTAS: {self._get_tools_summary(state)}

RESPONDE SOLO CON ESTE JSON (sin texto adicional):
{{
    "success": true,
    "user_query": "¿qué está pidiendo el usuario?",
    "tools_executed": ["lista", "de", "herramientas"],
    "specific_data": {{
        "urls": ["enlaces encontrados"],
        "prices": ["precios encontrados"],
        "dates": ["fechas encontradas"],
        "locations": ["ubicaciones encontradas"]
    }},
    "conversation_context": "resumen de 1 línea de la conversación",
    "assistant_response": "¿qué respondió el asistente?",
    "actionable_data": true,
    "timestamp": "{datetime.now().isoformat()}"
}}"""

            message = HumanMessage(content=prompt)
            response = self.llm.invoke([message])
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                return json.loads(response_text)
                
        except Exception as e:
            print(f"❌ Error generando JSON summary: {e}")
            return None

    def _init_supabase(self):
        """Inicializar cliente Supabase"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY')
        if not url or not key:
            print("❌ SUPABASE_URL o SUPABASE_SERVICE_KEY no configurados")
            self.supabase = None
        else:
            self.supabase = create_client(url, key)
            print("✅ Cliente Supabase inicializado")

    def save_conversation_to_supabase(self, state: AgentState, summary_data: Dict):
        """Guardar resumen en Supabase"""
        if not hasattr(self, 'supabase'):
            self._init_supabase()
        if not self.supabase:
            print("❌ Supabase no inicializado, no se guarda en la nube")
            return

        try:
            session_id = state.get("session_id", "unknown")
            data = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "summary_type": "conversation_summary",
                "structured_data": summary_data,
                "llm_summary": summary_data.get("conversation_context", ""),
            }
            response = self.supabase.table('summaries').insert(data).execute()
            print("✅ Resumen guardado en Supabase:", response)
        except Exception as e:
            print(f"❌ Error guardando en Supabase: {e}")

    def save_conversation_to_db(self, state: AgentState, summary_data: Dict):
        """Guardar conversación resumida en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session_id = state.get("session_id", "unknown")
            
            # Guardar resumen principal
            cursor.execute('''
                INSERT INTO summaries (session_id, timestamp, summary_type, structured_data, llm_summary)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                datetime.now().isoformat(),
                "conversation_summary",
                json.dumps(summary_data),
                summary_data.get("conversation_context", "")
            ))
            
            # Guardar mensajes que se van a eliminar del state
            messages_to_save = []
            for msg in state.get("conversation_history", []):
                if hasattr(msg, 'content'):
                    messages_to_save.append({
                        "content": str(msg.content),
                        "type": msg.__class__.__name__,
                        "timestamp": datetime.now().isoformat()
                    })
            
            cursor.execute('''
                INSERT INTO conversation_archive (session_id, archived_messages, timestamp)
                VALUES (?, ?, ?)
            ''', (
                session_id,
                json.dumps(messages_to_save),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            print(f"✅ Conversación guardada en DB: {session_id}")
            
            # Al final, después de guardar en SQLite:
            self.save_conversation_to_supabase(state, summary_data)
            
        except Exception as e:
            print(f"❌ Error guardando en DB: {e}")

    def _get_last_user_message(self, state: AgentState) -> str:
        """Extraer último mensaje del usuario"""
        for msg in reversed(state.get("messages", [])):
            if hasattr(msg, 'content') and 'Human' in str(type(msg)):
                return str(msg.content)
        return ""

    def _get_tools_summary(self, state: AgentState) -> str:
        """Resumen de herramientas ejecutadas"""
        tools = []
        if state.get("plan_status", {}).get("results"):
            for result in state["plan_status"]["results"]:
                if result.get("tool"):
                    tools.append(f"{result['tool']}: {str(result.get('result', ''))[:50]}")
        return " | ".join(tools[:3])

# ✅ CLASE 2: ShortMemoryContext (Nueva clase separada)
class ShortMemoryContext:
    """Clase especializada en recuperar contexto resumido y modificar el state"""
    
    def __init__(self, db_path: str = "summary.db"):
        self.db_path = db_path
    
    def enrich_state_with_context(self, state: AgentState) -> AgentState:
        """Modificar el state agregando contexto de mensajes resumidos usando context_memory"""
        try:
            session_id = state.get("session_id")
            print(f"🧠 ENRIQUECIENDO STATE para session: {session_id}")
            
            if not session_id:
                print("   ❌ No session_id - saltando enriquecimiento")
                return state
            
            # ✅ EXTRAER SOLO LOS JSON DE RESÚMENES
            recent_summaries = self._get_recent_summaries(session_id)
            
            print(f"   📊 Extraídos: {len(recent_summaries)} resúmenes")
            
            # 🔧 SIMPLIFICAR: SOLO LOS JSON STRUCTURED_DATA
            context_memory_json = []
            for summary in recent_summaries:
                json_data = summary.get("structured_data", {})
                if json_data:
                    context_memory_json.append(json_data)
            
            # ✅ ASIGNAR SOLO LA LISTA DE JSON AL context_memory
            state["context_memory"] = context_memory_json
            
            # ✅ VERIFICAR QUE SE LLENÓ CORRECTAMENTE
            print(f"   ✅ context_memory llenado con {len(context_memory_json)} JSON resúmenes")
            for i, json_data in enumerate(context_memory_json, 1):
                print(f"      {i}. Query: {json_data.get('user_query', 'N/A')}")
                print(f"         Tools: {json_data.get('tools_executed', [])}")
            
            return state
            
        except Exception as e:
            print(f"❌ Error enriqueciendo state: {e}")
            return state
    
    def _get_recent_summaries(self, session_id: str) -> List[Dict]:
        """Extraer últimos resúmenes de la sesión"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print(f"🔍 Buscando resúmenes para session: {session_id}")
            
            # ✅ BUSCAR EN TODAS LAS SESIONES PRIMERO PARA DEBUG
            cursor.execute('SELECT COUNT(*) FROM summaries')
            total_count = cursor.fetchone()[0]
            print(f"   📊 Total resúmenes en DB: {total_count}")
            
            # ✅ BUSCAR ESPECÍFICO DE LA SESIÓN
            cursor.execute('''
                SELECT structured_data, llm_summary, timestamp, session_id FROM summaries
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 3
            ''', (session_id,))
            
            results = cursor.fetchall()
            print(f"   📊 Resúmenes encontrados para session {session_id}: {len(results)}")
            
            if not results:
                # ✅ SI NO HAY PARA LA SESIÓN ACTUAL, BUSCAR LOS MÁS RECIENTES
                print("   🔍 No hay para la sesión actual, buscando los 3 más recientes...")
                cursor.execute('''
                    SELECT structured_data, llm_summary, timestamp, session_id FROM summaries
                    ORDER BY created_at DESC
                    LIMIT 3
                ''')
                results = cursor.fetchall()
                print(f"   📊 Resúmenes más recientes encontrados: {len(results)}")
            
            conn.close()
            
            summaries = []
            for row in results:
                try:
                    structured_data = json.loads(row[0])
                    summary_obj = {
                        "structured_data": structured_data,
                        "llm_summary": row[1],
                        "timestamp": row[2],
                        "session_id": row[3]
                    }
                    summaries.append(summary_obj)
                    print(f"   ✅ Resumen procesado: {structured_data.get('user_query', 'N/A')}")
                except Exception as e:
                    print(f"   ❌ Error procesando resumen: {e}")
                    continue
        
            return summaries
        
        except Exception as e:
            print(f"❌ Error obteniendo resúmenes: {e}")
            return []
    
    def _get_archived_messages(self, session_id: str) -> List[Dict]:
        """Extraer últimos mensajes archivados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT archived_messages, timestamp FROM conversation_archive
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT 2
            ''', (session_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            archived_messages = []
            for row in results:
                try:
                    messages_data = json.loads(row[0])
                    for msg in messages_data:
                        msg["archive_timestamp"] = row[1]
                        archived_messages.append(msg)
                except:
                    continue
            
            return archived_messages[-8:]  # Últimos 8 mensajes archivados
            
        except Exception as e:
            print(f"Error obteniendo mensajes archivados: {e}")
            return []
    
    def _create_enriched_context(self, summaries: List[Dict], archived_messages: List[Dict]) -> str:
        """Crear contexto enriquecido para el agente conversacional"""
        try:
            context_parts = []
            
            # ✅ CONTEXTO DE RESÚMENES PREVIOS
            if summaries:
                context_parts.append("CONTEXTO PREVIO DE LA CONVERSACIÓN:")
                for summary in summaries[:2]: # Últimos 2 resúmenes
                    structured = summary.get("structured_data", {})
                    context_parts.append(f"- {structured.get('conversation_context', 'Contexto no disponible')}")
                    
                    # Datos específicos importantes
                    specific_data = structured.get("specific_data", {})
                    if specific_data.get("urls"):
                        context_parts.append(f"  Enlaces: {', '.join(specific_data['urls'][:2])}")
                    if specific_data.get("prices"):
                        context_parts.append(f"  Precios: {', '.join(specific_data['prices'][:2])}")
                    if specific_data.get("locations"):
                        context_parts.append(f"  Ubicaciones: {', '.join(specific_data['locations'][:2])}")
            
            # ✅ CONTEXTO DE MENSAJES ARCHIVADOS RELEVANTES
            if archived_messages:
                context_parts.append("\nMENSAJES ANTERIORES IMPORTANTES:")
                user_messages = [msg for msg in archived_messages if "Human" in msg.get("type", "")]
                for msg in user_messages[-3:]:  # Últimos 3 mensajes del usuario
                    content_preview = msg["content"][:120] + "..." if len(msg["content"]) > 120 else msg["content"]
                    context_parts.append(f"- Usuario: {content_preview}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"Error creando contexto enriquecido: {e}")
            return "Contexto no disponible"

# ✅ NODOS PARA EL GRAFO
def create_summary_node():
    """Nodo summary - CORREGIDO"""
    
    def summary_node(state: AgentState) -> AgentState:
        print("📋 SUMMARY NODE - Procesando...")
        
        try:
            # ✅ CORREGIR: Usar el método correcto
            hybrid_integration = HybridMemoryIntegration()
            
            # ✅ OPCIÓN 1: Usar save_to_hybrid_memory (que ya funciona)
            hybrid_integration.save_to_hybrid_memory(state)
            print("✅ Conversación guardada en memoria híbrida")
            
        except AttributeError as e:
            print(f"⚠️ Error en summary: {e}")
            print("✅ Continuando sin guardar en memoria...")
        except Exception as e:
            print(f"⚠️ Error inesperado en summary: {e}")
        
        # ✅ MARCAR COMO COMPLETADO
        state["node"] = "summary_completed"
        state["summary_timestamp"] = datetime.now().isoformat()
        
        print("✅ Summary node completado")
        return state
    
    return summary_node

def create_short_memory_context_node():
    """Nodo que enriquece el state con memoria de contexto"""
    
    def short_memory_context_node(state: AgentState) -> AgentState:
        print("🧠 SHORT_MEMORY_CONTEXT: ¡INICIANDO!")
        print(f"   📊 Session ID: {state.get('session_id', 'No encontrado')}")
        
        memory_context = ShortMemoryContext()
        enriched_state = memory_context.enrich_state_with_context(state)
        
        # ✅ VERIFICAR context_memory SIMPLIFICADO
        context_memory = enriched_state.get("context_memory", [])
        
        if context_memory:
            print(f"   ✅ CONTEXT_MEMORY: {len(context_memory)} resúmenes JSON")
            
            for i, json_data in enumerate(context_memory, 1):
                print(f"      {i}. Query: {json_data.get('user_query', 'N/A')}")
                print(f"         Context: {json_data.get('conversation_context', 'N/A')}")
                print(f"         Tools: {json_data.get('tools_executed', [])}")
        else:
            print("   ❌ NO se encontró context_memory en el state")
        
        enriched_state["node"] = "conversational"
        return enriched_state
    
    return short_memory_context_node

class HybridMemoryIntegration:
    """🔗 Integración SQL + Vectorial - CORREGIDA"""
    
    def __init__(self):
        self.sql_memory = ShortMemoryContext()
        self.vector_memory = ShortMemoryContextWithQdrant()
        self.summary_agent = SummaryAgent()
    
    def enrich_state_with_hybrid_context(self, state: AgentState) -> AgentState:
        """Combinar SQL + Vectorial manteniendo compatibilidad"""
        
        try:
            # SQL Context (formato original para planner)
            sql_enriched_state = self.sql_memory.enrich_state_with_context(state.copy())
            sql_context = sql_enriched_state.get("context_memory", [])
            
            # Vector Context (enriquecimiento adicional)
            vector_enriched_state = self.vector_memory.enrich_state_with_context(state.copy())
            vector_context = vector_enriched_state.get("context_memory", [])
            
            # ✅ USAR MÉTODO DE FUSIÓN
            merged_context = self._merge_contexts(sql_context, vector_context)
            
            # ✅ MANTENER FORMATO CONSISTENTE
            state["context_memory"] = merged_context
            
            # ✅ OPCIONAL: Guardar contexto vectorial separado si es necesario
            if vector_context:
                state["vector_context"] = vector_context[:3]  # Solo los 3 más relevantes
            
            return state
            
        except Exception as e:
            print(f"⚠️ Error en hybrid context: {e}")
            return state
    
    def save_to_hybrid_memory(self, state: AgentState):
        """Guardar en ambos sistemas - SIN ERRORES"""
        
        try:
            # ✅ PROCESAR SOLO SI HAY MENSAJES
            messages = state.get('messages', [])
            if not messages:
                print("ℹ️ No hay mensajes para guardar")
                return
            
            # ✅ CONVERTIR AIMESSAGE A STRING SEGURO
            conversation_text = []
            for msg in messages:
                if hasattr(msg, 'content') and msg.content:
                    msg_type = msg.__class__.__name__
                    conversation_text.append(f"{msg_type}: {str(msg.content)}")
            
            # ✅ CREAR ESTADO SIMPLE PARA MEMORIA
            simple_state = {
                'session_id': state.get('session_id', 'unknown'),
                'user_id': state.get('user_id', 'default'),
                'conversation': '\n'.join(conversation_text),
                'timestamp': datetime.now().isoformat(),
                'message_count': len(messages)
            }
            
            # ✅ GUARDAR SOLO EN MEMORIA VECTORIAL (sin errores)
            try:
                # Solo si el método acepta strings
                if hasattr(self.vector_memory, 'save_text_to_memory'):
                    self.vector_memory.save_text_to_memory(simple_state['conversation'])
                    print("✅ Guardado en memoria vectorial")
            except Exception as e:
                print(f"ℹ️ Memoria vectorial no disponible: {e}")
            
            print("✅ Proceso de memoria completado")
            
        except Exception as e:
            print(f"ℹ️ Error no crítico en memoria: {e}")
    
    def _merge_contexts(self, sql_context, vector_context) -> list:
        """Fusionar contextos manteniendo compatibilidad con planner - CORREGIDO"""
        
        # ✅ NORMALIZAR SQL CONTEXT A LISTA
        sql_summaries = []
        if isinstance(sql_context, list):
            sql_summaries = sql_context
        elif isinstance(sql_context, dict) and sql_context:
            sql_summaries = [sql_context]
        
        # ✅ NORMALIZAR VECTOR CONTEXT A LISTA
        vector_summaries = []
        if isinstance(vector_context, list):
            vector_summaries = vector_context[:3]  # Solo los 3 más relevantes
        elif isinstance(vector_context, dict) and vector_context:
            vector_summaries = [vector_context]
        
        # ✅ FUSIONAR MANTENIENDO COMPATIBILIDAD CON PLANNER
        # El planner espera una lista de objetos JSON
        merged = []
        
        # Agregar contexto SQL primero (más confiable)
        merged.extend(sql_summaries)
        
        # Agregar contexto vectorial que no esté duplicado
        for vector_item in vector_summaries:
            if vector_item not in merged:
                merged.append(vector_item)
        
        # ✅ LIMITAR A MÁXIMO 5 ELEMENTOS PARA PERFORMANCE
        return merged[:5]

# ✅ NODOS CORREGIDOS
def create_short_memory_context_node():
    """Nodo híbrido con nombre original - CORREGIDO"""
    hybrid_integration = HybridMemoryIntegration()
    
    def short_memory_context_node(state: AgentState) -> AgentState:
        print("🧠 ENRIQUECIENDO STATE para session: {}".format(state.get('session_id', 'unknown')))
        
        try:
            enriched_state = hybrid_integration.enrich_state_with_hybrid_context(state)
            
            # ✅ DEBUG: Mostrar contexto cargado
            context_memory = enriched_state.get("context_memory", [])
            print(f"   📊 Contexto híbrido cargado: {len(context_memory)} elementos")
            
            return enriched_state
            
        except Exception as e:
            print(f"⚠️ Error en short_memory_context: {e}")
            return state
    
    return short_memory_context_node

def create_summary_node():
    """Nodo summary híbrido con nombre original - CORREGIDO"""
    hybrid_integration = HybridMemoryIntegration()
    summary_agent = SummaryAgent()  # <--- Instancia del agente

    def summary_node(state: AgentState) -> AgentState:
        print("📋 SUMMARY NODE - Guardando en memoria híbrida...")

        try:
            # Guardar en SQLite y Supabase
            summary_data = summary_agent._generate_json_summary(state)
            if summary_data:
                summary_agent.save_conversation_to_db(state, summary_data)
            else:
                print("❌ No se pudo generar el resumen JSON para guardar")

            # Guardar en memoria vectorial si aplica
            hybrid_integration.save_to_hybrid_memory(state)

            # Actualizar estado
            updated_state = state.copy()
            updated_state["node"] = "summary_completed"
            updated_state["timestamp"] = datetime.now()

            print("✅ Summary híbrido completado")
            return updated_state

        except Exception as e:
            print(f"⚠️ Error en summary: {e}")
            updated_state = state.copy()
            updated_state["node"] = "summary_completed"
            updated_state["timestamp"] = datetime.now()
            return updated_state

    return summary_node

