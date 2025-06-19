def get_tool_schema(tool_name: str) -> str:
    """Obtener schema actualizado directamente del MCP server"""
    if tool_name == "playwright":
        return """
HERRAMIENTA: playwright
CAMPOS REQUERIDOS: ["action", "url"]

🧠 ACCIONES INTELIGENTES (RECOMENDADAS):
• smart_extract - Extracción automática adaptada al sitio
  - Requiere: action, url, search_query, max_results
  - Ideal para: E-commerce, vuelos, hoteles, productos
  
• auto_search - Búsqueda automática con query
  - Requiere: action, url, search_query
  - Ideal para: Búsquedas complejas en sitios web

• analyze_site - Análisis completo de sitio web
  - Requiere: action, url
  - Ideal para: Entender estructura de sitios

🔧 ACCIONES TRADICIONALES:
• navigate - Navegar a URL
• extract_text - Extraer texto (requiere URL)
• take_screenshot - Capturar pantalla
• execute_js - Ejecutar JavaScript

❌ ACCIONES NO DISPONIBLES:
• fill_input, click_element, wait_for_element
"""

# PARA VUELOS ESPECÍFICAMENTE:
def plan_flight_search(origin: str, destination: str, date: str) -> dict:
    return {
        "tool": "playwright",
        "arguments": {
            "action": "smart_extract",
            "url": "https://www.avianca.com",
            "search_query": f"vuelos {origin} {destination} {date}",
            "max_results": 10
        }
    }