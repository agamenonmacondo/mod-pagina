import sys
from pathlib import Path
from typing import Dict, Any
import logging

# ✅ AGREGAR OAUTH_HELPER AL PATH
current_dir = Path(__file__).parent
tools_dir = current_dir.parent
ava_bot_dir = tools_dir.parent
utils_dir = ava_bot_dir / 'utils'
project_root = ava_bot_dir.parent.parent

paths_to_add = [str(project_root), str(utils_dir)]
for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

# ✅ IMPORTAR OAUTH_HELPER
try:
    from oauth_helper import get_google_credentials
    OAUTH_HELPER_AVAILABLE = True
    print("✅ OAuth helper disponible para Drive")
except ImportError:
    OAUTH_HELPER_AVAILABLE = False
    print("⚠️ OAuth helper no disponible para Drive")

try:
    from tools.base_tool import BaseTool
except ImportError:
    # Crear BaseTool básico si no existe
    class BaseTool:
        def __init__(self):
            pass

logger = logging.getLogger(__name__)

class DriveAdapter(BaseTool):
    """Adaptador para Google Drive con OAuth env vars"""
    
    name = "drive"
    description = "Gestiona archivos en Google Drive con OAuth env vars support"
    
    def __init__(self):
        super().__init__()
        try:
            # ✅ INTENTAR OAUTH HELPER PRIMERO
            self.drive_manager = None
            self.has_credentials = False
            
            if OAUTH_HELPER_AVAILABLE:
                try:
                    # Test de credenciales OAuth desde env vars
                    creds = get_google_credentials(['https://www.googleapis.com/auth/drive.file'])
                    if creds:
                        self._initialize_drive_with_oauth(creds)
                        logger.info("✅ DriveManager inicializado con OAuth env vars")
                        print("✅ DriveManager cargado - OAuth desde variables de entorno")
                    else:
                        logger.warning("⚠️ OAuth env vars no disponibles para Drive")
                except Exception as e:
                    logger.error(f"❌ Error con OAuth env vars Drive: {e}")
            
            if not self.has_credentials:
                logger.warning("⚠️ DriveManager not available - OAuth credentials missing")
                
        except Exception as e:
            logger.error(f"❌ Error initializing DriveAdapter: {e}")
            self.drive_manager = None
            self.has_credentials = False
    
    def _initialize_drive_with_oauth(self, creds):
        """Inicializar DriveManager con OAuth"""
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            
            class OAuthDriveManager:
                """DriveManager usando OAuth desde env vars"""
                
                def __init__(self, credentials):
                    self.service = build('drive', 'v3', credentials=credentials)
                
                def upload_file(self, file_path, folder_id=None, file_name=None):
                    """Subir archivo a Google Drive"""
                    
                    file_path = Path(file_path)
                    if not file_path.exists():
                        return {"error": f"File not found: {file_path}"}
                    
                    file_metadata = {'name': file_name or file_path.name}
                    if folder_id:
                        file_metadata['parents'] = [folder_id]
                    
                    media = MediaFileUpload(str(file_path), resumable=True)
                    
                    file = self.service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id,webViewLink,name'
                    ).execute()
                    
                    return {
                        "success": True,
                        "file_id": file.get('id'),
                        "link": file.get('webViewLink'),
                        "name": file.get('name')
                    }
                
                def list_files(self, limit=10):
                    """Listar archivos en Drive"""
                    
                    results = self.service.files().list(
                        pageSize=limit,
                        fields="nextPageToken, files(id, name, webViewLink, createdTime)"
                    ).execute()
                    
                    items = results.get('files', [])
                    
                    return {
                        "success": True,
                        "files": items,
                        "count": len(items)
                    }
            
            self.drive_manager = OAuthDriveManager(creds)
            self.has_credentials = True
            
        except ImportError as e:
            logger.error(f"Google API libraries not installed: {e}")
            raise Exception("Google API libraries required for Drive")
        except Exception as e:
            logger.error(f"Error inicializando OAuthDriveManager: {e}")
            raise

    @property
    def schema(self) -> Dict[str, Any]:
        """Schema actualizado para Drive con OAuth"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["upload", "download", "list", "share", "delete"],
                    "description": "Acción: upload=subir, list=listar archivos, share=compartir",
                    "default": "list"
                },
                "file_path": {
                    "type": "string",
                    "description": "Ruta local del archivo (para upload)",
                    "maxLength": 500
                },
                "file_name": {
                    "type": "string",
                    "description": "Nombre del archivo en Drive",
                    "maxLength": 255
                },
                "folder_id": {
                    "type": "string",
                    "description": "ID de carpeta de destino (opcional)",
                    "maxLength": 100
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de archivos a listar",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100
                }
            },
            "required": [],
            "additionalProperties": False
        }
    
    def process(self, params: Dict[str, Any]) -> Any:
        """Procesa operaciones de Drive con OAuth"""
        
        if not self.has_credentials:
            action = params.get("action", "list")
            
            return {
                "message": f"🔧 Google Drive {action} requiere OAuth configurado en variables de entorno",
                "action": action,
                "success": False,
                "note": "Configura GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_ACCESS_TOKEN, GOOGLE_REFRESH_TOKEN en .env",
                "oauth_available": OAUTH_HELPER_AVAILABLE
            }
        
        action = params.get("action", "list")
        
        try:
            if action == "upload":
                return self._upload_file(params)
            elif action == "list":
                return self._list_files(params)
            else:
                return {
                    "message": f"Acción {action} no implementada aún",
                    "success": False
                }
                
        except Exception as e:
            return {
                "message": f"Error en operación Drive OAuth {action}: {str(e)}",
                "success": False
            }
    
    def _upload_file(self, params):
        """Sube archivo usando OAuth"""
        file_path = params.get("file_path")
        file_name = params.get("file_name")
        folder_id = params.get("folder_id")
        
        if not file_path:
            return {"message": "file_path requerido para upload", "success": False}
        
        result = self.drive_manager.upload_file(file_path, folder_id, file_name)
        
        if result.get("success"):
            return {
                "message": f"📤 Archivo '{result['name']}' subido exitosamente a Google Drive",
                "file_id": result["file_id"],
                "link": result["link"],
                "success": True
            }
        else:
            return {
                "message": f"❌ Error subiendo archivo: {result.get('error')}",
                "success": False
            }
    
    def _list_files(self, params):
        """Lista archivos usando OAuth"""
        limit = params.get("limit", 10)
        
        result = self.drive_manager.list_files(limit)
        
        if result.get("success"):
            return {
                "message": f"📁 {result['count']} archivos encontrados en Google Drive",
                "files": result["files"],
                "count": result["count"],
                "success": True
            }
        else:
            return {
                "message": f"❌ Error listando archivos",
                "success": False
            }