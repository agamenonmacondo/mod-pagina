import os
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

# ✅ IMPORTAR OAUTH HELPER
sys.path.append(str(Path(__file__).parent.parent.parent / 'utils'))
try:
    from oauth_helper import get_google_credentials
    OAUTH_HELPER_AVAILABLE = True
    print("✅ OAuth helper disponible para Meet")
except ImportError:
    OAUTH_HELPER_AVAILABLE = False
    print("⚠️ OAuth helper no disponible para Meet")

class MeetManager:
    """Gestor de Google Meet"""
    
    def __init__(self):
        self.service = self._get_calendar_service()  # Meet usa Calendar API
    
    def _get_calendar_service(self):
        """Obtener servicio de Calendar para crear meets - ACTUALIZADO PARA ENV VARS"""
        
        scopes = ['https://www.googleapis.com/auth/calendar']
        
        # ✅ NUEVO: Intentar oauth_helper primero  
        if OAUTH_HELPER_AVAILABLE:
            try:
                creds = get_google_credentials(scopes)
                service = build('calendar', 'v3', credentials=creds)
                logger.info("✅ Meet (Calendar) API service initialized via oauth_helper (env vars)")
                return service
            except Exception as e:
                logger.warning(f"⚠️ Error with oauth_helper, falling back to legacy: {e}")
        
        # ✅ FALLBACK: Método legacy con archivos
        token_path = Path(__file__).parent.parent.parent / 'token.json'
        
        if not token_path.exists():
            logger.error(f"❌ No credentials available. Configure environment variables or provide {token_path}")
            return None
        
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), scopes)
            
            # Refrescar si es necesario
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            
            service = build('calendar', 'v3', credentials=creds)
            logger.info("✅ Meet (Calendar) API service initialized via legacy method")
            return service
            
        except Exception as e:
            logger.error(f"❌ Error initializing Meet service: {e}")
            return None
    
    def create_meeting(self, summary, start_time, end_time, attendees=None):
        """Crear reunión de Google Meet"""
        
        if not self.service:
            return {"error": "Meet service not available"}
        
        # Crear evento con Google Meet
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'America/New_York'},
            'end': {'dateTime': end_time, 'timeZone': 'America/New_York'},
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet-{int(time.time())}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        try:
            event = self.service.events().insert(
                calendarId='primary', 
                body=event,
                conferenceDataVersion=1
            ).execute()
            
            meet_link = event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', '')
            
            logger.info(f"✅ Meet created: {meet_link}")
            return {
                "success": True, 
                "event_id": event['id'], 
                "meet_link": meet_link,
                "calendar_link": event.get('htmlLink')
            }
        except Exception as e:
            logger.error(f"❌ Error creating meet: {e}")
            return {"error": str(e)}