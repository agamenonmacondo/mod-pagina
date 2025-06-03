import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import random
import string

class CalendarManager:
    def __init__(self, token_path='token.json'):
        self.token_path = token_path
        self.service = None
        self.simulation_mode = False
        self.simulated_events = []
        self._load_credentials()
    
    def _load_credentials(self):
        """Cargar credenciales desde token.json"""
        try:
            with open(self.token_path, 'r') as token:
                token_data = json.load(token)
            
            creds = Credentials(
                token=token_data['token'],
                refresh_token=token_data['refresh_token'],
                token_uri=token_data['token_uri'],
                client_id=token_data['client_id'],
                client_secret=token_data['client_secret'],
                scopes=token_data['scopes']
            )
            
            self.service = build('calendar', 'v3', credentials=creds)
            
        except Exception as e:
            print(f"Error cargando credenciales: {e}")
            raise
    
    def create_event(self, summary, start_time, end_time, attendees=None, timezone='UTC', description=None):
        """Crear evento SOLO en Google Calendar (SIN Google Meet)"""
        try:
            print(f"🔄 Creando evento de calendario: {summary} para {start_time}")
            
            # ✅ PROCESAR ATTENDEES
            attendees_list = []
            if attendees:
                if isinstance(attendees, str):
                    emails = [email.strip() for email in attendees.split(',') if email.strip()]
                    attendees_list = [{'email': email} for email in emails]
                elif isinstance(attendees, list):
                    attendees_list = [{'email': email} if isinstance(email, str) else email for email in attendees]
            
            # ✅ ESTRUCTURA DEL EVENTO SIN GOOGLE MEET
            event = {
                'summary': summary,
                'description': description or f"Evento programado automáticamente - {summary}",
                'start': {
                    'dateTime': start_time,
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': timezone,
                },
                'attendees': attendees_list,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 día antes
                        {'method': 'popup', 'minutes': 15},        # 15 minutos antes
                    ],
                }
            }
            
            print(f"📅 Creando evento SOLO en calendario")
            print(f"👥 Attendees: {attendees_list}")
            
            # ✅ INSERTAR EVENTO SIN conferenceDataVersion (sin Meet)
            result = self.service.events().insert(
                calendarId='primary',
                body=event,
                sendUpdates='all'  # Enviar invitaciones
            ).execute()
            
            print(f"✅ Evento de calendario creado exitosamente!")
            print(f"📝 ID: {result.get('id')}")
            print(f"🔗 URL Calendar: {result.get('htmlLink')}")
            
            # ✅ RESULTADO SOLO CON DATOS DE CALENDAR
            final_result = {
                'id': result.get('id'),
                'summary': result.get('summary'),
                'start': result.get('start'),
                'end': result.get('end'),
                'htmlLink': result.get('htmlLink'),
                'attendees': result.get('attendees', []),
                'status': result.get('status'),
                'created': result.get('created')
            }
            
            print(f"🎯 Evento de calendario completado:")
            print(f"   📅 Calendar: {final_result['htmlLink']}")
            
            return final_result
            
        except Exception as e:
            print(f"❌ Error creando evento de calendario: {e}")
            raise Exception(f"Error creando evento en Google Calendar: {str(e)}")
    
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
            
            if self.simulation_mode:
                # Verificar conflictos en eventos simulados - SILENCIOSO
                conflicts = []
                for event in self.simulated_events:
                    try:
                        event_start = datetime.fromisoformat(event["start"]["dateTime"])
                        event_end = datetime.fromisoformat(event["end"]["dateTime"])
                        
                        # Verificar solapamiento
                        if (start_time < event_end and end_time > event_start):
                            conflicts.append({
                                "summary": event["summary"],
                                "start": event["start"]["dateTime"],
                                "end": event["end"]["dateTime"]
                            })
                    except Exception:
                        continue
                
                available = len(conflicts) == 0
                
                if available:
                    message = f"✅ Horario disponible"
                else:
                    message = f"❌ Horario ocupado"
                
                return {
                    "available": available,
                    "message": message,
                    "conflicts": conflicts
                }
            
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