import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from .base_adapter import BaseMCPAdapter

class MeetAdapter(BaseMCPAdapter):
    """Adaptador MCP para la herramienta de Google Meet"""
    
    def __init__(self, meet_tool):
        super().__init__(meet_tool)
        self.name = "meet"
        self.description = "Crea reuniones de Google Meet con calendario integrado"
        
        self.schema = {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Título de la reunión (REQUERIDO)"
                },
                "start_time": {
                    "type": "string",
                    "description": "Fecha y hora de inicio (REQUERIDO) - formato: YYYY-MM-DDTHH:MM:SS"
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duración de la reunión en minutos",
                    "default": 60
                },
                "attendees": {
                    "type": "string",
                    "description": "Emails de asistentes separados por comas (opcional)"
                },
                "timezone": {
                    "type": "string", 
                    "description": "Zona horaria (opcional)",
                    "default": "America/Bogota"
                }
            },
            "required": ["title", "start_time"]
        }
    
    def process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa la solicitud de Google Meet"""
        try:
            # ✅ SOLO pasar parámetros que la herramienta original acepta
            tool_params = {}
            
            # Parámetros básicos requeridos
            if 'title' in params:
                tool_params['title'] = params['title']
            if 'start_time' in params:
                tool_params['start_time'] = params['start_time']
                
            # Parámetros opcionales SOLO si están en params
            if 'duration_minutes' in params:
                tool_params['duration_minutes'] = params['duration_minutes']
            if 'attendees' in params and params['attendees']:
                tool_params['attendees'] = str(params['attendees'])
            if 'timezone' in params:
                tool_params['timezone'] = params['timezone']
            
            # ❌ NO agregar 'description' automáticamente
            # ❌ NO agregar parámetros que no están en params originales
            
            print(f"🔧 DEBUG Meet: Enviando parámetros: {tool_params}")
            
            # Ejecutar herramienta original
            result = self.tool.process(tool_params)
            
            print(f"🔧 DEBUG Meet: Resultado: {result}")
            
            return {
                "message": f"✅ Reunión Meet '{params.get('title', 'Sin título')}' creada para {params.get('start_time')}",
                "success": True,
                "meet_details": result
            }
            
        except Exception as e:
            print(f"🔧 DEBUG Meet: Error: {str(e)}")
            return {
                "message": f"❌ Error creando reunión Google Meet: {str(e)}",
                "success": False
            }