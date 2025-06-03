#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
content_writer_node.py - Nodo para redacción de artículos SEO

Este script actúa como un nodo independiente que:
1. Lee los temas extraídos por el nodo anterior (seo_node)
2. Genera un artículo integrado optimizado para SEO usando la API de Groq
3. Permite al LLM total libertad creativa en estructura y contenido
4. Guarda el resultado como un archivo JSON sin restricciones predefinidas

Puede ejecutarse como un script independiente o importarse como módulo.
"""

import os
import json
import logging
import requests
from datetime import datetime
import random
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("content_writer_node")

# ==== CONFIGURACIÓN ====
INPUT_DIR = os.path.join("llmpagina", "ava_seo", "output", "seo_json")
OUTPUT_DIR = os.path.join("llmpagina", "ava_seo", "output", "articulos")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"  # Modelo LLaMA 3 más potente en Groq

# ==== FUNCIONES DE PROCESAMIENTO ====
def load_latest_topics(input_dir=INPUT_DIR, specific_file=None):
    """Carga el archivo JSON más reciente de temas extraídos o un archivo específico si se proporciona"""
    try:
        # Si se proporciona un archivo específico, intentar cargarlo primero
        if specific_file and os.path.exists(specific_file):
            logger.info(f"Cargando temas desde archivo específico: {specific_file}")
            with open(specific_file, 'r', encoding='utf-8') as f:
                topics_data = json.load(f)
            return topics_data
            
        # Si no hay archivo específico o no existe, buscar en el directorio de entrada
        # Asegurar que la ruta sea absoluta
        input_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), input_dir)
        
        # Intentar también la ruta directa si la anterior no funciona
        if not os.path.exists(input_path) or not os.path.isdir(input_path):
            # Intentar con la ruta directa
            if os.path.exists(input_dir) and os.path.isdir(input_dir):
                input_path = input_dir
                logger.info(f"Usando ruta directa para el directorio de entrada: {input_path}")
            else:
                # Intentar con la nueva ruta de seo_json
                seo_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "llmpagina/ava_seo/output/seo_json")
                if os.path.exists(seo_json_path) and os.path.isdir(seo_json_path):
                    input_path = seo_json_path
                    logger.info(f"Usando ruta de seo_json para el directorio de entrada: {input_path}")
                else:
                    # Intentar con la ruta absoluta desde el directorio de trabajo
                    base_dir = os.path.abspath(os.getcwd())
                    seo_json_path_alt = os.path.join(base_dir, "llmpagina", "ava_seo", "output", "seo_json")
                    if os.path.exists(seo_json_path_alt) and os.path.isdir(seo_json_path_alt):
                        input_path = seo_json_path_alt
                        logger.info(f"Usando ruta absoluta para el directorio de entrada: {input_path}")
                    else:
                        logger.error(f"No se pudo encontrar el directorio de entrada: {input_path} ni {input_dir} ni {seo_json_path} ni {seo_json_path_alt}")
                        return None
        
        # Listar archivos JSON de temas
        json_files = [f for f in os.listdir(input_path) if f.startswith('topics_full_') and f.endswith('.json')]
        
        if not json_files:
            logger.error(f"No se encontraron archivos de temas en {input_path}")
            return None
        
        # Ordenar por fecha (más reciente primero)
        latest_file = sorted(json_files, reverse=True)[0]
        file_path = os.path.join(input_path, latest_file)
        
        logger.info(f"Cargando temas desde: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            topics_data = json.load(f)
            
        return topics_data
    except Exception as e:
        logger.error(f"Error cargando temas: {str(e)}")
        return None

def categorize_topics(topics):
    """Agrupa los temas por categoría para integrarlos en el prompt"""
    categorized = {}
    
    for topic in topics:
        category = topic.get('category', 'otros')
        if category in categorized:
            categorized[category].append(topic)
        else:
            categorized[category] = [topic]
    
    return categorized

def prepare_prompt_from_topics(topics_data, valid_topics):
    """Prepara un prompt más conciso para el modelo, evitando excesiva longitud"""
    
    # Determinar la temática principal basada en los temas disponibles
    categorized = categorize_topics(valid_topics)
    categories_count = {cat: len(topics) for cat, topics in categorized.items()}
    main_theme = max(categories_count.items(), key=lambda x: x[1])[0] if categories_count else "inteligencia artificial"
    
    # Limitar el número de temas para evitar prompts demasiado largos
    max_topics = 3
    if len(valid_topics) > max_topics:
        logger.info(f"Limitando a {max_topics} temas de los {len(valid_topics)} disponibles para evitar prompts demasiado largos")
        # Ordenar por relevancia (usando la longitud del contenido como proxy)
        sorted_topics = sorted(
            valid_topics, 
            key=lambda x: len(x.get('full_content', {}).get('content', '')), 
            reverse=True
        )
        selected_topics = sorted_topics[:max_topics]
    else:
        selected_topics = valid_topics
    
    # Extraer información relevante pero limitada de los temas
    all_content = []
    all_sources = []
    all_keywords = set()
    
    for topic in selected_topics:
        # Extraer título y resumen (limitado)
        title = topic.get('title', '')
        summary = topic.get('summary', '')
        if len(summary) > 300:
            summary = summary[:300] + "..."
        
        # Extraer palabras clave
        keywords = topic.get('keywords', [])[:5]  # Limitar a 5 palabras clave
        all_keywords.update(keywords)
        
        # Extraer contenido resumido
        full_content = topic.get('full_content', {})
        content_text = ""
        if full_content.get('success', False) and full_content.get('content'):
            content_text = full_content['content']
            # Limitar longitud del contenido
            if len(content_text) > 500:
                content_text = content_text[:500] + "..."
        
        # Extraer fuentes (limitadas)
        sources = topic.get('sources', [])[:2]  # Limitar a 2 fuentes
        all_sources.extend(sources)
        
        # Añadir información resumida a la lista
        topic_info = f"TEMA: {title}\n\nRESUMEN: {summary}\n\n"
        if keywords:
            topic_info += f"PALABRAS CLAVE: {', '.join(keywords)}\n\n"
        if content_text:
            topic_info += f"CONTENIDO RESUMIDO: {content_text}\n\n"
        if sources:
            topic_info += f"FUENTES: {', '.join(sources)}\n\n"
        
        all_content.append(topic_info)
    
    # Limitar el número de palabras clave
    all_keywords = list(all_keywords)[:10]
    
    # Crear separadores para evitar problemas con f-strings
    content_separator = "\n\n"
    line_separator = "=" * 30
    
    # Base del prompt simplificada
    prompt = f"""Escribe un artículo breve en formato de blog de noticias en ESPAÑOL sobre {main_theme}.

INFORMACIÓN DISPONIBLE (RESUMIDA):

{line_separator}
{content_separator.join(all_content)}
{line_separator}

INSTRUCCIONES:
1. Escribe un artículo en formato de BLOG DE NOTICIAS en ESPAÑOL de aproximadamente 1000 palabras.
2. Utiliza la información proporcionada de las noticias extraídas, nombres , fechas ,sucesos,relevantes,etc.
3. Estructura el artículo con un titular principal, introducción y secciones con subtítulos.
4. Usa formato markdown con ## para los subtítulos.
5. siempre menciona las fuentes cuando sea relevante.

FORMATO DE SALIDA:
Responde con un objeto JSON con esta estructura:
{{
  "title": "Título del artículo en ESPAÑOL",
  "meta_description": "Descripción breve para SEO en ESPAÑOL (máximo 160 caracteres)",
  "keywords": ["palabra1", "palabra2", "etc"],
  "content": "Aquí va el contenido del artículo en ESPAÑOL con subtítulos en markdown",
  "references": ["url1", "url2", "etc"]
}}

IMPORTANTE: El artículo debe estar en ESPAÑOL y centrarse en las noticias proporcionadas.
"""
    
    return prompt

def generate_article_with_groq(prompt, model=GROQ_MODEL):
    """Genera un artículo usando la API de Groq con el modelo especificado"""
    logger.info(f"Generando artículo con Groq usando modelo {model}")
    
    if not GROQ_API_KEY:
        logger.error("No se encontró la clave API de Groq. Verifica tu archivo .env")
        raise ValueError("GROQ_API_KEY no está configurada")
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Verificar que el modelo existe en Groq
    valid_models = ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma-7b-it"]
    if model not in valid_models:
        logger.warning(f"El modelo {model} podría no ser válido en Groq. Usando llama3-8b-8192 como fallback.")
        model = "llama3-8b-8192"
    
    # Reducir el tamaño máximo de tokens para evitar errores de la API
    max_tokens = 2048  # Valor más conservador
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Eres un escritor de artículos de noticias en español. Escribe un artículo completo en ESPAÑOL en el campo 'content' del JSON. Utiliza un formato simple y conciso. Limita el contenido a 4500 palabras máximo."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # Reducir temperatura para mayor consistencia
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }
    
    try:
        # Imprimir información de depuración
        logger.info(f"Enviando solicitud a Groq con modelo: {model} y max_tokens: {max_tokens}")
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        # Verificar si hay error y mostrar detalles
        if response.status_code != 200:
            logger.error(f"Error en API Groq: {response.status_code} - {response.text}")
            
            # Intentar con configuración más simple si falla
            if response.status_code == 400:
                logger.info("Intentando con configuración simplificada...")
                
                # Simplificar aún más el prompt para evitar errores de JSON
                simple_prompt = "Escribe un breve artículo de noticias en español sobre las últimas novedades en inteligencia artificial y tecnología, basado en noticias recientes. Responde en formato JSON con los campos: title, meta_description, keywords, content y references."
                
                simple_payload = {
                    "model": "llama3-8b-8192",  # Usar modelo más básico
                    "messages": [
                        {"role": "system", "content": "Genera un JSON simple con los campos: title, meta_description, keywords (array), content (texto) y references (array)."},
                        {"role": "user", "content": simple_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1500,
                    "response_format": {"type": "json_object"}
                }
                
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=simple_payload
                )
                
                # Si sigue fallando, intentar sin formato JSON forzado
                if response.status_code != 200:
                    logger.info("Intentando sin formato JSON forzado...")
                    simple_payload.pop("response_format", None)
                    
                    response = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=simple_payload
                    )
        
        response.raise_for_status()
        result = response.json()
        
        article_content = result['choices'][0]['message']['content']
        logger.info(f"Artículo generado correctamente ({len(article_content)} caracteres)")
        
        # Intentar parsear el JSON para validar
        try:
            # Si el contenido no es JSON válido (puede ser texto plano en el fallback)
            if not article_content.strip().startswith("{"):
                # Crear estructura JSON manualmente
                article_json = {
                    "title": "Avances en Inteligencia Artificial",
                    "meta_description": "Análisis de las últimas tendencias en inteligencia artificial y su impacto",
                    "keywords": ["inteligencia artificial", "innovación", "tecnología"],
                    "content": article_content,  # Usar el contenido generado como texto
                    "references": []
                }
            else:
                # Intentar parsear como JSON
                article_json = json.loads(article_content)
            
            # Verificar que el campo content no esté vacío
            if not article_json.get('content') or len(article_json.get('content', '')) < 100:
                logger.warning("El campo 'content' está vacío o es muy corto. Usando contenido alternativo.")
                
                # Si tenemos el contenido como texto pero no en el campo correcto
                if len(article_content) > 100:
                    article_json["content"] = article_content
            
            return article_json
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON generado: {e}")
            logger.info("Contenido recibido: " + article_content[:500] + "...")
            
            # Crear un JSON válido manualmente
            return {
                "title": "Últimas Noticias en Inteligencia Artificial",
                "meta_description": "Un resumen de las noticias más recientes en el campo de la inteligencia artificial",
                "keywords": ["noticias IA", "inteligencia artificial", "avances tecnológicos", "innovación"],
                "content": article_content,  # Usar el contenido bruto como artículo
                "references": [],
                "error": str(e)
            }
    
    except Exception as e:
        logger.error(f"Error generando artículo con Groq: {str(e)}")
        
        # Crear contenido de respaldo en caso de error
        logger.info("Generando contenido de respaldo debido al error...")
        backup_content = "# Últimas Noticias en Inteligencia Artificial\n\n"
        
        for topic in valid_topics:
            title = topic.get('title', '')
            backup_content += f"\n## {title}\n\n"
            
            summary = topic.get('summary', '')
            if summary:
                backup_content += f"{summary}\n\n"
            
            full_content = topic.get('full_content', {})
            if full_content.get('success', False) and full_content.get('content'):
                content_text = full_content['content']
                # Limitar longitud del contenido para evitar problemas
                if len(content_text) > 500:
                    content_text = content_text[:500] + "..."
                backup_content += f"{content_text}\n\n"
            
            # Añadir fuentes si están disponibles
            sources = topic.get('sources', [])
            if sources:
                backup_content += f"**Fuentes:** {', '.join(sources)}\n\n"
        
        return {
            "title": "Últimas Noticias en Inteligencia Artificial",
            "meta_description": "Un resumen de las noticias más recientes en el campo de la inteligencia artificial",
            "keywords": ["noticias IA", "inteligencia artificial", "avances tecnológicos", "innovación"],
            "content": backup_content,
            "references": [],
            "error": str(e)
        }

# ==== FUNCIÓN PRINCIPAL DEL NODO ====
def run_content_writer_node(output_dir=OUTPUT_DIR, topics_file=None):
    """Función principal del nodo que ejecuta todo el proceso"""
    start_time = datetime.now()
    logger.info(f"Iniciando content_writer_node: {start_time}")
    
    # Crear directorio de salida si no existe
    # Usar ruta absoluta directa
    base_dir = os.path.abspath(os.getcwd())
    if output_dir == OUTPUT_DIR:
        # Si se usa el valor por defecto, usar la ruta absoluta
        output_path = os.path.join(base_dir, OUTPUT_DIR)
    else:
        # Si se proporciona una ruta personalizada, usarla directamente
        output_path = output_dir
    
    # Asegurar que el directorio existe
    os.makedirs(output_path, exist_ok=True)
    
    # Imprimir la ruta para verificación
    logger.info(f"Directorio de salida configurado: {output_path}")
    
    try:
        # PASO 1: Cargar temas extraídos
        topics_data = load_latest_topics(specific_file=topics_file)
        
        if not topics_data or 'topics' not in topics_data:
            logger.error("No se pudieron cargar los temas o el formato no es válido")
            return False
        
        # Filtrar temas con contenido extraído correctamente
        valid_topics = [t for t in topics_data['topics'] if t.get('full_content', {}).get('success', False)]
        
        if not valid_topics:
            logger.warning("No hay temas válidos con contenido extraído")
            return False
            
        logger.info(f"Cargados {len(valid_topics)} temas válidos para generar contenido")
        
        # PASO 2: Preparar prompt y generar artículo con Groq
        prompt = prepare_prompt_from_topics(topics_data, valid_topics)
        
        try:
            article_data = generate_article_with_groq(prompt)
            
            # Verificar si hay contenido
            if not article_data.get('content') or len(article_data.get('content', '')) < 100:
                logger.warning("El artículo generado no tiene contenido o es muy corto. Usando contenido de respaldo.")
                
                # Crear contenido de respaldo combinando la información de los temas
                backup_content = "# Últimas Noticias en Inteligencia Artificial\n\n"
                
                for topic in valid_topics:
                    title = topic.get('title', '')
                    backup_content += f"\n## {title}\n\n"
                    
                    summary = topic.get('summary', '')
                    if summary:
                        backup_content += f"{summary}\n\n"
                    
                    full_content = topic.get('full_content', {})
                    if full_content.get('success', False) and full_content.get('content'):
                        content_text = full_content['content']
                        backup_content += f"{content_text}\n\n"
                    
                    # Añadir fuentes si están disponibles
                    sources = topic.get('sources', [])
                    if sources:
                        backup_content += f"**Fuentes:** {', '.join(sources)}\n\n"
                
                # Usar el contenido de respaldo
                article_data['content'] = backup_content
            
            # PASO 3: Guardar el resultado como JSON
            # Crear nombre de archivo basado en el título o timestamp
            if "title" in article_data:
                filename_base = article_data["title"].lower()
                filename_base = ''.join(c if c.isalnum() else '_' for c in filename_base)
                filename_base = filename_base[:50]  # Limitar longitud
            else:
                filename_base = f"articulo_ia_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Añadir metadatos adicionales
            article_data["generated_at"] = datetime.now().isoformat()
            article_data["source_topics_count"] = len(valid_topics)
            article_data["source_topics"] = [t.get('title', '') for t in valid_topics]
            article_data["model_used"] = GROQ_MODEL
            
            # Guardar JSON
            json_filename = f"{filename_base}_{datetime.now().strftime('%Y%m%d')}.json"
            json_path = os.path.join(output_path, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Artículo integrado generado y guardado como JSON: {json_filename}")
            
            # Crear resultado para retornar
            result = {
                "title": article_data.get("title", "Artículo generado"),
                "json_file": json_filename,
                "word_count": len(article_data.get("content", "").split()) if "content" in article_data else 0
            }
            
            # Estadísticas finales
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Proceso completado en {duration:.2f} segundos")
            
            return result
        
        except Exception as e:
            logger.exception(f"Error generando artículo integrado: {e}")
            return False
    
    except Exception as e:
        logger.exception(f"Error generando artículo integrado: {e}")
        return False

# Si se ejecuta como script principal
if __name__ == "__main__":
    try:
        # Usar rutas absolutas
        base_dir = os.path.abspath(os.getcwd())
        output_dir = os.path.join(base_dir, "llmpagina", "ava_seo", "output", "articulos")
        
        # Asegurar que el directorio existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Ejecutar el nodo con la ruta absoluta
        logger.info(f"Ejecutando content_writer_node con salida en: {output_dir}")
        result = run_content_writer_node(output_dir=output_dir)
        
        if result:
            print(f"\n--- ARTÍCULO INTEGRADO GENERADO ---")
            print(f"Título: {result['title']}")
            print(f"Archivo JSON: {result['json_file']}")
            print(f"Palabras aproximadas: {result['word_count']}")
        else:
            print("\nNo se pudo generar el artículo. Consulta el log para más detalles.")
    
    except Exception as e:
        logger.exception("Error ejecutando el nodo")
        print(f"Error: {str(e)}")