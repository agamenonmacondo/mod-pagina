from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import uuid
import os
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from ...nodes.conversation_node import ConversationNode  # Adjust import path as necessary

if TYPE_CHECKING:
    from ...state import AICompanionState # Assuming state.py is two levels up
# Import the class itself, then access the constant via the class


class MeetManager:
    MEET_MANAGER_NODE_NAME = "meet_manager_node"

    def __init__(self):
        # Ruta correcta: sube 3 niveles hasta la raíz del proyecto
        token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'token.json')
        # Ensure the token path is absolute or correctly relative to the execution context
        if not os.path.exists(token_path):
            # Attempt to construct path from a known base or raise a clearer error
            # This might require knowing the project's root directory structure
            # For now, let's assume it's relative to this file's grandparent's parent
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            token_path = os.path.join(base_dir, 'token.json')
            if not os.path.exists(token_path):
                raise FileNotFoundError(f"Google API token file not found at {token_path} or expected relative path.")

        self.creds = Credentials.from_authorized_user_file(
            token_path,
            ['https://www.googleapis.com/auth/calendar']
        )

    def process(self, state: 'AICompanionState') -> str:
        """Processes the state to create a Google Meet event.
           This is the entry point for the langgraph node.
        """
        # Extract necessary information from state.context
        # These keys are examples; adjust them based on what entity_extraction_node provides
        summary = state.context.get('meet_summary', 'Reunión programada por AVA')
        start_time_str = state.context.get('meet_start_time') # Expecting ISO format string or datetime object
        duration_hours = state.context.get('meet_duration_hours', 1) # Default to 1 hour
        
        # Ensure attendees is a list, defaulting to an empty list if not provided or not a list
        raw_attendees = state.context.get('meet_attendees', [])
        if isinstance(raw_attendees, str):
            attendees = [email.strip() for email in raw_attendees.split(',') if email.strip()]
        elif isinstance(raw_attendees, list):
            attendees = raw_attendees
        else:
            attendees = []
            
        timezone = state.context.get('meet_timezone', 'America/Bogota') # Default to Bogota timezone

        missing_info = []
        if not start_time_str:
            missing_info.append("la hora de inicio de la reunión")
        
        if missing_info:
            state.response = f"Para crear la reunión, necesito saber: {', '.join(missing_info)}. ¿Podrías proporcionármelos?"
            # Optionally set active_task and step if this node should manage re-prompting
            # state.set_active_task("meet_task", step="awaiting_details") 
            state.current_node = ConversationNode.CONVERSATION_NODE_NAME # Use class to access constant
            return ConversationNode.CONVERSATION_NODE_NAME # Use class to access constant

        start_time = None
        if isinstance(start_time_str, str):
            try:
                # Attempt to parse common date/time formats if not strictly ISO
                # This is a simple example; a more robust parser might be needed
                if 'T' in start_time_str:
                    start_time = datetime.fromisoformat(start_time_str)
                else:
                    # Try a common format like "YYYY-MM-DD HH:MM:SS"
                    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                state.response = f"No pude entender la fecha y hora de inicio para la reunión '{start_time_str}'. Por favor, usa un formato como YYYY-MM-DDTHH:MM:SS o YYYY-MM-DD HH:MM:SS."
                state.current_node = ConversationNode.CONVERSATION_NODE_NAME # Use class to access constant
                return ConversationNode.CONVERSATION_NODE_NAME # Use class to access constant
        elif isinstance(start_time_str, datetime):
            start_time = start_time_str
        else:
            state.response = "Formato de hora de inicio no válido para la reunión."
            state.current_node = ConversationNode.CONVERSATION_NODE_NAME # Use class to access constant
            return ConversationNode.CONVERSATION_NODE_NAME # Use class to access constant

        # Call the internal method to create the meet event
        result = self.create_meet_event(
            summary=summary,
            start_time=start_time,
            duration_hours=duration_hours,
            attendees=attendees,
            timezone=timezone
        )

        if result.get('error'):
            state.response = f"Error al crear la reunión de Meet: {result['error']}"
        else:
            state.response = f"Reunión de Meet creada: {result.get('meet_link')}. Detalles del evento: {result.get('event_link')}"
        
        state.current_node = ConversationNode.CONVERSATION_NODE_NAME # Use class to access constant
        return ConversationNode.CONVERSATION_NODE_NAME # Use class to access constant

    def create_meet_event(self, summary: str, start_time: datetime, duration_hours: float, attendees: Optional[List[str]] = None, timezone: str = 'America/Bogota') -> Dict[str, Any]:
        """
        Crea una reunión de Google Meet con invitados.
        
        Args:
            summary: Título de la reunión.
            start_time: Objeto datetime para el inicio.
            duration_hours: Duración en horas.
            attendees: Lista de correos de invitados.
            timezone: Zona horaria (ej: 'America/Mexico_City').
        
        Returns:
            Dict con {'meet_link': str, 'event_link': str, 'error': str or None}
        """
        try:
            service = build('calendar', 'v3', credentials=self.creds)
            end_time = start_time + timedelta(hours=duration_hours)

            event_attendees = [{'email': email} for email in attendees] if attendees else []

            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': timezone,
                },
                'attendees': event_attendees,
                'conferenceData': {
                    'createRequest': {
                        'requestId': f'ava-meet-{uuid.uuid4()}', # Use uuid for better uniqueness
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                }
            }

            created_event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
            
            meet_link = None
            if created_event.get('conferenceData') and created_event['conferenceData'].get('entryPoints'):
                for entry_point in created_event['conferenceData']['entryPoints']:
                    if entry_point.get('entryPointType') == 'video':
                        meet_link = entry_point.get('uri')
                        break
            
            return {
                'meet_link': meet_link,
                'event_link': created_event.get('htmlLink'),
                'error': None
            }
        except Exception as error:
            # Log the full error for debugging if possible
            print(f"Error in create_meet_event: {error}") 
            return {
                'meet_link': None,
                'event_link': None,
                'error': str(error)
            }

# The main function here is for standalone testing, not used by langgraph directly
# To make it runnable standalone, it would need its own way to get credentials
# or be adapted to use the MeetManager instance.
# For now, commenting out to avoid NameError for 'create_meet_event' if run directly
# without proper setup.

# def main():
#     # Ejemplo de uso
#     # This requires 'token.json' in the script's directory or a valid path
#     # For simplicity, assuming MeetManager handles credential loading internally now.
#     manager = MeetManager() # This will attempt to load credentials
    
#     result = manager.create_meet_event(
#         summary="Reunión de estrategia AVA",
#         start_time=datetime.now() + timedelta(hours=1),
#         duration_hours=1.5,
#         attendees=[
#             'alejandro.sevilla@agenteava.com', # Corrected email
#             'agamenonmacondo@gmail.com'
#         ],
#         timezone='America/Bogota' # Example timezone
#     )
    
#     if result['error']:
#         print(f"Error: {result['error']}")
#     else:
#         print(f"Meet creado: {result['meet_link']}")
#         print(f"Evento en Calendar: {result['event_link']}")

# if __name__ == '__main__':
#     main()