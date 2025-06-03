from datetime import datetime

def register_filters(app):
    """Registrar filtros personalizados de Jinja2"""
    
    @app.template_filter('format_date')
    def format_date(date_str):
        """Formatear fecha para mostrar"""
        try:
            if isinstance(date_str, str):
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = date_str
            return dt.strftime('%d/%m/%Y %H:%M')
        except:
            return 'Fecha no disponible'
    
    @app.template_filter('timeago')
    def timeago(date_str):
        """Mostrar tiempo transcurrido desde una fecha"""
        try:
            if isinstance(date_str, str):
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                dt = date_str
            
            now = datetime.now()
            if dt.tzinfo:
                now = now.replace(tzinfo=dt.tzinfo)
            
            diff = now - dt
            
            if diff.days > 0:
                return f"hace {diff.days} días"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"hace {hours} horas"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"hace {minutes} minutos"
            else:
                return "hace un momento"
        except:
            return 'tiempo desconocido'