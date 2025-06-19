from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import os
import logging
from typing import Dict, Any, Optional
import json
import requests
from state import AICompanionState

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailResponder:
    def __init__(self):
        try:
            # Carga credenciales automáticamente
            self.creds = Credentials.from_authorized_user_file(
                os.path.join(os.path.dirname(__file__), '../../token.json'),
                ['https://www.googleapis.com/auth/gmail.modify']
            )
            self.service = build('gmail', 'v1', credentials=self.creds)
            self.groq_api_key = os.getenv("GROQ_API_KEY")
            self.groq_model = "meta-llama/llama-4-maverick-17b-128e-instruct"
            self.llm_api_url = "https://api.groq.com/openai/v1/chat/completions"
        except Exception as e:
            logger.error(f"Error initializing EmailResponder: {e}")
            raise

    def process(self, state: AICompanionState) -> str:
        """
        Procesa el estado y maneja respuestas a correos
        """
        logger.info("Processing email response request...")
        
        try:
            # Verificar si ya estamos en el proceso de responder a un correo
            if state.is_in_task("email_responding"):
                return self._continue_email_response(state)
            
            # Si hay IDs de correos en el contexto, preguntar cuál responder
            if 'email_ids' in state.context and state.context['email_ids']:
                if 'selected_email_id' not in state.context:
                    # Verificar si el usuario está seleccionando un correo por número
                    selected_num = None
                    for i in range(1, len(state.context['email_ids']) + 1):
                        if f"{i}" == state.input.strip() or f"número {i}" in state.input.lower() or f"correo {i}" in state.input.lower():
                            selected_num = i
                            break
                    
                    if selected_num:
                        state.context['selected_email_id'] = state.context['email_ids'][selected_num - 1]
                    else:
                        # Si no hay selección clara, preguntar
                        state.response = "¿A cuál de los correos quieres responder? Indica el número."
                        state.set_active_task("email_responding", step="select_email")
                        return None
            
            # Si llegamos aquí sin un correo seleccionado, pedir que primero lea los correos
            if 'selected_email_id' not in state.context:
                state.response = "Primero necesito que veas tus correos. ¿Quieres que te muestre los correos recientes?"
                return "email_reader"  # Redireccionar al lector de correos
            
            # Si tenemos un ID pero no tenemos el contenido de la respuesta, preguntar
            if 'response_content' not in state.context:
                state.response = "¿Qué respuesta quieres enviar?"
                state.set_active_task("email_responding", step="draft_response")
                return None
            
            # Si tenemos todo lo necesario, enviar la respuesta
            success = self.send_reply(
                state.context['selected_email_id'],
                state.context['response_content']
            )
            
            if success:
                state.response = "¡Respuesta enviada exitosamente!"
            else:
                state.response = "Lo siento, hubo un problema al enviar la respuesta."
            
            # Limpiar el contexto y la tarea activa
            state.context.pop('selected_email_id', None)
            state.context.pop('response_content', None)
            state.clear_active_task()
            
            return None
            
        except Exception as e:
            logger.error(f"Error in email_responder process: {e}")
            state.response = "Lo siento, hubo un error al procesar tu solicitud de respuesta."
            state.clear_active_task()
            return None

    def _continue_email_response(self, state: AICompanionState) -> Optional[str]:
        """
        Continúa el proceso de respuesta según el paso actual
        """
        current_step = state.task_status.get("step")
        
        if current_step == "select_email":
            # Procesar selección de correo
            selected_num = None
            for i in range(1, len(state.context['email_ids']) + 1):
                if f"{i}" == state.input.strip() or f"número {i}" in state.input.lower() or f"correo {i}" in state.input.lower():
                    selected_num = i
                    break
            
            if selected_num:
                state.context['selected_email_id'] = state.context['email_ids'][selected_num - 1]
                state.response = "¿Qué respuesta quieres enviar?"
                state.task_status["step"] = "draft_response"
                return None
            else:
                state.response = "No entendí qué correo quieres responder. Por favor indica el número."
                return None
                
        elif current_step == "draft_response":
            # Procesar contenido de la respuesta
            if state.input.strip():
                state.context['response_content'] = state.input.strip()
                
                # Confirmar antes de enviar
                state.response = f"¿Estás seguro de que quieres enviar esta respuesta?\n\n{state.context['response_content']}\n\nResponde 'sí' para confirmar o 'no' para cancelar."
                state.task_status["step"] = "confirm_send"
                return None
            else:
                state.response = "Por favor, indica el contenido de la respuesta."
                return None
                
        elif current_step == "confirm_send":
            # Confirmar y enviar
            if state.input.lower() in ['sí', 'si', 'yes', 'confirmar', 'confirm']:
                success = self.send_reply(
                    state.context['selected_email_id'],
                    state.context['response_content']
                )
                
                if success:
                    state.response = "¡Respuesta enviada exitosamente!"
                else:
                    state.response = "Lo siento, hubo un problema al enviar la respuesta."
                
                # Limpiar el contexto y la tarea activa
                state.context.pop('selected_email_id', None)
                state.context.pop('response_content', None)
                state.clear_active_task()
                return None
                
            elif state.input.lower() in ['no', 'cancelar', 'cancel']:
                state.response = "Envío cancelado. ¿Quieres redactar una nueva respuesta?"
                state.task_status["step"] = "draft_response"
                return None
            
            else:
                state.response = "Por favor responde 'sí' para confirmar o 'no' para cancelar."
                return None
        
        return None

    def send_reply(self, original_email_id: str, response_text: str) -> bool:
        """
        Envía una respuesta a un correo existente
        """
        try:
            # Obtener detalles del correo original
            original = self.service.users().messages().get(
                userId='me',
                id=original_email_id,
                format='metadata',
                metadataHeaders=['Subject', 'From', 'To', 'Message-ID', 'References', 'In-Reply-To']
            ).execute()
            
            # Obtener los headers relevantes
            headers = {item['name']: item['value'] for item in original['payload']['headers']}
            
            # Preparar el mensaje
            message = MIMEText(response_text)
            message['To'] = headers.get('From', '')
            original_subject = headers.get('Subject', '')
            if not original_subject.lower().startswith('re:'):
                message['Subject'] = f"Re: {original_subject}"
            else:
                message['Subject'] = original_subject
                
            # Headers para mantener la conversación enlazada
            if 'Message-ID' in headers:
                message['In-Reply-To'] = headers['Message-ID']
                message['References'] = headers.get('References', '') + ' ' + headers['Message-ID']
            
            # Codificar y enviar
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw, 'threadId': original.get('threadId')}
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            return False
            
# Instancia global
email_responder = EmailResponder()