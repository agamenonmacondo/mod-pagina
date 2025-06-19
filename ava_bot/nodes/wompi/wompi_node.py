#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
wompi_node.py - Nodo para integración con Wompi Colombia

Funcionalidades:
1. Creación de transacciones
2. Verificación de estado de pagos
3. Manejo de webhooks
4. Generación de links de pago
"""

import os
import json
import logging
import requests
import hashlib
import hmac
from datetime import datetime
from dotenv import load_dotenv

# Configuración inicial
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wompi_node")

# Configuración de Wompi
WOMPI_ENV = os.getenv("WOMPI_ENV", "sandbox")  # sandbox or prod
WOMPI_PRIVATE_KEY = os.getenv("WOMPI_PRIVATE_KEY")
WOMPI_PUBLIC_KEY = os.getenv("WOMPI_PUBLIC_KEY")
WOMPI_EVENT_KEY = os.getenv("WOMPI_EVENT_KEY")

BASE_URL = "https://sandbox.wompi.co/v1" if WOMPI_ENV == "sandbox" else "https://sandbox.wompi.co/v1"

class WompiNode:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {WOMPI_PRIVATE_KEY}",
            "Content-Type": "application/json"
        }
    def process(self, state):
        """
        Procesa el estado y ejecuta la acción correspondiente
        """
        logger.info("Procesando solicitud de Wompi...")
        
        # Ejemplo: Crear una transacción
        if state.context.get("action") == "create_transaction":
            amount = state.context.get("amount")
            customer_email = state.context.get("customer_email")
            payment_method = state.context.get("payment_method")
            reference = state.context.get("reference")
            redirect_url = state.context.get("redirect_url")
            
            response = self.create_transaction(
                amount=amount,
                customer_email=customer_email,
                payment_method=payment_method,
                reference=reference,
                redirect_url=redirect_url
            )
            state.response = response
        else:
            state.response = "Acción no reconocida para Wompi."
        
        return "conversation_node"    
    
    def create_transaction(self, amount, currency="COP", customer_email=None, 
                         payment_method=None, reference=None, redirect_url=None):
        """
        Crea una nueva transacción en Wompi
        
        Args:
            amount (float): Monto en pesos colombianos
            currency (str): Moneda (COP por defecto)
            customer_email (str): Email del cliente
            payment_method (dict): Método de pago
            reference (str): Referencia única
            redirect_url (str): URL de redirección post-pago
            
        Returns:
            dict: Respuesta de Wompi
        """
        payload = {
            "amount_in_cents": int(amount * 100),
            "currency": currency,
            "customer_email": customer_email,
            "payment_method": payment_method or {"type": "CARD"},
            "reference": reference or self._generate_reference(),
            "redirect_url": redirect_url or "https://yourdomain.com/payment/redirect"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/v1/transactions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creando transacción: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_transaction(self, transaction_id):
        """
        Obtiene el estado de una transacción
        
        Args:
            transaction_id (str): ID de transacción
            
        Returns:
            dict: Información de la transacción
        """
        try:
            response = requests.get(
                f"{BASE_URL}/v1/transactions/{transaction_id}",
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obteniendo transacción: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def create_payment_link(self, amount, description, currency="COP", 
                          expires_in=None, reference=None):
        """
        Crea un link de pago en Wompi
        
        Args:
            amount (float): Monto en pesos
            description (str): Descripción del pago
            currency (str): Moneda
            expires_in (int): Minutos hasta expiración
            reference (str): Referencia única
            
        Returns:
            dict: Respuesta con link de pago
        """
        payload = {
            "name": description,
            "description": description,
            "single_use": True,
            "collect_shipping": False,
            "amount_in_cents": int(amount * 100),
            "currency": currency,
            "expires_in": expires_in or 1440,  # 24 horas
            "reference": reference or self._generate_reference()
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/v1/payment_links",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creando link de pago: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def verify_webhook(self, request_body, signature):
        """
        Verifica la autenticidad de un webhook
        
        Args:
            request_body (bytes): Cuerpo de la petición
            signature (str): Firma recibida
            
        Returns:
            bool: True si la firma es válida
        """
        try:
            computed_signature = hmac.new(
                WOMPI_EVENT_KEY.encode(),
                request_body,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(computed_signature, signature)
        except Exception as e:
            logger.error(f"Error verificando webhook: {str(e)}")
            return False
    
    def _generate_reference(self):
        """Genera una referencia única para transacciones"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_hash = hashlib.sha256(os.urandom(16)).hexdigest()[:8]
        return f"ref_{timestamp}_{random_hash}"

def main():
    """Ejemplo de uso del nodo Wompi"""
    wompi = WompiNode()
    
    # Ejemplo: Crear link de pago
    payment_link = wompi.create_payment_link(
        amount=150000,
        description="Pago de servicio premium",
        expires_in=1440  # 24 horas
    )
    
    if payment_link.get("data"):
        print(f"Link de pago creado: {payment_link['data']['attributes']['url']}")
    else:
        print("Error creando link de pago")

if __name__ == "__main__":
    main()