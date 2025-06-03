#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
seo_node.py - Nodo SEO que reduce el tamaño de los informes

Este script modifica el comportamiento del seo_node para:
1. Limitar el tamaño del contenido extraído (máximo 1500 palabras)
2. Reducir el número de temas de 6 a 3
3. Limitar el número de imágenes a 1 por artículo
4. Crear una carpeta de salida con timestamp para evitar mezclar resultados
5. Utilizar la API de Tavily para búsqueda de artículos
"""

import os
import logging
import re
from collections import Counter
from typing import List, Dict, Any
from datetime import datetime
import json
import time
import requests
from bs4 import BeautifulSoup

# Configurar logging
logger = logging.getLogger("news_trigger_node")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 1. Reducir MAX_TOPICS_TO_RETURN de 6 a 3
MAX_TOPICS_TO_RETURN = 3  # Reducido de 6 a 3

# Variables globales que se asumen disponibles
SEARCH_TOPICS = ["artifical intelligence", " ai software development", "ai agents"]  # Ejemplo, ajustar según configuración real
MAX_RESULTS_PER_TOPIC = 10  # Ejemplo, ajustar según configuración real
all_results = []

# Importar Tavily API
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    logger.warning("Tavily no está disponible. Instalarlo con: pip install tavily")

# Obtener API key de Tavily desde variables de entorno
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY and TAVILY_AVAILABLE:
    logger.warning("TAVILY_API_KEY no encontrada en variables de entorno")

# Funciones que se asumen disponibles (sustituir con implementaciones reales si es necesario)
def filter_results(results, topic):
    """Filtra los resultados de búsqueda"""
    return results.get('results', [])

def extract_keywords_from_text(text: str, max_keywords: int = 5) -> List[str]:
    """
    Extrae palabras clave significativas de un texto
    
    Args:
        text: Texto de entrada
        max_keywords: Número máximo de palabras clave a devolver
            
    Returns:
        Lista de palabras clave
    """
    # Eliminar caracteres especiales y separar palabras
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    
    # Filtrar palabras comunes y cortas (stopwords en español e inglés)
    stopwords = {
        "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con", "contra",
        "cual", "cuando", "de", "del", "desde", "donde", "durante", "e", "el", "ella",
        "ellas", "ellos", "en", "entre", "era", "erais", "eran", "eras", "eres", "es",
        "esa", "esas", "ese", "eso", "esos", "esta", "estaba", "estabais", "estaban",
        "estabas", "estad", "estada", "estadas", "estado", "estados", "estamos", "estando",
        "estar", "estaremos", "estará", "estarán", "estarás", "estaré", "estaréis",
        "estaría", "estaríais", "estaríamos", "estarían", "estarías", "estas", "este",
        "estemos", "esto", "estos", "estoy", "estuve", "estuviera", "estuvierais",
        "estuvieran", "estuvieras", "estuvieron", "estuviese", "estuvieseis", "estuviesen",
        "estuvieses", "estuvimos", "estuviste", "estuvisteis", "estuviéramos",
        "estuviésemos", "estuvo", "está", "estábamos", "estáis", "están", "estás", "esté",
        "estéis", "estén", "estés", "fue", "fuera", "fuerais", "fueran", "fueras",
        "fueron", "fuese", "fueseis", "fuesen", "fueses", "fui", "fuimos", "fuiste",
        "fuisteis", "fuéramos", "fuésemos", "ha", "habida", "habidas", "habido", "habidos",
        "habiendo", "habremos", "habrá", "habrán", "habrás", "habré", "habréis", "habría",
        "habríais", "habríamos", "habrían", "habrías", "habéis", "había", "habíais",
        "habíamos", "habían", "habías", "han", "has", "hasta", "hay", "haya", "hayamos",
        "hayan", "hayas", "hayáis", "he", "hemos", "hube", "hubiera", "hubierais",
        "hubieran", "hubieras", "hubieron", "hubiese", "hubieseis", "hubiesen", "hubieses",
        "hubimos", "hubiste", "hubisteis", "hubiéramos", "hubiésemos", "hubo", "la", "las",
        "le", "les", "lo", "los", "me", "mi", "mis", "mucho", "muchos", "muy", "más",
        "mí", "mía", "mías", "mío", "míos", "nada", "ni", "no", "nos", "nosotras",
        "nosotros", "nuestra", "nuestras", "nuestro", "nuestros", "o", "os", "otra",
        "otras", "otro", "otros", "para", "pero", "poco", "por", "porque", "que",
        "quien", "quienes", "qué", "se", "sea", "seamos", "sean", "seas", "seremos",
        "será", "serán", "serás", "seré", "seréis", "sería", "seríais", "seríamos",
        "serían", "serías", "seáis", "sido", "siendo", "sin", "sobre", "sois", "somos",
        "son", "soy", "su", "sus", "suya", "suyas", "suyo", "suyos", "sí", "también",
        "tanto", "te", "tendremos", "tendrá", "tendrán", "tendrás", "tendré", "tendréis",
        "tendría", "tendríais", "tendríamos", "tendrían", "tendrías", "tened", "tenemos",
        "tenga", "tengamos", "tengan", "tengas", "tengo", "tengáis", "tenida", "tenidas",
        "tenido", "tenidos", "teniendo", "tenéis", "tenía", "teníais", "teníamos",
        "tenían", "tenías", "ti", "tiene", "tienen", "tienes", "todo", "todos", "tu",
        "tus", "tuve", "tuviera", "tuvierais", "tuvieran", "tuvieras", "tuvieron",
        "tuviese", "tuvieseis", "tuviesen", "tuvieses", "tuvimos", "tuviste", "tuvisteis",
        "tuviéramos", "tuviésemos", "tuvo", "tuya", "tuyas", "tuyo", "tuyos", "tú",
        "un", "una", "uno", "unos", "vosotras", "vosotros", "vuestra", "vuestras",
        "vuestro", "vuestros", "y", "ya", "yo", "él", "éramos",
        # English stopwords
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
        "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
        "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
        "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
        "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's",
        "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
        "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself",
        "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not",
        "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
        "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll",
        "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
        "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
        "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
        "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
        "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
        "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why",
        "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
        "you've", "your", "yours", "yourself", "yourselves"
    }
    
    # Filtrar stopwords y palabras muy cortas
    filtered_words = [word.lower() for word in words if word.lower() not in stopwords and len(word) > 3]
    
    # Contar frecuencia de palabras
    word_counts = Counter(filtered_words)
    
    # Obtener las palabras más frecuentes
    keywords = [word for word, _ in word_counts.most_common(max_keywords)]
    
    return keywords

def generate_topics(results, max_topics):
    """
    Genera temas a partir de los resultados de búsqueda
    
    Args:
        results: Lista de resultados de búsqueda
        max_topics: Número máximo de temas a generar
        
    Returns:
        Lista de temas generados con keywords extraídos
    """
    if not results:
        logger.warning("No hay resultados para generar temas")
        return []
    
    # Agrupar resultados por similitud (simplificado)
    topics = []
    used_results = set()
    
    for i, result in enumerate(results):
        if i >= max_topics or len(topics) >= max_topics:
            break
            
        if i in used_results:
            continue
            
        title = result.get('title', f'Tema {i+1}')
        content = result.get('content', '')
        
        # Extraer keywords del título y contenido
        title_keywords = extract_keywords_from_text(title, 3)
        content_keywords = extract_keywords_from_text(content, 5)
        
        # Combinar keywords y eliminar duplicados
        all_keywords = list(set(title_keywords + content_keywords))
        
        # Crear tema
        topic = {
            'title': title,
            'keywords': all_keywords[:5] if all_keywords else ['keyword1', 'keyword2'],  # Limitar a 5 keywords
            'relevance_score': 0.9 - (i * 0.1),  # Simulación de score
            'category': 'General',
            'original_result': result
        }
        
        topics.append(topic)
        used_results.add(i)
    
    return topics[:max_topics]

def search_with_fallback(topic, max_results):
    """
    Realiza búsqueda de artículos usando Tavily API con fallback a búsqueda simulada
    
    Args:
        topic: Tema de búsqueda
        max_results: Número máximo de resultados
        
    Returns:
        Diccionario con resultados de la búsqueda
    """
    logger.info(f"Buscando tema: {topic}")
    
    # Verificar si Tavily está disponible
    if TAVILY_AVAILABLE and TAVILY_API_KEY:
        try:
            logger.info(f"Buscando en Tavily: {topic}")
            
            # Inicializar cliente Tavily
            tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
            
            # Realizar búsqueda con Tavily
            response = tavily_client.search(
                query=topic,
                search_depth="basic",  # Usar "advanced" para búsquedas más profundas
                topic="news",          # Enfocado en noticias
                max_results=max_results,
                include_images=True,   # Incluir imágenes en los resultados
                include_raw_content=True  # Incluir contenido completo
            )
            
            # Verificar si la respuesta es válida
            if 'results' in response:
                results = response['results']
                logger.info(f"Encontrados {len(results)} resultados de Tavily")
                
                # Procesar resultados para formato uniforme
                processed_results = []
                for result in results:
                    processed_result = {
                        'title': result.get('title', ''),
                        'url': result.get('url', ''),
                        'content': result.get('content', ''),
                        'raw_content': result.get('raw_content', ''),
                        'score': result.get('score', 0),
                        'published_date': result.get('published_date', ''),
                        'source': 'tavily'
                    }
                    
                    # Añadir imagen si está disponible
                    if 'image_url' in result:
                        processed_result['image_url'] = result['image_url']
                    
                    processed_results.append(processed_result)
                
                return {
                    'success': True,
                    'results': processed_results
                }
            else:
                logger.error(f"Respuesta de Tavily API inválida: {response}")
        
        except Exception as e:
            logger.error(f"Error usando Tavily API: {str(e)}")
            logger.info("Usando fallback para búsqueda")
    else:
        logger.warning("Tavily no disponible, usando búsqueda simulada")
    
    # Fallback: Búsqueda simulada
    return {
        'success': True,
        'results': [{'title': f'Resultado {i} para {topic}', 'content': f'Contenido simulado para {topic}'} for i in range(max_results)]
    }

def extract_full_content_for_topics(topics):
    """Extrae el contenido completo para los temas proporcionados"""
    for topic in topics:
        # Si hay una URL en el resultado original, intentar extraer el contenido
        if 'original_result' in topic and 'url' in topic['original_result']:
            url = topic['original_result']['url']
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            full_content = extract_full_article_patched(url, headers, max_retries=3, timeout=10)
            topic['full_content'] = full_content
        else:
            # Si no hay URL, crear un contenido de ejemplo
            topic['full_content'] = {
                'success': True,
                'title': topic.get('title', 'Sin título'),
                'content': f"Contenido simulado para el tema: {topic.get('title', 'Sin título')}",
                'images': [],
                'url': 'https://example.com'
            }
    return topics

# 2. Función para extraer contenido completo
def extract_full_article(url, headers, max_retries, timeout):
    """Wrapper para la función patched para mantener compatibilidad con código existente"""
    return extract_full_article_patched(url, headers, max_retries, timeout)

def extract_full_article_patched(url, headers, max_retries, timeout):
    """Versión modificada de extract_full_article que limita el tamaño del contenido"""
    logger.info(f"Extrayendo contenido completo de: {url}")
    
    if not url or url == "https://example.com/1" or url == "https://example.com/2":
        # Caso de URLs de ejemplo (fallback)
        return {
            'success': False,
            'content': "Contenido de ejemplo no extraíble",
            'error': "URL de ejemplo"
        }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Parseamos el HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Eliminar elementos que no nos interesan
            for tag in soup(['script', 'style', 'iframe', 'nav', 'footer', 'aside']):
                tag.decompose()
            
            # Extraer título
            title = soup.title.text.strip() if soup.title else ""
            
            # Estrategia 1: Buscar el contenido principal
            main_content = None
            for selector in ['article', 'main', '.content', '.post-content', '.entry-content', '#content']:
                if not main_content:
                    main_content = soup.select_one(selector)
            
            # Si encontramos contenido principal, extraer texto
            if main_content:
                paragraphs = main_content.find_all('p')
                text = "\n\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
            else:
                # Estrategia 2: Obtener todos los párrafos largos
                paragraphs = soup.find_all('p')
                text = "\n\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 100])
            
            # Si aún no tenemos texto suficiente, usar todo el texto del body
            if len(text) < 500 and soup.body:
                text = soup.body.get_text().strip()
                # Limpiar espacios múltiples
                text = re.sub(r'\s+', ' ', text)
                # Dividir en párrafos por puntos
                text = re.sub(r'\.', '.\n\n', text)
            
            # NUEVO: Limitar el tamaño del contenido (máximo 1500 palabras)
            words = text.split()
            if len(words) > 1500:
                text = ' '.join(words[:1500]) + "... [Contenido truncado]"
                logger.info(f"Contenido truncado a 1500 palabras de {len(words)} originales")
            
            # Extraer imágenes principales (máximo 1 para reducir tamaño)
            images = []
            for img in soup.find_all('img', src=True)[:1]:  # Reducido a 1 imagen
                src = img['src']
                # Convertir URLs relativas a absolutas
                if src.startswith('/'):
                    base_url = '/'.join(url.split('/')[:3])  # http(s)://domain.com
                    src = base_url + src
                images.append(src)
            
            # Verificar si tenemos suficiente contenido
            if len(text) > 300:
                return {
                    'success': True,
                    'title': title,
                    'content': text,
                    'images': images,
                    'url': url
                }
            else:
                logger.warning(f"Contenido extraído demasiado corto ({len(text)} caracteres) de {url}")
                if attempt < max_retries - 1:
                    logger.info(f"Reintentando extracción ({attempt+2}/{max_retries})...")
                    time.sleep(2)  # Esperar antes de reintentar
                else:
                    return {
                        'success': False,
                        'content': text if text else "No se pudo extraer contenido suficiente",
                        'error': "Contenido insuficiente"
                    }
        
        except requests.Timeout:
            logger.warning(f"Timeout al extraer contenido de {url}")
            if attempt < max_retries - 1:
                logger.info(f"Reintentando extracción ({attempt+2}/{max_retries})...")
                time.sleep(2)
            else:
                return {
                    'success': False,
                    'error': "Timeout al extraer contenido"
                }
        
        except Exception as e:
            logger.error(f"Error extrayendo contenido de {url}: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Reintentando extracción ({attempt+2}/{max_retries})...")
                time.sleep(2)
            else:
                return {
                    'success': False,
                    'error': str(e)
                }
    
    return {
        'success': False,
        'error': "Máximo de intentos alcanzado"
    }

# 3. Función principal que necesita el flujo de trabajo
def run_news_trigger_node(output_dir="ava_seo/output/seo_json"):
    """Función principal que el flujo de trabajo busca para ejecutar el nodo"""
    return run_news_trigger_node_patched(output_dir)

# Implementación de la función patched
def run_news_trigger_node_patched(output_dir="ava_seo/output/seo_json"):
    """Versión modificada de run_news_trigger_node que crea una subcarpeta con timestamp"""
    start_time = datetime.now()
    logger.info(f"Iniciando news_trigger_node: {start_time}")
    
    # Obtener acceso a las funciones y variables globales
    global all_results, SEARCH_TOPICS, MAX_RESULTS_PER_TOPIC
    
    all_results = []
    
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # NUEVO: Crear una subcarpeta con timestamp para evitar mezclar resultados
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir_with_timestamp = os.path.join(output_dir, f"run_{timestamp_str}")
    os.makedirs(output_dir_with_timestamp, exist_ok=True)
    
    # PASO 1: Búsqueda y filtrado de noticias
    logger.info("PASO 1: Búsqueda y filtrado de noticias relevantes")
    for topic in SEARCH_TOPICS:
        logger.info(f"Buscando tema: {topic}")
        
        # Realizar búsqueda
        search_results = search_with_fallback(topic, MAX_RESULTS_PER_TOPIC)
        
        if search_results['success']:
            # Filtrar resultados
            filtered = filter_results(search_results, topic)
            all_results.extend(filtered)
            logger.info(f"  Encontrados {len(filtered)} resultados relevantes")
        else:
            logger.error(f"  Error en la búsqueda: {search_results.get('error', 'Desconocido')}")
    
    # Generar temas de los resultados (usando MAX_TOPICS_TO_RETURN reducido)
    topics = generate_topics(all_results, MAX_TOPICS_TO_RETURN)
    
    logger.info(f"Generados {len(topics)} temas principales:")
    for i, topic in enumerate(topics, 1):
        logger.info(f"{i}. {topic['title']}")
        logger.info(f"   Keywords: {', '.join(topic['keywords'] if topic['keywords'] else ['<sin keywords>'])}")
        logger.info(f"   Relevancia: {topic['relevance_score']:.2f}")
        logger.info(f"   Categoría: {topic['category']}")
    
    # PASO 2: Extracción de contenido completo
    logger.info("\nPASO 2: Extracción de contenido completo de artículos seleccionados")
    enriched_topics = extract_full_content_for_topics(topics)
    
    # Mostrar resumen de extracción
    success_count = sum(1 for t in enriched_topics if t.get('full_content', {}).get('success', False))
    logger.info(f"Extracción completa: {success_count}/{len(enriched_topics)} artículos extraídos con éxito")
    
    # Limpiar datos para guardar (eliminar información redundante)
    for topic in enriched_topics:
        if 'original_result' in topic:
            del topic['original_result']
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Guardar en la carpeta principal para compatibilidad con el flujo actual
    output_file = os.path.join(output_dir, f"topics_full_{timestamp}.json")
    
    # También guardar en la subcarpeta con timestamp
    output_file_timestamped = os.path.join(output_dir_with_timestamp, f"topics_full_{timestamp}.json")
    
    result_data = {
        'timestamp': datetime.now().isoformat(),
        'topics': enriched_topics
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    with open(output_file_timestamped, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Resultados completos guardados en: {output_file}")
    logger.info(f"Copia de resultados guardada en: {output_file_timestamped}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Proceso completado en {duration:.2f} segundos")
    
    # Devolver los temas para el siguiente nodo
    return enriched_topics

# Si se ejecuta como script principal
if __name__ == "__main__":
    # Configurar directorio de salida - usar ruta absoluta directa
    base_dir = os.path.abspath(os.getcwd())
    output_dir = os.path.join(base_dir,"llmpagina", "ava_seo", "output", "seo_json")
    
    
    
    # Imprimir la ruta para verificación
    logger.info(f"Directorio de salida configurado: {output_dir}")
    
    # Ejecutar el nodo
    logger.info("Ejecutando seo_node.py como script independiente")
    topics = run_news_trigger_node(output_dir)
    logger.info(f"Proceso completado con {len(topics)} temas generados") 