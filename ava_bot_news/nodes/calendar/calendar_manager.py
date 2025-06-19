import os
import json
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# ✅ IMPORTAR OAUTH HELPER
sys.path.append(str(Path(__file__).parent.parent.parent / 'utils'))
try:
    from oauth_helper import get_google_credentials
    OAUTH_HELPER_AVAILABLE = True
    print("✅ OAuth helper disponible para Calendar")
except ImportError:
    OAUTH_HELPER_AVAILABLE = False
    print("⚠️ OAuth helper no disponible para Calendar")

class CalendarManager:
    """Gestor de Google Calendar"""
    
    def __init__(self):
        self.service = self._get_calendar_service()
    
    def _get_calendar_service(self):
        """Obtener servicio de Google Calendar - ACTUALIZADO PARA ENV VARS"""
        
        scopes = ['https://www.googleapis.com/auth/calendar']
        
        # ✅ NUEVO: Intentar oauth_helper primero
        if OAUTH_HELPER_AVAILABLE:
            try:
                creds = get_google_credentials(scopes)
                service = build('calendar', 'v3', credentials=creds)
                logger.info("✅ Calendar API service initialized via oauth_helper (env vars)")
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
            logger.info("✅ Calendar API service initialized via legacy method")
            return service
            
        except Exception as e:
            logger.error(f"❌ Error initializing Calendar service: {e}")
            return None
    
    def create_event(self, summary, start_time, end_time, description=None, attendees=None):
        """Crear evento en Google Calendar"""
        
        if not self.service:
            return {"error": "Calendar service not available"}
        
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'America/New_York'},
            'end': {'dateTime': end_time, 'timeZone': 'America/New_York'},
        }
        
        if description:
            event['description'] = description
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        try:
            event = self.service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f"✅ Event created: {event.get('htmlLink')}")
            return {"success": True, "event_id": event['id'], "link": event.get('htmlLink')}
        except Exception as e:
            logger.error(f"❌ Error creating event: {e}")
            return {"error": str(e)}
    
    def list_events(self, start_date=None, end_date=None, max_results=10):
        """Listar eventos del calendario"""
        try:
            if not start_date:
                start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if not end_date:
                end_date = start_date + timedelta(days=1)
            
            time_min = start_date.isoformat() + 'Z'
            time_max = end_date.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return {
                    "message": f"No hay eventos programados",
                    "events": [],
                    "count": 0
                }
            
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                formatted_events.append({
                    "summary": event.get('summary', 'Sin título'),
                    "start": start,
                    "end": end,
                    "attendees": [attendee.get('email') for attendee in event.get('attendees', [])],
                    "link": event.get('htmlLink')
                })
            
            return {
                "message": f"Encontrados {len(events)} eventos",
                "events": formatted_events,
                "count": len(events)
            }
            
        except Exception as e:
            raise Exception(f"Error listando eventos: {str(e)}")
    
    def check_availability(self, start_time, duration_hours=1):
        """Verificar disponibilidad en un horario específico - SIN PRINTS"""
        try:
            end_time = start_time + timedelta(hours=duration_hours)
            
            # Modo real (Google Calendar) - SIN PRINTS
            time_min = start_time.isoformat() + 'Z'
            time_max = end_time.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                return {
                    "available": True,
                    "message": f"✅ Horario disponible",
                    "conflicts": []
                }
            else:
                conflicts = []
                for event in events:
                    conflicts.append({
                        "summary": event.get('summary', 'Sin título'),
                        "start": event['start'].get('dateTime', event['start'].get('date')),
                        "end": event['end'].get('dateTime', event['end'].get('date'))
                    })
                
                return {
                    "available": False,
                    "message": f"❌ Horario ocupado",
                    "conflicts": conflicts
                }
                
        except Exception as e:
            # Si falla el modo real, fallback a simulación SILENCIOSO
            if not self.simulation_mode:
                self.simulation_mode = True
                return self.check_availability(start_time, duration_hours)
            raise Exception(f"Error verificando disponibilidad: {str(e)}")
    
    def get_events_by_date_range(self, start_date_str, end_date_str):
        """Obtener eventos en un rango de fechas"""
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
            
            return self.list_events(start_date, end_date, max_results=50)
            
        except Exception as e:
            raise Exception(f"Error obteniendo eventos por rango: {str(e)}")