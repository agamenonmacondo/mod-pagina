from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
import os

class DriveManager:
    NODE_NAME = "drive_manager"
    
    def __init__(self):
        token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'token.json')
        self.creds = Credentials.from_authorized_user_file(
            token_path,
            ['https://www.googleapis.com/auth/drive']
        )

    def process(self, state):
        """
        Processes the state and interacts with Google Drive.
        This is the entry point for the langgraph node.
        """
        action = state.context.get("drive_action", "default")

        if action == "upload" and state.context.get("file_path_to_upload"):
            file_path = state.context.get("file_path_to_upload")
            folder_id = state.context.get("drive_folder_id")
            result = self.upload_file(file_path, folder_id)
            if result.get("error"):
                state.response = f"Error al subir archivo a Drive: {result.get('error')}"
            else:
                state.response = f"Archivo subido a Drive: {result.get('web_view_link')}"
        elif action == "list_files":
            query = state.context.get("drive_query")
            files = self.list_files(query=query)
            if isinstance(files, dict) and files.get("error"):
                 state.response = f"Error al listar archivos de Drive: {files.get('error')}"
            else:
                state.response = f"Archivos encontrados en Drive: {files}"
        elif action == "download":
            file_id = state.context.get("file_id_to_download")
            output_path = state.context.get("output_path")
            result = self.download_file(file_id, output_path)
            if result.get("success"):
                state.response = f"Archivo descargado exitosamente: {output_path}"
            else:
                state.response = f"Error al descargar archivo: {result.get('error')}"
        else:
            state.response = "DriveManager fue llamado, pero no se especificó una acción clara o faltan datos."

        return "conversation_node"

    def upload_file(self, file_path, folder_id=None):
        """Sube un archivo a Google Drive."""
        try:
            service = build('drive', 'v3', credentials=self.creds)
            file_name = os.path.basename(file_path)
            
            file_metadata = {'name': file_name}
            if folder_id:
                file_metadata['parents'] = [folder_id]

            media = MediaFileUpload(file_path, resumable=True)
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()

            return {
                'file_id': file.get('id'),
                'web_view_link': file.get('webViewLink'),
                'error': None
            }
        except Exception as e:
            return {
                'file_id': None,
                'web_view_link': None,
                'error': str(e)
            }

    def download_file(self, file_id, output_path):
        """
        Descarga un archivo de Google Drive (método de instancia).
        
        Args:
            file_id: ID del archivo en Drive.
            output_path: Ruta local para guardar el archivo.
        """
        try:
            service = build('drive', 'v3', credentials=self.creds)
            request = service.files().get_media(fileId=file_id)
            
            fh = io.FileIO(output_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            return {'success': True, 'error': None}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def list_files(self, query=None):
        """Lista archivos en Google Drive usando self.creds."""
        try:
            service = build('drive', 'v3', credentials=self.creds)
            results = service.files().list(
                q=query,
                pageSize=10,
                fields="files(id, name, mimeType)"
            ).execute()
            return results.get('files', [])
        except Exception as e:
            return {'error': str(e)}

# Funciones independientes para compatibilidad hacia atrás
def upload_file(credentials, file_path, folder_id=None):
    """Función independiente para subir archivo"""
    try:
        service = build('drive', 'v3', credentials=credentials)
        file_name = os.path.basename(file_path)
        
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink'
        ).execute()

        return {
            'file_id': file.get('id'),
            'web_view_link': file.get('webViewLink'),
            'error': None
        }
    except Exception as e:
        return {
            'file_id': None,
            'web_view_link': None,
            'error': str(e)
        }

def download_file(credentials, file_id, output_path):
    """Función independiente para descargar archivo"""
    try:
        service = build('drive', 'v3', credentials=credentials)
        request = service.files().get_media(fileId=file_id)
        
        fh = io.FileIO(output_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        return {'success': True, 'error': None}
    except Exception as e:
        return {'success': False, 'error': str(e)}