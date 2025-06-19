import os
import json
import logging
import time
from state import AICompanionState

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MemoryInjectionNode:
    def __init__(self):
        """Inicializa el nodo de inyección de memoria."""
        self.memory_store = {}  # Almacenamiento en memoria
        self.memory_path = os.path.join(os.path.dirname(__file__), '../../../output/memory')
        
        # Crear directorio de memoria si no existe
        os.makedirs(self.memory_path, exist_ok=True)
        
        # Cargar memoria existente
        self.load_memory()
        
    def load_memory(self):
        """Carga la memoria persistente desde el disco"""
        try:
            memory_file = os.path.join(self.memory_path, 'long_term_memory.json')
            if os.path.exists(memory_file):
                with open(memory_file, 'r', encoding='utf-8') as f:
                    self.memory_store = json.load(f)
                logger.info(f"Memoria cargada con {len(self.memory_store)} elementos")
        except Exception as e:
            logger.error(f"Error al cargar memoria: {e}")
            self.memory_store = {}
            
    def save_memory(self):
        """Guarda la memoria en disco"""
        try:
            memory_file = os.path.join(self.memory_path, 'long_term_memory.json')
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory_store, f, ensure_ascii=False, indent=2)
            logger.info(f"Memoria guardada con {len(self.memory_store)} elementos")
        except Exception as e:
            logger.error(f"Error al guardar memoria: {e}")

    def process(self, state: AICompanionState) -> str:
        """
        Guarda información relevante de la conversación en la memoria a largo plazo.
        
        Args:
            state: Estado actual del flujo de trabajo.
            
        Returns:
            String con el nombre del siguiente nodo a procesar
        """
        try:
            logger.info("Procesando en MemoryInjectionNode...")
            
            # Si hay una tarea activa, guardamos información sobre ella
            if state.active_task:
                task_key = f"task_{state.active_task}_{int(time.time())}"
                self.memory_store[task_key] = {
                    "task_type": state.active_task,
                    "status": state.task_status,
                    "last_input": state.input,
                    "response": state.response
                }
                logger.info(f"Guardada información de tarea: {state.active_task}")
            
            # Guardamos las últimas N interacciones para contexto
            if state.conversation_history and len(state.conversation_history) >= 2:
                # Tomamos los últimos 2 mensajes (usuario y asistente)
                last_messages = state.conversation_history[-2:]
                
                # Crear una clave basada en la entrada del usuario
                user_input = next((msg["content"] for msg in last_messages if msg["role"] == "user"), "")
                if user_input:
                    # Limitamos la longitud de la clave
                    memory_key = f"conv_{user_input[:50]}_{int(time.time())}"
                    self.memory_store[memory_key] = {
                        "conversation": last_messages,
                        "timestamp": time.time()
                    }
                    logger.info(f"Guardada conversación con clave: {memory_key}")
            
            # Guardar memoria persistente
            self.save_memory()
            
            # Una vez guardado, podemos reiniciar el estado si la tarea ha finalizado
            if state.active_task and state.context.get("task_completed", False):
                logger.info(f"Tarea {state.active_task} completada, limpiando estado")
                state.clear_active_task()
                state.context["task_completed"] = False
            
            # Si hay más nodos en el flujo, podemos continuar, de lo contrario terminamos
            return None  # None indica fin del flujo
            
        except Exception as e:
            logger.error(f"Error en inyección de memoria: {str(e)}")
            return None

# Instancia global del nodo (para usar en graph.py)
memory_injection_node = MemoryInjectionNode()
