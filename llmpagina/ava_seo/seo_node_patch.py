#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
seo_node_patch.py - Parche para el nodo SEO que reduce el tamaño de los informes

Este script modifica el comportamiento del seo_node para:
1. Limitar el tamaño del contenido extraído (máximo 1500 palabras)
2. Reducir el número de temas de 6 a 3
3. Limitar el número de imágenes a 1 por artículo
4. Crear una carpeta de salida con timestamp para evitar mezclar resultados
"""

# Aplicar este parche copiando el contenido a ava_seo/nodes/seo_nodes/seo_node
# o ejecutando: cp seo_node_patch.py ava_seo/nodes/seo_nodes/seo_node

# Modificaciones a realizar:

# 1. Reducir MAX_TOPICS_TO_RETURN de 6 a 3
MAX_TOPICS_TO_RETURN = 3  # Reducido de 6 a 3

# 2. Modificar extract_full_article para limitar el contenido
def extract_full_article_patched(url, headers, max_retries, timeout):
    """Versión modificada de extract_full_article que limita el tamaño del contenido"""
    import requests
    import re
    import time
    import logging
    from bs4 import BeautifulSoup
    
    logger = logging.getLogger("news_trigger_node")
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

# 3. Modificar run_news_trigger_node para crear una subcarpeta con timestamp
def run_news_trigger_node_patched(output_dir="output"):
    """Versión modificada de run_news_trigger_node que crea una subcarpeta con timestamp"""
    import os
    import json
    import logging
    from datetime import datetime
    
    logger = logging.getLogger("news_trigger_node")
    start_time = datetime.now()
    logger.info(f"Iniciando news_trigger_node: {start_time}")
    
    # Obtener acceso a las funciones y variables globales
    global all_results, SEARCH_TOPICS, MAX_RESULTS_PER_TOPIC, filter_results, generate_topics
    global extract_full_content_for_topics, search_with_fallback
    
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

# Instrucciones para aplicar el parche:
"""
Para aplicar este parche al seo_node, sigue estos pasos:

1. Abre el archivo seo_node original en ava_seo/nodes/seo_nodes/seo_node
2. Busca la constante MAX_TOPICS_TO_RETURN y cámbiala de 6 a 3
3. Reemplaza la función extract_full_article por la versión extract_full_article_patched
4. Reemplaza la función run_news_trigger_node por la versión run_news_trigger_node_patched
5. Guarda el archivo y ejecuta el workflow

Alternativamente, puedes copiar este archivo directamente:
cp seo_node_patch.py ava_seo/nodes/seo_nodes/seo_node
""" 