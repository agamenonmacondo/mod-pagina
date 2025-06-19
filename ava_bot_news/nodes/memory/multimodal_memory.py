from typing import Dict, Any, Optional, TYPE_CHECKING
import sqlite3
import numpy as np
from PIL import Image
import json
import io
import logging # Added for logging

from ..system_promt.system_promt import SystemPrompt
from ..entity_extraction_node.entity_extraction_node import EntityExtractionNode

if TYPE_CHECKING:
    from state import AICompanionState # Corrected import for type hinting

logger = logging.getLogger(__name__) # Added logger instance

class MultimodalMemory:
    MULTIMODAL_MEMORY_NODE_NAME = "multimodal_memory_node"

    def __init__(self, db_path="memories.db"): # Default to a persistent file
        self.conn = sqlite3.connect(db_path)
        self.db_path = db_path
        self._create_tables()
        # self.current_node = MultimodalMemory.MULTIMODAL_MEMORY_NODE_NAME # Not needed here, state manages current_node

    def _create_tables(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS text_data (
            session_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            PRIMARY KEY (session_id, key)
        )
        """)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS image_data (
            session_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value BLOB,
            PRIMARY KEY (session_id, key)
        )
        """)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS vector_data (
            session_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT,  -- Storing serialized JSON
            PRIMARY KEY (session_id, key)
        )
        """)
        self.conn.commit() # Ensure table creations are committed
        # Eliminar cualquier comentario con # en las consultas SQL (Comment from original, retained)

    # --- Métodos para texto ---
    def store_text(self, session_id: str, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO text_data (session_id, key, value) VALUES (?, ?, ?)",
            (session_id, key, value)
        )
        self.conn.commit()

    def get_text(self, session_id: str, key: str) -> Optional[str]:
        cursor = self.conn.execute("SELECT value FROM text_data WHERE session_id = ? AND key = ?", (session_id, key))
        result = cursor.fetchone()
        return result[0] if result else None

    # --- Métodos para imágenes ---
    def store_image(self, session_id: str, key: str, image: Image.Image):
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        self.conn.execute(
            "INSERT OR REPLACE INTO image_data (session_id, key, value) VALUES (?, ?, ?)",
            (session_id, key, img_byte_arr.getvalue())
        )
        self.conn.commit()

    def get_image(self, session_id: str, key: str) -> Optional[Image.Image]:
        cursor = self.conn.execute("SELECT value FROM image_data WHERE session_id = ? AND key = ?", (session_id, key))
        result = cursor.fetchone()
        if result:
            return Image.open(io.BytesIO(result[0]))
        return None

    # --- Métodos para vectores ---
    def store_vector(self, session_id: str, key: str, vector: np.ndarray):
        serialized = json.dumps(vector.tolist())
        self.conn.execute(
            "INSERT OR REPLACE INTO vector_data (session_id, key, value) VALUES (?, ?, ?)",
            (session_id, key, serialized)
        )
        self.conn.commit()

    def get_vector(self, session_id: str, key: str) -> Optional[np.ndarray]:
        cursor = self.conn.execute("SELECT value FROM vector_data WHERE session_id = ? AND key = ?", (session_id, key))
        result = cursor.fetchone()
        if result:
            return np.array(json.loads(result[0]))
        return None

    def process(self, state: 'AICompanionState') -> str:
        logger.info(f"Processing in {self.MULTIMODAL_MEMORY_NODE_NAME}")
        user_input = state.input
        session_id = state.session_id

        if not session_id:
            logger.error("Error: session_id is missing in MultimodalMemory.process. Cannot perform memory operations.")
            # Proceed to the next node, but memory operations for this turn will be skipped.
            state.current_node = EntityExtractionNode.ENTITY_EXTRACTION_NODE_NAME
            return EntityExtractionNode.ENTITY_EXTRACTION_NODE_NAME

        if user_input:
            # Retrieve current history for the session
            current_history = self.get_text(session_id, "conversation_history") or ""
            
            # Append new user input
            updated_history = f"{current_history}User: {user_input.strip()}\\n" 
            
            # Store updated history for the session
            self.store_text(session_id, "conversation_history", updated_history)
            
            # Ensure context dictionary exists
            if state.context is None:
                state.context = {}
            
            # Make the updated history available in the current state's context
            state.context["conversation_history"] = updated_history
            # Also pass the raw current input if useful for entity extraction directly
            state.context["raw_user_input"] = user_input
            logger.info(f"Stored/updated conversation history for session_id: {session_id}")
        
        # Transition to the entity extraction node
        next_node = EntityExtractionNode.ENTITY_EXTRACTION_NODE_NAME
        state.current_node = next_node
        logger.info(f"Transitioning from {self.MULTIMODAL_MEMORY_NODE_NAME} to {next_node}")
        return next_node