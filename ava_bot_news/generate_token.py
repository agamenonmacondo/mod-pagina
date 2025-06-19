from google_auth_oauthlib.flow import InstalledAppFlow
import os
import sys

# Define los scopes más completos
SCOPES = [
    # Gmail
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    
    # Calendar y Meet
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.events.readonly',
    
    # Google Drive
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly',
    
    # Google Sheets
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    
    # Google Docs (opcional)
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/documents.readonly'
]

def generate_token():
    try:
        # 1. Calcula rutas absolutas
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(script_dir))
        token_path = os.path.join(base_dir, 'token.json')
        client_secret_path = os.path.join(base_dir, 'client_secret.json')

        print(f"Intentando guardar token en: {token_path}")

        # 2. Verifica permisos de escritura
        try:
            with open(token_path, 'w') as test_file:
                test_file.write("test")
            os.remove(token_path)
        except Exception as e:
            print(f"Error de permisos: {str(e)}")
            print("Ejecuta PowerShell como administrador o verifica los permisos de la carpeta")
            sys.exit(1)

        # 3. Flujo de autenticación
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_path,
            SCOPES
        )
        creds = flow.run_local_server(port=0)
        
        # 4. Guardado robusto
        temp_path = token_path + '.tmp'
        with open(temp_path, 'w') as token_file:
            token_file.write(creds.to_json())
        os.replace(temp_path, token_path)
        
        print(f"Token guardado exitosamente en: {token_path}")
        return True
        
    except Exception as e:
        print(f"Error crítico: {str(e)}")
        return False

if __name__ == '__main__':
    if generate_token():
        print("Proceso completado con éxito")
    else:
        print("Hubo un error al generar el token")
        sys.exit(1)