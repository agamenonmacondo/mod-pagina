"""
PlaywrightAdapter - Automatización Web Universal con JavaScript Inteligente
==========================================================================

Adapter con generador automático de JavaScript que se adapta a cualquier sitio web.
- Detecta automáticamente el tipo de sitio
- Genera JavaScript optimizado específico
- Extrae información estructurada sin hardcodeo
- Funciona con e-commerce, inmobiliarios, noticias, etc.
"""

import asyncio
import logging
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from urllib.parse import urlparse

# Setup logging
logger = logging.getLogger(__name__)

# Verificar Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
    logger.info("✅ Playwright disponible")
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("⚠️ Playwright no instalado")

class JavaScriptGenerator:
    """Generador inteligente de JavaScript para cualquier sitio web"""
    
    def __init__(self):
        self.site_patterns = self._load_site_patterns()
        self.generic_patterns = self._load_generic_patterns()
    
    def _load_site_patterns(self) -> Dict[str, Dict]:
        """Patrones específicos para sitios conocidos"""
        return {
            'airbnb': {
                'domains': ['airbnb.com', 'airbnb.co'],
                'type': 'alojamiento',
                'selectors': {
                    'containers': ['[data-testid="card-container"]', '[data-testid="listing-card"]'],
                    'titles': ['[data-testid="listing-card-title"]'],
                    'prices': ['[data-testid="price-availability"]', 'span[aria-hidden="true"]'],
                    'ratings': ['[aria-label*="★"]'],
                    'search_input': ['#bigsearch-query-location-input', 'input[placeholder*="destino"]']
                }
            },
            'fincaraiz': {
                'domains': ['fincaraiz.com'],
                'type': 'inmobiliario',
                'selectors': {
                    'containers': ['.MuiGrid-item', '.property-card', '[class*="card"]'],
                    'titles': ['h2', 'h3', '.title', '[class*="title"]'],
                    'prices': ['.price', '.precio', '[class*="price"]'],
                    'locations': ['.location', '.address', '[class*="location"]']
                }
            },
            'mercadolibre': {
                'domains': ['mercadolibre.com'],
                'type': 'ecommerce',
                'selectors': {
                    'containers': [
                        '.ui-search-result',           # Selector principal
                        '.ui-search-result__wrapper',   # Alternativo  
                        '.poly-card',                  # Nuevo diseño
                        '[class*="item"]'              # Genérico
                    ],
                    'titles': [
                        '.ui-search-item__title',
                        '.poly-component__title',
                        'h2 a'
                    ],
                    'prices': [
                        '.andes-money-amount',
                        '.price-tag-amount',
                        '[class*="price"]'
                    ]
                }
            },
            'booking': {
                'domains': ['booking.com'],
                'type': 'alojamiento',
                'selectors': {
                    'containers': ['[data-testid="property-card"]', '.sr_property_block'],
                    'titles': ['[data-testid="title"]', '.sr-hotel__name'],
                    'prices': ['[data-testid="price-and-discounted-price"]', '.bui-price-display__value']
                }
            }
        }
    
    def _load_generic_patterns(self) -> Dict[str, List[str]]:
        """Patrones genéricos para sitios desconocidos"""
        return {
            'containers': [
                '.card', '.item', '.product', '.listing', '.result', '.property',
                '[class*="card"]', '[class*="item"]', '[class*="product"]',
                '[class*="listing"]', '[class*="result"]', '[class*="property"]',
                'article', '.entry', '.post', '.box', '.tile'
            ],
            'titles': [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                '.title', '.name', '.heading', '.header',
                '[class*="title"]', '[class*="name"]', '[class*="heading"]',
                'a[href]'
            ],
            'prices': [
                '.price', '.cost', '.amount', '.value', '.precio', '.money',
                '[class*="price"]', '[class*="cost"]', '[class*="amount"]',
                '[class*="value"]', '[class*="precio"]', '[class*="money"]',
                'span', 'div'
            ],
            'descriptions': [
                '.description', '.summary', '.excerpt', '.text', '.content',
                '[class*="description"]', '[class*="summary"]', 'p'
            ],
            'images': [
                'img', '.image', '[class*="image"]', 'picture'
            ],
            'links': [
                'a[href]', '.link', '[class*="link"]'
            ]
        }
    
    def detect_site_type(self, url: str) -> Dict[str, Any]:
        """Detecta automáticamente el tipo de sitio web"""
        domain = self._extract_domain(url)
        
        # Buscar patrón específico
        for site_key, pattern in self.site_patterns.items():
            if any(d in domain for d in pattern['domains']):
                return {
                    'site_key': site_key,
                    'type': pattern['type'],
                    'pattern': pattern,
                    'is_known': True
                }
        
        # Detectar por palabras clave en URL
        url_lower = url.lower()
        if any(word in url_lower for word in ['apartament', 'casa', 'vivienda', 'inmueble', 'property']):
            return {'type': 'inmobiliario', 'is_known': False}
        elif any(word in url_lower for word in ['hotel', 'booking', 'alojamiento', 'hospedaje']):
            return {'type': 'alojamiento', 'is_known': False}
        elif any(word in url_lower for word in ['tienda', 'shop', 'store', 'producto', 'compra']):
            return {'type': 'ecommerce', 'is_known': False}
        elif any(word in url_lower for word in ['noticia', 'news', 'articulo', 'blog']):
            return {'type': 'noticias', 'is_known': False}
        
        return {'type': 'generico', 'is_known': False}
    
    def _extract_domain(self, url: str) -> str:
        """Extrae dominio de URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return url.lower()
    
    def generate_smart_javascript(self, url: str, search_query: str = "", max_results: int = 8) -> str:
        """Genera JavaScript inteligente adaptado al sitio - VERSIÓN CORREGIDA"""
        
        site_info = self.detect_site_type(url)
        domain = self._extract_domain(url)
        
        # Seleccionar selectores apropiados
        if site_info.get('is_known') and 'pattern' in site_info:
            pattern = site_info['pattern']
            container_selectors = pattern['selectors']['containers']
            title_selectors = pattern['selectors']['titles']
            price_selectors = pattern['selectors']['prices']
        else:
            container_selectors = self.generic_patterns['containers']
            title_selectors = self.generic_patterns['titles']
            price_selectors = self.generic_patterns['prices']
        
        # Generar JavaScript dinámico CORREGIDO
        js_code = f"""(() => {{
    console.log('🔍 Análisis inteligente de {domain} iniciado...');
    
    const TIMEOUT_MS = 8000;
    const MAX_RESULTS = {max_results};
    const startTime = Date.now();
    
    const resultado = {{
        sitio: '{domain}',
        tipo_detectado: '{site_info.get("type", "generico")}',
        url: window.location.href,
        timestamp: new Date().toISOString(),
        busqueda_query: '{search_query}',
        elementos: [],
        estadisticas: {{}}
    }};
    
    // ✅ FUNCIONES AUXILIARES DEFINIDAS CORRECTAMENTE
    function esTextoDePrecio(text) {{
        return text && (
            text.includes('$') || 
            text.includes('€') || 
            text.includes('£') ||
            text.includes('COP') ||
            text.includes('USD') ||
            /[\\d,]+\\s*(pesos|dolares|euros)/.test(text)
        ) && !text.includes('Favorito') && text.length < 100;
    }}
    
    function detectarContenedoresInteligentes() {{
        const todosDivs = document.querySelectorAll('div');
        return Array.from(todosDivs).filter(div => {{
            const texto = div.textContent || '';
            const tieneTexto = texto.trim().length > 50 && texto.trim().length < 500;
            const tieneEnlaces = div.querySelectorAll('a').length > 0;
            const tieneImagenes = div.querySelectorAll('img').length > 0;
            const tienePrecio = esTextoDePrecio(texto);
            
            return tieneTexto && (tieneEnlaces || tieneImagenes || tienePrecio);
        }}).slice(0, 20);
    }}
    
    function intentarBusquedaAutomatica(query) {{
        const searchInputs = document.querySelectorAll('input[type="search"], input[placeholder*="buscar"], input[placeholder*="search"], input[placeholder*="Buscar"]');
        
        for (const input of searchInputs) {{
            try {{
                input.value = query;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'Búsqueda configurada: ' + query;
            }} catch (e) {{
                continue;
            }}
        }}
        
        return 'No se pudo configurar búsqueda automática';
    }}
    
    try {{
        // Análisis inicial de página
        resultado.estadisticas = {{
            titulo_pagina: document.title,
            total_divs: document.querySelectorAll('div').length,
            total_links: document.querySelectorAll('a').length,
            total_images: document.querySelectorAll('img').length
        }};
        
        // Búsqueda automática si hay query
        if ('{search_query}' && '{search_query}' !== '') {{
            resultado.busqueda_intentada = intentarBusquedaAutomatica('{search_query}');
        }}
        
        // Detectar contenedores principales con múltiples selectores
        const containerSelectors = {json.dumps(container_selectors)};
        let contenedores = [];
        
        for (const selector of containerSelectors) {{
            if (Date.now() - startTime > TIMEOUT_MS) break;
            
            contenedores = document.querySelectorAll(selector);
            if (contenedores.length > 0) {{
                console.log(`✅ Encontrados ${{contenedores.length}} elementos con: ${{selector}}`);
                resultado.selector_exitoso = selector;
                break;
            }}
        }}
        
        // Si no encuentra contenedores específicos, usar análisis inteligente
        if (contenedores.length === 0) {{
            console.log('🔍 Usando detección inteligente...');
            contenedores = detectarContenedoresInteligentes();
            resultado.metodo_deteccion = 'inteligente';
            resultado.selector_exitoso = 'detección inteligente';
        }}
        
        console.log(`📊 Total contenedores para procesar: ${{contenedores.length}}`);
        
        // Extraer información de cada contenedor
        const titleSelectors = {json.dumps(title_selectors)};
        const priceSelectors = {json.dumps(price_selectors)};
        
        for (let i = 0; i < Math.min(MAX_RESULTS, contenedores.length); i++) {{
            if (Date.now() - startTime > TIMEOUT_MS) break;
            
            const contenedor = contenedores[i];
            const item = {{
                indice: i + 1,
                titulo: 'No disponible',
                precio: 'No disponible',
                descripcion: 'No disponible',
                enlace: 'No disponible',
                rating: 'No disponible',
                imagen: 'No disponible'
            }};
            
            // Extraer título con múltiples selectores
            for (const selector of titleSelectors) {{
                try {{
                    const titleEl = contenedor.querySelector(selector);
                    if (titleEl && titleEl.textContent && titleEl.textContent.trim()) {{
                        item.titulo = titleEl.textContent.trim().substring(0, 150);
                        break;
                    }}
                }} catch (e) {{
                    continue;
                }}
            }}
            
            // Extraer precio con detectores inteligentes
            for (const selector of priceSelectors) {{
                try {{
                    const priceEls = contenedor.querySelectorAll(selector);
                    for (const priceEl of priceEls) {{
                        const text = priceEl.textContent;
                        if (text && esTextoDePrecio(text)) {{
                            item.precio = text.trim();
                            break;
                        }}
                    }}
                    if (item.precio !== 'No disponible') break;
                }} catch (e) {{
                    continue;
                }}
            }}
            
            // Extraer descripción
            try {{
                const descEl = contenedor.querySelector('.description, .summary, p');
                if (descEl && descEl.textContent && descEl.textContent.trim()) {{
                    item.descripcion = descEl.textContent.trim().substring(0, 200);
                }}
            }} catch (e) {{
                // Ignorar error
            }}
            
            // Extraer enlace
            try {{
                const linkEl = contenedor.querySelector('a[href]');
                if (linkEl && linkEl.href) {{
                    item.enlace = linkEl.href;
                }}
            }} catch (e) {{
                // Ignorar error
            }}
            
            // Extraer rating/calificación
            try {{
                const ratingEl = contenedor.querySelector('[aria-label*="★"], [class*="rating"], [class*="star"]');
                if (ratingEl) {{
                    item.rating = ratingEl.textContent || ratingEl.getAttribute('aria-label') || 'Encontrado';
                }}
            }} catch (e) {{
                // Ignorar error
            }}
            
            // Extraer imagen
            try {{
                const imgEl = contenedor.querySelector('img[src]');
                if (imgEl && imgEl.src) {{
                    item.imagen = imgEl.src;
                }}
            }} catch (e) {{
                // Ignorar error
            }}
            
            // Solo agregar si tiene información útil
            if (item.titulo !== 'No disponible' || item.precio !== 'No disponible') {{
                resultado.elementos.push(item);
            }}
        }}
        
    }} catch (error) {{
        resultado.error = error.message;
        console.error('❌ Error en análisis:', error);
    }}
    
    // Estadísticas finales
    resultado.total_procesados = resultado.elementos.length;
    resultado.tiempo_ejecucion = Date.now() - startTime;
    
    console.log(`🏁 Análisis completado: ${{resultado.total_procesados}} elementos en ${{resultado.tiempo_ejecucion}}ms`);
    
    return resultado;
}})()"""
        
        return js_code

class PlaywrightAdapter:
    """
    Adapter con JavaScript inteligente integrado
    """
    
    def __init__(self):
        self.name = "playwright"
        self.description = "Automatización web universal con JavaScript inteligente - adapta a cualquier sitio"
        self.available = PLAYWRIGHT_AVAILABLE
        self.js_generator = JavaScriptGenerator()  # ✅ INTEGRAR GENERADOR
        
        # Configuración
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.screenshots_dir = self.base_path / "generated_images" / "web_screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Esquema actualizado con nueva acción
        self.schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "navigate",
                        "extract_text",
                        "extract_html", 
                        "extract_links",
                        "execute_js",
                        "smart_extract",        # ✅ NUEVA ACCIÓN INTELIGENTE
                        "auto_search",          # ✅ BÚSQUEDA AUTOMÁTICA
                        "analyze_site",         # ✅ ANÁLISIS DE SITIO
                        "take_screenshot",
                        "get_page_info"
                    ],
                    "description": "Acción de automatización web a realizar"
                },
                "url": {
                    "type": "string",
                    "description": "URL de destino"
                },
                "search_query": {
                    "type": "string", 
                    "description": "Término de búsqueda para sitios web"
                },
                "max_results": {
                    "type": "integer",
                    "default": 8,
                    "description": "Máximo número de resultados a extraer"
                },
                "javascript": {
                    "type": "string",
                    "description": "Código JavaScript personalizado"
                },
                "screenshot_name": {
                    "type": "string",
                    "description": "Nombre del archivo de captura"
                },
                "full_page": {
                    "type": "boolean",
                    "default": True,
                    "description": "Captura de página completa"
                },
                "timeout": {
                    "type": "integer",
                    "default": 10000,
                    "description": "Timeout en milisegundos"
                },
                "selector": {
                    "type": "string",
                    "description": "Selector CSS para extraer contenido específico"
                },
                "attribute": {
                    "type": "string",
                    "description": "Nombre del atributo a extraer"
                }
            },
            "required": ["action"]
        }
        
        logger.info(f"🎭 PlaywrightAdapter con JS inteligente inicializado - Disponible: {self.available}")
    
    async def smart_extract(self, params: Dict[str, Any]) -> str:
        """✅ NUEVA FUNCIÓN: Extracción inteligente automática"""
        playwright = browser = context = page = None
        
        try:
            url = params.get('url', '').strip()
            search_query = params.get('search_query', '').strip()
            max_results = params.get('max_results', 8)
            
            if not url:
                return "❌ Error: URL requerida para extracción inteligente"
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            logger.info(f"🧠 Extracción inteligente: {url}")
            
            # Crear sesión
            playwright, browser, context, page = await self._create_browser_session()
            
            # Navegar
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(5000)  # 5 segundos en lugar de 3
            
            # Generar y ejecutar JavaScript inteligente
            smart_js = self.js_generator.generate_smart_javascript(url, search_query, max_results)
            result = await page.evaluate(smart_js)
            
            # Cerrar sesión
            await self._close_browser_session(playwright, browser, context, page)
            
            # Formatear respuesta
            if isinstance(result, dict):
                return self._format_smart_result(result, url, search_query)
            else:
                return f"✅ Extracción completada: {str(result)}"
            
        except Exception as e:
            logger.error(f"❌ Error en extracción inteligente: {e}")
            
            if playwright or browser or context or page:
                await self._close_browser_session(playwright, browser, context, page)
            
            return f"❌ Error: {str(e)}"
    
    def _format_smart_result(self, result: Dict, url: str, search_query: str) -> str:
        """Formatea el resultado de extracción inteligente"""
        sitio = result.get('sitio', 'Sitio desconocido')
        tipo = result.get('tipo_detectado', 'generico')
        elementos = result.get('elementos', [])
        stats = result.get('estadisticas', {})
        
        # Emojis por tipo
        type_emojis = {
            'inmobiliario': '🏠',
            'alojamiento': '🏨', 
            'ecommerce': '🛒',
            'noticias': '📰',
            'generico': '🌐'
        }
        
        emoji = type_emojis.get(tipo, '🌐')
        
        response = f"""
{emoji} **Extracción Inteligente: {sitio}**

**📊 Información del sitio:**
• **Tipo detectado:** {tipo.title()}
• **URL:** {url}
• **Título:** {stats.get('titulo_pagina', 'No disponible')}
"""
        
        if search_query:
            response += f"• **Búsqueda:** {search_query}\n"
        
        response += f"""
**📈 Estadísticas:**
• **Elementos encontrados:** {len(elementos)}
• **Tiempo de ejecución:** {result.get('tiempo_ejecucion', 0)}ms
• **Selector exitoso:** {result.get('selector_exitoso', 'Detección inteligente')}

"""
        
        if elementos:
            response += "**🎯 Resultados extraídos:**\n\n"
            
            for i, item in enumerate(elementos[:8], 1):
                titulo = item.get('titulo', 'Sin título')[:80]
                precio = item.get('precio', 'Sin precio')
                rating = item.get('rating', 'Sin rating')
                
                response += f"""
**{i}. {titulo}**
💰 **Precio:** {precio}
⭐ **Rating:** {rating}
"""
                
                if item.get('enlace') != 'No disponible':
                    response += f"🔗 **Enlace:** {item['enlace'][:100]}...\n"
                
                response += "\n"
        else:
            response += "❌ **No se encontraron elementos** en esta página.\n"
            
            if result.get('error'):
                response += f"**Error:** {result['error']}\n"
        
        return response
    
    async def auto_search(self, params: Dict[str, Any]) -> str:
        """✅ NUEVA FUNCIÓN: Búsqueda automática en sitios web"""
        url = params.get('url', '').strip()
        search_query = params.get('search_query', '').strip()
        
        if not search_query:
            return "❌ Error: search_query requerido para búsqueda automática"
        
        # Usar smart_extract con búsqueda
        params['action'] = 'smart_extract'
        return await self.smart_extract(params)
    
    async def analyze_site(self, params: Dict[str, Any]) -> str:
        """✅ NUEVA FUNCIÓN: Análisis completo de sitio web"""
        playwright = browser = context = page = None
        
        try:
            url = params.get('url', '').strip()
            if not url:
                return "❌ Error: URL requerida para análisis"
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            logger.info(f"🔍 Analizando sitio: {url}")
            
            # Detectar tipo de sitio sin navegar
            site_info = self.js_generator.detect_site_type(url)
            
            # Crear sesión para análisis profundo
            playwright, browser, context, page = await self._create_browser_session()
            
            # Navegar
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Análisis de estructura
            analysis = await page.evaluate('''
                () => {
                    return {
                        titulo: document.title,
                        meta_description: document.querySelector('meta[name="description"]')?.content || '',
                        meta_keywords: document.querySelector('meta[name="keywords"]')?.content || '',
                        idioma: document.documentElement.lang || 'No especificado',
                        charset: document.characterSet || '',
                        
                        estructura: {
                            total_elementos: document.querySelectorAll('*').length,
                            divs: document.querySelectorAll('div').length,
                            links: document.querySelectorAll('a[href]').length,
                            imagenes: document.querySelectorAll('img').length,
                            formularios: document.querySelectorAll('form').length,
                            botones: document.querySelectorAll('button, input[type="submit"]').length,
                            inputs: document.querySelectorAll('input, textarea, select').length,
                            tablas: document.querySelectorAll('table').length,
                            scripts: document.querySelectorAll('script').length
                        },
                        
                        tecnologias: {
                            tiene_jquery: typeof window.jQuery !== 'undefined',
                            tiene_react: document.querySelector('[data-reactroot]') !== null,
                            tiene_vue: typeof window.Vue !== 'undefined',
                            tiene_angular: typeof window.angular !== 'undefined'
                        },
                        
                        seo: {
                            tiene_h1: document.querySelectorAll('h1').length,
                            total_headings: document.querySelectorAll('h1,h2,h3,h4,h5,h6').length,
                            enlaces_externos: Array.from(document.querySelectorAll('a[href]'))
                                .filter(a => a.hostname !== window.location.hostname).length,
                            imagenes_sin_alt: document.querySelectorAll('img:not([alt])').length
                        }
                    };
                }
            ''')
            
            # Cerrar sesión
            await self._close_browser_session(playwright, browser, context, page)
            
            return f"""
🔍 **Análisis Completo de Sitio Web**

**🌐 Información Básica:**
• **URL:** {url}
• **Título:** {analysis['titulo']}
• **Tipo detectado:** {site_info.get('type', 'generico').title()}
• **Sitio conocido:** {'Sí' if site_info.get('is_known') else 'No'}
• **Idioma:** {analysis['idioma']}
• **Charset:** {analysis['charset']}

**📋 Meta Information:**
• **Descripción:** {analysis['meta_description'][:150]}...
• **Keywords:** {analysis['meta_keywords'][:100]}...

**🏗️ Estructura:**
• **Total elementos:** {analysis['estructura']['total_elementos']:,}
• **Divs:** {analysis['estructura']['divs']:,}
• **Enlaces:** {analysis['estructura']['links']:,}
• **Imágenes:** {analysis['estructura']['imagenes']:,}
• **Formularios:** {analysis['estructura']['formularios']}
• **Botones:** {analysis['estructura']['botones']}
• **Campos de entrada:** {analysis['estructura']['inputs']}
• **Scripts:** {analysis['estructura']['scripts']}

**⚙️ Tecnologías Detectadas:**
• **jQuery:** {'✅' if analysis['tecnologias']['tiene_jquery'] else '❌'}
• **React:** {'✅' if analysis['tecnologias']['tiene_react'] else '❌'}
• **Vue:** {'✅' if analysis['tecnologias']['tiene_vue'] else '❌'}
• **Angular:** {'✅' if analysis['tecnologias']['tiene_angular'] else '❌'}

**🎯 SEO Analysis:**
• **H1 tags:** {analysis['seo']['tiene_h1']}
• **Total headings:** {analysis['seo']['total_headings']}
• **Enlaces externos:** {analysis['seo']['enlaces_externos']}
• **Imágenes sin ALT:** {analysis['seo']['imagenes_sin_alt']}

**💡 Recomendaciones:**
• Use `smart_extract` para extraer contenido automáticamente
• Use `auto_search` para búsquedas específicas
• El sitio {'está optimizado' if site_info.get('is_known') else 'se analizará'} con selectores {'específicos' if site_info.get('is_known') else 'genéricos'}
"""
            
        except Exception as e:
            logger.error(f"❌ Error analizando sitio: {e}")
            
            if playwright or browser or context or page:
                await self._close_browser_session(playwright, browser, context, page)
            
            return f"❌ Error: {str(e)}"
    
    async def _create_browser_session(self, headless: bool = True):
        """Crear una nueva sesión de navegador"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        page.set_default_timeout(20000)
        
        return playwright, browser, context, page
    
    async def _close_browser_session(self, playwright, browser, context, page):
        """Cerrar sesión de navegador de forma segura"""
        try:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
        except Exception as e:
            logger.warning(f"⚠️ Error cerrando sesión: {e}")
    
    async def navigate(self, params: Dict[str, Any]) -> str:
        """Navegar a una URL específica"""
        playwright = browser = context = page = None
        
        try:
            url = params.get('url', '').strip()
            if not url:
                return "❌ Error: URL requerida"
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            timeout = params.get('timeout', 30000)
            
            logger.info(f"🌐 Navegando a: {url}")
            
            # Crear sesión
            playwright, browser, context, page = await self._create_browser_session()
            
            # Navegar
            response = await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            
            if response and response.status >= 400:
                return f"❌ Error HTTP {response.status} al cargar {url}"
            
            # Esperar carga adicional
            await page.wait_for_timeout(2000)
            
            # Obtener información básica
            title = await page.title() or "Sin título"
            final_url = page.url
            
            # Cerrar sesión
            await self._close_browser_session(playwright, browser, context, page)
            
            return f"""
🌐 **Navegación Exitosa**

**URL solicitada:** {url}
**URL final:** {final_url}
**Título:** {title}
**Estado:** ✅ Página cargada

💡 *Usa otras acciones para interactuar con la página*
"""
            
        except Exception as e:
            logger.error(f"❌ Error navegando: {e}")
            
            if playwright or browser or context or page:
                await self._close_browser_session(playwright, browser, context, page)
            
            return f"❌ Error navegando a {url}: {str(e)}"
    
    async def extract_text(self, params: Dict[str, Any]) -> str:
        """Extraer texto de página o elemento específico"""
        playwright = browser = context = page = None
        
        try:
            url = params.get('url')
            selector = params.get('selector')
            
            if not url:
                return "❌ Error: URL requerida para extracción"
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            logger.info(f"📄 Extrayendo texto de: {url}")
            
            # Crear sesión
            playwright, browser, context, page = await self._create_browser_session()
            
            # Navegar
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Extraer texto
            if selector:
                # Texto de elemento específico
                element = await page.query_selector(selector)
                if not element:
                    return f"❌ No se encontró elemento con selector: {selector}"
                text = await element.inner_text()
                source = f"elemento '{selector}'"
            else:
                # Texto de toda la página (limpio)
                text = await page.evaluate('''
                    () => {
                        // Remover elementos no deseados
                        const unwanted = document.querySelectorAll('script, style, nav, header, footer, .ad, .ads, .advertisement');
                        unwanted.forEach(el => el.remove());
                        
                        return document.body ? document.body.innerText.trim() : '';
                    }
                ''')
                source = "página completa"
            
            # Cerrar sesión
            await self._close_browser_session(playwright, browser, context, page)
            
            # Limitar longitud si es muy largo
            if len(text) > 3000:
                text = text[:3000] + "\n\n[... contenido truncado ...]"
            
            return f"""
📄 **Texto extraído de {source}:**

{text}

**Fuente:** {url}
**Caracteres:** {len(text):,}
"""
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo texto: {e}")
            
            if playwright or browser or context or page:
                await self._close_browser_session(playwright, browser, context, page)
            
            return f"❌ Error: {str(e)}"
    
    async def execute_js(self, params: Dict[str, Any]) -> str:
        """Ejecutar código JavaScript personalizado"""
        playwright = browser = context = page = None
        
        try:
            url = params.get('url')
            javascript = params.get('javascript')
            
            if not url:
                return "❌ Error: URL requerida"
            if not javascript:
                return "❌ Error: Código JavaScript requerido"
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            logger.info(f"⚡ Ejecutando JS en: {url}")
            
            # Crear sesión
            playwright, browser, context, page = await self._create_browser_session()
            
            # Navegar
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Ejecutar JavaScript
            result = await page.evaluate(javascript)
            
            # Cerrar sesión
            await self._close_browser_session(playwright, browser, context, page)
            
            return f"""
⚡ **JavaScript ejecutado exitosamente**

**URL:** {url}
**Código ejecutado:**
```javascript
{javascript}
```

**Resultado:**
```json
{json.dumps(result, indent=2, ensure_ascii=False)}
```
"""
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando JS: {e}")
            
            if playwright or browser or context or page:
                await self._close_browser_session(playwright, browser, context, page)
            
            return f"❌ Error ejecutando JavaScript: {str(e)}"
    
    async def take_screenshot(self, params: Dict[str, Any]) -> str:
        """Tomar captura de pantalla"""
        playwright = browser = context = page = None
        
        try:
            url = params.get('url')
            if not url:
                return "❌ Error: URL requerida para captura"
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = params.get('screenshot_name', f"screenshot_{timestamp}.png")
            full_page = params.get('full_page', True)
            
            if not filename.endswith('.png'):
                filename += '.png'
            
            filepath = self.screenshots_dir / filename
            
            logger.info(f"📸 Capturando: {url}")
            
            # Crear sesión
            playwright, browser, context, page = await self._create_browser_session()
            
            # Navegar
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # Tomar captura
            await page.screenshot(path=str(filepath), full_page=full_page)
            
            title = await page.title() or "Sin título"
            
            # Cerrar sesión
            await self._close_browser_session(playwright, browser, context, page)
            
            if not filepath.exists():
                return "❌ Error: No se pudo crear la captura"
            
            size_kb = filepath.stat().st_size // 1024
            
            return f"""
📸 **Captura creada exitosamente**

**Archivo:** {filename}
**Página:** {title}
**URL:** {url}
**Tamaño:** {size_kb}KB
**Tipo:** {'Página completa' if full_page else 'Vista actual'}
**Ubicación:** {filepath}

✅ Captura guardada correctamente
"""
            
        except Exception as e:
            logger.error(f"❌ Error capturando: {e}")
            
            if playwright or browser or context or page:
                await self._close_browser_session(playwright, browser, context, page)
            
            return f"❌ Error tomando captura: {str(e)}"
    
    def process(self, params: Dict[str, Any]) -> str:
        """Procesar comandos del adapter con nuevas funciones inteligentes"""
        try:
            if not self.available:
                return """
❌ **Playwright no disponible**

Para instalarlo:
```bash
pip install playwright
playwright install
```
"""
            
            action = params.get('action', '').strip()
            if not action:
                return "❌ Error: Acción requerida"
            
            # Ejecutar acción
            try:
                if action == 'smart_extract':
                    return asyncio.run(self.smart_extract(params))
                elif action == 'auto_search':
                    return asyncio.run(self.auto_search(params))
                elif action == 'analyze_site':
                    return asyncio.run(self.analyze_site(params))
                elif action == 'execute_js':
                    return asyncio.run(self.execute_js(params))
                elif action == 'navigate':
                    return asyncio.run(self.navigate(params))
                elif action == 'extract_text':
                    return asyncio.run(self.extract_text(params))
                elif action == 'take_screenshot':
                    return asyncio.run(self.take_screenshot(params))
                else:
                    return f"""
❌ **Acción no válida:** {action}

**🧠 Acciones Inteligentes:**
• `smart_extract` - **Extracción automática adaptada al sitio**
• `auto_search` - **Búsqueda automática con query**
• `analyze_site` - **Análisis completo de sitio web**

**🔧 Acciones Tradicionales:**
• `execute_js` - Ejecutar JavaScript personalizado
• `navigate` - Navegar a URL
• `extract_text` - Extraer texto
• `take_screenshot` - Capturar pantalla

**🚀 Ejemplo de uso inteligente:**
```json
{{
    "action": "smart_extract",
    "url": "https://cualquier-sitio.com",
    "search_query": "apartamentos Bogotá",
    "max_results": 5
}}
```

**🎯 Funciona automáticamente con:**
• E-commerce (productos, precios)
• Inmobiliarios (propiedades, ubicaciones)
• Alojamientos (hoteles, apartamentos)
• Noticias (artículos, fechas)
• ¡Y cualquier sitio web!
"""
            except RuntimeError as re:
                if "asyncio.run() cannot be called from a running event loop" in str(re):
                    # Manejar event loop
                    import concurrent.futures
                    
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            if action == 'smart_extract':
                                return new_loop.run_until_complete(self.smart_extract(params))
                            elif action == 'auto_search':
                                return new_loop.run_until_complete(self.auto_search(params))
                            elif action == 'analyze_site':
                                return new_loop.run_until_complete(self.analyze_site(params))
                            elif action == 'execute_js':
                                return new_loop.run_until_complete(self.execute_js(params))
                            elif action == 'navigate':
                                return new_loop.run_until_complete(self.navigate(params))
                            elif action == 'extract_text':
                                return new_loop.run_until_complete(self.extract_text(params))
                            elif action == 'take_screenshot':
                                return new_loop.run_until_complete(self.take_screenshot(params))
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_thread)
                        return future.result()
                else:
                    raise re
            
        except Exception as e:
            logger.error(f"❌ Error en process: {e}")
            return f"❌ Error ejecutando '{action}': {str(e)}"
    
    def execute(self, params: Dict[str, Any]) -> str:
        """Alias para compatibilidad MCP"""
        return self.process(params)


# PRUEBA SIMPLE DEL SISTEMA INTELIGENTE
def test_smart_extraction():
    """Prueba básica del sistema inteligente"""
    print("\n" + "="*70)
    print("🧪 PRUEBA: SISTEMA INTELIGENTE LIMPIO")
    print("="*70)
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright no disponible")
        return
    
    adapter = PlaywrightAdapter()
    print(f"🤖 Adapter: {adapter.name}")
    print(f"✅ Disponible: {adapter.available}")
    
    # Prueba con MercadoLibre
    test = {
        'name': '🛒 MercadoLibre - Extracción Inteligente',
        'params': {
            'action': 'smart_extract',
            'url': 'https://www.mercadolibre.com.co',
            'search_query': 'productos',
            'max_results': 3
        }
    }
    
    print(f"\n🔬 EJECUTANDO: {test['name']}")
    print("-" * 60)
    
    try:
        result = adapter.process(test['params'])
        print(result)
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("✅ Prueba completada")


if __name__ == "__main__":
    test_smart_extraction()