"""
PlaywrightAdapter - Automatización Web Modular
=============================================

Adapter genérico para automatización web con Playwright.
Proporciona funcionalidades modulares para:
- Navegación web
- Extracción de contenido
- Interacción con elementos
- Capturas de pantalla
- Ejecución de JavaScript
- Gestión de formularios

Autor: AVA Assistant
Fecha: 2025
"""

import asyncio
import logging
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

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

class PlaywrightAdapter:
    """
    Adapter modular para automatización web con Playwright
    
    Funcionalidades genéricas:
    - Navegación a URLs
    - Extracción de contenido (texto, HTML, elementos)
    - Interacción con elementos (click, escribir, scroll)
    - Ejecución de JavaScript personalizado
    - Capturas de pantalla
    - Gestión de formularios
    - Espera de elementos
    """
    
    def __init__(self):
        self.name = "playwright"
        self.description = "Automatización web modular con Playwright - navegación, extracción e interacción"
        self.available = PLAYWRIGHT_AVAILABLE
        
        # Configuración
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.screenshots_dir = self.base_path / "generated_images" / "web_screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Esquema de acciones disponibles
        self.schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "navigate",              # Navegar a URL
                        "extract_text",          # Extraer texto de página o elemento
                        "extract_html",          # Extraer HTML
                        "extract_attributes",    # Extraer atributos de elementos
                        "extract_links",         # Extraer enlaces
                        "click_element",         # Hacer clic en elemento
                        "type_text",            # Escribir texto en elemento
                        "fill_form",            # Llenar formulario
                        "execute_js",           # Ejecutar JavaScript
                        "take_screenshot",      # Captura de pantalla
                        "scroll_page",          # Hacer scroll
                        "wait_for_element",     # Esperar elemento
                        "get_page_info",        # Información de página
                        "close_browser"         # Cerrar navegador
                    ],
                    "description": "Acción de automatización web a realizar"
                },
                "url": {
                    "type": "string",
                    "description": "URL de destino para navegación"
                },
                "selector": {
                    "type": "string", 
                    "description": "Selector CSS del elemento objetivo"
                },
                "text": {
                    "type": "string",
                    "description": "Texto a escribir o buscar"
                },
                "javascript": {
                    "type": "string",
                    "description": "Código JavaScript a ejecutar"
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
                "scroll_direction": {
                    "type": "string",
                    "enum": ["up", "down", "top", "bottom"],
                    "default": "down",
                    "description": "Dirección del scroll"
                },
                "scroll_amount": {
                    "type": "integer",
                    "default": 500,
                    "description": "Cantidad de píxeles para scroll"
                },
                "form_data": {
                    "type": "object",
                    "description": "Datos del formulario como {selector: valor}"
                },
                "attribute": {
                    "type": "string",
                    "description": "Nombre del atributo a extraer"
                }
            },
            "required": ["action"]
        }
        
        logger.info(f"🎭 PlaywrightAdapter inicializado - Disponible: {self.available}")
    
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
    
    async def extract_html(self, params: Dict[str, Any]) -> str:
        """Extraer HTML de página o elemento"""
        playwright = browser = context = page = None
        
        try:
            url = params.get('url')
            selector = params.get('selector')
            
            if not url:
                return "❌ Error: URL requerida"
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            logger.info(f"🔤 Extrayendo HTML de: {url}")
            
            # Crear sesión
            playwright, browser, context, page = await self._create_browser_session()
            
            # Navegar
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Extraer HTML
            if selector:
                element = await page.query_selector(selector)
                if not element:
                    return f"❌ No se encontró elemento: {selector}"
                html = await element.inner_html()
                source = f"elemento '{selector}'"
            else:
                html = await page.content()
                source = "página completa"
            
            # Cerrar sesión
            await self._close_browser_session(playwright, browser, context, page)
            
            # Limitar longitud
            if len(html) > 5000:
                html = html[:5000] + "\n\n[... HTML truncado ...]"
            
            return f"""
🔤 **HTML extraído de {source}:**

```html
{html}
```

**Fuente:** {url}
**Caracteres:** {len(html):,}
"""
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo HTML: {e}")
            
            if playwright or browser or context or page:
                await self._close_browser_session(playwright, browser, context, page)
            
            return f"❌ Error: {str(e)}"
    
    async def extract_links(self, params: Dict[str, Any]) -> str:
        """Extraer enlaces de la página"""
        playwright = browser = context = page = None
        
        try:
            url = params.get('url')
            if not url:
                return "❌ Error: URL requerida"
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            logger.info(f"🔗 Extrayendo enlaces de: {url}")
            
            # Crear sesión
            playwright, browser, context, page = await self._create_browser_session()
            
            # Navegar
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Extraer enlaces
            links = await page.evaluate('''
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links
                        .filter(link => link.href.startsWith('http') && link.innerText.trim())
                        .slice(0, 20)
                        .map(link => ({
                            text: link.innerText.trim(),
                            url: link.href,
                            title: link.title || ''
                        }));
                }
            ''')
            
            # Cerrar sesión
            await self._close_browser_session(playwright, browser, context, page)
            
            if not links:
                return f"❌ No se encontraron enlaces en {url}"
            
            result = f"""
🔗 **Enlaces encontrados en:** {url}
📊 **Total:** {len(links)} enlaces

"""
            
            for i, link in enumerate(links, 1):
                text = link['text'][:60] + ('...' if len(link['text']) > 60 else '')
                result += f"""
**{i}. {text}**
🔗 {link['url']}
📝 {link['title']}

"""
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo enlaces: {e}")
            
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
    
    async def get_page_info(self, params: Dict[str, Any]) -> str:
        """Obtener información detallada de la página"""
        playwright = browser = context = page = None
        
        try:
            url = params.get('url')
            if not url:
                return "❌ Error: URL requerida"
            
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            
            logger.info(f"📊 Obteniendo info de: {url}")
            
            # Crear sesión
            playwright, browser, context, page = await self._create_browser_session()
            
            # Navegar
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Extraer información
            title = await page.title() or "Sin título"
            final_url = page.url
            
            page_data = await page.evaluate('''
                () => {
                    const data = {};
                    
                    // Meta tags
                    const description = document.querySelector('meta[name="description"]');
                    data.description = description ? description.content : '';
                    
                    const keywords = document.querySelector('meta[name="keywords"]');
                    data.keywords = keywords ? keywords.content : '';
                    
                    // Contadores
                    data.links = document.querySelectorAll('a[href]').length;
                    data.images = document.querySelectorAll('img').length;
                    data.forms = document.querySelectorAll('form').length;
                    data.buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"]').length;
                    data.inputs = document.querySelectorAll('input, textarea, select').length;
                    data.headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6').length;
                    
                    // Texto
                    data.text_length = document.body ? document.body.innerText.length : 0;
                    
                    return data;
                }
            ''')
            
            # Cerrar sesión
            await self._close_browser_session(playwright, browser, context, page)
            
            return f"""
📊 **Información de la página**

**🌐 Básico:**
• **Título:** {title}
• **URL solicitada:** {url}
• **URL final:** {final_url}
• **Descripción:** {page_data.get('description', 'No disponible')[:150]}

**📈 Estadísticas:**
• **Enlaces:** {page_data.get('links', 0)}
• **Imágenes:** {page_data.get('images', 0)}
• **Formularios:** {page_data.get('forms', 0)}
• **Botones:** {page_data.get('buttons', 0)}
• **Campos de entrada:** {page_data.get('inputs', 0)}
• **Encabezados:** {page_data.get('headings', 0)}
• **Caracteres de texto:** {page_data.get('text_length', 0):,}

**🏷️ SEO:**
• **Keywords:** {page_data.get('keywords', 'No disponible')}
"""
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo info: {e}")
            
            if playwright or browser or context or page:
                await self._close_browser_session(playwright, browser, context, page)
            
            return f"❌ Error: {str(e)}"
    
    def process(self, params: Dict[str, Any]) -> str:
        """Procesar comandos del adapter"""
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
                if action == 'navigate':
                    return asyncio.run(self.navigate(params))
                elif action == 'extract_text':
                    return asyncio.run(self.extract_text(params))
                elif action == 'extract_html':
                    return asyncio.run(self.extract_html(params))
                elif action == 'extract_links':
                    return asyncio.run(self.extract_links(params))
                elif action == 'execute_js':
                    return asyncio.run(self.execute_js(params))
                elif action == 'take_screenshot':
                    return asyncio.run(self.take_screenshot(params))
                elif action == 'get_page_info':
                    return asyncio.run(self.get_page_info(params))
                else:
                    return f"""
❌ **Acción no válida:** {action}

**Acciones disponibles:**
• `navigate` - Navegar a URL
• `extract_text` - Extraer texto de página/elemento
• `extract_html` - Extraer HTML
• `extract_links` - Extraer enlaces
• `execute_js` - Ejecutar JavaScript personalizado
• `take_screenshot` - Capturar pantalla
• `get_page_info` - Información detallada de página

**Ejemplo de uso:**
```json
{{
    "action": "extract_text",
    "url": "https://example.com",
    "selector": ".content"
}}
```
"""
            except RuntimeError as re:
                if "asyncio.run() cannot be called from a running event loop" in str(re):
                    # Usar thread si hay loop corriendo
                    import concurrent.futures
                    
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            if action == 'navigate':
                                return new_loop.run_until_complete(self.navigate(params))
                            elif action == 'extract_text':
                                return new_loop.run_until_complete(self.extract_text(params))
                            elif action == 'extract_html':
                                return new_loop.run_until_complete(self.extract_html(params))
                            elif action == 'extract_links':
                                return new_loop.run_until_complete(self.extract_links(params))
                            elif action == 'execute_js':
                                return new_loop.run_until_complete(self.execute_js(params))
                            elif action == 'take_screenshot':
                                return new_loop.run_until_complete(self.take_screenshot(params))
                            elif action == 'get_page_info':
                                return new_loop.run_until_complete(self.get_page_info(params))
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


def test_playwright_adapter():
    """Pruebas del adapter modular"""
    print("\n" + "="*60)
    print("🧪 PRUEBAS PLAYWRIGHT ADAPTER MODULAR")
    print("="*60)
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright no disponible")
        print("   Instala con: pip install playwright && playwright install")
        return
    
    adapter = PlaywrightAdapter()
    print(f"🎭 Adapter: {adapter.name}")
    print(f"✅ Disponible: {adapter.available}")
    
    # Pruebas modulares genéricas
    tests = [
        {
            'name': 'Información de página',
            'params': {
                'action': 'get_page_info',
                'url': 'https://httpbin.org/html'
            }
        },
        {
            'name': 'Extraer texto completo',
            'params': {
                'action': 'extract_text',
                'url': 'https://httpbin.org/html'
            }
        },
        {
            'name': 'Extraer enlaces',
            'params': {
                'action': 'extract_links',
                'url': 'https://example.com'
            }
        },
        {
            'name': 'Ejecutar JavaScript',
            'params': {
                'action': 'execute_js',
                'url': 'https://httpbin.org/html',
                'javascript': '() => ({ title: document.title, links: document.querySelectorAll("a").length })'
            }
        },
        {
            'name': 'Captura de pantalla',
            'params': {
                'action': 'take_screenshot',
                'url': 'https://example.com',
                'screenshot_name': 'test_modular'
            }
        }
    ]
    
    # Ejemplo específico para MercadoLibre (en las pruebas)
    mercadolibre_test = {
        'name': 'Ejemplo: Buscar en MercadoLibre (usando JS)',
        'params': {
            'action': 'execute_js',
            'url': 'https://listado.mercadolibre.com.co/smartphone',
            'javascript': '''
                () => {
                    const products = [];
                    const items = document.querySelectorAll('.ui-search-results__item');
                    
                    for (let i = 0; i < Math.min(3, items.length); i++) {
                        const item = items[i];
                        const title = item.querySelector('.ui-search-item__title')?.innerText || '';
                        const price = item.querySelector('.andes-money-amount__fraction')?.innerText || '';
                        
                        if (title && price) {
                            products.push({ title, price });
                        }
                    }
                    
                    return { total_found: items.length, products };
                }
            '''
        }
    }
    
    # 🏠 NUEVA PRUEBA: Airbnb - Listado de alojamientos
    airbnb_test = {
        'name': '🏠 Ejemplo: Listar alojamientos en Airbnb Colombia (usando JS)',
        'params': {
            'action': 'execute_js',
            'url': 'https://www.airbnb.com.co/?_set_bev_on_new_domain=1749074462_EANjZiMTAyOTFmYj',
            'javascript': '''
                () => {
                    // Esperar a que carguen los elementos
                    const alojamientos = [];
                    
                    // Múltiples selectores para elementos de alojamiento
                    const selectors = [
                        '[data-testid="listing-card-title"]',
                        '[data-testid="card-container"]',
                        '[role="group"]',
                        '.c1yo0219',
                        '.t1jojoys'
                    ];
                    
                    let items = [];
                    for (const selector of selectors) {
                        items = document.querySelectorAll(selector);
                        if (items.length > 0) {
                            console.log(`Encontrados ${items.length} elementos con selector: ${selector}`);
                            break;
                        }
                    }
                    
                    // Si no encuentra con selectores específicos, buscar por estructura
                    if (items.length === 0) {
                        // Buscar divs que contengan información de alojamiento
                        const allDivs = document.querySelectorAll('div');
                        items = Array.from(allDivs).filter(div => {
                            const text = div.innerText;
                            return text && (
                                text.includes('$') || 
                                text.includes('noche') || 
                                text.includes('habitación') ||
                                text.includes('★')
                            );
                        }).slice(0, 10);
                    }
                    
                    for (let i = 0; i < Math.min(8, items.length); i++) {
                        const item = items[i];
                        
                        try {
                            // Buscar título del alojamiento
                            let titulo = '';
                            const titleSelectors = [
                                '[data-testid="listing-card-title"]',
                                'h3',
                                'h2',
                                '.t1jojoys',
                                '[aria-label*="habitación"]',
                                '[aria-label*="casa"]'
                            ];
                            
                            for (const sel of titleSelectors) {
                                const titleEl = item.querySelector(sel);
                                if (titleEl && titleEl.innerText.trim()) {
                                    titulo = titleEl.innerText.trim();
                                    break;
                                }
                            }
                            
                            // Si no encuentra título en el elemento, usar el texto del elemento padre
                            if (!titulo) {
                                const parentText = item.innerText || '';
                                const lines = parentText.split('\\n').filter(line => line.trim());
                                titulo = lines[0] || 'Alojamiento sin título';
                            }
                            
                            // Buscar precio
                            let precio = '';
                            const priceSelectors = [
                                '[data-testid="price-availability"]',
                                '.t1l5tixz',
                                '.a8jt5op',
                                'span[aria-hidden="true"]'
                            ];
                            
                            for (const sel of priceSelectors) {
                                const priceEl = item.querySelector(sel);
                                if (priceEl && priceEl.innerText.includes('$')) {
                                    precio = priceEl.innerText.trim();
                                    break;
                                }
                            }
                            
                            // Buscar precio en el texto del elemento
                            if (!precio) {
                                const text = item.innerText || '';
                                const priceMatch = text.match(/\\$[\\d,]+/);
                                if (priceMatch) {
                                    precio = priceMatch[0];
                                }
                            }
                            
                            // Buscar rating
                            let rating = '';
                            const ratingSelectors = [
                                '[aria-label*="★"]',
                                '.r1dxllyb',
                                'span[aria-hidden="true"]'
                            ];
                            
                            for (const sel of ratingSelectors) {
                                const ratingEl = item.querySelector(sel);
                                if (ratingEl && ratingEl.innerText.includes('★')) {
                                    rating = ratingEl.innerText.trim();
                                    break;
                                }
                            }
                            
                            // Buscar rating en texto
                            if (!rating) {
                                const text = item.innerText || '';
                                const ratingMatch = text.match(/★\\s*[\\d,\\.]+/);
                                if (ratingMatch) {
                                    rating = ratingMatch[0];
                                }
                            }
                            
                            // Buscar enlace
                            let enlace = '';
                            const linkEl = item.querySelector('a[href]');
                            if (linkEl) {
                                enlace = linkEl.href;
                            }
                            
                            // Solo agregar si tiene información mínima
                            if (titulo && titulo.length > 5) {
                                alojamientos.push({
                                    titulo: titulo.substring(0, 100),
                                    precio: precio || 'Precio no disponible',
                                    rating: rating || 'Sin rating',
                                    enlace: enlace || 'Sin enlace directo',
                                    elemento_indice: i
                                });
                            }
                            
                        } catch (error) {
                            console.log(`Error procesando elemento ${i}: ${error.message}`);
                        }
                    }
                    
                    // Información adicional de la página
                    const pageInfo = {
                        titulo_pagina: document.title,
                        url_actual: window.location.href,
                        total_elementos_encontrados: items.length,
                        alojamientos_procesados: alojamientos.length
                    };
                    
                    return {
                        info_pagina: pageInfo,
                        alojamientos: alojamientos,
                        debug: {
                            selectores_probados: selectors,
                            elementos_encontrados: items.length
                        }
                    };
                }
            '''
        }
    }
    
    # Agregar las pruebas específicas
    tests.append(mercadolibre_test)
    tests.append(airbnb_test)
    
    for i, test in enumerate(tests, 1):
        print(f"\n🔬 PRUEBA {i}: {test['name']}")
        print("-" * 50)
        
        try:
            result = adapter.process(test['params'])
            print(result)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*50)
    
    print("✅ Pruebas completadas")


if __name__ == "__main__":
    test_playwright_adapter()