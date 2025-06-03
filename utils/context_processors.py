from datetime import datetime

def register_context_processors(app):
    """Registrar procesadores de contexto globales"""
    
    @app.context_processor
    def inject_globals():
        """Inyectar variables globales en todos los templates"""
        current_time = datetime.now()
        return {
            'now': current_time,  # Objeto datetime, no función
            'current_year': current_time.year,  # Año actual como entero
            'current_date': current_time.strftime('%Y-%m-%d'),  # Fecha formateada
            'current_datetime': current_time.strftime('%Y-%m-%d %H:%M:%S'),  # Fecha y hora
            'app_name': 'AVA - Agentes Virtuales Avanzados'
        }