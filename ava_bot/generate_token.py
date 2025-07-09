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
        # 🔧 CORREGIR: Las rutas deben apuntar a la carpeta ava_bot
        script_dir = os.path.dirname(os.path.abspath(__file__))  # ava_bot/
        token_path = os.path.join(script_dir, 'token.json')      # ava_bot/token.json
        client_secret_path = os.path.join(script_dir, 'client_secret.json')  # ava_bot/client_secret.json

        print(f"📁 Directorio del script: {script_dir}")
        print(f"🔑 Buscando client_secret en: {client_secret_path}")
        print(f"💾 Guardando token en: {token_path}")

        # 2. Verificar que client_secret.json existe
        if not os.path.exists(client_secret_path):
            print(f"❌ No se encontró client_secret.json en: {client_secret_path}")
            return False

        # 3. Verifica permisos de escritura
        try:
            with open(token_path, 'w') as test_file:
                test_file.write("test")
            os.remove(token_path)
            print("✅ Permisos de escritura verificados")
        except Exception as e:
            print(f"❌ Error de permisos: {str(e)}")
            print("💡 Ejecuta PowerShell como administrador o verifica los permisos de la carpeta")
            return False

        # 4. Flujo de autenticación
        print("🔄 Iniciando flujo de autenticación...")
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_path,
            SCOPES
        )
        creds = flow.run_local_server(port=0)
        
        # 5. Guardado robusto
        temp_path = token_path + '.tmp'
        with open(temp_path, 'w') as token_file:
            token_file.write(creds.to_json())
        os.replace(temp_path, token_path)
        
        print(f"✅ Token guardado exitosamente en: {token_path}")
        print(f"📅 Token válido hasta: {creds.expiry}")
        return True
        
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 Generador de Token de Google OAuth")
    print("=" * 50)
    
    if generate_token():
        print("🎉 Proceso completado con éxito")
    else:
        print("💥 Hubo un error al generar el token")
        sys.exit(1)