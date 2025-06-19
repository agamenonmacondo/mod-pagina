import os
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

# ✅ IMPORTAR OAUTH HELPER
sys.path.append(str(Path(__file__).parent.parent.parent / 'utils'))
try:
    from oauth_helper import get_google_credentials
    OAUTH_HELPER_AVAILABLE = True
    print("✅ OAuth helper disponible para Drive")
except ImportError:
    OAUTH_HELPER_AVAILABLE = False
    print("⚠️ OAuth helper no disponible para Drive")

class DriveManager:
    """Gestor de Google Drive"""
    
    def __init__(self):
        self.service = self._get_drive_service()
    
    def _get_drive_service(self):
        """Obtener servicio de Google Drive - ACTUALIZADO PARA ENV VARS"""
        
        scopes = ['https://www.googleapis.com/auth/drive.file']
        
        # ✅ NUEVO: Intentar oauth_helper primero
        if OAUTH_HELPER_AVAILABLE:
            try:
                creds = get_google_credentials(scopes)
                service = build('drive', 'v3', credentials=creds)
                logger.info("✅ Drive API service initialized via oauth_helper (env vars)")
                return service
            except Exception as e:
                logger.warning(f"⚠️ Error with oauth_helper, falling back to legacy: {e}")
        
        # ✅ FALLBACK: Método legacy con archivos
        token_path = Path(__file__).parent.parent.parent / 'token.json'
        
        if not token_path.exists():
            logger.error(f"❌ No credentials available. Configure environment variables or provide {token_path}")
            return None
        
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), scopes)
            
            # Refrescar si es necesario
            if creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            
            service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Drive API service initialized via legacy method")
            return service
            
        except Exception as e:
            logger.error(f"❌ Error initializing Drive service: {e}")
            return None
    
    def upload_file(self, file_path, folder_id=None):
        """Subir archivo a Google Drive"""
        
        if not self.service:
            return {"error": "Drive service not available"}
        
        from googleapiclient.http import MediaFileUpload
        
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        file_metadata = {'name': file_path.name}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(str(file_path), resumable=True)
        
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            logger.info(f"✅ File uploaded to Drive: {file.get('webViewLink')}")
            return {
                "success": True,
                "file_id": file.get('id'),
                "link": file.get('webViewLink')
            }
        except Exception as e:
            logger.error(f"❌ Error uploading file: {e}")
            return {"error": str(e)}