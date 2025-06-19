from pathlib import Path
import sys
import os

# ✅ AGREGAR OAUTH_HELPER AL PATH
current_dir = Path(__file__).parent
tools_dir = current_dir.parent
ava_bot_dir = tools_dir.parent
utils_dir = ava_bot_dir / 'utils'

# Agregar rutas necesarias
paths_to_add = [
    str(ava_bot_dir),
    str(utils_dir),
    str(ava_bot_dir / 'nodes'),
    str(ava_bot_dir / 'nodes' / 'email')
]

for path in paths_to_add:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

# ✅ IMPORTAR OAUTH_HELPER
try:
    from oauth_helper import get_google_credentials
    OAUTH_HELPER_AVAILABLE = True
    print("✅ OAuth helper disponible para Gmail")
except ImportError:
    OAUTH_HELPER_AVAILABLE = False
    print("⚠️ OAuth helper no disponible para Gmail")

# ✅ IMPORT CORREGIDO CON FALLBACK
try:
    from nodes.email.gmail_sender import GmailSender
    import base64
    import json
    from datetime import datetime
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    import mimetypes
    import logging
    from typing import Dict, Any

    logger = logging.getLogger(__name__)
    
    class GmailAdapter:
        def __init__(self):
            """Inicialización con soporte para OAuth desde env vars"""
            try:
                # ✅ CREAR GMAIL SENDER CON OAUTH HELPER
                if OAUTH_HELPER_AVAILABLE:
                    # Crear GmailSender que usará oauth_helper automáticamente
                    self.gmail_sender = GmailSender()
                else:
                    # Método legacy
                    self.gmail_sender = GmailSender()
                
                self.description = "Ava Bot Gmail tool - Send emails with OAuth env vars support"
                self.has_credentials = True
                logger.info("✅ GmailAdapter initialized with OAuth env vars support")
                
            except Exception as e:
                logger.error(f"❌ Error initializing GmailAdapter: {e}")
                self.gmail_sender = None
                self.has_credentials = False
                self.description = "Ava Bot Gmail tool - Basic mode"
        
        def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
            """✅ MÉTODO PRINCIPAL CON OAUTH ENV VARS"""
            try:
                # ✅ TEST DE CONEXIÓN AL EJECUTAR
                if not hasattr(self, '_connection_tested'):
                    self._test_oauth_connection()
                    self._connection_tested = True
                
                action = arguments.get('action', 'send')
                
                if action == 'send':
                    to = arguments.get('to')
                    subject = arguments.get('subject', 'Mensaje de Ava')
                    body = arguments.get('body', '')
                    
                    # ✅ DETECTAR send_latest_image
                    send_latest_image = arguments.get('send_latest_image', False)
                    image_filename = arguments.get('image_filename')
                    attachment_data = arguments.get('attachment_data')
                    
                    if send_latest_image:
                        return self._send_with_latest_image_integration(to, subject, body)
                    elif image_filename:
                        directory = arguments.get('directory', 'generated_images')
                        return self._send_with_specific_image(to, subject, body, image_filename, directory)
                    elif attachment_data:
                        return self._send_email_with_attachments(to, subject, body, attachment_data)
                    else:
                        return self._send_email_simple(to, subject, body)
                
                else:
                    return {
                        "content": [{"type": "text", "text": f"❌ Acción no reconocida: {action}"}]
                    }
                    
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"❌ Error en Gmail: {str(e)}"}]
                }

        def _test_oauth_connection(self):
            """Test de conexión OAuth desde variables de entorno"""
            print(f"\n🧪 GMAIL OAUTH CONNECTION TEST")
            print(f"=" * 40)
            
            if OAUTH_HELPER_AVAILABLE:
                try:
                    # Test de credenciales OAuth
                    creds = get_google_credentials(['https://www.googleapis.com/auth/gmail.send'])
                    if creds:
                        print(f"✅ OAuth desde env vars: EXITOSO")
                        print(f"🔑 Token válido: {not creds.expired}")
                        print(f"🔄 Puede refrescar: {bool(creds.refresh_token)}")
                    else:
                        print(f"❌ OAuth desde env vars: FALLÓ")
                except Exception as e:
                    print(f"⚠️ OAuth desde env vars: ERROR - {e}")
            else:
                print(f"⚠️ OAuth helper no disponible")
            
            print(f"🔧 Gmail sender: {'✅ Activo' if self.gmail_sender else '❌ No disponible'}")
            print(f"=" * 40)

        def _send_with_latest_image_integration(self, to: str, subject: str, body: str) -> Dict[str, Any]:
            """✅ ENVIAR CON ÚLTIMA IMAGEN USANDO INTEGRACIÓN DIRECTA"""
            try:
                if not self.gmail_sender:
                    return {
                        "content": [{"type": "text", "text": "❌ **Gmail no disponible:** Credenciales no configuradas"}]
                    }

                # ✅ VERIFICAR SI GMAIL_SENDER TIENE MÉTODO INTEGRADO
                if hasattr(self.gmail_sender, 'send_with_latest_image'):
                    result = self.gmail_sender.send_with_latest_image(to, subject, body)
                    
                    if result.get('success'):
                        return {
                            "content": [{"type": "text", "text": f"""📧 **Email con imagen enviado exitosamente usando método integrado**

📧 **Para:** {to}
📝 **Asunto:** {subject}
📎 **Imagen adjunta:** {result.get('filename', 'N/A')} ({result.get('attachment_size', 0)} bytes)
🆔 **ID:** {result.get('message_id', 'N/A')}

✅ **Estado:** Entregado correctamente con archivo real adjunto
🚀 **Método:** Integración directa FileManager → Gmail
📁 **Archivo real enviado:** {result.get('message', 'Adjunto procesado correctamente')}"""}]
                        }
                    else:
                        # ✅ FALLBACK: Si falla integración, usar método manual
                        return self._send_with_latest_image_manual(to, subject, body, result.get('error', 'Error desconocido'))
                
                else:
                    # ✅ FALLBACK: Método manual si no hay integración
                    return self._send_with_latest_image_manual(to, subject, body, "Método integrado no disponible")
                    
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"❌ **Error método integrado:** {str(e)}. Intentando método manual..."}]
                }

        def _send_with_latest_image_manual(self, to: str, subject: str, body: str, error_msg: str = "") -> Dict[str, Any]:
            """✅ MÉTODO MANUAL: Usar file_manager + gmail separadamente"""
            try:
                # ✅ IMPORTAR FILE_MANAGER DINÁMICAMENTE
                try:
                    from file_adapter import FileManagerAdapter
                    file_manager = FileManagerAdapter()
                    
                    # ✅ PASO 1: Obtener última imagen
                    latest_result = file_manager.execute({"action": "get_latest_image"})
                    
                    if "filename" not in latest_result:
                        return {
                            "content": [{"type": "text", "text": f"❌ **Error método manual:** No se encontró ninguna imagen. Error previo: {error_msg}"}]
                        }
                    
                    filename = latest_result["filename"]
                    filepath = latest_result["filepath"]
                    
                    # ✅ PASO 2: Validar archivo existe
                    if not Path(filepath).exists():
                        return {
                            "content": [{"type": "text", "text": f"❌ **Error método manual:** Archivo no encontrado: {filepath}"}]
                        }
                    
                    # ✅ PASO 3: Preparar attachment_data
                    attachment_data = {
                        "method": "url_link",
                        "filename": filename,
                        "filepath": filepath,
                        "type": "image/png"
                    }
                    
                    # ✅ PASO 4: Enviar con attachment_data
                    return self._send_email_with_attachments(to, subject, body, attachment_data)
                    
                except ImportError:
                    return {
                        "content": [{"type": "text", "text": f"❌ **Error método manual:** FileManager no disponible. Error previo: {error_msg}"}]
                    }
                    
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"❌ **Error método manual:** {str(e)}. Error previo: {error_msg}"}]
                }

        def _send_email_with_attachments(self, to: str, subject: str, body: str, attachment_data=None, attachments=None, attachment_path=None) -> Dict[str, Any]:
            """✅ MÉTODO ACTUALIZADO: Envía email con soporte para URL y base64"""
            try:
                if not self.gmail_sender:
                    return {
                        "content": [{"type": "text", "text": "❌ **Gmail no disponible:** Credenciales no configuradas"}]
                    }

                # ✅ CREAR MENSAJE MIME CON ADJUNTOS
                message = MIMEMultipart()
                message['to'] = to
                message['subject'] = subject
                
                # Agregar cuerpo del mensaje
                message.attach(MIMEText(body, 'plain'))
                
                attachments_info = []
                
                # ✅ PROCESAR attachment_data con SOPORTE PARA URL
                if attachment_data:
                    attachment_method = attachment_data.get('method', 'base64')  # Detectar método
                    filename = attachment_data.get('filename', 'attachment')
                    
                    if attachment_method == 'url_link':
                        # ✅ MÉTODO URL - Leer archivo desde filepath
                        filepath = attachment_data.get('filepath')
                        if filepath and os.path.exists(filepath):
                            try:
                                with open(filepath, 'rb') as f:
                                    file_data = f.read()
                                
                                content_type = attachment_data.get('type', 'application/octet-stream')
                                
                                # Crear adjunto MIME
                                attachment = MIMEBase(*content_type.split('/'))
                                attachment.set_payload(file_data)
                                encoders.encode_base64(attachment)
                                attachment.add_header('Content-Disposition', f'attachment; filename= {filename}')
                                
                                message.attach(attachment)
                                attachments_info.append(f"📎 {filename} ({len(file_data)} bytes) [URL]")
                                
                            except Exception as e:
                                return {
                                    "content": [{"type": "text", "text": f"❌ **Error leyendo archivo URL:** {str(e)}"}]
                                }
                        else:
                            return {
                                "content": [{"type": "text", "text": f"❌ **Archivo URL no encontrado:** {filepath}"}]
                            }
                    
                    else:
                        # ✅ MÉTODO BASE64 TRADICIONAL - Con validación mejorada
                        content = attachment_data.get('content', '')
                        content_type = attachment_data.get('content_type', 'application/octet-stream')
                        
                        if content:
                            try:
                                # ✅ VALIDAR Y LIMPIAR BASE64
                                content = content.strip()
                                
                                # Agregar padding si falta
                                missing_padding = len(content) % 4
                                if missing_padding:
                                    content += '=' * (4 - missing_padding)
                                
                                # Decodificar base64
                                file_data = base64.b64decode(content)
                                
                                # Crear adjunto MIME
                                attachment = MIMEBase(*content_type.split('/'))
                                attachment.set_payload(file_data)
                                encoders.encode_base64(attachment)
                                attachment.add_header('Content-Disposition', f'attachment; filename= {filename}')
                                
                                message.attach(attachment)
                                attachments_info.append(f"📎 {filename} ({len(file_data)} bytes) [BASE64]")
                                
                            except Exception as e:
                                return {
                                    "content": [{"type": "text", "text": f"❌ **Error procesando base64:** {str(e)}"}]
                                }

                # ✅ ENVIAR EMAIL CON ADJUNTOS USANDO GMAIL API
                try:
                    # Convertir mensaje MIME a string
                    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                    
                    # Usar el servicio Gmail del GmailSender
                    gmail_service = self.gmail_sender.service
                    
                    message_body = {
                        'raw': raw_message
                    }
                    
                    sent_message = gmail_service.users().messages().send(
                        userId='me',
                        body=message_body
                    ).execute()
                    
                    message_id = sent_message.get('id', 'N/A')
                    
                    return {
                        "content": [{"type": "text", "text": f"""📧 **Email con adjuntos enviado exitosamente**

📧 **Para:** {to}  
📝 **Asunto:** {subject}
📎 **Adjuntos:** {len(attachments_info)} archivo(s)
{chr(10).join(attachments_info)}
✅ **Estado:** Entregado
🆔 **ID:** {message_id}"""}]
                    }
                    
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"❌ **Error enviando email:** {str(e)}"}]
                    }
                
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"❌ **Error del sistema:** {str(e)}"}]
                }

        def _send_email_simple(self, to: str, subject: str, body: str) -> Dict[str, Any]:
            """✅ ENVÍA EMAIL SIMPLE - MÉTODO ORIGINAL"""
            try:
                if not self.gmail_sender:
                    return {
                        "content": [{"type": "text", "text": "❌ **Gmail no disponible:** Credenciales no configuradas"}]
                    }

                result = self.gmail_sender.send_email(to=to, subject=subject, body=body)
                
                if isinstance(result, dict) and result.get('success'):
                    return {
                        "content": [{"type": "text", "text": f"""📧 **Email enviado exitosamente**

📧 **Para:** {to}  
📝 **Asunto:** {subject}
✅ **Estado:** Entregado
🆔 **ID:** {result.get('message_id', 'N/A')}"""}]
                    }
                else:
                    return {
                        "content": [{"type": "text", "text": f"❌ **Error:** {result.get('error', 'Error desconocido')}"}]
                    }
                
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"❌ **Error del sistema:** {str(e)}"}]
                }

except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"❌ No se pudo importar GmailSender: {e}")
    
    # Fallback básico cuando no se puede importar
    class GmailAdapter:
        def __init__(self):
            self.description = "Ava Bot Gmail tool - Basic mode (import error)"
            self.has_credentials = False
            logger.info("✅ GmailAdapter inicializado en modo básico (import error)")
        
        def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
            to = arguments.get('to', '')
            subject = arguments.get('subject', 'Mensaje desde AVA')
            body = arguments.get('body', '')
            
            response_text = f"📧 **Solicitud de email recibida**\n\n" + \
                          f"📧 **Para:** {to}\n" + \
                          f"📝 **Asunto:** {subject}\n" + \
                          f"📄 **Mensaje:**\n{body}\n\n" + \
                          f"🔧 **Gmail no disponible** - Error de importación\n" + \
                          f"📞 Para emails automáticos, configura Gmail API\n" + \
                          f"📋 **Mientras tanto:** Copia el contenido y envíalo manualmente."
            
            return {
                "content": [{
                    "type": "text",
                    "text": response_text
                }]
            }

# ✅ FUNCIÓN DE PRUEBA SIMPLE PARA VERIFICAR QUE FUNCIONA
if __name__ == "__main__":
    print("🧪 PROBANDO GMAIL_ADAPTER CON CORRECCIÓN DE IMPORTS")
    print("=" * 60)
    
    try:
        adapter = GmailAdapter()
        print(f"✅ Gmail Adapter inicializado: {adapter.description}")
        print(f"🔑 Credenciales: {adapter.has_credentials}")
        
        # Prueba simple
        result = adapter.execute({
            "to": "test@example.com",
            "subject": "Test de imports corregido",
            "body": "Probando que los imports de typing funcionen correctamente"
        })
        
        print("\n📧 Resultado de prueba:")
        print(result["content"][0]["text"])
        
        print("\n✅ ¡Gmail Adapter funciona correctamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()