from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS, cross_origin
import os
import json
from datetime import datetime
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Permitir CORS para todas las rutas

# Configuración
IMAGE_FOLDER = Path("generated_images")
IMAGE_FOLDER.mkdir(exist_ok=True)

@app.route('/api/images', methods=['GET'])
@cross_origin()
def get_images():
    """Endpoint para obtener todas las imágenes generadas"""
    try:
        images = []
        
        # Buscar todas las imágenes en la carpeta
        for image_file in IMAGE_FOLDER.glob("*.png"):
            images.append({
                "id": image_file.stem,
                "filename": image_file.name,
                "url": f"http://localhost:5001/images/{image_file.name}",
                "created_at": datetime.fromtimestamp(image_file.stat().st_mtime).isoformat()
            })
        
        # Ordenar por fecha de creación (más recientes primero)
        images.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            "status": "success",
            "total_images": len(images),
            "images": images
        })
        
    except Exception as e:
        logger.error(f"Error getting images: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/images/<filename>')
@cross_origin()
def serve_image(filename):
    """Servir imágenes estáticas"""
    try:
        return send_from_directory(IMAGE_FOLDER, filename)
    except FileNotFoundError:
        return jsonify({
            "status": "error",
            "message": "Image not found"
        }), 404

@app.route('/api/images/<image_id>', methods=['GET'])
@cross_origin()
def get_image_details(image_id):
    """Obtener detalles de una imagen específica"""
    try:
        image_path = IMAGE_FOLDER / f"{image_id}.png"
        
        if not image_path.exists():
            return jsonify({
                "status": "error",
                "message": "Image not found"
            }), 404
        
        return jsonify({
            "status": "success",
            "image": {
                "id": image_id,
                "filename": image_path.name,
                "url": f"http://localhost:5001/images/{image_path.name}",
                "created_at": datetime.fromtimestamp(image_path.stat().st_mtime).isoformat(),
                "size": image_path.stat().st_size
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting image details: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "AVA Image Server",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    logger.info("Starting AVA Image Server...")
    logger.info(f"Images folder: {IMAGE_FOLDER.absolute()}")
    logger.info(f"Server will run on http://localhost:5001")
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True
    )