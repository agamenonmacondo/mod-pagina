# REMOVER CÓDIGO DE DEBUG y restaurar envío de emails:

def send_email(self, to_email, subject, body, attachments=None):
    """Enviar email via Gmail"""
    try:
        print(f"📧 Enviando email a: {to_email}")
        print(f"📧 Asunto: {subject}")
        
        # ✅ CREAR MENSAJE
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        message['from'] = 'me'  # Gmail API usa 'me' para el usuario autenticado
        
        # ✅ CODIFICAR MENSAJE
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # ✅ ENVIAR EMAIL REAL
        send_result = self.service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        print(f"✅ Email enviado con ID: {send_result.get('id')}")
        
        return {
            'id': send_result.get('id'),
            'status': 'sent',
            'to': to_email,
            'subject': subject,
            'message': 'Email enviado exitosamente'
        }
        
    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        raise