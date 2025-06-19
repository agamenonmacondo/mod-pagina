import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# Configuración básica
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("google_search_node")

class GoogleSearchNode:
    def __init__(self):
        # Tavily API (prioridad)
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.tavily_client = None
        self.use_tavily = False
        
        # Intentar importar Tavily
        if self.tavily_api_key:
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=self.tavily_api_key)
                self.use_tavily = True
                logger.info("✅ Tavily client initialized - using fast search")
            except ImportError:
                logger.warning("⚠️ Tavily not installed. Install with: pip install tavily-python")
                self.use_tavily = False
            except Exception as e:
                logger.warning(f"⚠️ Error initializing Tavily: {e}")
                self.use_tavily = False
        else:
            logger.warning("⚠️ TAVILY_API_KEY not found in .env")
        
        # Google API (fallback)
        self.api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyCQUEVdnOc_pU5fZc0152cgkxJvfx1QJSo")
        self.cx = os.getenv("GOOGLE_CX_ID", "f423b49f6e8d64839")
        
        # Groq API para análisis
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = None
        
        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
                logger.info("✅ Groq client initialized for search analysis")
            except ImportError:
                logger.warning("⚠️ Groq not installed. Install with: pip install groq")
            except Exception as e:
                logger.warning(f"⚠️ Error initializing Groq: {e}")
        else:
            logger.warning("⚠️ GROQ_API_KEY not found - analysis disabled")
        
        # Contadores para Google API
        self.search_count = 0
        self.last_reset = datetime.now()
        self.max_daily_searches = 100
        
        # Verificar al menos una API disponible
        if not self.use_tavily and (not self.api_key or not self.cx):
            logger.error("❌ No search API available")
            raise ValueError("No search API configured")
        
        logger.info(f"🔍 Search mode: {'Tavily (fast)' if self.use_tavily else 'Google (fallback)'}")

    def search(self, query, num_results=5):
        """🔍 MÉTODO PRINCIPAL DE BÚSQUEDA"""
        logger.info(f"🔍 Searching for: '{query}' (max {num_results} results)")
        
        if not query or len(query.strip()) < 2:
            logger.warning("Query too short or empty")
            return []
        
        # Usar Tavily si está disponible
        if self.use_tavily:
            return self._search_with_tavily(query, num_results)
        else:
            return self._search_with_google(query, num_results)
    
    def _search_with_tavily(self, query, num_results=5):
        """Búsqueda con Tavily"""
        try:
            logger.info(f"🚀 Tavily search: '{query}'")
            start_time = datetime.now()
            
            response = self.tavily_client.search(
                query=query,
                search_depth="basic",
                include_answer=False,
                include_raw_content=False,
                max_results=num_results
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"⚡ Tavily completed in {duration:.2f}s")
            
            # Convertir resultados al formato esperado
            results = []
            if 'results' in response:
                for item in response['results'][:num_results]:
                    results.append({
                        "title": item.get("title", "Sin título"),
                        "link": item.get("url", "#"),
                        "snippet": item.get("content", "Sin descripción")[:200] + "...",
                        "displayLink": self._extract_domain(item.get("url", "")),
                        "score": item.get("score", 0)
                    })
            
            logger.info(f"✅ Tavily: {len(results)} results found")
            return results
            
        except Exception as e:
            logger.error(f"❌ Tavily error: {e}")
            return self._search_with_google(query, num_results)
    
    def _search_with_google(self, query, num_results=5):
        """Búsqueda con Google API"""
        logger.info(f"🐌 Google search: '{query}'")
        
        if not self._check_daily_limit():
            logger.warning("Google daily limit reached")
            return []

        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": self.cx,
                "q": query,
                "num": min(num_results, 10),
                "hl": "es",
                "lr": "lang_es",
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            self.search_count += 1
            logger.info(f"Google search #{self.search_count}")
            
            results = []
            for item in response.json().get("items", []):
                results.append({
                    "title": item.get("title", "Sin título"),
                    "link": item.get("link", "#"),
                    "snippet": item.get("snippet", "Sin descripción"),
                    "displayLink": item.get("displayLink", self._extract_domain(item.get("link", ""))),
                })
            
            logger.info(f"✅ Google: {len(results)} results found")
            return results
            
        except Exception as e:
            logger.error(f"Google search error: {e}")
            return []
    
    def analyze_with_groq(self, query, results):
        """🧠 ANÁLISIS CON GROQ LLAMA 3.1"""
        if not self.groq_client or not results:
            logger.warning("Groq client not available or no results to analyze")
            return self._create_simple_analysis(query, results)
        
        try:
            logger.info(f"🧠 Analyzing {len(results)} results with Groq")
            
            # Preparar contexto de resultados
            results_context = ""
            for i, result in enumerate(results[:5], 1):
                results_context += f"{i}. **{result['title']}**\n"
                results_context += f"   URL: {result['link']}\n"
                results_context += f"   Descripción: {result['snippet']}\n\n"
            
            # Prompt para Groq
            prompt = f"""Como asistente experto en análisis de información, analiza estos resultados de búsqueda para la consulta: "{query}"

RESULTADOS ENCONTRADOS:
{results_context}

Por favor proporciona:
1. Un resumen conciso de la información más relevante
2. Los puntos clave encontrados
3. Recomendaciones o conclusiones útiles

Responde en español de manera clara y estructurada. Máximo 300 palabras."""

            # Llamar a Groq
            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[
                    {"role": "system", "content": "Eres un asistente especializado en análisis de información web. Proporciona análisis concisos y útiles."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            analysis = response.choices[0].message.content.strip()
            logger.info(f"✅ Groq analysis completed ({len(analysis)} chars)")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Groq analysis error: {e}")
            return self._create_simple_analysis(query, results)
    
    def _create_simple_analysis(self, query, results):
        """Análisis simple sin IA externa"""
        if not results:
            return f"No se encontraron resultados para '{query}'"
            
        analysis = f"📊 **Resumen de búsqueda: '{query}'**\n\n"
        analysis += f"Encontré {len(results)} resultados relevantes:\n\n"
        
        for i, result in enumerate(results[:3], 1):
            analysis += f"**{i}. {result['title']}**\n"
            analysis += f"   🔗 {result['link']}\n"
            analysis += f"   📝 {result['snippet']}\n\n"
        
        if len(results) > 3:
            analysis += f"... y {len(results) - 3} resultados más.\n"
        
        return analysis
    
    def _extract_domain(self, url):
        """Extrae el dominio de una URL"""
        try:
            if url.startswith(("http://", "https://")):
                return url.split("//")[1].split("/")[0]
            return url.split("/")[0]
        except:
            return "unknown"
    
    def refine_search_query(self, query):
        """🔧 REFINAMIENTO DE CONSULTA"""
        cleaned = query.strip().lower()
        
        # Correcciones básicas
        corrections = {
            "ggolge": "google",
            "lolazmientos": "lanzamientos", 
            "intener": "internet",
            "vibe coding": "vibe coding programming",
            "empelo": "empleo",
            "programdor": "programador"
        }
        
        for wrong, correct in corrections.items():
            cleaned = cleaned.replace(wrong, correct)
        
        logger.info(f"Query refined: '{query}' -> '{cleaned}'")
        return cleaned
    
    def _check_daily_limit(self):
        """Verificar límite diario Google API"""
        if datetime.now() - self.last_reset > timedelta(days=1):
            self.search_count = 0
            self.last_reset = datetime.now()
            
        if self.search_count >= self.max_daily_searches:
            logger.warning(f"Google daily limit reached ({self.max_daily_searches})")
            return False
        return True

# Test directo
if __name__ == "__main__":
    try:
        search_node = GoogleSearchNode()
        print(f"✅ GoogleSearchNode initialized")
        
        # Test de búsqueda
        results = search_node.search("vibe coding", 3)
        print(f"📊 Found {len(results)} results")
        
        if results:
            print("\n📋 Resultados:")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['title']}")
                print(f"   {result['link']}")
                print(f"   {result['snippet'][:100]}...\n")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()