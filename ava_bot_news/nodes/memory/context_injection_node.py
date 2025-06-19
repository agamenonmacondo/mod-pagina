import logging
import requests
import os
import json
from typing import Dict, Any
from state import AICompanionState

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ContextInjectionNode:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = "meta-llama/llama-4-maverick-17b-128e-instruct"
        self.llm_api_url = "https://api.groq.com/openai/v1/chat/completions"
        
    def _call_llm_for_context_relevance(self, query, context):
        """Llama al LLM para determinar qué contexto es relevante"""
        if not self.groq_api_key:
            logger.warning("No se encontró GROQ_API_KEY. No se puede evaluar la relevancia del contexto.")
            return []
            
        try:
            system_message = (
                "Como asistente, tu tarea es evaluar la relevancia de fragmentos de memoria para una "
                "consulta actual. Analiza cada fragmento y determina si es útil para responder la consulta. "
                "Devuelve solo los índices (números) de los fragmentos relevantes separados por comas, "
                "por ejemplo: '0,2,5'. Si ninguno es relevante, devuelve 'ninguno'."
            )
            
            # Preparar el contexto para el LLM
            context_formatted = ""
            for i, (key, value) in enumerate(context.items()):
                content = value.get("content", str(value))
                context_formatted += f"[{i}] {key}: {content}\n"
                
            user_message = f"Consulta: {query}\n\nFragmentos de memoria:\n{context_formatted}"
            
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.groq_model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.2,
                "max_tokens": 50
            }
            
            response = requests.post(self.llm_api_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json().get('choices', [{}])[0].get('message', {}).get('content', "ninguno").strip()
            logger.info(f"Resultado de evaluación de relevancia: {result}")
            
            if result.lower() == "ninguno":
                return []
                
            try:
                relevant_indices = [int(idx.strip()) for idx in result.split(',')]
                return relevant_indices
            except Exception:
                logger.error(f"Error al procesar índices relevantes: {result}")
                return []
                
        except Exception as e:
            logger.error(f"Error al llamar al LLM para relevancia: {e}")
            return []

    def process(self, state: AICompanionState) -> str:
        """
        Inyecta contexto relevante al estado del flujo de trabajo.
        
        Args:
            state: Estado actual del flujo de trabajo.
            
        Returns:
            String con el nombre del siguiente nodo a procesar
        """
        try:
            logger.info("Procesando en ContextInjectionNode...")
            
            # Obtener la memoria extraída del estado anterior
            extracted_memory = state.context.get('extracted_memory', {})
            related_memories = state.context.get('related_memories', [])
            
            # Si hay memoria extraída, evaluar su relevancia
            if related_memories:
                # Convertir la memoria extraída a un formato fácil de indexar
                indexed_memories = {i: memory for i, memory in enumerate(related_memories)}
                
                # Evaluar relevancia con el LLM
                relevant_indices = self._call_llm_for_context_relevance(state.input, indexed_memories)
                
                # Filtrar solo las memorias relevantes
                filtered_memories = []
                for idx in relevant_indices:
                    if idx < len(related_memories):
                        filtered_memories.append(related_memories[idx])
                
                # Actualizar el contexto con las memorias filtradas
                state.context['relevant_memories'] = filtered_memories
                
                if filtered_memories:
                    # Crear un resumen de contexto para añadir al input
                    context_summary = "Contexto relevante:\n"
                    for memory in filtered_memories:
                        context_summary += f"- {memory['topic']}: {memory['content']}\n"
                    
                    # Guardar el resumen en el estado para su uso en otros nodos
                    state.context['context_summary'] = context_summary
                    logger.info(f"Contexto añadido con {len(filtered_memories)} memorias relevantes")
            
            # Decidir el siguiente nodo según el estado de tareas activas
            if state.active_task:
                # Si hay una tarea activa, ir al router personalizado
                return "context_to_next_router"
            else:
                # Si no hay tarea activa, ir al router general
                return "router_node"
                
        except Exception as e:
            logger.error(f"Error al inyectar contexto: {e}")
            return "router_node"

# Instancia global para usar en graph.py
context_injection_node = ContextInjectionNode()
