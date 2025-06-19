import os
import json
import logging
import requests
from dotenv import load_dotenv
from state import AICompanionState # Asegúrate que AICompanionState esté disponible
from nodes.system_promt.system_promt import SystemPrompt # Changed to absolute import
from router_node import RouterNode # This should be fine as router_node.py is separate

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cargar variables de entorno para la API de Groq
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL_FOR_ENTITY_EXTRACTION", "llama3-8b-8192") # O un modelo adecuado para extracción

class EntityExtractionNode:
    ENTITY_EXTRACTION_NODE_NAME = "entity_extraction_node" # Added NODE_NAME

    def __init__(self):
        self.llm_api_url = "https://api.groq.com/openai/v1/chat/completions"
        if not GROQ_API_KEY:
            logger.error("GROQ_API_KEY no encontrada en las variables de entorno.")
            raise ValueError("GROQ_API_KEY no configurada.")
        logger.info(f"EntityExtractionNode inicializado con modelo: {GROQ_MODEL}")

    def process(self, state: AICompanionState) -> str:
        logger.info("Procesando en EntityExtractionNode...")

        # Combinar la entrada actual con el historial de conversación para dar más contexto
        # Podrías limitar el historial para no exceder el límite de tokens del LLM
        conversation_history_text = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in state.conversation_history[-5:]] # Últimos 5 mensajes
        )
        
        # Texto de entrada para el LLM
        # input_text = f"Historial de conversación:\n{conversation_history_text}\n\nEntrada actual del usuario:\n{state.input}"
        # Simplificado para probar, idealmente se usa más contexto:
        input_text = state.input
        
        if not input_text.strip():
            logger.info("Entrada vacía, no se extraen entidades.")
            # No es necesario modificar state.context si no hay nada que extraer
            return "router_node" # O el siguiente nodo según tu grafo

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SystemPrompt.ENTITY_EXTRACTION_NODE},
                {"role": "user", "content": input_text}
            ],
            "temperature": 0.1, # Baja temperatura para respuestas más deterministas/precisas
            "max_tokens": 1024, # Ajustar según necesidad
            "response_format": {"type": "json_object"} # Solicitar respuesta en formato JSON
        }

        try:
            response = requests.post(self.llm_api_url, headers=headers, json=payload)
            response.raise_for_status()  # Lanza una excepción para errores HTTP (4xx o 5xx)
            
            # La respuesta del LLM debería ser un string JSON
            extracted_entities_json_str = response.json().get('choices', [{}])[0].get('message', {}).get('content', '{}')
            logger.info(f"Respuesta JSON cruda del LLM para extracción: {extracted_entities_json_str}")

            extracted_entities = json.loads(extracted_entities_json_str) # Convertir string JSON a diccionario Python
            
            if not isinstance(extracted_entities, dict):
                logger.warning(f"Las entidades extraídas no son un diccionario: {extracted_entities}. Se usará un diccionario vacío.")
                extracted_entities = {}

            logger.info(f"Entidades extraídas: {extracted_entities}")

            # Actualizar state.context con las nuevas entidades.
            # Se podría fusionar con el contexto existente o reemplazar claves específicas.
            # Por ahora, simplemente actualizamos/añadimos las nuevas.
            if state.context is None:
                state.context = {}
            
            for key, value in extracted_entities.items():
                if value: # Solo añadir si el valor no está vacío (ej. lista vacía, string vacío)
                    state.context[key] = value
            
            logger.info(f"state.context actualizado: {state.context}")

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"Error HTTP durante la extracción de entidades: {http_err} - {response.text}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Error de Request durante la extracción de entidades: {req_err}")
        except json.JSONDecodeError as json_err:
            logger.error(f"Error al decodificar JSON de entidades extraídas: {json_err}. Respuesta recibida: {extracted_entities_json_str}")
        except Exception as e:
            logger.error(f"Error inesperado en EntityExtractionNode: {e}")
            # En caso de error, es mejor no modificar el contexto o limpiarlo selectivamente.

        # Decidir el siguiente nodo
        # Updated logic: if active_task is awaiting details, go to resume_active_task_router, else router_node
        if state.active_task and state.task_status and state.task_status.get("step") == "awaiting_details":
            logger.info(f"Active task ({state.active_task}) is awaiting details. Routing to resume_active_task_router.")
            # Use the string literal for the node name to avoid circular import
            next_node_name = "resume_active_task_router"
        else:
            logger.info(f"No active task awaiting details or new task. Routing to {RouterNode.ROUTER_NODE_NAME}.")
            next_node_name = RouterNode.ROUTER_NODE_NAME
        
        state.current_node = next_node_name
        return next_node_name

# Para pruebas directas del nodo (opcional)
if __name__ == '__main__':
    # Crear un estado de prueba
    test_state = AICompanionState(
        input="Agenda una reunión con juan@example.com para mañana a las 3 PM sobre el proyecto Alpha.",
        conversation_history=[
            {"role": "user", "content": "Hola Ava"},
            {"role": "assistant", "content": "Hola, ¿cómo puedo ayudarte hoy?"},
            {"role": "user", "content": "Necesito organizar mi agenda."}
        ],
        current_node="entity_extraction_node",
        context={},
        active_task=None,
        task_status={}
    )

    # Instanciar y procesar
    entity_node = EntityExtractionNode()
    next_node = entity_node.process(test_state)

    print(f"\nSiguiente nodo decidido: {next_node}")
    print(f"Contexto final del estado: {test_state.context}")

    # Prueba con otra entrada
    test_state_2 = AICompanionState(
        input="Envíale un correo a marketing@example.com y a ventas@example.com, asunto: Nuevo Reporte, cuerpo: Adjunto el nuevo reporte.",
        conversation_history=[], current_node="entity_extraction_node", context={}
    )
    next_node_2 = entity_node.process(test_state_2)
    print(f"\nSiguiente nodo 2: {next_node_2}")
    print(f"Contexto final 2: {test_state_2.context}")

    test_state_3 = AICompanionState(
        input="Solo quería saludar.",
        conversation_history=[], current_node="entity_extraction_node", context={}
    )
    next_node_3 = entity_node.process(test_state_3)
    print(f"\nSiguiente nodo 3: {next_node_3}")
    print(f"Contexto final 3: {test_state_3.context}")
