"""
Wrappers que MEJORAN los nodos de memoria existentes sin reescribirlos
- Mantienen toda la funcionalidad original
- Añaden capacidades del unified_memory_manager
- Preservan compatibilidad total
"""

import logging
from typing import Dict, Any
from state import AICompanionState

logger = logging.getLogger(__name__)

def context_injection_enhanced(state: AICompanionState) -> str:
    """
    🎯 WRAPPER para context_injection_node existente
    
    QUÉ HACE:
    1. Busca memorias relevantes con unified_memory
    2. Las prepara en formato compatible con el nodo original
    3. Usa la excelente lógica LLM del nodo existente
    4. Mantiene toda la funcionalidad original
    
    BENEFICIOS:
    - Reutiliza tu evaluación LLM perfecta
    - Añade búsqueda inteligente de memorias
    - Zero breaking changes
    """
    try:
        logger.info("🎯 Enhanced context injection starting...")
        
        # 🔍 PASO 1: BUSCAR MEMORIAS RELEVANTES (NUEVO)
        session_id = getattr(state, 'session_id', 'default')
        user_input = state.input
        
        if user_input:
            try:
                # Importar unified_memory dentro de la función para evitar circular imports
                from .unified_memory_manager import unified_memory
                
                # Buscar memorias relevantes usando el sistema unificado
                relevant_memories = unified_memory.search_relevant_memories(
                    session_id=session_id,
                    query=user_input,
                    limit=5
                )
                
                logger.info(f"🔍 Found {len(relevant_memories)} relevant memories")
                
                # 🔄 PASO 2: CONVERTIR A FORMATO COMPATIBLE (CLAVE)
                # El nodo original espera 'related_memories' en el contexto
                if relevant_memories:
                    if not hasattr(state, 'context'):
                        state.context = {}
                    
                    # Convertir formato unified_memory -> formato original
                    formatted_memories = []
                    for memory in relevant_memories:
                        if isinstance(memory, dict):
                            formatted_memories.append({
                                'topic': memory.get('topic', 'Memory'),
                                'content': memory.get('content', str(memory)),
                                'relevance': memory.get('relevance', 0.5)
                            })
                        else:
                            formatted_memories.append({
                                'topic': 'Memory',
                                'content': str(memory),
                                'relevance': 0.5
                            })
                    
                    state.context['related_memories'] = formatted_memories
                    state.context['memory_enhanced'] = True
                    
                    logger.info(f"✅ Prepared {len(formatted_memories)} memories for original node")
                
            except Exception as e:
                logger.warning(f"⚠️ Error searching memories, proceeding without: {e}")
                # Si falla la búsqueda, continuar sin memorias (graceful degradation)
        
        # 🎯 PASO 3: USAR NODO ORIGINAL (SIN CAMBIOS)
        # Importar el nodo existente que ya funciona perfecto
        from .context_injection_node import context_injection_node
        
        # Crear instancia si es una clase
        if hasattr(context_injection_node, 'process'):
            # Es una clase instanciada
            next_node = context_injection_node.process(state)
        else:
            # Es una función o necesita instanciación
            node_instance = context_injection_node()
            next_node = node_instance.process(state)
        
        logger.info("✅ Enhanced context injection completed using original logic")
        return next_node or "conversation_node"
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced context injection: {e}")
        # Graceful fallback: continuar sin contexto mejorado
        return "conversation_node"

def memory_injection_enhanced(state: AICompanionState) -> str:
    """
    💾 WRAPPER para memory_injection_node existente
    
    QUÉ HACE:
    1. Usa el nodo original para persistencia (mantiene compatibilidad)
    2. Añade guardado en unified_memory (Redis + SQLite + JSON)
    3. Auto-sumarización inteligente cada N mensajes
    4. Preserva toda la funcionalidad original
    
    BENEFICIOS:
    - Mantiene tu sistema de persistencia actual
    - Añade redundancia en múltiples sistemas
    - Auto-organización de memoria
    - Zero breaking changes
    """
    try:
        logger.info("💾 Enhanced memory injection starting...")
        
        # 🔄 PASO 1: USAR NODO ORIGINAL PRIMERO (MANTENER COMPATIBILIDAD)
        try:
            from .memory_injection_node import memory_injection_node
            
            # Ejecutar nodo original para mantener compatibilidad
            if hasattr(memory_injection_node, 'process'):
                original_result = memory_injection_node.process(state)
            else:
                node_instance = memory_injection_node()
                original_result = node_instance.process(state)
                
            logger.info("✅ Original memory injection completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Original memory injection failed: {e}")
            original_result = None
        
        # 💾 PASO 2: AÑADIR UNIFIED_MEMORY (NUEVO)
        session_id = getattr(state, 'session_id', 'default')
        
        if state.input and state.response:
            try:
                from .unified_memory_manager import unified_memory
                import time
                
                # Crear datos de interacción completa
                interaction_data = {
                    "user_input": state.input,
                    "assistant_response": state.response,
                    "tools_used": getattr(state, 'tools_used', []),
                    "context_injected": state.context.get('memory_enhanced', False),
                    "node_path": getattr(state, 'node_path', []),
                    "timestamp": time.time()
                }
                
                # Guardar en unified_memory con timestamp único
                timestamp = int(time.time())
                result = unified_memory.store_memory(
                    session_id=session_id,
                    key=f"interaction_{timestamp}",
                    value=interaction_data,
                    data_type="conversation",
                    metadata={
                        "importance": "medium",
                        "interaction_type": "chat",
                        "enhanced": True
                    }
                )
                
                if result.get("success"):
                    systems_used = result.get("systems_used", [])
                    logger.info(f"✅ Interaction stored in unified memory: {', '.join(systems_used)}")
                else:
                    logger.warning(f"⚠️ Failed to store in unified memory: {result.get('error')}")
                
            except Exception as e:
                logger.warning(f"⚠️ Error storing in unified memory: {e}")
        
        # 📊 PASO 3: AUTO-SUMARIZACIÓN INTELIGENTE (NUEVO)
        try:
            conversation_count = len(state.conversation_history)
            
            # Cada 10 mensajes, crear auto-resumen
            if conversation_count >= 10 and conversation_count % 10 == 0:
                logger.info("🔄 Triggering auto-summarization...")
                
                from tools.adapters.memory_summarize_adapter import MemorySummarizeAdapter
                summarizer = MemorySummarizeAdapter()
                
                summary_result = summarizer.execute({
                    "session_id": session_id,
                    "summary_type": "conversation",
                    "save_summary": True
                })
                
                if summary_result.get("success"):
                    logger.info("✅ Auto-summary created and stored")
                    state.context['auto_summary_created'] = True
                else:
                    logger.warning("⚠️ Auto-summary failed")
                    
        except Exception as e:
            logger.warning(f"⚠️ Auto-summarization error: {e}")
        
        logger.info("✅ Enhanced memory injection completed")
        return original_result or END  # Usar resultado del nodo original
        
    except Exception as e:
        logger.error(f"❌ Error in enhanced memory injection: {e}")
        return None  # END del flujo

def memory_command_executor(state: AICompanionState) -> str:
    """
    🧠 NUEVO NODO para ejecutar comandos específicos de memoria
    
    QUÉ HACE:
    - Ejecuta comandos como "Recuerda que...", "¿Qué sabes sobre...?"
    - Usa las memory_adapters ya creadas
    - Establece la respuesta del asistente
    - Maneja errores gracefully
    
    BENEFICIOS:
    - Comandos de memoria explícitos
    - Reutiliza todas las memory_adapters
    - Integración transparente con el grafo
    """
    try:
        memory_command = state.context.get('memory_command', {})
        action = memory_command.get('action')
        session_id = getattr(state, 'session_id', 'default')
        
        logger.info(f"🧠 Executing memory command: {action}")
        
        if action == "save":
            # 💾 COMANDO: "Recuerda que..."
            try:
                from tools.adapters.memory_save_adapter import MemorySaveAdapter
                adapter = MemorySaveAdapter()
                
                result = adapter.execute({
                    "content": memory_command.get('content', ''),
                    "session_id": session_id,
                    "data_type": "text",
                    "importance": "high",  # Comandos explícitos son importantes
                    "tags": "user_request,explicit_command"
                })
                
                if result.get("success"):
                    state.response = result["result"]["message"]
                else:
                    state.response = f"❌ Error guardando: {result.get('error', 'Error desconocido')}"
                    
            except Exception as e:
                logger.error(f"Error in memory save: {e}")
                state.response = f"❌ Error interno guardando memoria: {str(e)}"
        
        elif action == "search":
            # 🔍 COMANDO: "¿Qué sabes sobre...?"
            try:
                from tools.adapters.memory_search_adapter import MemorySearchAdapter
                adapter = MemorySearchAdapter()
                
                query = memory_command.get('query', '').strip()
                if not query:
                    state.response = "❌ No especificaste qué buscar en mi memoria."
                else:
                    result = adapter.execute({
                        "query": query,
                        "session_id": session_id,
                        "limit": 5
                    })
                    
                    if result.get("success"):
                        state.response = result["result"]["message"]
                    else:
                        state.response = f"❌ Error buscando: {result.get('error', 'Error desconocido')}"
                        
            except Exception as e:
                logger.error(f"Error in memory search: {e}")
                state.response = f"❌ Error interno buscando en memoria: {str(e)}"
        
        elif action == "summarize":
            # 📝 COMANDO: "Resume nuestra conversación"
            try:
                from tools.adapters.memory_summarize_adapter import MemorySummarizeAdapter
                adapter = MemorySummarizeAdapter()
                
                result = adapter.execute({
                    "session_id": session_id,
                    "summary_type": "conversation",
                    "save_summary": True
                })
                
                if result.get("success"):
                    state.response = result["result"]["message"]
                else:
                    state.response = f"❌ Error generando resumen: {result.get('error', 'Error desconocido')}"
                    
            except Exception as e:
                logger.error(f"Error in memory summarize: {e}")
                state.response = f"❌ Error interno generando resumen: {str(e)}"
        
        else:
            logger.warning(f"Unknown memory command: {action}")
            state.response = f"❌ Comando de memoria no reconocido: {action}"
        
        # Registrar en contexto para debugging
        state.context['memory_command_executed'] = {
            "action": action,
            "success": not state.response.startswith("❌"),
            "timestamp": logger.info.__self__.name if hasattr(logger, 'info') else "unknown"
        }
        
        logger.info(f"🧠 Memory command '{action}' executed")
        return "memory_injection_node"  # Siempre ir a guardar la interacción
        
    except Exception as e:
        logger.error(f"❌ Critical error executing memory command: {e}")
        state.response = f"❌ Error crítico ejecutando comando de memoria: {str(e)}"
        return "memory_injection_node"  # Aún así, intentar guardar