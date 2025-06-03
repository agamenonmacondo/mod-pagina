#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
seo_workflow.py - Flujo de trabajo unificado para el sistema SEO implementado como LangGraph

Este script implementa un flujo de trabajo como grafo dirigido donde:
1. seo_node.py: Extrae noticias sobre IA de fuentes web usando Tavily
2. content_writer_node: Genera artículos basados en las noticias
3. image_generator_node: Crea imágenes para acompañar los artículos

El flujo de trabajo es secuencial, donde cada nodo pasa su salida al siguiente.
Los resultados finales (imagen y artículo) se preparan para mostrar en login.html.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
import traceback
from pathlib import Path
import importlib.util
import shutil
from typing import Dict, List, Any, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("seo_workflow.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("seo_workflow")

# Directorios y rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Ruta a llmpagina/ava_seo
OUTPUT_DIR = os.path.join(BASE_DIR,"output")
SEO_JSON_DIR = os.path.join(OUTPUT_DIR,"seo_json")
ARTICULOS_DIR = os.path.join(OUTPUT_DIR,"articulos")
STATIC_DIR = os.path.join(OUTPUT_DIR,"static")
RESULTS_DIR = os.path.join(BASE_DIR,"results")  # Carpeta para resultados procesados



# Archivo para almacenar los resultados más recientes
RESULTS_FILE = os.path.join(RESULTS_DIR, "latest_results.json")
LATEST_ARTICLES_FILE = os.path.join(RESULTS_DIR, "latest_articles.json")  # Nuevo archivo para los 3 últimos artículos

# ===== DEFINICIÓN DE LA ESTRUCTURA DEL GRAFO =====

class LangGraphNode:
    """Clase base para los nodos del grafo de flujo de trabajo"""
    
    def __init__(self, name: str):
        self.name = name
        self.input_data = None
        self.output_data = None
        
    def process(self, input_data: Optional[Dict] = None) -> Dict:
        """Procesa la entrada y produce una salida"""
        self.input_data = input_data
        self.output_data = self._execute()
        return self.output_data
    
    def _execute(self) -> Dict:
        """Implementación específica del nodo"""
        raise NotImplementedError("Cada nodo debe implementar su lógica de ejecución")

class LangGraph:
    """Clase que representa el grafo de flujo de trabajo"""
    
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.results = {}
    
    def add_node(self, node: LangGraphNode) -> None:
        """Añade un nodo al grafo"""
        self.nodes[node.name] = node
        self.edges[node.name] = []
        logger.info(f"Nodo '{node.name}' añadido al grafo")
    
    def add_edge(self, from_node: str, to_node: str) -> None:
        """Añade una conexión dirigida entre dos nodos"""
        if from_node in self.nodes and to_node in self.nodes:
            self.edges[from_node].append(to_node)
            logger.info(f"Conexión añadida: {from_node} -> {to_node}")
        else:
            logger.error(f"No se puede añadir conexión: nodo no encontrado")
    
    def run(self, start_node: str) -> Dict:
        """Ejecuta el grafo comenzando por el nodo especificado"""
        if start_node not in self.nodes:
            logger.error(f"Nodo inicial '{start_node}' no encontrado en el grafo")
            return {}
        
        logger.info(f"Iniciando ejecución del grafo desde el nodo '{start_node}'")
        current_node = start_node
        input_data = None
        
        # Registrar tiempo de inicio
        start_time = time.time()
        
        while current_node:
            logger.info(f"Ejecutando nodo: {current_node}")
            
            try:
                # Ejecutar el nodo actual
                node_instance = self.nodes[current_node]
                output = node_instance.process(input_data)
                
                # Guardar el resultado
                self.results[current_node] = output
                
                # Preparar para el siguiente nodo
                next_nodes = self.edges[current_node]
                if next_nodes:
                    current_node = next_nodes[0]  # Tomar el primer nodo conectado
                    input_data = output  # La salida de este nodo es la entrada del siguiente
                else:
                    # No hay más nodos conectados, terminar
                    current_node = None
            except Exception as e:
                logger.error(f"Error ejecutando nodo '{current_node}': {str(e)}")
                logger.error(traceback.format_exc())
                break
        
        # Calcular tiempo total
        execution_time = time.time() - start_time
        logger.info(f"Ejecución del grafo completada en {execution_time:.2f} segundos")
        
        # Añadir tiempo de ejecución a los resultados
        self.results["execution_time"] = execution_time
        
        return self.results

# ===== IMPLEMENTACIÓN DE NODOS ESPECÍFICOS =====

def import_module_from_file(file_path, module_name):
    """Importa un módulo Python desde un archivo"""
    try:
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            logger.error(f"El archivo no existe: {file_path}")
            
            # Intentar con extensión .py si no tiene extensión
            if not file_path.endswith('.py'):
                py_file_path = f"{file_path}.py"
                if os.path.exists(py_file_path):
                    logger.info(f"Usando archivo con extensión .py: {py_file_path}")
                    file_path = py_file_path
                else:
                    logger.error(f"Tampoco existe el archivo con extensión .py: {py_file_path}")
                    return None
            else:
                return None
                
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            logger.error(f"No se pudo cargar el módulo desde {file_path}")
            return None
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Error importando {module_name} desde {file_path}: {e}")
        logger.error(traceback.format_exc())
        return None

class SeoNode(LangGraphNode):
    """Nodo para la extracción de noticias y temas relevantes usando Tavily"""
    
    def __init__(self):
        super().__init__("seo_node.py")
    
    def _execute(self) -> Dict:
        """Ejecuta el nodo de búsqueda de noticias"""
        logger.info("Ejecutando nodo de búsqueda de noticias (seo_node.py)...")
        
        try:
            # Usar directamente el archivo seo_node.py que ya existe
            seo_node_py = os.path.join(BASE_DIR, "nodes", "seo_nodes", "seo_node.py")
            
            # Verificar si el archivo existe
            if not os.path.exists(seo_node_py):
                logger.error(f"El archivo seo_node.py no existe en {seo_node_py}")
                raise FileNotFoundError(f"El archivo seo_node.py no existe en {seo_node_py}")
            
            # Importar y ejecutar el nodo de búsqueda
            seo_module = import_module_from_file(seo_node_py, "seo_node")
            
            if not seo_module:
                logger.error("No se pudo importar el módulo seo_node")
                raise ImportError("No se pudo importar el módulo seo_node")
                
            # Verificar si el módulo tiene la función run_news_trigger_node
            if hasattr(seo_module, "run_news_trigger_node"):
                # Ejecutar el nodo y obtener los resultados
                topics = seo_module.run_news_trigger_node(SEO_JSON_DIR)
                
                # Guardar los resultados en un formato adecuado para el siguiente nodo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                topics_file = os.path.join(SEO_JSON_DIR, f"topics_full_{timestamp}.json")
                
                with open(topics_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "topics": topics
                    }, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Nodo de búsqueda completado. Resultados guardados en {topics_file}")
                
                return {
                    "topics": topics,
                    "topics_file": topics_file,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error("El módulo seo_node no tiene la función run_news_trigger_node")
                raise AttributeError("El módulo seo_node no tiene la función run_news_trigger_node")
        except Exception as e:
            logger.error(f"Error ejecutando nodo de búsqueda: {e}")
            logger.error(traceback.format_exc())
            raise

class ContentWriterNode(LangGraphNode):
    """Nodo para la generación de contenido basado en los temas"""
    
    def __init__(self):
        super().__init__("content_writer_node")
    
    def _execute(self) -> Dict:
        """Ejecuta el nodo de generación de contenido"""
        logger.info("Ejecutando nodo de generación de contenido (content_writer_node)...")
        
        if not self.input_data or "topics" not in self.input_data:
            logger.error("No se recibieron temas válidos del nodo SEO")
            raise ValueError("Datos de entrada inválidos para el nodo de contenido")
        
        try:
            # Importar y ejecutar el nodo de contenido
            content_node_path = os.path.join(BASE_DIR, "content_node", "content_writer_node.py")
            content_module = import_module_from_file(content_node_path, "content_writer_node")
            
            if not content_module:
                logger.error("No se pudo importar el módulo content_writer_node")
                raise ImportError("No se pudo importar el módulo content_writer_node")
            
            # Modificar la variable INPUT_DIR en el módulo para que apunte a la ruta correcta
            if hasattr(content_module, "INPUT_DIR"):
                # Guardar el valor original para restaurarlo después
                original_input_dir = content_module.INPUT_DIR
                # Establecer la ruta correcta (directamente al directorio seo_json)
                content_module.INPUT_DIR = SEO_JSON_DIR
                logger.info(f"Ajustada ruta de entrada en content_writer_node: {content_module.INPUT_DIR}")
                
                # Establecer la ruta de salida correcta (directamente al directorio articulos)
                if hasattr(content_module, "OUTPUT_DIR"):
                    original_output_dir = content_module.OUTPUT_DIR
                    content_module.OUTPUT_DIR = ARTICULOS_DIR
                    logger.info(f"Ajustada ruta de salida en content_writer_node: {content_module.OUTPUT_DIR}")
                
            # Verificar si el módulo tiene la función run_content_writer_node
            if hasattr(content_module, "run_content_writer_node"):
                # Pasar explícitamente el archivo de temas generado por el nodo anterior
                topics_file = self.input_data.get("topics_file")
                
                # Verificar que el archivo existe
                if topics_file and os.path.exists(topics_file):
                    logger.info(f"Usando archivo de temas: {topics_file}")
                    
                    # Ejecutar el nodo con los temas del nodo anterior, pasando el archivo específico y la ruta de salida
                    result = content_module.run_content_writer_node(output_dir=ARTICULOS_DIR, topics_file=topics_file)
                else:
                    logger.warning(f"Archivo de temas no encontrado: {topics_file}")
                    # Buscar el archivo más reciente en el directorio SEO_JSON_DIR
                    json_files = [f for f in os.listdir(SEO_JSON_DIR) if f.startswith('topics_full_') and f.endswith('.json')]
                    if json_files:
                        latest_file = sorted(json_files, reverse=True)[0]
                        latest_file_path = os.path.join(SEO_JSON_DIR, latest_file)
                        logger.info(f"Usando el archivo de temas más reciente: {latest_file_path}")
                        result = content_module.run_content_writer_node(output_dir=ARTICULOS_DIR, topics_file=latest_file_path)
                    else:
                        logger.error("No se encontraron archivos de temas en el directorio de salida")
                        # Intentar ejecutar sin archivo específico pero con la ruta de salida correcta
                        result = content_module.run_content_writer_node(output_dir=ARTICULOS_DIR)
                
                # Restaurar el valor original de INPUT_DIR si lo modificamos
                if hasattr(content_module, "INPUT_DIR") and 'original_input_dir' in locals():
                    content_module.INPUT_DIR = original_input_dir
                
                # Restaurar el valor original de OUTPUT_DIR si lo modificamos
                if hasattr(content_module, "OUTPUT_DIR") and 'original_output_dir' in locals():
                    content_module.OUTPUT_DIR = original_output_dir
                
                if not result:
                    logger.error("El nodo de contenido no produjo resultados")
                    raise RuntimeError("El nodo de contenido no produjo resultados")
                
                # Cargar el artículo generado para pasarlo al siguiente nodo
                json_file = result.get("json_file")
                if json_file:
                    article_path = os.path.join(ARTICULOS_DIR, json_file)
                    try:
                        with open(article_path, 'r', encoding='utf-8') as f:
                            article_data = json.load(f)
                            
                        # Añadir información al resultado
                        result["article_data"] = article_data
                        result["article_path"] = article_path
                        
                        logger.info(f"Nodo de contenido completado. Artículo: {result.get('title')}")
                        
                        # Combinar con los datos de entrada para mantener contexto
                        output = {
                            "seo_result": self.input_data,
                            "content_result": result
                        }
                        
                        return output
                    except Exception as e:
                        logger.error(f"Error leyendo archivo de artículo: {e}")
                        raise
                else:
                    logger.warning("No se encontró el archivo JSON del artículo en el resultado")
                    
                    # Devolver lo que tenemos aunque falte el archivo
                    output = {
                        "seo_result": self.input_data,
                        "content_result": result
                    }
                    
                    return output
            else:
                logger.error("El módulo content_writer_node no tiene la función run_content_writer_node")
                raise AttributeError("El módulo content_writer_node no tiene la función run_content_writer_node")
        except Exception as e:
            logger.error(f"Error ejecutando nodo de contenido: {e}")
            logger.error(traceback.format_exc())
            raise

class ImageGeneratorNode(LangGraphNode):
    """Nodo para la generación de imágenes basadas en el artículo"""
    
    def __init__(self):
        super().__init__("image_generator_node")
    
    def _execute(self) -> Dict:
        """Ejecuta el nodo de generación de imágenes"""
        logger.info("Ejecutando nodo de generación de imágenes (image_generator_node)...")
        
        if not self.input_data or "content_result" not in self.input_data:
            logger.error("No se recibieron datos de artículo válidos del nodo de contenido")
            raise ValueError("Datos de entrada inválidos para el nodo de imágenes")
        
        try:
            # Importar y ejecutar el nodo de imágenes
            image_node_path = os.path.join(BASE_DIR, "seo_image/image_generator_node.py")
            image_module = import_module_from_file(image_node_path, "image_generator_node")
            
            if not image_module:
                logger.error("No se pudo importar el módulo image_generator_node")
                raise ImportError("No se pudo importar el módulo image_generator_node")
            
            # Ajustar la ruta de entrada en el módulo de imágenes si es necesario
            if hasattr(image_module, "INPUT_DIR"):
                original_input_dir = image_module.INPUT_DIR
                image_module.INPUT_DIR = ARTICULOS_DIR
                logger.info(f"Ajustada ruta de entrada en image_generator_node: {image_module.INPUT_DIR}")
            
            # Ajustar la ruta de salida en el módulo de imágenes si es necesario
            if hasattr(image_module, "OUTPUT_DIR"):
                original_output_dir = image_module.OUTPUT_DIR
                image_module.OUTPUT_DIR = STATIC_DIR
                logger.info(f"Ajustada ruta de salida en image_generator_node: {image_module.OUTPUT_DIR}")
            
            # Verificar si el módulo tiene la función run_image_generator_node
            if hasattr(image_module, "run_image_generator_node"):
                # Obtener la ruta del archivo del artículo generado por el nodo anterior
                content_result = self.input_data.get("content_result", {})
                article_path = content_result.get("article_path")
                
                # Verificar que el archivo existe
                if article_path and os.path.exists(article_path):
                    logger.info(f"Usando archivo de artículo: {article_path}")
                    # Ejecutar el nodo con el artículo del nodo anterior y la ruta de salida correcta
                    result = image_module.run_image_generator_node(output_dir=STATIC_DIR, article_file=article_path)
                else:
                    logger.warning(f"Archivo de artículo no encontrado: {article_path}")
                    # Intentar ejecutar sin archivo específico pero con la ruta de salida correcta
                    result = image_module.run_image_generator_node(output_dir=STATIC_DIR)
                
                # Restaurar el valor original de INPUT_DIR si lo modificamos
                if hasattr(image_module, "INPUT_DIR") and 'original_input_dir' in locals():
                    image_module.INPUT_DIR = original_input_dir
                
                # Restaurar el valor original de OUTPUT_DIR si lo modificamos
                if hasattr(image_module, "OUTPUT_DIR") and 'original_output_dir' in locals():
                    image_module.OUTPUT_DIR = original_output_dir
                
                if not result:
                    logger.error("El nodo de imágenes no produjo resultados")
                    # No lanzamos excepción aquí para permitir continuar el flujo
                    result = {"error": "No se pudo generar la imagen"}
                    
                logger.info(f"Nodo de imágenes completado. Imagen: {result.get('image_path', 'No generada')}")
                
                # Combinar con los datos de entrada para mantener contexto completo
                output = {
                    "seo_result": self.input_data.get("seo_result"),
                    "content_result": self.input_data.get("content_result"),
                    "image_result": result
                }
                
                return output
            else:
                logger.error("El módulo image_generator_node no tiene la función run_image_generator_node")
                raise AttributeError("El módulo image_generator_node no tiene la función run_image_generator_node")
        except Exception as e:
            logger.error(f"Error ejecutando nodo de imágenes: {e}")
            logger.error(traceback.format_exc())
            
            # Devolver lo que tenemos aunque haya error
            return {
                "seo_result": self.input_data.get("seo_result"),
                "content_result": self.input_data.get("content_result"),
                "image_result": {"error": str(e)}
            }

class ResultsFormatterNode(LangGraphNode):
    """Nodo para formatear los resultados para mostrar en login.html"""
    
    def __init__(self):
        super().__init__("results_formatter_node")
    
    def _execute(self) -> Dict:
        """Formatea los resultados para mostrar en login.html"""
        logger.info("Ejecutando nodo de formateo de resultados...")
        
        if not self.input_data:
            logger.error("No se recibieron datos de los nodos anteriores")
            raise ValueError("Datos de entrada inválidos para el nodo de formateo")
        
        try:
            # Extraer datos de los nodos anteriores
            seo_result = self.input_data.get("seo_result", {})
            content_result = self.input_data.get("content_result", {})
            image_result = self.input_data.get("image_result", {})
            
            # Preparar datos para guardar
            timestamp = datetime.now().isoformat()
            run_id = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # Extraer información relevante
            article_data = {}
            image_data = {}
            
            # Datos del artículo
            if content_result and isinstance(content_result, dict):
                if "article_data" in content_result:
                    article_data = content_result["article_data"]
                elif "json_file" in content_result:
                    article_json_file = content_result.get("json_file")
                    article_path = os.path.join(ARTICULOS_DIR, article_json_file)
                    logger.info(f"Procesando artículo desde: {article_path}")
                    try:
                        with open(article_path, 'r', encoding='utf-8') as f:
                            article_data = json.load(f)
                    except Exception as e:
                        logger.error(f"Error leyendo archivo de artículo: {e}")
                        article_data = {
                            'title': content_result.get("title", f"Avances en IA: Reporte {run_id}"),
                            'content': f"Este artículo presenta los últimos avances en inteligencia artificial. Generado automáticamente el {timestamp}.",
                            'keywords': ['inteligencia artificial', 'IA', 'tecnología', 'innovación']
                        }
            else:
                logger.warning(f"No se recibió un resultado válido del nodo de contenido")
                article_data = {
                    'title': f"Avances en IA: Reporte {run_id}",
                    'content': f"Este artículo presenta los últimos avances en inteligencia artificial. Generado automáticamente el {timestamp}.",
                    'keywords': ['inteligencia artificial', 'IA', 'avances', 'tecnología']
                }
            
            # Datos de la imagen
            if image_result and isinstance(image_result, dict) and "image_path" in image_result:
                image_path = image_result.get("image_path")
                logger.info(f"Procesando imagen desde: {image_path}")
                # Generar ruta web para la imagen
                static_image_path = self._copy_image_to_static(image_path)
                
                image_data = {
                    "original_path": image_path,
                    "web_path": f"/static/{os.path.basename(image_path)}",  # Ruta correcta para la web
                    "article_title": article_data.get('title', "Artículo sin título")
                }
            else:
                logger.warning(f"No se recibió un resultado válido del nodo de imágenes")
                # Usar una imagen predeterminada si no hay imagen
                default_image = os.path.join(STATIC_DIR, "default_image.png")
                if os.path.exists(default_image):
                    image_data = {
                        "original_path": default_image,
                        "web_path": f"/static/{os.path.basename(default_image)}",  # Ruta correcta para la web
                        "article_title": article_data.get('title', "Artículo sin título")
                    }
            
            # Crear objeto de resultados
            result = {
                "timestamp": timestamp,
                "article": article_data,
                "image": image_data,
                "run_id": run_id
            }
            
            # Ya no generamos archivos JSON aquí, eso lo hace app.py
            logger.info(f"Nodo de formateo completado. app.py se encargará de generar los archivos JSON.")
            
            # Devolver el resultado formateado junto con todos los datos del flujo
            output = {
                "seo_result": seo_result,
                "content_result": content_result,
                "image_result": image_result,
                "display_result": result
            }
            
            return output
        except Exception as e:
            logger.error(f"Error formateando resultados: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _copy_image_to_static(self, image_path):
        """Devuelve la ruta correcta para acceder a la imagen desde la web"""
        try:
            # Verificar si la imagen existe
            if not os.path.exists(image_path):
                logger.error(f"La imagen no existe en la ruta: {image_path}")
                return None
                
            # Extraer el nombre de archivo
            filename = os.path.basename(image_path)
            
            # Ruta para la web - usamos /static/ que es la ruta correcta para servir archivos estáticos
            web_path = f"/static/{filename}"
            logger.info(f"URL generada para la web: {web_path}")
            
            return web_path
            
        except Exception as e:
            logger.error(f"Error al generar URL de imagen: {str(e)}")
            return None

# ===== FUNCIÓN PRINCIPAL PARA EJECUTAR EL GRAFO =====

def run_workflow():
    """Inicia el flujo de trabajo como un grafo LangGraph"""
    start_time = datetime.now()
    logger.info("Iniciando flujo de trabajo SEO como grafo LangGraph...")
    
    try:
        # Crear directorio de resultados si no existe
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        # Crear objetos de grafo y nodos
        graph = LangGraph()
        
        # 1. Nodo de búsqueda de noticias
        seo_node_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                     "nodes", "seo_nodes", "seo_node.py")
        
        seo_module = import_module_from_file(seo_node_path, "seo_node")
        seo_node = SeoNode()  # Usar nuestro propio nodo SeoNode en lugar de NewsTriggerNode
        graph.add_node(seo_node)
        logger.info("Nodo 'seo_node.py' añadido al grafo")
        
        # 2. Nodo de generación de contenido
        content_writer_node = ContentWriterNode()
        graph.add_node(content_writer_node)
        logger.info("Nodo 'content_writer_node' añadido al grafo")
        
        # 3. Nodo de generación de imágenes
        image_generator_node = ImageGeneratorNode()
        graph.add_node(image_generator_node)
        logger.info("Nodo 'image_generator_node' añadido al grafo")
        
        # 4. Nodo de formateo de resultados
        results_formatter_node = ResultsFormatterNode()
        graph.add_node(results_formatter_node)
        logger.info("Nodo 'results_formatter_node' añadido al grafo")
        
        # Conectar nodos
        graph.add_edge("seo_node.py", "content_writer_node")
        logger.info("Conexión añadida: seo_node.py -> content_writer_node")
        
        graph.add_edge("content_writer_node", "image_generator_node")
        logger.info("Conexión añadida: content_writer_node -> image_generator_node")
        
        graph.add_edge("image_generator_node", "results_formatter_node")
        logger.info("Conexión añadida: image_generator_node -> results_formatter_node")
        
        # Ejecutar el grafo
        logger.info("Iniciando ejecución del grafo desde el nodo 'seo_node.py'")
        result = graph.run("seo_node.py")
        
        # Calcular tiempo de ejecución
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        logger.info(f"Ejecución del grafo completada en {execution_time:.2f} segundos")
        
        # Forzar actualización de latest_results.json y latest_articles.json
        try:
            # Verificar si existe el archivo de resultados
            if os.path.exists(RESULTS_FILE):
                # Cargar resultados
                with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                
                # Verificar rutas de imágenes
                modified = False
                for item in results:
                    if 'image' in item and 'original_path' in item['image']:
                        # Extraer nombre de archivo
                        filename = os.path.basename(item['image']['original_path'])
                        # Corregir web_path si es necesario
                        if not item['image'].get('web_path', '').startswith('/static/'):
                            item['image']['web_path'] = f"/static/{filename}"
                            modified = True
                            
                # Guardar cambios si hubo modificaciones
                if modified:
                    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(results, f, ensure_ascii=False, indent=2)
                    logger.info(f"Se actualizaron rutas de imágenes en {RESULTS_FILE}")
                
                # Actualizar también el archivo de los 3 últimos artículos
                latest_three = results[:3]
                with open(LATEST_ARTICLES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(latest_three, f, ensure_ascii=False, indent=2)
                logger.info(f"Se actualizaron los 3 últimos artículos en {LATEST_ARTICLES_FILE}")
        except Exception as e:
            logger.error(f"Error actualizando archivos de resultados: {e}")
        
        logger.info("Flujo de trabajo LangGraph completado")
        return result
    except Exception as e:
        logger.error(f"Error en el flujo de trabajo: {e}")
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    try:
        result = run_workflow()
        
        if result:
            print(f"\n--- FLUJO DE TRABAJO LANGGRAPH COMPLETADO ---")
            print(f"Tiempo de ejecución: {result.get('execution_time', 0):.2f} segundos")
            
            if "content_result" in result and result["content_result"]:
                print(f"Artículo generado: {result['content_result'].get('title', 'Sin título')}")
            
            if "image_result" in result and result["image_result"]:
                print(f"Imagen generada: {result['image_result'].get('image_path', 'N/A')}")
                
            print(f"Resultados preparados para mostrar en login.html")
            sys.exit(0)
        else:
            print(f"\n--- FLUJO DE TRABAJO LANGGRAPH FALLÓ ---")
            print("Consulta el archivo de log para más detalles.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error en el flujo de trabajo principal: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) 