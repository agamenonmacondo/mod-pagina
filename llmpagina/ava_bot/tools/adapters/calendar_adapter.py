import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ✅ AGREGAR OAUTH_HELPER AL PATH
current_dir = Path(__file__).parent
tools_dir = current_dir.parent
ava_bot_dir = tools_dir.parent
utils_dir = ava_bot_dir / 'utils'

# Agregar ruta de utils
if str(utils_dir) not in sys.path:
    sys.path.insert(0, str(utils_dir))

# ✅ IMPORTAR OAUTH_HELPER
try:
    from oauth_helper import get_google_credentials
    OAUTH_HELPER_AVAILABLE = True
    print("✅ OAuth helper disponible para Calendar")
except ImportError:
    OAUTH_HELPER_AVAILABLE = False
    print("⚠️ OAuth helper no disponible para Calendar")

class CalendarAdapter:
    """Adaptador para crear eventos de Google Calendar con OAuth env vars"""
    
    name = "calendar"
    description = "Create and manage Google Calendar events with OAuth env vars"
    
    def __init__(self):
        """Inicialización con OAuth desde variables de entorno"""
        try:
            self.description = "Ava Bot calendar tool - OAuth env vars support"
            
            # ✅ INTENTAR OAUTH HELPER PRIMERO
            self.calendar_manager = None
            self.has_credentials = False
            
            if OAUTH_HELPER_AVAILABLE:
                try:
                    # Test de credenciales OAuth desde env vars
                    creds = get_google_credentials(['https://www.googleapis.com/auth/calendar'])
                    if creds:
                        # ✅ CREAR CALENDAR MANAGER CON OAUTH HELPER
                        self._initialize_calendar_with_oauth(creds)
                        logger.info("✅ CalendarManager inicializado con OAuth env vars")
                        print("✅ CalendarManager cargado - OAuth desde variables de entorno")
                    else:
                        logger.warning("⚠️ OAuth env vars no disponibles")
                except Exception as e:
                    logger.error(f"❌ Error con OAuth env vars: {e}")
            
            # ✅ FALLBACK: Método legacy con archivos
            if not self.has_credentials:
                logger.info("🔄 Intentando método legacy con archivos...")
                self._initialize_calendar_legacy()
            
            logger.info("✅ CalendarAdapter inicializado")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando CalendarAdapter: {e}")
            self.has_credentials = False
            self.calendar_manager = None
            self.description = "Ava Bot calendar tool - Basic mode"
    
    def _initialize_calendar_with_oauth(self, creds):
        """Inicializar CalendarManager con credenciales OAuth"""
        try:
            from googleapiclient.discovery import build
            
            class OAuthCalendarManager:
                """CalendarManager usando OAuth desde env vars"""
                
                def __init__(self, credentials):
                    self.service = build('calendar', 'v3', credentials=credentials)
                
                def create_event(self, summary, start_time, end_time, attendees=None, description="", timezone='America/Bogota'):
                    """Crear evento en Google Calendar"""
                    
                    # Procesar asistentes
                    event_attendees = []
                    if attendees:
                        if isinstance(attendees, str):
                            for email in attendees.split(','):
                                email = email.strip()
                                if email and '@' in email:
                                    event_attendees.append({'email': email})
                        elif isinstance(attendees, list):
                            for email in attendees:
                                if email and '@' in email:
                                    event_attendees.append({'email': email.strip()})
                    
                    # Crear evento
                    event = {
                        'summary': summary,
                        'description': description,
                        'start': {
                            'dateTime': start_time,
                            'timeZone': timezone,
                        },
                        'end': {
                            'dateTime': end_time,
                            'timeZone': timezone,
                        },
                        'attendees': event_attendees,
                        'reminders': {
                            'useDefault': False,
                            'overrides': [
                                {'method': 'email', 'minutes': 24 * 60},
                                {'method': 'popup', 'minutes': 10},
                            ],
                        },
                    }
                    
                    created_event = self.service.events().insert(calendarId='primary', body=event).execute()
                    
                    return {
                        'id': created_event.get('id'),
                        'htmlLink': created_event.get('htmlLink'),
                        'summary': created_event.get('summary'),
                        'start': created_event.get('start', {}).get('dateTime'),
                        'end': created_event.get('end', {}).get('dateTime'),
                        'attendees': [att.get('email') for att in created_event.get('attendees', [])],
                        'error': None
                    }
                
                def list_events(self, max_results=10):
                    """Listar eventos del calendario"""
                    now = datetime.utcnow().isoformat() + 'Z'
                    
                    events_result = self.service.events().list(
                        calendarId='primary',
                        timeMin=now,
                        maxResults=max_results,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                    
                    processed_events = []
                    for event in events:
                        processed_events.append({
                            'summary': event.get('summary', 'Sin título'),
                            'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                            'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                            'htmlLink': event.get('htmlLink', ''),
                            'attendees': [att.get('email') for att in event.get('attendees', [])]
                        })
                    
                    return {
                        'count': len(processed_events),
                        'events': processed_events
                    }
            
            self.calendar_manager = OAuthCalendarManager(creds)
            self.has_credentials = True
            
        except Exception as e:
            logger.error(f"Error inicializando OAuthCalendarManager: {e}")
            raise
    
    def _initialize_calendar_legacy(self):
        """Método legacy con archivos JSON"""
        token_path = ava_bot_dir / 'token.json'
        
        if token_path.exists():
            try:
                calendar_nodes_path = str(ava_bot_dir / 'nodes' / 'calendar')
                if calendar_nodes_path not in sys.path:
                    sys.path.append(calendar_nodes_path)
                
                from calendar_manager import CalendarManager
                self.calendar_manager = CalendarManager(str(token_path))
                self.has_credentials = True
                logger.info("✅ CalendarManager legacy inicializado")
                
            except Exception as e:
                logger.error(f"❌ Error con método legacy: {e}")
                self.has_credentials = False
        else:
            logger.info("ℹ️ Token no encontrado - modo básico")
            self.has_credentials = False

    @property
    def schema(self) -> Dict[str, Any]:
        """Schema EXACTO para Calendar - SOLO parámetros que funcionan"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "list", "check"],
                    "description": "Acción a realizar"
                },
                "title": {
                    "type": "string",
                    "description": "Título del evento (REQUERIDO para create)",
                    "minLength": 1,
                    "maxLength": 200
                },
                "summary": {
                    "type": "string",
                    "description": "Título del evento (alternativo a title)"
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
                    "type": "integer",
                    "description": "Duración del evento en minutos",
                    "default": 60,
                    "minimum": 15,
                    "maximum": 480
                },
                "attendees": {
                    "type": "string",
                    "description": "Emails de asistentes separados por comas"
                },
                "description": {
                    "type": "string",
                    "description": "Descripción del evento"
                }
            },
            "required": [],
            "additionalProperties": False
        }
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar acción de calendario"""
        try:
            # ✅ SELF-TEST AL EJECUTAR
            if not hasattr(self, '_self_tested'):
                self._run_self_test()
                self._self_tested = True
            
            action = arguments.get('action', 'create')
            
            if action == 'create':
                return self._create_event(arguments)
            elif action == 'list':
                return self._list_events(arguments)
            elif action == 'check':
                return self._check_availability(arguments)
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ Acción no reconocida: {action}. Usa: create, list, check"
                    }]
                }
                
        except Exception as e:
            logger.error(f"Error en CalendarAdapter.execute: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error procesando calendario: {str(e)}"
                }]
            }
    
    def _run_self_test(self):
        """Auto-test actualizado con info de OAuth"""
        print(f"\n🧪 CALENDAR ADAPTER SELF-TEST")
        print(f"=" * 40)
        print(f"🌐 OAuth helper: {'✅ Disponible' if OAUTH_HELPER_AVAILABLE else '❌ No disponible'}")
        print(f"🔑 Has credentials: {self.has_credentials}")
        print(f"🔧 Calendar manager: {'✅ Activo' if self.calendar_manager else '❌ No disponible'}")
        
        if self.calendar_manager and OAUTH_HELPER_AVAILABLE:
            print(f"🎯 Método: OAuth desde variables de entorno")
        elif self.calendar_manager:
            print(f"🎯 Método: Legacy con archivos JSON")
        else:
            print(f"ℹ️ Modo básico - sin conexión real")
        
        print(f"=" * 40)
    
    def _create_event(self, arguments: dict) -> dict:
        """Crear evento de calendario con LINKS REALES de Google Calendar"""
        try:
            # ✅ EXTRAER ARGUMENTOS - múltiples formatos
            event_title = (arguments.get('title') or 
                          arguments.get('summary') or 
                          arguments.get('event_name') or 
                          'Reunión con AVA')
            
            event_date = (arguments.get('date') or 
                         arguments.get('start_time') or 
                         arguments.get('start'))
            
            event_duration = arguments.get('duration', 60)  # minutos
            event_attendees = arguments.get('attendees', '')
            event_description = arguments.get('description', '')
            
            # ✅ GENERAR FECHA SI NO EXISTE
            if not event_date:
                # Usar mañana a las 3 PM como default
                tomorrow = datetime.now() + timedelta(days=1)
                event_date = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
                print(f"📅 Fecha generada automáticamente: {event_date}")
            
            # ✅ PROCESAR DURACIÓN
            if isinstance(event_duration, str):
                if 'hour' in event_duration:
                    # "2 hours" -> 120
                    event_duration = int(''.join(filter(str.isdigit, event_duration))) * 60
                elif 'minuto' in event_duration:
                    # "30 minutos" -> 30
                    event_duration = int(''.join(filter(str.isdigit, event_duration)))
                else:
                    event_duration = 60
            
            # ✅ VALIDAR QUE LA FECHA SEA FUTURA
            try:
                if 'T' not in event_date:
                    # Solo fecha, agregar hora
                    event_date = f"{event_date}T15:00:00"
                
                start_time = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                now = datetime.now()
                
                # Verificar que la fecha sea futura
                if start_time < now:
                    print(f"⚠️ FECHA PASADA DETECTADA: {start_time} < {now}")
                    # Corregir automáticamente
                    start_time = now + timedelta(days=1)
                    start_time = start_time.replace(hour=15, minute=0, second=0, microsecond=0)
                    print(f"✅ FECHA CORREGIDA A: {start_time}")
                
                end_time = start_time + timedelta(minutes=event_duration)
                
                # Convertir a formato ISO string
                start_time_str = start_time.isoformat()
                end_time_str = end_time.isoformat()
                
            except Exception as e:
                print(f"❌ Error procesando fecha: {e}")
                # Usar fecha por defecto
                tomorrow = datetime.now() + timedelta(days=1)
                start_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
                end_time = start_time + timedelta(minutes=event_duration)
                start_time_str = start_time.isoformat()
                end_time_str = end_time.isoformat()
            
            # ✅ CREAR EVENTO REAL CON LINKS REALES
            if self.has_credentials and self.calendar_manager:
                # MODO REAL - CREAR EVENTO EN GOOGLE CALENDAR
                logger.info(f"🗓️ Creando evento REAL: {event_title}")
                
                try:
                    result = self.calendar_manager.create_event(
                        summary=event_title,
                        start_time=start_time_str,
                        end_time=end_time_str,
                        attendees=event_attendees,
                        description=event_description,
                        timezone='America/Bogota'
                    )
                    
                    if result and not result.get('error'):
                        # ✅ USAR LINKS REALES DEVUELTOS POR GOOGLE
                        event_link = result.get('htmlLink', 'No disponible')
                        event_id = result.get('id', 'No disponible')
                        
                        # ✅ DEBUG - MOSTRAR RESULTADO COMPLETO
                        print(f"\n🔍 DEBUG - RESULTADO COMPLETO DE GOOGLE:")
                        print(f"   📋 Claves disponibles: {list(result.keys())}")
                        print(f"   🆔 ID: {event_id}")
                        print(f"   🔗 htmlLink: {event_link}")
                        print(f"   📅 Summary: {result.get('summary', 'N/A')}")
                        
                        # ✅ FORMATEAR FECHAS PARA MOSTRAR
                        start_formatted = start_time.strftime('%Y-%m-%d %H:%M:%S')
                        end_formatted = end_time.strftime('%Y-%m-%d %H:%M:%S')
                        
                        response_text = f"""📅 **¡EVENTO CREADO EXITOSAMENTE EN GOOGLE CALENDAR!**

🎯 **Título:** {event_title}
📅 **Inicio:** {start_formatted}
🏁 **Fin:** {end_formatted}
⏱️ **Duración:** {event_duration} minutos
👥 **Asistentes:** {event_attendees if event_attendees else 'Ninguno'}

🔗 **ENLACE DIRECTO (REAL):** {event_link}
🆔 **ID del evento:** {event_id}

✅ **Estado:** Evento agregado a tu Google Calendar
📧 **Invitaciones:** {('Enviadas a ' + event_attendees) if event_attendees else 'No hay asistentes'}
🔔 **Recordatorios:** Configurados automáticamente

💡 **Para acceder:** Haz clic en el enlace o busca por ID en tu calendario"""
                        
                        print(f"✅ EVENTO REAL CREADO CON ÉXITO")
                        print(f"🔗 Link real: {event_link}")
                        
                    else:
                        # Error en la creación
                        error_msg = result.get('error', 'Error desconocido') if result else 'No se recibió respuesta'
                        response_text = f"""❌ **Error creando evento real**

🔍 **Detalles del error:** {error_msg}
📞 **Solución:** Verifica las credenciales de Google Calendar API

💡 **Alternativas:**
• Revisa los permisos del token
• Verifica la configuración de la API
• Contacta al administrador"""
                        
                        print(f"❌ ERROR CREANDO EVENTO: {error_msg}")
                        
                except Exception as e:
                    logger.error(f"Error creando evento real: {e}")
                    response_text = f"""❌ **Error de conexión con Google Calendar**

🔍 **Error técnico:** {str(e)}
📞 **Posibles causas:**
• Token expirado o inválido
• Problemas de conectividad
• Permisos insuficientes

💡 **Solución:** Regenera las credenciales de Google Calendar"""
                    
                    print(f"❌ EXCEPCIÓN CREANDO EVENTO: {e}")
            else:
                # MODO BÁSICO INFORMATIVO
                start_formatted = start_time.strftime('%Y-%m-%d %H:%M:%S')
                end_formatted = end_time.strftime('%Y-%m-%d %H:%M:%S')
                
                response_text = f"""📅 **Solicitud de evento recibida**

🎯 **Título:** {event_title}
📅 **Inicio:** {start_formatted}
🏁 **Fin:** {end_formatted}
⏱️ **Duración:** {event_duration} minutos
👥 **Asistentes:** {event_attendees if event_attendees else 'Ninguno'}

📞 **Para crear eventos REALES en Google Calendar:**
• Configura Google Calendar API
• Autoriza acceso a tu calendario  
• Reinicia el sistema MCP

📧 **Mientras tanto:** Puedo ayudarte a coordinar por email"""
            
            return {
                "content": [{
                    "type": "text",
                    "text": response_text
                }]
            }
            
        except Exception as e:
            logger.error(f"Error creando evento: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error creando evento: {str(e)}"
                }]
            }
    
    def _list_events(self, arguments: dict) -> dict:
        """Listar eventos del calendario con LINKS REALES"""
        try:
            if self.has_credentials and self.calendar_manager:
                events_data = self.calendar_manager.list_events(max_results=10)
                
                if events_data['count'] == 0:
                    response_text = "📅 **No tienes eventos programados próximamente**"
                else:
                    response_text = f"📅 **Eventos encontrados: {events_data['count']}**\n\n"
                    
                    for i, event in enumerate(events_data['events'], 1):
                        # ✅ USAR LINKS REALES DE CADA EVENTO
                        event_link = event.get('htmlLink', 'No disponible')
                        
                        response_text += f"**{i}. {event['summary']}**\n"
                        response_text += f"   📅 {event['start']} - {event['end']}\n"
                        
                        if event.get('attendees'):
                            response_text += f"   👥 {', '.join(event['attendees'])}\n"
                        
                        if event_link != 'No disponible':
                            response_text += f"   🔗 {event_link}\n"
                        
                        response_text += "\n"
            else:
                response_text = """📅 **Listado no disponible**

🔧 **Configura Google Calendar API para:**
• Ver eventos existentes
• Verificar disponibilidad
• Gestionar tu calendario

📞 **Necesitas ayuda?** Te puedo guiar en la configuración"""
            
            return {
                "content": [{
                    "type": "text",
                    "text": response_text
                }]
            }
            
        except Exception as e:
            logger.error(f"Error listando eventos: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error listando eventos: {str(e)}"
                }]
            }
    
    def _check_availability(self, arguments: dict) -> dict:
        """Verificar disponibilidad en calendario"""
        try:
            event_date = arguments.get('date', '')
            duration = arguments.get('duration', 60)
            
            if not event_date:
                return {
                    "content": [{
                        "type": "text",
                        "text": "❌ **Fecha requerida** - Especifica la fecha y hora para verificar disponibilidad"
                    }]
                }
            
            if self.has_credentials and self.calendar_manager:
                start_time = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                availability = self.calendar_manager.check_availability(
                    start_time, 
                    duration_hours=duration/60
                )
                
                if availability['available']:
                    response_text = f"""✅ **Horario disponible**

📅 **Fecha:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}
⏱️ **Duración:** {duration} minutos
🎯 **Estado:** Libre para programar evento"""
                else:
                    response_text = f"""❌ **Horario ocupado**

📅 **Fecha:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}
⏱️ **Duración:** {duration} minutos

⚠️ **Conflictos encontrados:**"""
                    
                    for conflict in availability['conflicts']:
                        response_text += f"\n• **{conflict['summary']}**"
                        response_text += f"\n  📅 {conflict['start']} - {conflict['end']}"
            else:
                response_text = """📅 **Verificación no disponible**

🔧 **Configura Google Calendar API para:**
• Verificar disponibilidad en tiempo real
• Detectar conflictos automáticamente
• Sugerir horarios alternativos"""
            
            return {
                "content": [{
                    "type": "text",
                    "text": response_text
                }]
            }
            
        except Exception as e:
            logger.error(f"Error verificando disponibilidad: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error verificando disponibilidad: {str(e)}"
                }]
            }
    
    def process(self, arguments: Dict[str, Any]) -> str:
        """Alias para execute (compatibilidad)"""
        result = self.execute(arguments)
        if isinstance(result, dict) and "content" in result:
            return result["content"][0]["text"]
        return str(result)

# ✅ SELF-TEST AL IMPORTAR
if __name__ == "__main__":
    print("🧪 PROBANDO CALENDAR ADAPTER...")
    adapter = CalendarAdapter()
    
    # Test básico con fecha futura
    tomorrow = datetime.now() + timedelta(days=1)
    test_date = tomorrow.replace(hour=16, minute=0, second=0, microsecond=0).isoformat()
    
    test_args = {
        "action": "create",
        "title": "🧪 Test Calendar Adapter - LINKS REALES",
        "date": test_date,
        "duration": 60,
        "attendees": "agamenonmacondo@gmail.com",
        "description": "Evento de prueba para validar links reales de Google Calendar"
    }
    
    print(f"\n📋 ARGUMENTOS DE PRUEBA:")
    print(f"   📅 Fecha: {test_date}")
    print(f"   👤 Asistente: agamenonmacondo@gmail.com")
    
    result = adapter.execute(test_args)
    print(f"\n📋 RESULTADO:")
    print(result["content"][0]["text"])
    
    print(f"\n🔚 Test completado")