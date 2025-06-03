#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scheduler.py - Programador para el flujo de trabajo SEO

Este script programa la ejecución automática del flujo de trabajo SEO
cada 24 horas para mantener las noticias constantemente actualizadas.
"""

import os
import sys
import time
import logging
import schedule
import subprocess
from datetime import datetime, timedelta
import traceback

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("scheduler")

# Ruta al script de flujo de trabajo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKFLOW_SCRIPT = os.path.join(BASE_DIR, "seo_workflow.py")

def run_workflow():
    """Ejecuta el script de flujo de trabajo"""
    logger.info("Ejecutando flujo de trabajo programado...")
    
    try:
        # Ejecutar el script como un proceso separado
        result = subprocess.run(
            [sys.executable, WORKFLOW_SCRIPT],
            capture_output=True,
            text=True,
            check=False
        )
        
        # Registrar la salida
        logger.info(f"Código de salida: {result.returncode}")
        
        if result.stdout:
            logger.info(f"Salida estándar: {result.stdout}")
            
        if result.stderr:
            logger.warning(f"Error estándar: {result.stderr}")
            
        if result.returncode == 0:
            logger.info("Flujo de trabajo completado correctamente")
        else:
            logger.error(f"El flujo de trabajo falló con código {result.returncode}")
            
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error ejecutando flujo de trabajo: {e}")
        logger.error(traceback.format_exc())
        return False

def schedule_jobs():
    """Programa la ejecución periódica del flujo de trabajo"""
    # Ejecutar cada día a la 1:00 AM
    schedule.every().day.at("01:00").do(run_workflow)
    logger.info("Programado flujo de trabajo para ejecutarse cada día a la 1:00 AM")

def run_pending_jobs():
    """Ejecuta trabajos pendientes en un bucle infinito"""
    while True:
        # Ejecutar trabajos pendientes
        schedule.run_pending()
        
        # Esperar antes de la siguiente verificación (5 minutos)
        time.sleep(300)
        
        # Log periódico para verificar que el programador sigue funcionando
        if datetime.now().minute % 60 == 0:  # Log cada hora
            next_run = None
            for job in schedule.jobs:
                if job.next_run:
                    if not next_run or job.next_run < next_run:
                        next_run = job.next_run
                        
            if next_run:
                time_until = next_run - datetime.now()
                logger.info(f"Programador activo, próxima ejecución en {time_until}")
            else:
                logger.warning("Programador activo, pero no hay trabajos programados")

def run_now():
    """Ejecuta el flujo de trabajo inmediatamente"""
    logger.info("Ejecutando flujo de trabajo inmediatamente...")
    return run_workflow()

if __name__ == "__main__":
    logger.info("Iniciando programador de flujo de trabajo SEO cada 24 horas...")
    
    # Verificar argumentos de línea de comandos
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # Ejecutar ahora si se especifica --now
        success = run_now()
        sys.exit(0 if success else 1)
    else:
        # Configurar programación
        schedule_jobs()
        
        # Ejecutar flujo de trabajo inmediatamente al iniciar
        run_workflow()
        
        # Ejecutar bucle principal
        try:
            run_pending_jobs()
        except KeyboardInterrupt:
            logger.info("Programador detenido por el usuario")
            sys.exit(0) 