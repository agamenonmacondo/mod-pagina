# filepath: c:\Users\h\Downloads\ava_bot\nodes\email\gmail_sender.py
import os
import sys
import base64
import logging
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import json

# ✅ IMPORTAR FILE MANAGER DIRECTAMENTE
from pathlib import Path

# Agregar ruta del file_manager
current_dir = Path(__file__).parent
ava_bot_dir = current_dir.parent.parent
tools_dir = ava_bot_dir / 'tools' / 'adapters'
sys.path.append(str(tools_dir))

try:
    from file_adapter import FileManagerAdapter
    FILE_MANAGER_AVAILABLE = True
except ImportError:
    FILE_MANAGER_AVAILABLE = False
    print("⚠️ FileManager no disponible")

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define proper scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class GmailSender:
    """Tool for sending emails via Gmail"""
    name = "gmail_tool"
    
    def __init__(self):
        self.service = self._get_gmail_service()
        
        # ✅ INTEGRAR FILE MANAGER
        if FILE_MANAGER_AVAILABLE:
            self.file_manager = FileManagerAdapter()
            print("✅ FileManager integrado en GmailSender")
        else:
            self.file_manager = None
    
    def _get_gmail_service(self):
        """Get Gmail API service"""
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), "../../token.json")
        credentials_path = os.path.join(os.path.dirname(__file__), "../../credentials.json")
        
        logger.info(f"Looking for Gmail credentials at: {token_path}")
        
        # Load credentials if they exist
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_info(
                    json.loads(open(token_path, 'r').read()), 
                    SCOPES
                )
                logger.info("Gmail credentials loaded successfully")
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Gmail credentials refreshed successfully")
                except RefreshError:
                    logger.warning("Credentials expired and could not be refreshed, need new authorization")
                    os.remove(token_path) if os.path.exists(token_path) else None
                    creds = None
            
            # If still no valid creds, need to authorize
            if not creds:
                if not os.path.exists(credentials_path):
                    logger.error(f"Credentials file not found at: {credentials_path}")
                    return None
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    logger.info("New Gmail authorization completed successfully")
                    
                    # Save credentials
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    logger.info(f"Credentials saved to {token_path}")
                except Exception as e:
                    logger.error(f"Error during authorization: {e}")
                    return None
        
        # Build and return Gmail service
        try:
            service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service initialized")
            return service
        except Exception as e:
            logger.error(f"Error building Gmail service: {e}")
            return None
    
    # Rename from 'execute' to 'process' to match what tool_manager is expecting
    def process(self, params=None, **kwargs):
        """Process the Gmail sending tool request"""
        logger.info(f"Processing email sending request with params: {params}, kwargs: {kwargs}")
        
        # Handle different parameter formats
        if params is None and kwargs:
            # Called with keyword arguments directly
            actual_params = kwargs
        elif isinstance(params, dict):
            # Format 1: {"tool": "gmail_tool", "params": {...}}
            if 'params' in params:
                actual_params = params['params']
            # Format 2: Direct parameters
            else:
                actual_params = params
        else:
            # Merge params and kwargs if both provided
            actual_params = params or {}
            actual_params.update(kwargs)
        
        # Extract email parameters
        to = actual_params.get('to')
        subject = actual_params.get('subject', 'No subject')
        body = actual_params.get('body', '')
        
        # ✅ DETECTAR DIFERENTES TIPOS DE ENVÍO
        send_latest_image = actual_params.get('send_latest_image', False)
        image_filename = actual_params.get('image_filename')
        directory = actual_params.get('directory', 'generated_images')
        
        # Check for required parameters
        if not to:
            logger.error("Missing 'to' parameter in email request")
            return {'success': False, 'message': 'Destinatario de correo no especificado'}
        
        logger.info(f"Extracted email parameters - to: {to}, subject: {subject}, body length: {len(body)}")
        logger.info(f"Special flags - send_latest_image: {send_latest_image}, image_filename: {image_filename}")
        
        try:
            # ✅ ELEGIR MÉTODO DE ENVÍO SEGÚN PARÁMETROS
            if send_latest_image:
                logger.info("Sending latest image automatically")
                return self.send_with_latest_image(to, subject, body)
            
            elif image_filename:
                logger.info(f"Sending specific image: {image_filename}")
                return self.send_specific_image(to, subject, body, image_filename, directory)
            
            else:
                logger.info("Sending simple email")
                return self.send_email(to, subject, body)
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'message': 'Error al enviar el correo. Por favor, intente nuevamente.'}
    
    # Keep the execute method for backward compatibility
    def execute(self, **kwargs):
        """For backward compatibility"""
        return self.process(**kwargs)
    
    def send_email(self, to, subject, body):
        """Send email using Gmail API"""
        logger.info(f"Preparing to send email to: {to}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body preview: {body[:50]}... ")
        
        if not self.service:
            logger.error("Gmail service not initialized")
            return {'success': False, 'message': 'Servicio de Gmail no inicializado'}
        
        # Create message
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        # Encode message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Create message body
        create_message = {
            'raw': encoded_message
        }
        
        try:
            logger.info("Sending email through Gmail API...")
            sent_message = self.service.users().messages().send(
                userId="me", 
                body=create_message
            ).execute()
            
            logger.info(f"Email sent successfully! Message ID: {sent_message.get('id')}")
            return {
                'success': True, 
                'message': 'Correo enviado correctamente',
                'message_id': sent_message.get('id')
            }
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise

    def send_email_with_attachment(self, to: str, subject: str, body: str, attachments: list = None):
        """Nuevo método para emails con adjuntos"""
        logger.info(f"Preparing to send email with attachments to: {to}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body preview: {body[:50]}... ")
        
        if not self.service:
            logger.error("Gmail service not initialized")
            return {'success': False, 'message': 'Servicio de Gmail no inicializado'}
        
        # Create message
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        
        # Agregar cuerpo del mensaje
        message.attach(MIMEText(body, 'plain'))
        
        # Agregar adjuntos
        if attachments:
            for attachment in attachments:
                # Procesar archivo adjunto...
                pass
        
        # Encode message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Create message body
        create_message = {
            'raw': encoded_message
        }
        
        try:
            logger.info("Sending email with attachments through Gmail API...")
            sent_message = self.service.users().messages().send(
                userId="me", 
                body=create_message
            ).execute()
            
            logger.info(f"Email with attachments sent successfully! Message ID: {sent_message.get('id')}")
            return {
                'success': True, 
                'message': 'Correo con adjuntos enviado correctamente',
                'message_id': sent_message.get('id')
            }
        except Exception as e:
            logger.error(f"Error sending email with attachments: {e}")
            raise

    def send_with_latest_image(self, to: str, subject: str, body: str) -> dict:
        """✅ ENVIAR EMAIL CON ÚLTIMA IMAGEN AUTOMÁTICAMENTE"""
        try:
            if not self.file_manager:
                return {"success": False, "error": "FileManager no disponible"}

            # 1. Obtener última imagen
            latest_result = self.file_manager.execute({"action": "get_latest_image"})
            
            if "filename" not in latest_result:
                return {"success": False, "error": "No se encontró ninguna imagen"}

            filename = latest_result["filename"]
            filepath = latest_result["filepath"]

            # 2. Validar que el archivo existe
            if not Path(filepath).exists():
                return {"success": False, "error": f"Archivo no encontrado: {filepath}"}

            # 3. Enviar con archivo real
            return self.send_with_file_attachment(to, subject, body, filepath, filename)

        except Exception as e:
            return {"success": False, "error": f"Error enviando imagen: {str(e)}"}

    def send_with_file_attachment(self, to: str, subject: str, body: str, filepath: str, filename: str = None) -> dict:
        """✅ ENVIAR EMAIL CON ARCHIVO ESPECÍFICO"""
        try:
            # ✅ IMPORTAR MÓDULOS NECESARIOS PARA ADJUNTOS
            import mimetypes
            from email.mime.base import MIMEBase
            from email import encoders
            
            file_path = Path(filepath)
            
            if not file_path.exists():
                return {"success": False, "error": f"Archivo no encontrado: {filepath}"}

            if not filename:
                filename = file_path.name

            logger.info(f"Preparing to send email with attachment: {filename}")

            # Crear mensaje MIME
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            # Leer archivo
            with open(file_path, 'rb') as f:
                file_data = f.read()

            # Detectar tipo MIME
            content_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
            logger.info(f"Detected content type: {content_type} for file: {filename}")

            # Crear adjunto
            main_type, sub_type = content_type.split('/', 1)
            attachment = MIMEBase(main_type, sub_type)
            attachment.set_payload(file_data)
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename={filename}')
            
            message.attach(attachment)

            # Enviar vía Gmail API
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            message_body = {'raw': raw_message}
            
            logger.info("Sending email with attachment through Gmail API...")
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message_body
            ).execute()

            logger.info(f"Email with attachment sent successfully! Message ID: {sent_message.get('id')}")
            return {
                "success": True,
                "message_id": sent_message.get('id'),
                "attachment_size": len(file_data),
                "filename": filename,
                "message": f"Email enviado con adjunto: {filename} ({len(file_data)} bytes)"
            }

        except Exception as e:
            logger.error(f"Error sending file attachment: {str(e)}")
            return {"success": False, "error": f"Error enviando archivo: {str(e)}"}

    def send_specific_image(self, to: str, subject: str, body: str, image_filename: str, directory: str = "generated_images") -> dict:
        """✅ ENVIAR IMAGEN ESPECÍFICA POR NOMBRE"""
        try:
            if not self.file_manager:
                return {"success": False, "error": "FileManager no disponible"}

            # 1. Preparar imagen específica
            prepare_result = self.file_manager.execute({
                "action": "prepare_for_email_url",
                "filename": image_filename,
                "directory": directory
            })

            if "attachment_data" not in prepare_result:
                return {"success": False, "error": f"Error preparando imagen: {image_filename}"}

            attachment_data = prepare_result["attachment_data"]
            filepath = attachment_data["filepath"]

            # 2. Enviar archivo
            return self.send_with_file_attachment(to, subject, body, filepath, image_filename)

        except Exception as e:
            return {"success": False, "error": f"Error enviando imagen específica: {str(e)}"}

# When this module is run directly, perform a test of the Gmail sender
if __name__ == "__main__":
    print("🧪 PROBANDO GMAIL SENDER CON INTEGRACIÓN FILEMANAGER")
    print("=" * 60)
    
    sender = GmailSender()
    
    # ✅ TEST 1: Email simple
    print("\n📧 TEST 1: Email simple")
    print("-" * 30)
    result1 = sender.process({
        "to": "agamenonmacondo@gmail.com",
        "subject": "Test Email Simple",
        "body": "Este es un email de prueba simple."
    })
    print(f"Resultado: {result1}")
    
    # ✅ TEST 2: Email con última imagen (si está disponible)
    print("\n🖼️ TEST 2: Email con última imagen")
    print("-" * 30)
    result2 = sender.process({
        "to": "agamenonmacondo@gmail.com", 
        "subject": "Test con Última Imagen",
        "body": "Email con la última imagen generada adjunta.",
        "send_latest_image": True
    })
    print(f"Resultado: {result2}")
    
    # ✅ TEST 3: Email con imagen específica (si existe)
    print("\n📷 TEST 3: Email con imagen específica")
    print("-" * 30)
    result3 = sender.process({
        "to": "agamenonmacondo@gmail.com",
        "subject": "Test con Imagen Específica", 
        "body": "Email con imagen específica adjunta.",
        "image_filename": "ava_generated_20250602_011919.png"
    })
    print(f"Resultado: {result3}")
    
    print("\n" + "=" * 60)
    print("🎯 PRUEBAS COMPLETADAS")
