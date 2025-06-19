import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from ava_graph_state import AgentState
import os
import uuid
import time

# ✅ QDRANT CON CONFIGURACIÓN ROBUSTA
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

class MultiModalMemory:
    """🧠 MEMORIA VECTORIAL OPTIMIZADA PARA TU AGENTSTATE EXACTO"""
    
    def __init__(self):
        """Inicializar Qdrant con configuración robusta"""
        
        # ✅ CONFIGURACIÓN ROBUSTA PARA QDRANT-NEW
        self.collection_name = "ava_memory"
        self.embeddings = SentenceTransformer('all-MiniLM-L6-v2')
        
        # ✅ INTENTAR MÚLTIPLES CONFIGURACIONES
        qdrant_configs = [
            {"host": "localhost", "port": 6333, "timeout": 60},
            {"host": "127.0.0.1", "port": 6333, "timeout": 60},
            {"url": "http://localhost:6333", "timeout": 60},
        ]
        
        self.client = None
        connection_error = None
        
        print("🔄 Conectando a qdrant-new...")
        
        for config in qdrant_configs:
            try:
                print(f"🔍 Probando: {config}")
                
                if "url" in config:
                    client = QdrantClient(
                        url=config["url"], 
                        timeout=config["timeout"],
                        prefer_grpc=False  # Usar HTTP
                    )
                else:
                    client = QdrantClient(
                        host=config["host"], 
                        port=config["port"],
                        timeout=config["timeout"],
                        prefer_grpc=False  # Usar HTTP
                    )
                
                # ✅ PROBAR CONEXIÓN CON REINTENTOS
                for attempt in range(3):
                    try:
                        collections = client.get_collections()
                        self.client = client
                        print(f"✅ Conectado a qdrant-new con: {config}")
                        break
                    except Exception as e:
                        if attempt < 2:
                            print(f"⚠️ Intento {attempt + 1} falló, reintentando en 2s...")
                            time.sleep(2)
                        else:
                            raise e
                
                if self.client:
                    break
                    
            except Exception as e:
                connection_error = e
                print(f"❌ Error con {config}: {str(e)[:100]}")
                continue
        
        # ✅ FALLBACK A MEMORIA SI NO FUNCIONA QDRANT EXTERNO
        if self.client is None:
            try:
                print("🔄 Usando Qdrant en memoria como fallback...")
                self.client = QdrantClient(":memory:")
                print("⚠️ Conectado a Qdrant en memoria (sin persistencia)")
            except Exception as e:
                raise Exception(f"❌ No se pudo conectar a Qdrant: {connection_error}. Error memoria: {e}")
        
        # ✅ CREAR COLECCIÓN CON MANEJO DE ERRORES
        try:
            self.client.get_collection(self.collection_name)
            print(f"✅ Colección '{self.collection_name}' ya existe")
        except:
            try:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                print(f"✅ Colección '{self.collection_name}' creada exitosamente")
            except Exception as e:
                print(f"⚠️ Error creando colección: {e}")
                if "already exists" not in str(e).lower():
                    raise
    
    def _generar_point_id(self, user_id: str, session_id: str, timestamp: str) -> str:
        """Generar UUID válido para Qdrant"""
        data = f"{user_id}_{session_id}_{timestamp}"
        hash_md5 = hashlib.md5(data.encode()).hexdigest()
        uuid_str = f"{hash_md5[:8]}-{hash_md5[8:12]}-{hash_md5[12:16]}-{hash_md5[16:20]}-{hash_md5[20:32]}"
        return uuid_str
    
    def guardar_agent_state(self, state: AgentState) -> str:
        """💾 GUARDAR AGENTSTATE USANDO TUS CAMPOS EXACTOS"""
        
        # ✅ Extraer campos exactos de tu AgentState
        user_id = state.get("user_id", "default_user")
        session_id = state.get("session_id", "default_session")
        messages = state.get("messages", [])
        conversation_history = state.get("conversation_history", [])
        
        # ✅ Crear texto para embedding usando tus campos
        texto_embedding = self._crear_texto_para_embedding(state)
        
        # ✅ Generar embedding
        vector = self.embeddings.encode(texto_embedding).tolist()
        
        # ✅ Crear payload con EXACTAMENTE tus campos del AgentState
        timestamp = datetime.now().isoformat()
        payload = {
            # 📝 Identificación
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": timestamp,
            
            # 💬 Mensajes (tus campos exactos)
            "messages": messages,
            "conversation_history": conversation_history,
            "current_message": messages[-1] if messages else "",
            "messages_count": len(messages),
            "history_count": len(conversation_history),
            
            # 📋 Plan y ejecución (tus campos exactos)
            "execution_plan": state.get("execution_plan", {}),
            "plan_status": state.get("plan_status", {}),
            "current_step": state.get("execution_plan", {}).get("current_step", ""),
            "plan_steps": list(state.get("execution_plan", {}).keys()),
            "status_results": state.get("plan_status", {}),
            
            # 🔧 Herramientas (tus campos exactos)
            "tool_to_execute": state.get("tool_to_execute"),
            "tool_arguments": state.get("tool_arguments", {}),
            "tool_result": state.get("tool_result", ""),
            "available_tools": state.get("available_tools", {}),
            "tools_used": list(state.get("available_tools", {}).keys()),
            
            # 🧠 Contexto y estado (tus campos exactos)
            "context_memory": state.get("context_memory", {}),
            "node": state.get("node", "start"),
            "error_message": state.get("error_message"),
            
            # 📊 Métricas derivadas de tus campos
            "has_error": state.get("error_message") is not None,
            "has_tool_result": bool(state.get("tool_result", "")),
            "plan_complexity": len(state.get("execution_plan", {})),
            "tools_available": len(state.get("available_tools", {})),
            
            # 🏷️ Clasificación automática
            "conversation_type": self._clasificar_conversacion(messages),
            "state_status": self._evaluar_estado(state),
            
            # 🎯 Estado completo para casos especiales
            "full_state": state
        }
        
        # ✅ Generar ID único
        point_id = self._generar_point_id(user_id, session_id, timestamp)
        
        # ✅ Crear punto
        point = PointStruct(
            id=point_id,
            vector=vector,
            payload=payload
        )
        
        # ✅ Guardar en Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        return point_id
    
    def _crear_texto_para_embedding(self, state: AgentState) -> str:
        """📝 Crear texto para embedding usando TUS CAMPOS EXACTOS"""
        
        partes = []
        
        # 💬 Mensajes actuales
        messages = state.get("messages", [])
        if messages:
            for i, msg in enumerate(messages):
                partes.append(f"Mensaje {i+1}: {msg}")
        
        # 📚 Historial de conversación
        conversation_history = state.get("conversation_history", [])
        if conversation_history:
            historial_texto = " ".join(conversation_history[-3:])  # Últimas 3
            partes.append(f"Historial: {historial_texto}")
        
        # 📋 Plan de ejecución
        execution_plan = state.get("execution_plan", {})
        if execution_plan:
            plan_texto = ", ".join([f"{k}: {v}" for k, v in execution_plan.items()])
            partes.append(f"Plan: {plan_texto}")
        
        # 📊 Estado del plan
        plan_status = state.get("plan_status", {})
        if plan_status:
            status_texto = ", ".join([f"{k}: {v}" for k, v in plan_status.items()])
            partes.append(f"Estado: {status_texto}")
        
        # 🔧 Herramienta actual
        tool_to_execute = state.get("tool_to_execute")
        if tool_to_execute:
            partes.append(f"Herramienta: {tool_to_execute}")
        
        # 📈 Resultado de herramienta
        tool_result = state.get("tool_result", "")
        if tool_result:
            partes.append(f"Resultado: {tool_result}")
        
        # 🧠 Memoria contextual
        context_memory = state.get("context_memory", {})
        if context_memory:
            if isinstance(context_memory, dict):
                context_texto = ", ".join([f"{k}: {v}" for k, v in context_memory.items()])
            else:
                context_texto = str(context_memory)
            partes.append(f"Contexto: {context_texto}")
        
        # ❌ Errores
        error_message = state.get("error_message")
        if error_message:
            partes.append(f"Error: {error_message}")
        
        return " | ".join(partes)
    
    def _clasificar_conversacion(self, messages: List[str]) -> str:
        """🏷️ Clasificar conversación basada en mensajes"""
        if not messages:
            return "empty"
        
        ultimo_mensaje = messages[-1].lower() if messages else ""
        
        if "?" in ultimo_mensaje or any(palabra in ultimo_mensaje for palabra in ["cómo", "qué", "por qué", "cuándo"]):
            return "question"
        elif any(palabra in ultimo_mensaje for palabra in ["error", "problema", "falla", "bug"]):
            return "error_support"
        elif any(palabra in ultimo_mensaje for palabra in ["código", "implementar", "desarrollar", "crear"]):
            return "development"
        elif any(palabra in ultimo_mensaje for palabra in ["ejecutar", "correr", "iniciar"]):
            return "execution"
        else:
            return "general"
    
    def _evaluar_estado(self, state: AgentState) -> str:
        """📊 Evaluar estado basado en tus campos"""
        
        # ❌ Si hay error
        if state.get("error_message"):
            return "error"
        
        # 🔧 Si hay herramienta ejecutándose
        if state.get("tool_to_execute"):
            return "executing_tool"
        
        # ✅ Si hay resultado de herramienta
        if state.get("tool_result"):
            return "tool_completed"
        
        # 📋 Si hay plan activo
        if state.get("execution_plan"):
            return "planning"
        
        # 💬 Si solo hay mensajes
        if state.get("messages"):
            return "conversing"
        
        return "idle"
    
    def buscar_estados_similares(self, state: AgentState, limite: int = 5, threshold: float = 0.6) -> List[Dict]:
        """🔍 BUSCAR ESTADOS SIMILARES USANDO TUS CAMPOS - SIN WARNINGS"""
        
        user_id = state.get("user_id", "default_user")
        
        # ✅ Crear consulta basada en tu state
        query_text = self._crear_texto_para_embedding(state)
        query_vector = self.embeddings.encode(query_text).tolist()
        
        # ✅ USAR query_points (método actualizado, sin warnings)
        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter={
                "must": [{"key": "user_id", "match": {"value": user_id}}]
            },
            limit=limite * 2,
            score_threshold=threshold
        )
        
        # ✅ Formatear resultados con tus campos
        estados_similares = []
        mensajes_vistos = set()
        
        for hit in search_result.points:  # ✅ Cambio: .points
            current_message = hit.payload["current_message"]
            
            # Evitar duplicados por mensaje
            if current_message not in mensajes_vistos:
                estado = {
                    "id": hit.id,
                    "similarity_score": hit.score,
                    "timestamp": hit.payload["timestamp"],
                    
                    # 💬 Tus campos de mensajes
                    "messages": hit.payload["messages"],
                    "conversation_history": hit.payload["conversation_history"],
                    "current_message": current_message,
                    "messages_count": hit.payload["messages_count"],
                    
                    # 📋 Tus campos de plan
                    "execution_plan": hit.payload["execution_plan"],
                    "plan_status": hit.payload["plan_status"],
                    "current_step": hit.payload["current_step"],
                    
                    # 🔧 Tus campos de herramientas
                    "tool_to_execute": hit.payload["tool_to_execute"],
                    "tool_result": hit.payload["tool_result"],
                    "available_tools": hit.payload["available_tools"],
                    
                    # 🧠 Tus campos de contexto
                    "context_memory": hit.payload["context_memory"],
                    "node": hit.payload["node"],
                    "error_message": hit.payload["error_message"],
                    
                    # 📊 Clasificaciones
                    "conversation_type": hit.payload["conversation_type"],
                    "state_status": hit.payload["state_status"],
                    
                    # 🎯 Estado completo
                    "full_state": hit.payload.get("full_state", {})
                }
                estados_similares.append(estado)
                mensajes_vistos.add(current_message)
                
                if len(estados_similares) >= limite:
                    break
        
        return estados_similares
    
    def obtener_historial_usuario(self, user_id: str, limite: int = 10) -> List[Dict]:
        """📚 OBTENER HISTORIAL USANDO TUS CAMPOS"""
        
        search_result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter={
                "must": [{"key": "user_id", "match": {"value": user_id}}]
            },
            limit=limite,
            with_payload=True
        )
        
        # ✅ Formatear con tus campos exactos
        historial = []
        for point in search_result[0]:
            estado = {
                "id": point.id,
                "timestamp": point.payload["timestamp"],
                "session_id": point.payload["session_id"],
                
                # 💬 Tus campos principales
                "current_message": point.payload["current_message"],
                "messages_count": point.payload["messages_count"],
                "conversation_type": point.payload["conversation_type"],
                "state_status": point.payload["state_status"],
                
                # 📋 Plan info
                "current_step": point.payload["current_step"],
                "plan_complexity": point.payload["plan_complexity"],
                
                # 🔧 Tool info
                "tool_to_execute": point.payload["tool_to_execute"],
                "has_tool_result": point.payload["has_tool_result"],
                
                # ❌ Error info
                "has_error": point.payload["has_error"],
                "error_message": point.payload["error_message"],
                
                # 🎯 Estado completo
                "full_state": point.payload.get("full_state", {})
            }
            historial.append(estado)
        
        # ✅ Ordenar por timestamp
        historial.sort(key=lambda x: x["timestamp"], reverse=True)
        return historial
    
    # ✅ FUNCIONES LEGACY PARA COMPATIBILIDAD
    def guardar_conversacion(self, user_id: str, session_id: str, 
                           pregunta: str, respuesta: str, herramientas: List[str] = None):
        """Función legacy - crear state temporal"""
        temp_state = {
            "user_id": user_id,
            "session_id": session_id,
            "messages": [pregunta, respuesta],
            "conversation_history": [],
            "execution_plan": {},
            "plan_status": {},
            "tool_to_execute": None,
            "tool_arguments": {},
            "tool_result": "",
            "available_tools": {tool: {} for tool in (herramientas or [])},
            "node": "start",
            "timestamp": datetime.now(),
            "error_message": None,
            "context_memory": {}
        }
        return self.guardar_agent_state(temp_state)
    
    def buscar_memorias(self, consulta: str, user_id: str, limite: int = 5, threshold: float = 0.7):
        """Función legacy - SIN WARNINGS"""
        temp_state = {
            "user_id": user_id,
            "messages": [consulta],
            "conversation_history": [],
            "execution_plan": {},
            "plan_status": {},
            "tool_to_execute": None,
            "tool_arguments": {},
            "tool_result": "",
            "available_tools": {},
            "node": "start",
            "timestamp": datetime.now(),
            "error_message": None,
            "context_memory": {}
        }
        
        estados = self.buscar_estados_similares(temp_state, limite, threshold)
        
        # Convertir a formato legacy
        memorias = []
        for estado in estados:
            if estado["messages"] and len(estado["messages"]) >= 2:
                memoria = {
                    "id": estado["id"],
                    "score": estado["similarity_score"],
                    "user_id": user_id,
                    "session_id": estado.get("session_id", ""),
                    "pregunta": estado["messages"][0] if estado["messages"] else "",
                    "respuesta": estado["messages"][1] if len(estado["messages"]) > 1 else "",
                    "herramientas": list(estado["available_tools"].keys()),
                    "timestamp": estado["timestamp"]
                }
                memorias.append(memoria)
        
        return memorias
    
    def obtener_contexto_usuario(self, user_id: str, limite: int = 10):
        """Función legacy"""
        historial = self.obtener_historial_usuario(user_id, limite)
        
        contexto = []
        for estado in historial:
            if estado["full_state"].get("messages"):
                messages = estado["full_state"]["messages"]
                conv = {
                    "id": estado["id"],
                    "user_id": user_id,
                    "session_id": estado["session_id"],
                    "pregunta": messages[0] if messages else "",
                    "respuesta": messages[1] if len(messages) > 1 else "",
                    "herramientas": list(estado["full_state"].get("available_tools", {}).keys()),
                    "timestamp": estado["timestamp"]
                }
                contexto.append(conv)
        
        return contexto

class ShortMemoryContextWithQdrant:
    """🔗 INTEGRACIÓN OPTIMIZADA PARA TUS CAMPOS EXACTOS"""
    
    def __init__(self):
        self.memory = MultiModalMemory()
    
    def enrich_state_with_context(self, state: AgentState) -> AgentState:
        """🌟 ENRIQUECER USANDO TUS CAMPOS EXACTOS"""
        
        # ✅ Buscar estados similares
        estados_similares = self.memory.buscar_estados_similares(state, limite=3, threshold=0.5)
        
        # ✅ Enriquecer context_memory (tu campo exacto)
        context_memory = state.get("context_memory", {})
        
        # Si es dict, agregar entradas de contexto
        if isinstance(context_memory, dict):
            context_memory["similar_states"] = []
            for estado in estados_similares:
                context_entry = {
                    "conversation_context": estado["current_message"],
                    "tools_used": list(estado["available_tools"].keys()),
                    "relevance_score": estado["similarity_score"],
                    "timestamp": estado["timestamp"],
                    "conversation_type": estado["conversation_type"],
                    "state_status": estado["state_status"],
                    "plan_step": estado["current_step"]
                }
                context_memory["similar_states"].append(context_entry)
        
        # ✅ Actualizar tu campo exacto
        state["context_memory"] = context_memory
        
        return state
    
    def save_conversation_to_memory(self, state: AgentState) -> str:
        """💾 GUARDAR ESTADO COMPLETO"""
        return self.memory.guardar_agent_state(state)

def create_qdrant_memory_node():
    """🧠 NODO OPTIMIZADO PARA TUS CAMPOS EXACTOS"""
    
    memory_context = ShortMemoryContextWithQdrant()
    
    def memory_node(state: AgentState) -> AgentState:
        """Procesar estado usando tus campos exactos"""
        
        # ✅ Enriquecer context_memory con estados similares
        enriched_state = memory_context.enrich_state_with_context(state)
        
        # ✅ Guardar estado completo
        memory_context.save_conversation_to_memory(enriched_state)
        
        return enriched_state
    
    return memory_node

# ✅ MANTENER FUNCIÓN DE PRUEBA
def test_sistema_ava_completo():
    """🧪 PRUEBA CON TUS CAMPOS EXACTOS"""
    print("🎉 Probando sistema AVA con tus campos exactos...")
    print("=" * 60)
    
    try:
        memory = MultiModalMemory()
        print("✅ MultiModalMemory inicializada")
        
        # ✅ Crear states de prueba con TUS CAMPOS EXACTOS
        test_states = [
            {
                "messages": ["¿Cómo crear un plan de ejecución?"],
                "conversation_history": [],
                "execution_plan": {"step1": "analyze", "step2": "execute"},
                "plan_status": {"step1": "completed"},
                "tool_to_execute": "planner",
                "tool_arguments": {"type": "execution"},
                "tool_result": "Plan creado exitosamente",
                "available_tools": {"planner": {}, "executor": {}},
                "node": "planning",
                "user_id": "test_user",
                "session_id": "session_001",
                "timestamp": datetime.now(),
                "error_message": None,
                "context_memory": {"previous_plans": []}
            },
            {
                "messages": ["Ejecutar herramienta de análisis", "Análisis completado correctamente"],
                "conversation_history": ["¿Cómo crear un plan de ejecución?"],
                "execution_plan": {"step1": "analyze", "step2": "execute"},
                "plan_status": {"step1": "completed", "step2": "in_progress"},
                "tool_to_execute": "analyzer",
                "tool_arguments": {"target": "data"},
                "tool_result": "Análisis: 95% de precisión",
                "available_tools": {"analyzer": {}, "reporter": {}},
                "node": "executing",
                "user_id": "test_user",
                "session_id": "session_002",
                "timestamp": datetime.now(),
                "error_message": None,
                "context_memory": {"analysis_results": ["95% precision"]}
            }
        ]
        
        # ✅ Guardar states de prueba
        print("\n💾 Guardando states de prueba...")
        for i, state in enumerate(test_states, 1):
            point_id = memory.guardar_agent_state(state)
            print(f"  ✅ State {i} guardado: {point_id}")
        
        # ✅ Buscar estados similares
        print("\n🔍 Probando búsqueda de estados similares...")
        query_state = {
            "messages": ["¿Cómo planificar una ejecución?"],
            "conversation_history": [],
            "execution_plan": {},
            "plan_status": {},
            "user_id": "test_user",
            "context_memory": {}
        }
        
        estados_similares = memory.buscar_estados_similares(query_state, limite=2)
        
        for i, estado in enumerate(estados_similares, 1):
            print(f"  {i}. [Similitud: {estado['similarity_score']:.3f}]")
            print(f"     💬 Mensaje: {estado['current_message']}")
            print(f"     📋 Plan: {estado['current_step']}")
            print(f"     🔧 Tool: {estado['tool_to_execute']}")
            print(f"     📊 Estado: {estado['state_status']}")
        
        # ✅ Probar integración
        print("\n🔗 Probando integración ShortMemoryContext...")
        memory_context = ShortMemoryContextWithQdrant()
        
        enriched_state = memory_context.enrich_state_with_context(query_state)
        print(f"✅ Context memory enriquecido: {len(enriched_state['context_memory'].get('similar_states', []))} estados")
        
        # ✅ Estadísticas
        print("\n📊 Estadísticas del sistema...")
        collection_info = memory.client.get_collection(memory.collection_name)
        print(f"✅ Vectores almacenados: {collection_info.points_count}")
        
        print(f"\n🎉 ¡SISTEMA FUNCIONANDO CON TUS CAMPOS EXACTOS!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 INICIANDO SISTEMA AVA CON AGENTSTATE EXACTO...")
    print("-" * 60)
    
    exito = test_sistema_ava_completo()
    
    if exito:
        print(f"\n🎯 SISTEMA LISTO CON TUS CAMPOS:")
        print(f"📝 messages, conversation_history")
        print(f"📋 execution_plan, plan_status")
        print(f"🔧 tool_to_execute, tool_arguments, tool_result")
        print(f"🧠 context_memory, available_tools")
        print(f"🎮 node, user_id, session_id, timestamp")
        print(f"❌ error_message")
        
        print(f"\n✨ ¡Tu sistema AVA usa EXACTAMENTE tus campos! 🎉")