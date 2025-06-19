#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
image_generator_node.py - Generador de imágenes artísticas con IA

Este script genera imágenes artísticas usando modelos de IA como FLUX.1-schnell-Free.
Puede funcionar con o sin texto de entrada, generando imágenes conceptuales.
"""

import os
import json
import logging
import requests
import base64
from datetime import datetime
from dotenv import load_dotenv
import re
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
import hashlib
import io
import argparse
from nodes.system_promt.system_promt import SystemPrompt

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("image_generator")

# Configuración de APIs
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
OUTPUT_DIR = os.path.join("output", "static")

class ImageGeneratorNode:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.together_api_key = os.getenv("TOGETHER_API_KEY")
        self.output_dir = os.path.join("output", "static")

    def process(self, state):
        """
        Procesa el estado y genera una imagen basada en el input del usuario.
        
        Args:
            state: El estado actual de la conversación
            
        Returns:
            str: El siguiente nodo o None para terminar
        """
        logger.info("Processing in ImageGeneratorNode...")
        
        # Establecer tarea activa si no existe
        if not state.is_in_task("image_task"):
            state.set_active_task("image_task", step="init")
        
        # Extraer el texto para generar la imagen del input del usuario
        prompt_text = state.input
        
        # Generar la imagen
        img_path = self.generate_image(prompt_text)
        
        # Preparar respuesta según el resultado
        if img_path:
            # Obtener ruta relativa para mostrar al usuario
            relative_path = os.path.relpath(img_path, os.getcwd())
            state.response = f"He generado una imagen basada en tu solicitud. La imagen está guardada en: {relative_path}"
        else:
            state.response = "Lo siento, no pude generar la imagen solicitada. Por favor intenta con otra descripción."
        
        # Limpiar tarea activa
        state.clear_active_task()
        
        # No hay siguiente nodo que procesar
        return None

    def generate_image(self, prompt_text=None):
        """Genera una imagen a partir de un texto descriptivo"""
        logger.info("Generando imagen...")
        
        # Paso 1: Generar prompt
        image_prompt = create_image_prompt(prompt_text)
        logger.info(f"Prompt generado: {image_prompt[:100]}...")
        
        # Paso 2: Generar imagen
        image_result = generate_image_with_flux(image_prompt)
        
        if not image_result["success"]:
            logger.warning("Usando generador de respaldo...")
            image_data = generate_fallback_image(image_prompt)
            if not image_data:
                logger.error("No se pudo generar la imagen")
                return None
        else:
            image_data = image_result["image_data"]
        
        # Paso 3: Guardar resultados
        img_path, meta_path = save_results(image_data, image_prompt, self.output_dir)
        
        if img_path and meta_path:
            logger.info(f"Imagen guardada en: {img_path}")
            logger.info(f"Metadatos guardados en: {meta_path}")
            return img_path
        else:
            logger.error("Error al guardar los resultados")
            return None 

def create_image_prompt(prompt_text=None):
    """Genera un prompt creativo para la imagen"""
    if not prompt_text:
        prompt_text = "Concepto abstracto futurista de tecnología e inteligencia artificial"    
    prompt = f"""
Eres un artista conceptual. Crea un prompt detallado para generar una imagen sobre:
{prompt_text}

El prompt debe incluir:
- Estilo profesional y comercial
- Elementos visuales principales
- Paleta de colores atractiva
- Composición equilibrada
- Detalles de close-up para mejor calidad

Respuesta solo con el prompt en inglés (50-200 palabras).
"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "Eres un artista especializado en crear prompts para imágenes comerciales."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    
    except Exception as e:
        logger.error(f"Error con Groq API: {str(e)}")
        return f"A futuristic, high-tech illustration about {prompt_text}. Professional style, vibrant colors, detailed close-up."

def generate_image_with_flux(image_prompt):
    """Genera imagen usando FLUX.1-schnell-Free"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOGETHER_API_KEY}"
    }
    
    payload = {
        "model": "black-forest-labs/FLUX.1-schnell-Free",
        "prompt": image_prompt,
        "width": 1024,
        "height": 768,
        "steps": 4,
        "response_format": "b64_json"
    }
    
    try:
        response = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("data") and data["data"][0].get("b64_json"):
            return {
                "image_data": base64.b64decode(data["data"][0]["b64_json"]),
                "success": True
            }
        return {"success": False, "error": "Invalid response format"}
    
    except Exception as e:
        logger.error(f"Error con Together API: {str(e)}")
        return {"success": False, "error": str(e)}

def generate_fallback_image(prompt):
    """Genera una imagen simple como respaldo"""
    try:
        img = Image.new('RGB', (1024, 768), color=(50, 50, 100))
        draw = ImageDraw.Draw(img)
        
        # Texto simple
        try:
            font = ImageFont.truetype("arial.ttf", 40) if os.name == 'nt' else ImageFont.load_default()
            draw.text((512, 384), prompt[:50], fill=(255,255,255), anchor="mm", font=font)
        except:
            pass
            
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        logger.error(f"Error generando imagen de respaldo: {str(e)}")
        return None

def save_results(image_data, prompt, output_dir):
    """Guarda la imagen y metadatos"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Guardar imagen
        img_path = os.path.join(output_dir, f"ai_image_{timestamp}.png")
        with open(img_path, 'wb') as f:
            f.write(image_data)
        
        # Guardar metadatos
        meta = {
            "prompt": prompt,
            "generated_at": datetime.now().isoformat(),
            "model": "FLUX.1-schnell-Free"
        }
        
        meta_path = os.path.join(output_dir, f"ai_image_{timestamp}_meta.json")
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)
            
        return img_path, meta_path
    
    except Exception as e:
        logger.error(f"Error guardando resultados: {str(e)}")
        return None, None

def main():
    parser = argparse.ArgumentParser(description='Generador de imágenes con IA')
    parser.add_argument('--prompt', '-p', help='Texto descriptivo para la imagen')
    parser.add_argument('--output', '-o', default=OUTPUT_DIR, help='Directorio de salida')
    args = parser.parse_args()
    
    logger.info("Iniciando generación de imagen...")
    
    # Paso 1: Generar prompt
    image_prompt = create_image_prompt(args.prompt)
    logger.info(f"Prompt generado: {image_prompt[:100]}...")
    
    # Paso 2: Generar imagen
    image_result = generate_image_with_flux(image_prompt)
    
    if not image_result["success"]:
        logger.warning("Usando generador de respaldo...")
        image_data = generate_fallback_image(image_prompt)
        if not image_data:
            logger.error("No se pudo generar la imagen")
            return
    else:
        image_data = image_result["image_data"]
    
    # Paso 3: Guardar resultados
    img_path, meta_path = save_results(image_data, image_prompt, args.output)
    
    if img_path and meta_path:
        logger.info(f"Imagen guardada en: {img_path}")
        logger.info(f"Metadatos guardados en: {meta_path}")
        print(f"\nImagen generada exitosamente:\n{img_path}")
    else:
        logger.error("Error al guardar los resultados")

if __name__ == "__main__":
    main()