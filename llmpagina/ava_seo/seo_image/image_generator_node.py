#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
image_generator_node.py - Nodo para generación de imágenes artísticas para artículos SEO

Este script actúa como un nodo independiente que:
1. Lee el contenido de los artículos generados por el nodo de contenido
2. Utiliza Groq para analizar el artículo y crear un prompt creativo para la generación de imágenes
3. Genera una imagen artística usando el modelo FLUX.1-schnell-Free de Black Forest Labs
4. Guarda la imagen junto con metadatos relevantes

Puede ejecutarse como un script independiente o importarse como módulo.
"""

import os
import json
import logging
import requests
import base64
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import re
from PIL import Image, ImageDraw
import hashlib
import io

# Intentar importar la biblioteca Together
try:
    import together
except ImportError:
    together = None
    # Intentar instalar la biblioteca si no está disponible
    try:
        import subprocess
        import sys
        logger = logging.getLogger("image_generator_node")
        logger.info("Biblioteca Together no encontrada. Intentando instalar...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "together"])
        import together
        logger.info("Biblioteca Together instalada correctamente")
    except Exception as e:
        logger.error(f"No se pudo instalar la biblioteca Together: {e}")
        together = None

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("image_generator_node")

# ==== CONFIGURACIÓN ====
INPUT_DIR = os.path.join("llmpagina", "ava_seo", "output", "articulos")  # Directorio donde están los artículos generados
OUTPUT_DIR = os.path.join("llmpagina", "ava_seo", "output", "static")  # Directorio para guardar las imágenes generadas
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"  # Modelo para analizar el artículo y crear prompts
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")  # API Key para Together.ai

# ==== FUNCIONES DE PROCESAMIENTO ====
def load_latest_article(input_dir=INPUT_DIR, specific_file=None):
    """Carga el archivo JSON más reciente de artículos generados o un archivo específico si se proporciona"""
    try:
        # Si se proporciona un archivo específico, intentar cargarlo primero
        if specific_file and os.path.exists(specific_file):
            logger.info(f"Cargando artículo desde archivo específico: {specific_file}")
            
            with open(specific_file, 'r', encoding='utf-8') as f:
                article_data = json.load(f)
                
            return {
                "article_data": article_data,
                "file_name": os.path.basename(specific_file),
                "file_path": specific_file
            }
            
        # Si no hay archivo específico o no existe, buscar en el directorio de entrada
        # Usar ruta absoluta directa
        base_dir = os.path.abspath(os.getcwd())
        input_path = os.path.join(base_dir, input_dir)
        
        # Verificar si el directorio existe
        if not os.path.exists(input_path) or not os.path.isdir(input_path):
            logger.warning(f"El directorio de entrada no existe: {input_path}")
            
            # Intentar con la ruta de articulos
            articulos_path = os.path.join(base_dir, "llmpagina", "ava_seo", "output", "articulos")
            if os.path.exists(articulos_path) and os.path.isdir(articulos_path):
                input_path = articulos_path
                logger.info(f"Usando ruta de articulos para el directorio de entrada: {input_path}")
            else:
                # Intentar con la ruta absoluta desde el directorio de trabajo
                articulos_path_alt = os.path.join(base_dir, "ava_seo", "output", "articulos")
                if os.path.exists(articulos_path_alt) and os.path.isdir(articulos_path_alt):
                    input_path = articulos_path_alt
                    logger.info(f"Usando ruta alternativa para el directorio de entrada: {input_path}")
                else:
                    logger.error(f"No se encontró un directorio de entrada válido")
                    return None
        
        # Buscar archivos JSON en el directorio
        json_files = [f for f in os.listdir(input_path) if f.endswith('.json')]
        
        if not json_files:
            logger.warning(f"No se encontraron archivos JSON en {input_path}")
            return None
        
        # Ordenar por fecha de modificación (más reciente primero)
        json_files.sort(key=lambda x: os.path.getmtime(os.path.join(input_path, x)), reverse=True)
        latest_file = os.path.join(input_path, json_files[0])
        
        logger.info(f"Cargando el artículo más reciente: {latest_file}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            article_data = json.load(f)
        
        return {
            "article_data": article_data,
            "file_name": json_files[0],
            "file_path": latest_file
        }
    
    except Exception as e:
        logger.error(f"Error cargando el artículo: {str(e)}")
        return None

def create_image_prompt(article_data, groq_model=GROQ_MODEL):
    """Genera un prompt creativo para la imagen basado en el contenido del artículo"""
    logger.info(f"Generando prompt para imagen usando Groq con modelo {groq_model}")
    
    if not GROQ_API_KEY:
        logger.error("No se encontró la clave API de Groq. Verifica tu archivo .env")
        raise ValueError("GROQ_API_KEY no está configurada")
    
    # Extraer información relevante del artículo
    title = article_data.get("title", "")
    content = article_data.get("content", "")
    keywords = article_data.get("keywords", [])
    
    # Limitar el contenido para no sobrecargar el prompt
    content_preview = content[:3000] if len(content) > 3000 else content
    
    # Crear prompt para Groq
    prompt = f"""
Eres un artista conceptual y director creativo. Necesito que crees un prompt detallado para generar una imagen artística 
que acompañe un artículo sobre inteligencia artificial. La imagen debe ser conceptual, reflexiva y visualmente impactante.

INFORMACIÓN DEL ARTÍCULO:
Título: {title}
Palabras clave: {', '.join(keywords)}
Contenido: {content_preview}

TAREA:
Crea un prompt detallado para generar una imagen conceptual que:
1. Capture la esencia del artículo
2. Sea visualmente atractiva y artística
3. Tenga un estilo profesional , comercial y moderno
4. Incluya elementos simbólicos relacionados con la IA
5. Tenga una paleta de colores coherente y atractiva

El prompt debe ser detallado y específico, incluyendo:
- Elementos visuales principales
- Estilo artístico profesional, publicitario y comercial
- Paleta de colores
- Composición
- Estilo fotográfico
-procura que sean close up detallados, para que la calidad de la imagen sea mejor
- Elementos simbólicos

FORMATO DE RESPUESTA:
Proporciona solo el prompt para la imagen, sin introducción ni explicación. El prompt debe estar en inglés para mejorar los resultados
con el modelo de generación de imágenes. Debe tener entre 50 y 200 palabras.
"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": "Eres un artista grafico publicista especializado en crear prompts para generar imágenes llamativas,comerciales, promocionales profesionales."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.89,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        
        image_prompt = result['choices'][0]['message']['content'].strip()
        logger.info(f"Prompt para imagen generado: {image_prompt[:100]}...")
        
        return image_prompt
    
    except Exception as e:
        logger.error(f"Error generando prompt para imagen: {str(e)}")
        
        # Prompt de respaldo en caso de error
        fallback_prompt = f"A conceptual artistic illustration about artificial intelligence and technology, inspired by the article '{title}'. Futuristic, elegant, with symbolic elements representing AI and innovation. Deep blues and purples with accent lighting."
        logger.info(f"Usando prompt de respaldo: {fallback_prompt}")
        
        return fallback_prompt

def generate_image_with_flux(image_prompt):
    """Genera una imagen usando el modelo FLUX.1-schnell-Free de Black Forest Labs"""
    logger.info("Generando imagen con FLUX.1-schnell-Free")
    
    if not TOGETHER_API_KEY:
        logger.error("No se encontró la clave API de Together. Verifica tu archivo .env")
        raise ValueError("TOGETHER_API_KEY no está configurada")
    
    try:
        # Intentar usar la biblioteca oficial de Together primero
        try:
            logger.info("Usando biblioteca oficial de Together para generar imagen...")
            
            # Configurar la API key
            together.api_key = TOGETHER_API_KEY
            
            # Crear cliente
            client = together.Together()
            
            # Generar imagen
            response = client.images.generate(
                prompt=image_prompt,
                model="black-forest-labs/FLUX.1-schnell-Free",
                width=1024,
                height=768,
                steps=4,
                n=1,
                response_format="b64_json"
            )
            
            # Extraer la imagen
            if hasattr(response, 'data') and len(response.data) > 0:
                # Si la respuesta contiene datos en base64
                if hasattr(response.data[0], 'b64_json'):
                    image_data = base64.b64decode(response.data[0].b64_json)
                    logger.info(f"Imagen generada correctamente con biblioteca Together ({len(image_data)} bytes)")
                    
                    return {
                        "image_data": image_data,
                        "prompt": image_prompt,
                        "model": "FLUX.1-schnell-Free",
                        "success": True
                    }
                # Si la respuesta contiene una URL
                elif hasattr(response.data[0], 'url'):
                    image_url = response.data[0].url
                    logger.info(f"Descargando imagen desde URL: {image_url}")
                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    
                    image_data = img_response.content
                    logger.info(f"Imagen descargada correctamente ({len(image_data)} bytes)")
                    
                    return {
                        "image_data": image_data,
                        "prompt": image_prompt,
                        "model": "FLUX.1-schnell-Free",
                        "success": True
                    }
            
            logger.error("Formato de respuesta inesperado de la API de Together")
            logger.debug(f"Respuesta recibida: {response}")
            raise Exception("Formato de respuesta inesperado")
            
        except ImportError:
            logger.warning("Biblioteca Together no disponible, usando requests directamente")
            # Continuar con el método de requests si la biblioteca no está disponible
        except Exception as e:
            logger.error(f"Error usando biblioteca Together: {str(e)}")
            logger.info("Intentando con método alternativo usando requests...")
    
        # Método alternativo usando requests directamente
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOGETHER_API_KEY}"
        }
        
        payload = {
            "model": "black-forest-labs/FLUX.1-schnell-Free",
            "prompt": image_prompt,
            "negative_prompt": "low quality, blurry, distorted, deformed, disfigured, bad anatomy, watermark, signature, text",
            "width": 1024,
            "height": 768,
            "steps": 4,
            "n": 1,
            "response_format": "b64_json"
        }
        
        logger.info("Enviando solicitud a la API de Together.ai usando requests...")
        response = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers=headers,
            json=payload,
            verify=True
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Verificar si la respuesta contiene la imagen
        if "data" in result and len(result["data"]) > 0:
            if "b64_json" in result["data"][0]:
                # Decodificar la imagen de base64
                image_data = base64.b64decode(result["data"][0]["b64_json"])
                logger.info(f"Imagen generada correctamente con requests ({len(image_data)} bytes)")
                
                return {
                    "image_data": image_data,
                    "prompt": image_prompt,
                    "model": "FLUX.1-schnell-Free",
                    "success": True
                }
            elif "url" in result["data"][0]:
                # La API devuelve una URL
                image_url = result["data"][0]["url"]
                logger.info(f"Descargando imagen desde URL: {image_url}")
                img_response = requests.get(image_url)
                img_response.raise_for_status()
                
                image_data = img_response.content
                logger.info(f"Imagen descargada correctamente ({len(image_data)} bytes)")
                
                return {
                    "image_data": image_data,
                    "prompt": image_prompt,
                    "model": "FLUX.1-schnell-Free",
                    "success": True
                }
        
        logger.error("La respuesta no contiene imágenes en el formato esperado")
        logger.debug(f"Respuesta recibida: {result}")
        return {"success": False, "error": "No images in response"}
    
    except Exception as e:
        logger.error(f"Error generando imagen: {str(e)}")
        
        # Si todo falla, intentar con el generador de respaldo
        try:
            logger.info("Intentando con generador de respaldo...")
            fallback_image_data = generate_fallback_image(image_prompt)
            
            if fallback_image_data:
                return {
                    "image_data": fallback_image_data,
                    "prompt": image_prompt,
                    "model": "fallback_model",
                    "success": True
                }
        except Exception as fallback_error:
            logger.error(f"Error en generación de respaldo: {str(fallback_error)}")
        
        return {"success": False, "error": str(e)}

def generate_fallback_image(prompt):
    """Genera una imagen de respaldo usando un servicio alternativo o una imagen local"""
    try:
        # Crear una imagen más atractiva basada en el prompt
        logger.info("Generando imagen de respaldo artística...")
        
        # Importar las librerías necesarias
        from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
        import hashlib
        import random
        import math
        
        # Generar colores basados en el hash del prompt
        hash_obj = hashlib.md5(prompt.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Crear paleta de colores armónica
        hue = int(hash_hex[0:2], 16) / 255.0
        saturation = 0.6 + (int(hash_hex[2:4], 16) / 255.0) * 0.4
        lightness_base = 0.4 + (int(hash_hex[4:6], 16) / 255.0) * 0.2
        
        # Función para convertir HSL a RGB
        def hsl_to_rgb(h, s, l):
            if s == 0:
                r = g = b = l
            else:
                def hue_to_rgb(p, q, t):
                    if t < 0: t += 1
                    if t > 1: t -= 1
                    if t < 1/6: return p + (q - p) * 6 * t
                    if t < 1/2: return q
                    if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                    return p
                
                q = l * (1 + s) if l < 0.5 else l + s - l * s
                p = 2 * l - q
                r = hue_to_rgb(p, q, h + 1/3)
                g = hue_to_rgb(p, q, h)
                b = hue_to_rgb(p, q, h - 1/3)
            
            return (int(r * 255), int(g * 255), int(b * 255))
        
        # Generar paleta de colores
        color1 = hsl_to_rgb(hue, saturation, lightness_base)
        color2 = hsl_to_rgb((hue + 0.5) % 1, saturation, lightness_base)
        color3 = hsl_to_rgb((hue + 0.2) % 1, saturation, lightness_base * 1.2)
        
        # Crear imagen base
        img_size = 1024
        img = Image.new('RGB', (img_size, img_size), color1)
        draw = ImageDraw.Draw(img)
        
        # Determinar estilo basado en el hash
        style = int(hash_hex[6:8], 16) % 5
        
        if style == 0:
            # Estilo abstracto con círculos
            for i in range(50):
                x = random.randint(0, img_size)
                y = random.randint(0, img_size)
                radius = random.randint(20, 200)
                color = color2 if i % 2 == 0 else color3
                draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
            
            # Aplicar filtro de desenfoque
            img = img.filter(ImageFilter.GaussianBlur(radius=5))
            
        elif style == 1:
            # Estilo de gradiente con líneas
            for i in range(0, img_size, 4):
                # Calcular color interpolado
                t = i / img_size
                r = int(color1[0] * (1-t) + color2[0] * t)
                g = int(color1[1] * (1-t) + color2[1] * t)
                b = int(color1[2] * (1-t) + color2[2] * t)
                
                draw.line([(0, i), (img_size, i)], fill=(r, g, b), width=4)
            
            # Añadir líneas diagonales
            for i in range(20):
                start_x = random.randint(0, img_size)
                end_x = random.randint(0, img_size)
                draw.line([(start_x, 0), (end_x, img_size)], fill=color3, width=3)
            
        elif style == 2:
            # Estilo de ondas
            for y in range(img_size):
                for x in range(img_size):
                    # Crear patrón de ondas
                    val = math.sin(x/50) * math.cos(y/50) * 127 + 128
                    r = int((color1[0] + color2[0] + val) / 3)
                    g = int((color1[1] + color2[1] + val) / 3)
                    b = int((color1[2] + color2[2] + val) / 3)
                    
                    img.putpixel((x, y), (r, g, b))
            
        elif style == 3:
            # Estilo de mosaico
            tile_size = 32
            for y in range(0, img_size, tile_size):
                for x in range(0, img_size, tile_size):
                    # Alternar colores
                    if (x//tile_size + y//tile_size) % 2 == 0:
                        color = color2
                    else:
                        color = color3
                    
                    draw.rectangle([x, y, x+tile_size, y+tile_size], fill=color)
            
            # Añadir círculos superpuestos
            for i in range(10):
                x = random.randint(0, img_size)
                y = random.randint(0, img_size)
                radius = random.randint(50, 200)
                # Color semitransparente
                draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color1)
            
        else:
            # Estilo de fractales simples
            def draw_fractal(x, y, size, depth):
                if depth <= 0 or size < 5:
                    return
                
                color = hsl_to_rgb((hue + depth/5) % 1, saturation, lightness_base)
                draw.rectangle([x, y, x+size, y+size], outline=color)
                
                new_size = size // 2
                draw_fractal(x, y, new_size, depth-1)
                draw_fractal(x+new_size, y, new_size, depth-1)
                draw_fractal(x, y+new_size, new_size, depth-1)
                draw_fractal(x+new_size, y+new_size, new_size, depth-1)
            
            # Dibujar fractal
            draw_fractal(0, 0, img_size, 5)
        
        # Añadir un efecto de viñeta
        vignette = Image.new('L', (img_size, img_size), 0)
        vignette_draw = ImageDraw.Draw(vignette)
        
        # Dibujar un gradiente circular
        for i in range(img_size//2, -1, -1):
            opacity = int(255 * (i / (img_size/2)))
            vignette_draw.ellipse(
                (img_size//2 - i, img_size//2 - i, img_size//2 + i, img_size//2 + i),
                fill=opacity
            )
        
        # Aplicar viñeta
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.8)
        img.putalpha(vignette)
        
        # Añadir texto artístico (título del artículo)
        try:
            # Intentar cargar una fuente
            font_size = 40
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Extraer título del prompt (primeras 30 palabras)
            title_text = " ".join(prompt.split()[:10])
            if len(title_text) > 50:
                title_text = title_text[:47] + "..."
            
            # Añadir texto
            text_position = (img_size//2, img_size - 100)
            text_color = (255, 255, 255, 200)  # Blanco semitransparente
            
            # Añadir sombra para legibilidad
            draw.text((text_position[0]+2, text_position[1]+2), title_text, fill=(0, 0, 0, 150), font=font, anchor="ms")
            draw.text(text_position, title_text, fill=text_color, font=font, anchor="ms")
        except Exception as text_error:
            logger.warning(f"No se pudo añadir texto a la imagen: {text_error}")
        
        # Convertir a formato PNG
        img_byte_arr = io.BytesIO()
        img = img.convert('RGB')  # Convertir a RGB si tiene canal alpha
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        return img_byte_arr
    
    except Exception as e:
        logger.error(f"Error generando imagen de respaldo: {str(e)}")
        
        # Si todo falla, crear una imagen muy simple
        try:
            from PIL import Image
            img = Image.new('RGB', (512, 512), color=(100, 100, 100))
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()
        except:
            return None

def save_image(image_result, article_info, output_dir=OUTPUT_DIR):
    """Guarda la imagen generada y sus metadatos"""
    try:
        # Usar la ruta absoluta del directorio de trabajo
        base_dir = os.path.abspath(os.getcwd())
        output_path = os.path.join(base_dir, output_dir)
       
        
        # Crear un nombre de archivo basado en el título del artículo
        article_title = article_info["article_data"].get("title", "")
        base_filename = re.sub(r'[^\w\s-]', '', article_title).strip().lower()
        base_filename = re.sub(r'[-\s]+', '_', base_filename)
        
        if not base_filename:
            base_filename = f"ai_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Guardar la imagen
        image_filename = f"{base_filename}.png"
        image_path = os.path.join(output_path, image_filename)
        
        with open(image_path, 'wb') as f:
            f.write(image_result["image_data"])
        
        logger.info(f"Imagen guardada en: {image_path}")
        
        # Guardar metadatos
        metadata = {
            "image_filename": image_filename,
            "article_title": article_info["article_data"].get("title", ""),
            "article_file": article_info["file_name"],
            "prompt": image_result["prompt"],
            "model": image_result["model"],
            "generated_at": datetime.now().isoformat(),
            "keywords": article_info["article_data"].get("keywords", [])
        }
        
        metadata_filename = f"{base_filename}_metadata.json"
        metadata_path = os.path.join(output_path, metadata_filename)
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Metadatos guardados en: {metadata_path}")
        
        return {
            "image_path": image_path,
            "metadata_path": metadata_path
        }
    
    except Exception as e:
        logger.error(f"Error guardando imagen: {str(e)}")
        return None

# ==== FUNCIÓN PRINCIPAL DEL NODO ====
def run_image_generator_node(output_dir=OUTPUT_DIR, article_file=None):
    """Función principal del nodo que ejecuta todo el proceso"""
    start_time = datetime.now()
    logger.info(f"Iniciando image_generator_node: {start_time}")
    
    # Crear directorio de salida si no existe
    base_dir = os.path.abspath(os.getcwd())
    output_path = os.path.join(base_dir, output_dir)
    os.makedirs(output_path, exist_ok=True)
    
    logger.info(f"Directorio de salida configurado: {output_path}")
    
    try:
        # PASO 1: Cargar el artículo más reciente
        article_info = load_latest_article(specific_file=article_file)
        
        if not article_info:
            logger.error("No se pudo cargar el artículo")
            return False
            
        logger.info(f"Artículo cargado: {article_info['file_name']}")
        
        # PASO 2: Crear prompt para la imagen
        image_prompt = create_image_prompt(article_info["article_data"])
        
        if not image_prompt:
            logger.error("No se pudo generar el prompt para la imagen")
            return False
        
        # PASO 3: Generar imagen con FLUX
        image_result = generate_image_with_flux(image_prompt)
        
        if not image_result["success"]:
            logger.error(f"Error generando imagen: {image_result.get('error', 'Error desconocido')}")
            return False
        
        # PASO 4: Guardar imagen y metadatos
        save_result = save_image(image_result, article_info, output_dir)
        
        if not save_result:
            logger.error("Error guardando la imagen")
            return False
        
        # Estadísticas finales
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Proceso completado en {duration:.2f} segundos")
        
        return {
            "article_title": article_info["article_data"].get("title", ""),
            "image_path": save_result["image_path"],
            "metadata_path": save_result["metadata_path"]
        }
    
    except Exception as e:
        logger.exception(f"Error generando imagen: {e}")
        return False

# Si se ejecuta como script principal
if __name__ == "__main__":
    try:
        # Usar ruta absoluta directa
        base_dir = os.path.abspath(os.getcwd())
        output_dir = os.path.join(base_dir, "llmpagina", "ava_seo", "output", "static")
        
        # Asegurar que el directorio existe
        os.makedirs(output_dir, exist_ok=True)
        
        # Ejecutar el nodo con la ruta absoluta
        logger.info(f"Ejecutando image_generator_node con salida en: {output_dir}")
        result = run_image_generator_node(output_dir=output_dir)
        
        if result:
            print(f"\n--- IMAGEN GENERADA CORRECTAMENTE ---")
            print(f"Artículo: {result['article_title']}")
            print(f"Imagen: {result['image_path']}")
            print(f"Metadatos: {result['metadata_path']}")
        else:
            print("\nNo se pudo generar la imagen. Consulta el log para más detalles.")
    
    except Exception as e:
        logger.exception("Error ejecutando el nodo")
        print(f"Error: {str(e)}") 