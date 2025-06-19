"""
Adaptador para verificar disponibilidad en el calendario antes de crear citas
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.base_tool import BaseTool
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CalendarCheckAdapter(BaseTool):
    """Verifica disponibilidad en el calendario"""
    
    name = "calendar_check"
    
    schema = {
        "type": "object",
        "properties": {
            "start_time": {
                "type": "string",
                "description": "Fecha y hora de inicio en formato ISO (YYYY-MM-DDTHH:MM:SS)"
            },
            "duration_hours": {
                "type": "number",
                "description": "Duración del evento en horas",
                "default": 1
            },
            "check_conflicts": {
                "type": "boolean",
                "description": "Si verificar conflictos con eventos existentes",
                "default": True
            }
        },
        "required": ["start_time"]
    }
    
    def __init__(self):
        """Inicializa el verificador de calendario"""
        try:
            from nodes.calendar.calendar_node import CalendarNode
            self.calendar_node = CalendarNode()
            logger.info("Calendar check adapter initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing calendar node: {e}")
            self.calendar_node = None
    
    def process(self, params):
        """Verifica disponibilidad en el calendario"""
        if not self.calendar_node:
            return {
                "success": False,
                "error": "Calendar node no disponible"
            }
        
        try:
            start_time = params.get("start_time")
            duration_hours = params.get("duration_hours", 1)
            check_conflicts = params.get("check_conflicts", True)
            
            # Parsear fecha
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                return {
                    "success": False,
                    "error": f"Formato de fecha inválido: {start_time}"
                }
            
            end_dt = start_dt + timedelta(hours=duration_hours)
            
            # Verificar si es un horario razonable
            hour = start_dt.hour
            is_business_hours = 8 <= hour <= 18
            is_weekend = start_dt.weekday() >= 5
            
            # Buscar eventos existentes
            conflicts = []
            if check_conflicts and hasattr(self.calendar_node, 'get_events'):
                try:
                    existing_events = self.calendar_node.get_events(
                        start_time=start_dt.isoformat(),
                        end_time=end_dt.isoformat()
                    )
                    
                    if existing_events:
                        conflicts = [
                            {
                                "title": event.get("summary", "Sin título"),
                                "start": event.get("start", ""),
                                "end": event.get("end", "")
                            }
                            for event in existing_events
                        ]
                        
                except Exception as e:
                    logger.warning(f"Error checking conflicts: {e}")
            
            # Preparar respuesta
            availability = {
                "available": len(conflicts) == 0,
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "duration_hours": duration_hours,
                "is_business_hours": is_business_hours,
                "is_weekend": is_weekend,
                "conflicts": conflicts
            }
            
            # Crear mensaje informativo
            if availability["available"]:
                message = f"✅ **Horario disponible**\n"
                message += f"📅 {start_dt.strftime('%A, %d de %B de %Y')}\n"
                message += f"🕐 {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}\n"
                message += f"⏱️ Duración: {duration_hours} hora(s)\n"
                
                if not is_business_hours:
                    message += "⚠️ Nota: Fuera del horario comercial\n"
                if is_weekend:
                    message += "📅 Nota: Es fin de semana\n"
                    
                message += "\n¿Quieres que proceda a crear la cita?"
            else:
                message = f"❌ **Conflicto de horarios detectado**\n"
                message += f"📅 {start_dt.strftime('%A, %d de %B de %Y')}\n"
                message += f"🕐 {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}\n\n"
                message += "**Eventos existentes:**\n"
                
                for conflict in conflicts:
                    message += f"• {conflict['title']}\n"
                
                message += "\n💡 Te sugiero elegir otro horario."
            
            return {
                "success": True,
                "result": {
                    "message": message,
                    "availability": availability
                }
            }
            
        except Exception as e:
            logger.error(f"Error in calendar check: {e}")
            return {
                "success": False,
                "error": f"Error verificando calendario: {str(e)}"
            }

    def validate_params(self, params):
        """Validación personalizada"""
        validated = super().validate_params(params)
        
        start_time = params.get("start_time")
        if not start_time:
            raise ValueError("start_time es requerido")
        
        # Validar que la fecha no sea en el pasado
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if start_dt < datetime.now():
                raise ValueError("La fecha no puede ser en el pasado")
        except Exception as e:
            raise ValueError(f"Formato de fecha inválido: {e}")
        
        return validated