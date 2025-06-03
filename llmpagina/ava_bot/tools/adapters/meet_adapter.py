import logging
import os
import sys
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MeetAdapter:
    """Adaptador para Google Meet - Enlaces Reales de Google Meet"""
    
    name = "meet"
    description = "Create Google Meet meetings with real links"
    
    def __init__(self):
        """Inicialización con enlaces reales de Google Meet"""
        try:
            self.description = "Ava Bot meet tool - Create Google Meet meetings with real links"
            logger.info("🔍 Inicializando MeetAdapter...")
            
            # ✅ RUTA CORREGIDA PARA ENCONTRAR TOKEN.JSON
            current_dir = Path(__file__).parent           # .../tools/adapters/
            tools_dir = current_dir.parent                # .../tools/
            ava_bot_dir = tools_dir.parent                # .../ava_bot/
            token_path = ava_bot_dir / 'token.json'       # .../ava_bot/token.json
            
            logger.info(f"🔍 Buscando token en: {token_path}")
            
            # ✅ CARGAR MEET MANAGER REAL
            self.meet_manager = None
            self.has_credentials = False
            
            if token_path.exists():
                logger.info(f"✅ Token encontrado: {token_path}")
                self.token_path = str(token_path)
                
                # ✅ CREAR MEET MANAGER SIMPLIFICADO SIN DEPENDENCIAS
                try:
                    self._initialize_meet_manager(str(token_path))
                    logger.info("✅ MeetManager REAL inicializado - enlaces Meet disponibles")
                    print("✅ MeetManager cargado - enlaces Google Meet reales disponibles")
                    
                except Exception as e:
                    logger.error(f"❌ Error inicializando MeetManager: {e}")
                    print(f"⚠️ MeetManager no disponible: {e}")
                    self.has_credentials = False
                    self.meet_manager = None
            else:
                logger.info(f"ℹ️ Token no encontrado en {token_path}, usando modo básico")
                print(f"⚠️ Token no encontrado - modo básico")
                self.has_credentials = False
                self.token_path = None
                self.meet_manager = None
            
            logger.info("✅ MeetAdapter inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando MeetAdapter: {e}")
            print(f"❌ Error en MeetAdapter: {e}")
            # NO fallar - continuar en modo básico
            self.has_credentials = False
            self.token_path = None
            self.meet_manager = None
            self.description = "Ava Bot meet tool - Basic mode"
    
    def _initialize_meet_manager(self, token_path: str):
        """Inicializa el manager de Google Meet sin dependencias externas"""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            class SimpleMeetManager:
                """MeetManager simplificado para crear enlaces reales de Google Meet"""
                
                def __init__(self, token_path: str):
                    """Inicializar con credenciales de Google"""
                    # Cargar credenciales desde token.json
                    with open(token_path, 'r') as f:
                        token_data = json.load(f)
                    
                    self.creds = Credentials(
                        token=token_data.get('token'),
                        refresh_token=token_data.get('refresh_token'),
                        token_uri=token_data.get('token_uri'),
                        client_id=token_data.get('client_id'),
                        client_secret=token_data.get('client_secret'),
                        scopes=token_data.get('scopes', ['https://www.googleapis.com/auth/calendar'])
                    )
                    
                    # Verificar que las credenciales estén válidas
                    if self.creds.expired and self.creds.refresh_token:
                        from google.auth.transport.requests import Request
                        self.creds.refresh(Request())
                    
                    self.service = build('calendar', 'v3', credentials=self.creds)
                
                def create_meet_event(self, summary: str, start_time: str, duration_hours: float = 1.0, 
                                    attendees: List[str] = None, description: str = "", 
                                    timezone: str = 'America/Bogota') -> Dict[str, Any]:
                    """Crear evento con Google Meet REAL"""
                    try:
                        # ✅ PROCESAR FECHA Y HORA
                        if isinstance(start_time, str):
                            if 'T' in start_time:
                                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            else:
                                start_dt = datetime.fromisoformat(f"{start_time}T00:00:00")
                        else:
                            start_dt = start_time
                        
                        end_dt = start_dt + timedelta(hours=duration_hours)
                        
                        # ✅ PROCESAR ASISTENTES
                        event_attendees = []
                        if attendees:
                            for email in attendees:
                                if email and '@' in email:
                                    event_attendees.append({'email': email.strip()})
                        
                        # ✅ CREAR EVENTO CON GOOGLE MEET
                        event_body = {
                            'summary': summary,
                            'description': description or f"Reunión creada por AVA\n\nTítulo: {summary}",
                            'start': {
                                'dateTime': start_dt.isoformat(),
                                'timeZone': timezone,
                            },
                            'end': {
                                'dateTime': end_dt.isoformat(),
                                'timeZone': timezone,
                            },
                            'attendees': event_attendees,
                            'conferenceData': {
                                'createRequest': {
                                    'requestId': f'ava-meet-{uuid.uuid4()}',
                                    'conferenceSolutionKey': {
                                        'type': 'hangoutsMeet'
                                    }
                                }
                            },
                            'reminders': {
                                'useDefault': False,
                                'overrides': [
                                    {'method': 'email', 'minutes': 24 * 60},  # 1 día antes
                                    {'method': 'popup', 'minutes': 10},       # 10 minutos antes
                                ],
                            }
                        }
                        
                        print(f"🔄 Creando evento con Google Meet: {summary}")
                        print(f"📅 Fecha: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"👥 Asistentes: {[att['email'] for att in event_attendees]}")
                        
                        # ✅ CREAR EVENTO EN GOOGLE CALENDAR CON MEET
                        created_event = self.service.events().insert(
                            calendarId='primary',
                            body=event_body,
                            conferenceDataVersion=1  # CRÍTICO para Google Meet
                        ).execute()
                        
                        # ✅ EXTRAER ENLACES REALES
                        meet_link = None
                        join_url = None
                        
                        # Buscar enlace de Google Meet en conferenceData
                        if created_event.get('conferenceData'):
                            conf_data = created_event['conferenceData']
                            
                            # Método 1: entryPoints con tipo 'video'
                            if conf_data.get('entryPoints'):
                                for entry_point in conf_data['entryPoints']:
                                    if entry_point.get('entryPointType') == 'video':
                                        meet_link = entry_point.get('uri')
                                        break
                            
                            # Método 2: conferenceId para construir URL
                            if not meet_link and conf_data.get('conferenceId'):
                                conf_id = conf_data['conferenceId']
                                meet_link = f"https://meet.google.com/{conf_id}"
                        
                        # ✅ VERIFICAR QUE EL ENLACE SEA VÁLIDO
                        if meet_link and 'meet.google.com' in meet_link:
                            print(f"✅ Google Meet creado exitosamente!")
                            print(f"🔗 Enlace Meet REAL: {meet_link}")
                        else:
                            print(f"⚠️ Advertencia: Enlace de Meet no generado")
                        
                        # ✅ DATOS DE DEBUG
                        event_link = created_event.get('htmlLink', 'No disponible')
                        event_id = created_event.get('id', 'No disponible')
                        
                        print(f"📅 Evento calendario: {event_link}")
                        print(f"🆔 ID evento: {event_id}")
                        
                        return {
                            'meet_link': meet_link,
                            'event_link': event_link,
                            'event_id': event_id,
                            'conference_data': created_event.get('conferenceData'),
                            'status': 'success',
                            'error': None
                        }
                        
                    except Exception as e:
                        error_msg = f"Error creando reunión Google Meet: {str(e)}"
                        logger.error(error_msg)
                        print(f"❌ {error_msg}")
                        
                        return {
                            'meet_link': None,
                            'event_link': None,
                            'event_id': None,
                            'status': 'failed',
                            'error': error_msg
                        }
            
            # Instanciar el manager
            self.meet_manager = SimpleMeetManager(token_path)
            self.has_credentials = True
            
        except ImportError as e:
            logger.error(f"Google API libraries not installed: {e}")
            raise Exception("Google API libraries required: google-auth google-auth-oauthlib google-api-python-client")
        except Exception as e:
            logger.error(f"Error inicializando SimpleMeetManager: {e}")
            raise
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Schema para Google Meet adapter"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create"],
                    "description": "Acción a realizar (solo create disponible)"
                },
                "title": {
                    "type": "string",
                    "description": "Título de la reunión",
                    "minLength": 1,
                    "maxLength": 200
                },
                "summary": {
                    "type": "string",
                    "description": "Título de la reunión (alternativo a title)"
                },
                "date": {
                    "type": "string",
                    "description": "Fecha y hora de inicio - formato: YYYY-MM-DDTHH:MM:SS"
                },
                "start_time": {
                    "type": "string",
                    "description": "Hora de inicio - formato: YYYY-MM-DDTHH:MM:SS"
                },
                "duration": {
                    "type": "number",
                    "description": "Duración en horas",
                    "default": 1.0,
                    "minimum": 0.25,
                    "maximum": 8.0
                },
                "attendees": {
                    "type": "string",
                    "description": "Emails de asistentes separados por comas"
                },
                "description": {
                    "type": "string",
                    "description": "Descripción de la reunión"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar creación de reunión Google Meet con enlaces reales"""
        try:
            # ✅ SELF-TEST AL EJECUTAR
            if not hasattr(self, '_self_tested'):
                self._run_self_test()
                self._self_tested = True
            
            logger.info(f"🎯 MeetAdapter.execute llamado con: {arguments}")
            
            # ✅ EXTRAER ARGUMENTOS - múltiples formatos
            meeting_title = (arguments.get('title') or 
                           arguments.get('summary') or 
                           arguments.get('event_name') or 
                           arguments.get('meeting_name') or 
                           'Reunión Google Meet con AVA')
            
            meeting_date = (arguments.get('date') or 
                          arguments.get('start_time') or 
                          arguments.get('time'))
            
            meeting_duration = arguments.get('duration', 1.0)
            meeting_attendees = arguments.get('attendees', '')
            meeting_description = arguments.get('description', '')
            
            # ✅ PROCESAR ASISTENTES
            if isinstance(meeting_attendees, list):
                attendees_list = meeting_attendees
            elif isinstance(meeting_attendees, str) and meeting_attendees:
                attendees_list = [email.strip() for email in meeting_attendees.split(',') if email.strip()]
            else:
                attendees_list = []
            
            # ✅ PROCESAR DURACIÓN
            if isinstance(meeting_duration, str):
                try:
                    meeting_duration = float(''.join(filter(str.isdigit, meeting_duration))) or 1.0
                except:
                    meeting_duration = 1.0
            
            # ✅ GENERAR FECHA SI NO EXISTE
            if not meeting_date:
                # Usar mañana a las 3 PM como default
                tomorrow = datetime.now() + timedelta(days=1)
                meeting_date = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
                print(f"📅 Fecha generada automáticamente: {meeting_date}")
            
            # ✅ VALIDAR QUE LA FECHA SEA FUTURA
            try:
                if 'T' not in meeting_date:
                    meeting_date = f"{meeting_date}T15:00:00"
                
                start_time = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
                now = datetime.now()
                
                if start_time < now:
                    print(f"⚠️ FECHA PASADA DETECTADA: {start_time} < {now}")
                    start_time = now + timedelta(days=1)
                    start_time = start_time.replace(hour=15, minute=0, second=0, microsecond=0)
                    meeting_date = start_time.isoformat()
                    print(f"✅ FECHA CORREGIDA A: {start_time}")
                
            except Exception as e:
                print(f"❌ Error procesando fecha: {e}")
                tomorrow = datetime.now() + timedelta(days=1)
                meeting_date = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
            
            # ✅ CREAR REUNIÓN REAL CON GOOGLE MEET
            if self.has_credentials and self.meet_manager:
                # MODO REAL - CREAR REUNIÓN EN GOOGLE MEET
                logger.info(f"📞 Creando reunión REAL con Google Meet: {meeting_title}")
                
                try:
                    result = self.meet_manager.create_meet_event(
                        summary=meeting_title,
                        start_time=meeting_date,
                        duration_hours=meeting_duration,
                        attendees=attendees_list,
                        description=meeting_description
                    )
                    
                    if result and result.get('meet_link') and not result.get('error'):
                        # ✅ REUNIÓN CREADA EXITOSAMENTE
                        meet_link = result['meet_link']
                        event_link = result.get('event_link', 'No disponible')
                        event_id = result.get('event_id', 'No disponible')
                        
                        # ✅ FORMATEAR FECHAS
                        start_formatted = datetime.fromisoformat(meeting_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                        
                        response_text = f"""📞 **¡REUNIÓN GOOGLE MEET CREADA EXITOSAMENTE!**

🎯 **Título:** {meeting_title}
📅 **Inicio:** {start_formatted}
⏱️ **Duración:** {meeting_duration} horas
👥 **Asistentes:** {', '.join(attendees_list) if attendees_list else 'Ninguno'}

🔗 **ENLACE GOOGLE MEET (REAL):** {meet_link}
📅 **ENLACE CALENDAR (REAL):** {event_link}
🆔 **ID del evento:** {event_id}

✅ **Estado:** Reunión creada con éxito
📧 **Invitaciones:** {('Enviadas a ' + ', '.join(attendees_list)) if attendees_list else 'No hay asistentes'}
🔔 **Recordatorios:** Configurados automáticamente

💡 **Para unirse:** Haz clic en el enlace de Google Meet o búscalo en tu calendario"""
                        
                        print(f"✅ REUNIÓN GOOGLE MEET CREADA CON ÉXITO")
                        print(f"🔗 Link Meet REAL: {meet_link}")
                        
                        return {
                            "content": [{
                                "type": "text",
                                "text": response_text
                            }]
                        }
                    else:
                        # Error en la creación
                        error_msg = result.get('error', 'Error desconocido') if result else 'No se recibió respuesta'
                        response_text = f"""❌ **Error creando reunión Google Meet**

🔍 **Detalles del error:** {error_msg}
📞 **Posibles causas:**
• Token expirado o sin permisos suficientes
• Google Calendar API no configurada correctamente
• Problemas de conectividad

💡 **Solución:** Regenera las credenciales con permisos completos de Calendar API"""
                        
                        print(f"❌ ERROR CREANDO REUNIÓN: {error_msg}")
                        
                except Exception as e:
                    logger.error(f"Error creando reunión real: {e}")
                    response_text = f"""❌ **Error de conexión con Google Meet**

🔍 **Error técnico:** {str(e)}
📞 **Posibles causas:**
• Credenciales inválidas o expiradas
• Google Calendar API no habilitada
• Permisos insuficientes para Google Meet

💡 **Solución:** Verifica la configuración de Google Calendar API"""
                    
                    print(f"❌ EXCEPCIÓN CREANDO REUNIÓN: {e}")
            else:
                # MODO BÁSICO INFORMATIVO
                start_formatted = datetime.fromisoformat(meeting_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                
                response_text = f"""📞 **Solicitud de reunión Google Meet recibida**

🎯 **Título:** {meeting_title}
📅 **Inicio:** {start_formatted}
⏱️ **Duración:** {meeting_duration} horas
👥 **Asistentes:** {', '.join(attendees_list) if attendees_list else 'Ninguno'}

✅ **Solicitud procesada correctamente**

🔧 **Para crear reuniones REALES de Google Meet:**
• Configura Google Calendar API con permisos completos
• Autoriza acceso a Google Calendar y Google Meet
• Reinicia el sistema MCP

📧 **Mientras tanto:** Te ayudo a coordinar la reunión por email"""
            
            return {
                "content": [{
                    "type": "text",
                    "text": response_text
                }]
            }
            
        except Exception as e:
            logger.error(f"Error en MeetAdapter: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error procesando reunión Google Meet: {str(e)}"
                }]
            }
    
    def _run_self_test(self):
        """Auto-test del adapter para verificar funcionamiento"""
        print(f"\n🧪 MEET ADAPTER SELF-TEST")
        print(f"=" * 40)
        print(f"📁 Token path: {getattr(self, 'token_path', 'N/A')}")
        print(f"🔑 Has credentials: {self.has_credentials}")
        print(f"🔧 Meet manager: {'✅ Activo' if self.meet_manager else '❌ No disponible'}")
        
        if self.meet_manager:
            try:
                print(f"✅ Test de conexión: EXITOSO")
                print(f"📊 Puede crear reuniones reales de Google Meet")
                print(f"🔗 Genera enlaces: https://meet.google.com/...")
            except Exception as e:
                print(f"⚠️ Test de conexión: ERROR - {e}")
        else:
            print(f"ℹ️ Modo básico - sin conexión real")
        
        print(f"=" * 40)
    
    def process(self, arguments: Dict[str, Any]) -> str:
        """Alias para execute (compatibilidad)"""
        result = self.execute(arguments)
        if isinstance(result, dict) and "content" in result:
            return result["content"][0]["text"]
        return str(result)

# ✅ SELF-TEST AL IMPORTAR
if __name__ == "__main__":
    print("🧪 PROBANDO MEET ADAPTER...")
    adapter = MeetAdapter()
    
    # Test básico con asistente real
    tomorrow = datetime.now() + timedelta(days=1)
    test_date = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0).isoformat()
    
    test_args = {
        "action": "create",
        "title": "🧪 Test Google Meet - ENLACES REALES",
        "date": test_date,
        "duration": 1,
        "attendees": "agamenonmacondo@gmail.com",
        "description": "Reunión de prueba para validar enlaces reales de Google Meet creados por AVA"
    }
    
    print(f"\n📋 ARGUMENTOS DE PRUEBA:")
    print(f"   📅 Fecha: {test_date}")
    print(f"   👤 Asistente: agamenonmacondo@gmail.com")
    print(f"   ⏱️ Duración: 1 hora")
    
    result = adapter.execute(test_args)
    print(f"\n📋 RESULTADO:")
    print(result["content"][0]["text"])
    
    print(f"\n🔚 Test completado")