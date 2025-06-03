from flask import Blueprint, request, jsonify
import logging

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

@api_bp.route('/test', methods=['GET'])
def api_test():
    """Endpoint de prueba de la API"""
    return jsonify({
        'status': 'success',
        'message': 'API funcionando correctamente',
        'endpoint': 'api_test'
    })

# ✅ COMENTAR O RENOMBRAR ESTA FUNCIÓN SI EXISTE
# Si hay una función chat_message aquí, es lo que está causando el conflicto

# OPCIÓN 1: Comentar completamente
"""
@api_bp.route('/chat', methods=['POST'])
def chat_message():  # ❌ ESTA CAUSA CONFLICTO CON chat_routes.py
    # Código comentado para evitar conflicto
    pass
"""

# OPCIÓN 2: Renombrar la función
@api_bp.route('/chat_legacy', methods=['POST'])
def api_chat_legacy():  # ✅ NOMBRE DIFERENTE, RUTA DIFERENTE
    """Endpoint de chat legacy (usar /api/chat/message en su lugar)"""
    return jsonify({
        'success': True,
        'message': 'Este endpoint es legacy. Usar /api/chat/message',
        'redirect_to': '/api/chat/message'
    })