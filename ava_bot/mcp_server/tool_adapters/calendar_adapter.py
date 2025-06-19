import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from .base_adapter import BaseMCPAdapter

class CalendarAdapter(BaseMCPAdapter):
    """Adaptador MCP para la herramienta de calendario"""
    
    def __init__(self, calendar_tool):
        super().__init__(calendar_tool)
        self.name = "calendar"
        self.description = "Crea y gestiona eventos en Google Calendar"
        
        self.schema = {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Título/resumen del evento (REQUERIDO)"
                },
                "start_time": {
                    "type": "string",
                    "description": "Fecha y hora de inicio (REQUERIDO) - formato: YYYY-MM-DDTHH:MM:SS"
                },
                "end_time": {
                    "type": "string",
                    "description": "Fecha y hora de fin (opcional)"
                },
                "duration_hours": {
                    "type": "number",
                    "description": "Duración en horas si no se especifica end_time",
                    "default": 1
                },
                "attendees": {
                    "type": "string",
                    "description": "Emails de asistentes separados por comas (opcional)"
                },
                "location": {
                    "type": "string",
                    "description": "Ubicación del evento (opcional)"
                },
                "timezone": {
                    "type": "string",
                    "description": "Zona horaria (opcional)",
                    "default": "America/Bogota"
                }
            },
            "required": ["summary", "start_time"]
        }
    
    def _parse_attendees(self, attendees: str) -> str:
        """Parse attendees string - mantener como string separado por comas"""
        if not attendees:
            return ""
        
        if isinstance(attendees, list):
            return ','.join(attendees)
        
        # Ya es string, limpiarlo
        if isinstance(attendees, str):
            # Split, limpiar y rejoin
            email_list = []
            for email in attendees.split(','):
                email = email.strip()
                if email:
                    email_list.append(email)
            return ','.join(email_list)
        
        return str(attendees)
    
    def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa la solicitud de calendario"""
        try:
            # ✅ SOLO pasar parámetros básicos que funcionan
            tool_params = {}
            
            # Parámetros básicos requeridos
            if 'summary' in params:
                tool_params['summary'] = params['summary']
            if 'start_time' in params:
                tool_params['start_time'] = params['start_time']
                
            # Parámetros opcionales simples
            if 'duration_hours' in params:
                tool_params['duration_hours'] = params['duration_hours']
            if 'end_time' in params:
                tool_params['end_time'] = params['end_time']
            if 'location' in params:
                tool_params['location'] = params['location']
            if 'timezone' in params:
                tool_params['timezone'] = params['timezone']
            
            # Attendees procesado
            if 'attendees' in params and params['attendees']:
                tool_params['attendees'] = self._parse_attendees(params['attendees'])
            
            # ❌ NO agregar 'action' ni otros parámetros automáticamente
            
            print(f"🔧 DEBUG Calendar: Enviando parámetros: {tool_params}")
            
            # Ejecutar herramienta original
            result = self.tool.process(tool_params)
            
            print(f"🔧 DEBUG Calendar: Resultado: {result}")
            
            return {
                "message": f"✅ Evento '{params.get('summary', 'Sin título')}' creado para {params.get('start_time')}",
                "success": True,
                "event_details": result
            }
            
        except Exception as e:
            print(f"🔧 DEBUG Calendar: Error: {str(e)}")
            return {
                "message": f"❌ Error creando evento: {str(e)}",
                "success": False
            }
    
    def _read_calendar(self, params):
        """Lee eventos REALES del calendario de Google - FORMATO JSON LIMPIO"""
        try:
            # ✅ REMOVER TODOS LOS PRINTS QUE ROMPEN JSON
            date_str = params.get("date")
            date_range = params.get("date_range")
            max_results = params.get("max_results", 10)
            
            # Determinar qué período leer
            if date_range:
                # Leer rango de fechas: "2025-05-28,2025-06-03"
                start_str, end_str = date_range.split(",")
                start_str = start_str.strip()
                end_str = end_str.strip()
                
                result = self.calendar_manager.get_events_by_date_range(start_str, end_str)
                
            elif date_str:
                # Leer fecha específica: "2025-05-28"
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                end_date = date_obj + timedelta(days=1)
                result = self.calendar_manager.list_events(date_obj, end_date, max_results)
                
            else:
                # Leer eventos de HOY por defecto
                today = datetime.now()
                start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                result = self.calendar_manager.list_events(start_of_day, end_of_day, max_results)
            
            # Procesar resultado SIN PRINTS
            if not result or result.get("count", 0) == 0:
                if date_str:
                    return {
                        "message": f"📅 No tienes eventos programados para {date_str}",
                        "events": [],
                        "count": 0,
                        "calendar_empty": True
                    }
                elif date_range:
                    return {
                        "message": f"📅 No tienes eventos en el período {date_range}",
                        "events": [],
                        "count": 0,
                        "calendar_empty": True
                    }
                else:
                    return {
                        "message": "📅 No tienes eventos programados para hoy",
                        "events": [],
                        "count": 0,
                        "calendar_empty": True
                    }
            
            # ✅ FORMATEAR EVENTOS DE MANERA PROFESIONAL
            events = result.get("events", [])
            
            # Crear resumen por día
            events_by_day = {}
            for event in events:
                summary = event.get('summary', 'Sin título')
                start = event.get('start', '')
                attendees = event.get('attendees', [])
                
                # Formatear fecha/hora de inicio
                if start:
                    try:
                        if 'T' in start:
                            # Evento con hora específica
                            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            date_key = start_dt.strftime('%Y-%m-%d')
                            time_str = start_dt.strftime('%H:%M')
                            day_name = start_dt.strftime('%A')
                            date_display = start_dt.strftime('%d/%m/%Y')
                        else:
                            # Evento de día completo
                            start_dt = datetime.strptime(start, '%Y-%m-%d')
                            date_key = start_dt.strftime('%Y-%m-%d')
                            time_str = "Todo el día"
                            day_name = start_dt.strftime('%A')
                            date_display = start_dt.strftime('%d/%m/%Y')
                    except:
                        date_key = "fecha_desconocida"
                        time_str = "Hora no especificada"
                        day_name = "Día desconocido"
                        date_display = "Fecha no válida"
                else:
                    date_key = "fecha_desconocida"
                    time_str = "Hora no especificada"
                    day_name = "Día desconocido"
                    date_display = "Fecha no válida"
                
                # Formatear asistentes
                attendees_str = ""
                if attendees and len(attendees) > 0:
                    if len(attendees) == 1:
                        attendees_str = f" - Con: {attendees[0]}"
                    elif len(attendees) <= 3:
                        attendees_str = f" - Con: {', '.join(attendees)}"
                    else:
                        attendees_str = f" - Con: {', '.join(attendees[:2])} y {len(attendees) - 2} más"
                
                # Agrupar por día
                if date_key not in events_by_day:
                    events_by_day[date_key] = {
                        'day_name': day_name,
                        'date_display': date_display,
                        'events': []
                    }
                
                events_by_day[date_key]['events'].append({
                    'time': time_str,
                    'summary': summary,
                    'attendees_str': attendees_str
                })
            
            # ✅ CREAR MENSAJE ESTRUCTURADO POR DÍAS
            message_parts = []
            message_parts.append(f"📅 **MI AGENDA ESTA SEMANA - {len(events)} eventos programados:**\n")
            
            # Ordenar días cronológicamente
            sorted_days = sorted(events_by_day.items())
            
            for date_key, day_info in sorted_days:
                day_name = day_info['day_name']
                date_display = day_info['date_display']
                day_events = day_info['events']
                
                # Traducir días al español
                day_translations = {
                    'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                    'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
                }
                day_name_es = day_translations.get(day_name, day_name)
                
                message_parts.append(f"\n📆 **{day_name_es} {date_display}:**")
                
                # Ordenar eventos por hora
                day_events.sort(key=lambda x: x['time'])
                
                for i, event in enumerate(day_events, 1):
                    time_str = event['time']
                    summary = event['summary']
                    attendees_str = event['attendees_str']
                    
                    message_parts.append(f"  {i}. 🕐 **{time_str}** - {summary}{attendees_str}")
            
            # ✅ AGREGAR RESUMEN FINAL
            message_parts.append(f"\n✨ **Total: {len(events)} reuniones esta semana**")
            
            final_message = "\n".join(message_parts)
            
            return {
                "message": final_message,
                "events": events,
                "count": len(events),
                "calendar_empty": False,
                "period_queried": date_str or date_range or "esta semana"
            }
            
        except Exception as e:
            # ✅ ERROR SIN PRINTS
            return {
                "error": f"Error leyendo calendario: {str(e)}",
                "message": "❌ No pude acceder a tu calendario en este momento. Verifica tu conexión a Google.",
                "events": [],
                "count": 0
            }