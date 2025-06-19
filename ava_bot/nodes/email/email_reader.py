from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import logging
import base64
from typing import Dict, Any, List
from state import AICompanionState

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailReader:
    NODE_NAME = "email_reader"  # Add this line
    def __init__(self):
        # Carga credenciales automáticamente
        try:
            self.creds = Credentials.from_authorized_user_file(
                os.path.join(os.path.dirname(__file__), '../../token.json'),
                ['https://www.googleapis.com/auth/gmail.readonly']
            )
            self.service = build('gmail', 'v1', credentials=self.creds)
        except Exception as e:
            logger.error(f"Error initializing EmailReader: {e}")
            raise

    def process(self, state: AICompanionState) -> str:
        """
        Procesa el estado y lee los correos según la solicitud del usuario
        """
        logger.info("Processing email reading request...")
        
        try:
            # Determinar qué correos leer basado en los parámetros de búsqueda del contexto o del input
            query = ""
            
            # Si hay parámetros de búsqueda en el contexto, usarlos
            if 'email_search_params' in state.context:
                search_params = state.context.get('email_search_params', {})
                
                # Construir la consulta de búsqueda
                if search_params.get('time_period') == 'today':
                    query += "newer_than:1d "
                elif search_params.get('time_period') == 'yesterday':
                    query += "newer_than:2d older_than:1d "
                elif search_params.get('time_period') == 'this_week':
                    query += "newer_than:7d "
                elif search_params.get('time_period') == 'this_month':
                    query += "newer_than:30d "
                
                if search_params.get('read_status') == 'unread':
                    query += "is:unread "
                elif search_params.get('read_status') == 'read':
                    query += "is:read "
                
                if search_params.get('is_important') == True:
                    query += "is:important "
                
                if search_params.get('has_attachments') == True:
                    query += "has:attachment "
                
                if search_params.get('sender'):
                    query += f"from:{search_params['sender']} "
                
                # Añadir palabras clave
                if search_params.get('keywords'):
                    for keyword in search_params['keywords']:
                        query += f"{keyword} "
                
                # Añadir etiquetas
                if search_params.get('labels'):
                    for label in search_params.get('labels', []):
                        query += f"in:{label} "
                
                limit = search_params.get('limit', 5)
            else:
                # Determinar la consulta basada en el input del usuario
                query = self._parse_email_query(state.input)
                limit = 5
            
            logger.info(f"Using search query: '{query}'")
            
            # Obtener correos según la consulta
            emails = self.get_filtered_emails(query=query, max_results=limit)
            
            if not emails:
                state.response = "No se encontraron correos que coincidan con tu solicitud."
                return None
                
            # Formatear los correos para presentarlos al usuario
            email_summary = self._format_email_summary(emails)
            state.response = f"Aquí están los correos solicitados:\n\n{email_summary}"
            
            # Guardar los IDs de los correos en el contexto para posibles acciones futuras
            state.context['email_ids'] = [email['id'] for email in emails]
            
            # Limpiar la tarea de lectura
            state.clear_active_task()
            
            return None
            
        except Exception as e:
            logger.error(f"Error in email_reader process: {e}")
            state.response = "Lo siento, hubo un error al leer tus correos."
            state.clear_active_task()
            return None

    def _parse_email_query(self, user_input: str) -> str:
        """
        Analiza la entrada del usuario para determinar los filtros de búsqueda
        """
        query = ""
        
        # Búsqueda básica por palabras clave en el input
        keywords = ["importante", "urgente", "no leído", "unread", 
                    "hoy", "ayer", "esta semana", "this week"]
                    
        if any(keyword in user_input.lower() for keyword in ["no leído", "unread"]):
            query += "is:unread "
            
        if "importante" in user_input.lower() or "urgente" in user_input.lower():
            query += "is:important "
            
        if "hoy" in user_input.lower():
            query += "newer_than:1d "
            
        if "ayer" in user_input.lower():
            query += "newer_than:2d older_than:1d "
            
        if any(keyword in user_input.lower() for keyword in ["esta semana", "this week"]):
            query += "newer_than:7d "
        
        # Buscar remitentes específicos
        if "de " in user_input.lower() or "from " in user_input.lower():
            parts = user_input.lower().replace("de ", "from ").split("from ")
            if len(parts) > 1:
                sender = parts[1].split()[0]  # Tomar la primera palabra después de "from"
                query += f"from:{sender} "
        
        return query.strip()

    def get_recent_emails(self, max_results=10):
        """Obtiene los últimos correos sin filtros"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                labelIds=['INBOX']
            ).execute()
            
            emails = []
            if 'messages' in results:
                for msg in results['messages']:
                    email = self._get_email_details(msg['id'])
                    emails.append(email)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error getting recent emails: {e}")
            return []

    def get_filtered_emails(self, query="", max_results=10):
        """Obtiene correos filtrados según query"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            emails = []
            if 'messages' in results:
                for msg in results['messages']:
                    email = self._get_email_details(msg['id'])
                    emails.append(email)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error getting filtered emails: {e}")
            return []

    def _get_email_details(self, msg_id):
        """Obtiene los detalles de un correo específico"""
        msg = self.service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()
        
        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sin asunto')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Fecha desconocida')
        
        # Obtener el cuerpo del mensaje (simplificado)
        body = ""
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode()
                    break
        elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
            body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode()
        
        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'snippet': msg.get('snippet', ''),
            'body': body[:500] + ('...' if len(body) > 500 else '')  # Limitar longitud
        }

    def _format_email_summary(self, emails):
        """Formatea una lista de correos para presentarlos al usuario"""
        result = ""
        for i, email in enumerate(emails, 1):
            result += f"{i}. De: {email['sender']}\n"
            result += f"   Asunto: {email['subject']}\n"
            result += f"   Fecha: {email['date']}\n"
            result += f"   Resumen: {email['snippet']}\n\n"
        
        return result

# Crear una instancia global del nodo
email_reader = EmailReader()