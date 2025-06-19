import os
import json
import logging
import requests
from dotenv import load_dotenv
from PIL import Image
from datetime import datetime
import io
from groq import Groq
import base64

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vision_node")
class VisionNode:
    """Clase para el nodo de visión que interactúa con la API de Groq."""
    def __init__(self):
        self.node_name = "vision_node"  
    NODE_NAME = "vision_node"  # Nombre del nodo
# Configuración de la API
GROQ_API_KEY = os.getenv("GROQ_API_KEY","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"
)
GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"  # Modelo LLaMA Maverick

# Load .env file explicitly from the workspace root
workspace_root = "C:/Users/h/Downloads/ava_bot"
env_file_path = os.path.join(workspace_root, ".env")

if os.path.exists(env_file_path):
    logger.info(f"Loading .env file from: {env_file_path}")
    with open(env_file_path, 'r') as f:
        for line in f:
            if line.startswith('GROQ_API_KEY='):
                GROQ_API_KEY = line.strip().split('=')[1]
                break
    logger.info(f"GROQ_API_KEY read directly from file: {GROQ_API_KEY}")
    os.environ['GROQ_API_KEY'] = GROQ_API_KEY
    logger.info(f"GROQ_API_KEY after setting os.environ: {GROQ_API_KEY}")
    if GROQ_API_KEY == "TU_API_KEY":
        logger.error("GROQ_API_KEY is the placeholder value. Please update your .env file.")
        # Handle the case where the API key is the placeholder
        raise ValueError("GROQ_API_KEY is not configured correctly.")
else:
    logger.error(f"No .env file found at {env_file_path}")
    # Handle the case where .env file is missing

# Validate GROQ_API_KEY
if GROQ_API_KEY is None or GROQ_API_KEY == "TU_API_KEY":
    logger.error("Invalid GROQ_API_KEY. Please check your .env file.")
    # You can raise an exception or handle this case as needed


def load_image(image_path):
    """Carga una imagen desde la ruta especificada."""
    try:
        image = Image.open(image_path)
        logger.info(f"Imagen cargada: {image_path}")
        return image
    except Exception as e:
        logger.error(f"Error al cargar la imagen: {str(e)}")
        return None


def analyze_image(image):
    """Envía la imagen a la API de Groq para análisis."""
    logger.info("Analizando imagen con Groq...")
    
    if not GROQ_API_KEY:
        logger.error("No se encontró la clave API de Groq. Verifica tu archivo .env")
        raise ValueError("GROQ_API_KEY no está configurada")
    
    client = Groq(api_key=GROQ_API_KEY)
    
    # Convertir la imagen a un archivo temporal
    image_byte_arr = io.BytesIO()
    image.save(image_byte_arr, format='PNG')
    image_byte_arr.seek(0)  # Reiniciar el puntero al inicio del archivo

    # Crear el payload para la API
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "¿Qué hay en esta imagen?"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + base64.b64encode(image_byte_arr.getvalue()).decode()
                        }
                    }
                ]
            }
        ],
        "temperature": 1,
        "max_completion_tokens": 1024,
        "top_p": 1,
        "stream": False,
        "stop": None,
    }
    
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=payload["messages"],
            temperature=payload["temperature"],
            max_completion_tokens=payload["max_completion_tokens"],
            top_p=payload["top_p"],
            stream=payload["stream"],
            stop=payload["stop"]
        )
        logger.info("Análisis de imagen completado.")
        return completion.choices[0].message
    except Exception as e:
        logger.error(f"Error analizando la imagen: {str(e)}")
        return None


def get_information(query, image=None):
    """Realiza una llamada a la API de Groq para obtener información específica según la consulta."""
    logger.info(f"Obteniendo información para la consulta: {query}")
    
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        messages = [{
            "role": "user",
            "content": query
        }]
        
        # Si se proporciona una imagen, agregar al payload
        if image is not None:
            # Convertir la imagen a un archivo temporal
            image_byte_arr = io.BytesIO()
            image.save(image_byte_arr, format='PNG')
            image_byte_arr.seek(0)  # Reiniciar el puntero al inicio del archivo
            
            # Agregar la imagen al payload
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + base64.b64encode(image_byte_arr.getvalue()).decode()
                        }
                    }
                ]
            })
        
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=1,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,
            stop=None
        )
        logger.info("Información obtenida correctamente.")
        return completion.choices[0].message
    except Exception as e:
        logger.error(f"Error obteniendo información: {str(e)}")
        return None


def run_vision_node(image_path, user_query):
    """Función principal que ejecuta el nodo de visión."""
    start_time = datetime.now()
    logger.info(f"Iniciando vision_node: {start_time}")
    
    # Cargar la imagen
    image = load_image(image_path)
    if image is None:
        return False
    
    # Analizar la imagen
    analysis_result = analyze_image(image)
    if analysis_result is None:
        return False
    
    # Obtener información específica
    information_result = get_information(user_query, image)
    if information_result is None:
        return False
    
    # Mostrar resultados
    logger.info(f"Resultados del análisis: {analysis_result}")
    logger.info(f"Información obtenida: {information_result}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Proceso completado en {duration:.2f} segundos")
    
    return {
        "analysis": analysis_result,
        "information": information_result
    }

# Si se ejecuta como script principal
if __name__ == "__main__":
    image_path = r"D:\GIBI\gibi _edit\lora gibi\image\gibi_32.06\gibi_fer_100\img_01 (3).jpeg"  # Ruta de la imagen para análisis
    user_query = input("Ingrese su consulta: ")  # Consulta del usuario para información específica
    
    result = run_vision_node(image_path, user_query)
    if result:
        print("Análisis e información obtenidos con éxito.")
    else:
        print("Error en el procesamiento del nodo de visión.")