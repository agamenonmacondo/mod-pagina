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

# ==== CONFIGURACIÓN ====
INPUT_DIR = os.path.join("ava_seo", "output")  # Directorio donde están los artículos generados
OUTPUT_DIR = os.path.join("ava_seo", "output", "images")  # Directorio para guardar las imágenes generadas
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"  # Modelo para analizar el artículo y crear prompts
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")  # API Key para Together.ai

# ... existing code ... 