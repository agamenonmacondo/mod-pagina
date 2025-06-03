#!/usr/bin/env python3
"""
Test Específico para Meet y Calendar - Enlaces Funcionales
=========================================================

Prueba la creación de reuniones y eventos con enlaces reales
"""
import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# Agregar la ruta del proyecto
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

async def test_meet_calendar_with_links():
    """Test específico de Meet y Calendar con verificación de enlaces"""
    print("📅 TEST ESPECÍFICO: MEET Y CALENDAR CON ENLACES FUNCIONALES")
    print("=" * 60)
    
    # 1. Importar y configurar sistema
    print("\n📦 1. Inicializando sistema Ava...")
    try:
        from llm_mcp_integration import LLMWithMCPTools
        
        # Configurar variables
        groq_api_key = os.getenv('GROQ_API_KEY')
        mcp_server_path = os.path.join(current_dir, "mcp_server", "run_server.py")
        
        # Inicializar sistema
        ava_system = LLMWithMCPTools(
            groq_api_key=groq_api_key,
            mcp_server_path=mcp_server_path
        )
        await ava_system.initialize()
        print("   ✅ Sistema inicializado correctamente")
        
    except Exception as e:
        print(f"   ❌ Error inicializando: {e}")
        return False
    
    # 2. Casos de prueba específicos para Meet y Calendar
    tomorrow = datetime.now() + timedelta(days=1)
    next_week = datetime.now() + timedelta(days=7)
    
    test_cases = [
        {
            'name': 'Meet - Reunión Básica',
            'tool': 'meet',
            'input': 'crea una reunión de Google Meet llamada "Reunión de Prueba Ava" para mañana a las 2pm con duración de 1 hora',
            'expected_elements': ['meet', 'enlace', 'link', 'google', 'reunión'],
            'check_link': True
        },
        {
            'name': 'Meet - Con Asistentes',
            'tool': 'meet',
            'input': f'crea una reunión llamada "Demo Ava Bot" para {tomorrow.strftime("%Y-%m-%d")} a las 15:30 con los asistentes test@example.com y demo@ava.com',
            'expected_elements': ['meet', 'asistentes', 'invitación', 'email'],
            'check_link': True
        },
        {
            'name': 'Calendar - Evento con Meet',
            'tool': 'calendar',
            'input': f'crea un evento en Google Calendar llamada "Presentación Ava" para el {next_week.strftime("%Y-%m-%d")} a las 16:00 con duración de 2 horas',
            'expected_elements': ['calendario', 'evento', 'creado', 'google'],
            'check_link': True
        },
        {
            'name': 'Meet - Reunión Urgente',
            'tool': 'meet',
            'input': 'necesito crear una reunión urgente para dentro de 30 minutos llamada "Reunión Emergencia" con juan@empresa.com',
            'expected_elements': ['meet', 'urgente', 'creada'],
            'check_link': True
        }
    ]
    
    print(f"\n🧪 2. Ejecutando {len(test_cases)} tests específicos...")
    
    results = {}
    links_found = []
    
    for i, test_case in enumerate(test_cases, 1):
        test_name = test_case['name']
        tool = test_case['tool']
        user_input = test_case['input']
        expected_elements = test_case['expected_elements']
        check_link = test_case.get('check_link', False)
        
        print(f"\n   🔧 Test {i}: {test_name}")
        print(f"      Herramienta: {tool}")
        print(f"      Input: '{user_input}'")
        
        try:
            # Ejecutar el test
            response = await asyncio.wait_for(
                ava_system.process_user_input(user_input),
                timeout=45.0  # 45 segundos timeout para dar tiempo a crear enlaces reales
            )
            
            print(f"      📝 Respuesta completa:")
            print(f"         {response}")
            
            # Verificar elementos esperados
            response_lower = response.lower()
            found_elements = [elem for elem in expected_elements if elem in response_lower]
            
            if len(found_elements) >= len(expected_elements) * 0.7:  # 70% de elementos encontrados
                print(f"      ✅ Elementos encontrados: {', '.join(found_elements)}")
            else:
                print(f"      ⚠️ Pocos elementos encontrados: {', '.join(found_elements)}")
            
            # Buscar enlaces específicos
            if check_link:
                # Patrones de enlaces comunes
                link_patterns = [
                    'meet.google.com',
                    'calendar.google.com',
                    'https://',
                    'http://',
                    'meet/',
                    'calendar/'
                ]
                
                found_links = []
                for pattern in link_patterns:
                    if pattern in response:
                        # Extraer el enlace completo
                        lines = response.split('\n')
                        for line in lines:
                            if pattern in line:
                                found_links.append(line.strip())
                
                if found_links:
                    print(f"      🔗 ENLACES ENCONTRADOS:")
                    for link in found_links:
                        print(f"         • {link}")
                        links_found.append({
                            'test': test_name,
                            'tool': tool,
                            'link': link
                        })
                    results[test_name] = 'success_with_links'
                else:
                    print(f"      ⚠️ No se encontraron enlaces funcionales")
                    results[test_name] = 'success_no_links'
            else:
                results[test_name] = 'success'
            
            # Verificar si es una respuesta real o modo básico
            if 'configuración adicional' in response_lower or 'modo básico' in response_lower:
                print(f"      ℹ️ MODO BÁSICO detectado - necesita configuración completa")
                results[test_name] = 'basic_mode'
            elif 'error' in response_lower or 'falló' in response_lower:
                print(f"      ❌ ERROR detectado en respuesta")
                results[test_name] = 'error'
                
        except asyncio.TimeoutError:
            print(f"      ⏰ Timeout en test (>45s)")
            results[test_name] = 'timeout'
        except Exception as e:
            print(f"      ❌ Error en test: {e}")
            results[test_name] = 'failed'
    
    # 3. Análisis de resultados
    print("\n" + "=" * 60)
    print("📊 ANÁLISIS DE RESULTADOS")
    print("=" * 60)
    
    # Contar resultados
    total_tests = len(results)
    success_with_links = sum(1 for r in results.values() if r == 'success_with_links')
    success_no_links = sum(1 for r in results.values() if r == 'success_no_links')
    basic_mode = sum(1 for r in results.values() if r == 'basic_mode')
    errors = sum(1 for r in results.values() if r == 'error')
    timeouts = sum(1 for r in results.values() if r == 'timeout')
    failed = sum(1 for r in results.values() if r == 'failed')
    
    print(f"🎯 RESUMEN:")
    print(f"   • Total de tests: {total_tests}")
    print(f"   • Éxito con enlaces: {success_with_links}")
    print(f"   • Éxito sin enlaces: {success_no_links}")
    print(f"   • Modo básico: {basic_mode}")
    print(f"   • Errores: {errors}")
    print(f"   • Timeouts: {timeouts}")
    print(f"   • Fallidos: {failed}")
    
    print(f"\n📋 DETALLE POR TEST:")
    status_emojis = {
        'success_with_links': '🔗✅',
        'success_no_links': '✅',
        'basic_mode': '⚙️',
        'error': '❌',
        'timeout': '⏰',
        'failed': '💥'
    }
    
    for test_name, result in results.items():
        emoji = status_emojis.get(result, '❓')
        print(f"   {emoji} {test_name}: {result}")
    
    # 4. Mostrar enlaces encontrados
    if links_found:
        print(f"\n🔗 ENLACES FUNCIONALES ENCONTRADOS ({len(links_found)}):")
        print("-" * 50)
        for link_info in links_found:
            print(f"🎯 Test: {link_info['test']}")
            print(f"🛠️ Herramienta: {link_info['tool']}")
            print(f"🔗 Enlace: {link_info['link']}")
            print()
    else:
        print(f"\n⚠️ NO SE ENCONTRARON ENLACES FUNCIONALES")
        print("   Posibles razones:")
        print("   • Google Calendar API no configurado completamente")
        print("   • Token sin permisos de Meet/Calendar")
        print("   • Sistema en modo básico/informativo")
    
    # 5. Recomendaciones
    print(f"\n💡 RECOMENDACIONES:")
    
    if success_with_links > 0:
        print("   ✅ ¡Excelente! Algunas herramientas generan enlaces funcionales")
        print("   📈 Para mejores resultados:")
        print("     • Verifica que Google Calendar API esté completamente configurado")
        print("     • Asegúrate de que token.json tenga permisos de Calendar y Meet")
    
    if basic_mode > 0:
        print("   🔧 Configuración adicional necesaria:")
        print("     • Configurar Google Calendar API con scopes completos")
        print("     • Autorizar permisos de Google Meet")
        print("     • Verificar credenciales en token.json")
    
    if success_with_links >= total_tests * 0.75:
        print("\n🎉 EXCELENTE: Las herramientas Meet/Calendar funcionan perfectamente")
        evaluation = "excellent"
    elif success_with_links + success_no_links >= total_tests * 0.75:
        print("\n✅ BUENO: Las herramientas funcionan, necesitan configuración para enlaces")
        evaluation = "good"
    elif basic_mode >= total_tests * 0.75:
        print("\n⚙️ BÁSICO: Sistema funciona en modo informativo, necesita configuración")
        evaluation = "basic"
    else:
        print("\n⚠️ ATENCIÓN: Múltiples problemas detectados")
        evaluation = "needs_attention"
    
    # 6. Cleanup
    print(f"\n🧹 Limpiando sistema...")
    try:
        if hasattr(ava_system, 'cleanup'):
            await ava_system.cleanup()
        print("   ✅ Sistema cerrado correctamente")
    except Exception as e:
        print(f"   ⚠️ Warning en cleanup: {e}")
    
    return evaluation in ['excellent', 'good']

def main():
    """Función principal"""
    print(f"🚀 Test Meet/Calendar - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        success = asyncio.run(test_meet_calendar_with_links())
        
        print("\n" + "=" * 60)
        if success:
            print("🎊 ¡Tests de Meet/Calendar completados exitosamente!")
            print("\n📋 SIGUIENTES PASOS:")
            print("1. Usar los enlaces generados para verificar funcionalidad")
            print("2. Probar unirse a las reuniones creadas")
            print("3. Verificar que las invitaciones lleguen por email")
        else:
            print("🔧 Tests completados - revisar configuración para enlaces funcionales")
            print("\n📋 SIGUIENTES PASOS:")
            print("1. Configurar Google Calendar API completamente")
            print("2. Verificar permisos en token.json")
            print("3. Autorizar acceso a Google Meet")
        
        return success
        
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        return False

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
# test_mcp_direct.py
import asyncio
import os
import sys
from datetime import datetime, timedelta

# Agregar la ruta del proyecto
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

async def test_mcp_direct():
    """Test directo del MCP client"""
    print("🔧 TEST DIRECTO MCP CLIENT")
    print("=" * 50)
    
    try:
        # Importar el cliente MCP
        from tools.adapters.mcp_client import MCPClient
        
        # Configurar cliente
        server_path = os.path.join(current_dir, "mcp_server", "run_server.py")
        python_path = os.path.join(os.path.dirname(current_dir), "venv", "Scripts", "python.exe")
        
        print(f"📍 Server path: {server_path}")
        print(f"🐍 Python path: {python_path}")
        
        # Inicializar cliente
        client = MCPClient(server_path, python_path)
        await client.start()
        
        print("✅ Cliente MCP iniciado")
        
        # Listar herramientas
        tools = await client.list_tools()
        print(f"🔧 Herramientas disponibles: {len(tools)}")
        for tool in tools:
            print(f"   • {tool['name']}: {tool.get('description', 'No description')}")
        
        # Test 1: Meet directo
        print("\n🧪 Test 1: Meet directo")
        tomorrow = datetime.now() + timedelta(days=1)
        
        meet_args = {
            "summary": "Test Meet Directo",
            "start_time": tomorrow.strftime("%Y-%m-%dT14:00:00"),
            "duration": "1 hora",
            "attendees": ["test@example.com"]
        }
        
        print(f"📞 Creando reunión Meet con args: {meet_args}")
        meet_result = await client.call_tool("meet", meet_args)
        print(f"📋 Resultado Meet:")
        print(f"   Status: {meet_result.get('status', 'unknown')}")
        
        if 'content' in meet_result:
            for content in meet_result['content']:
                if content.get('type') == 'text':
                    text = content.get('text', '')
                    print(f"   Contenido: {text}")
                    
                    # Buscar enlaces
                    if 'meet.google.com' in text or 'https://' in text:
                        print("   🔗 ¡ENLACE ENCONTRADO!")
                    else:
                        print("   ⚠️ No se encontró enlace")
        
        # Test 2: Calendar directo
        print("\n🧪 Test 2: Calendar directo")
        next_week = datetime.now() + timedelta(days=7)
        
        calendar_args = {
            "summary": "Test Calendar Directo",
            "start_time": next_week.strftime("%Y-%m-%dT16:00:00"),
            "end_time": next_week.strftime("%Y-%m-%dT17:00:00"),
            "description": "Evento de prueba directo"
        }
        
        print(f"📅 Creando evento Calendar con args: {calendar_args}")
        calendar_result = await client.call_tool("calendar", calendar_args)
        print(f"📋 Resultado Calendar:")
        print(f"   Status: {calendar_result.get('status', 'unknown')}")
        
        if 'content' in calendar_result:
            for content in calendar_result['content']:
                if content.get('type') == 'text':
                    text = content.get('text', '')
                    print(f"   Contenido: {text}")
                    
                    # Buscar enlaces
                    if 'calendar.google.com' in text or 'https://' in text:
                        print("   🔗 ¡ENLACE ENCONTRADO!")
                    else:
                        print("   ⚠️ No se encontró enlace")
        
        # Verificar configuración
        print("\n🔍 Verificando configuración...")
        
        # Buscar archivos de configuración
        config_files = [
            "credentials.json",
            "token.json",
            ".env"
        ]
        
        for config_file in config_files:
            config_path = os.path.join(current_dir, config_file)
            if os.path.exists(config_path):
                print(f"   ✅ {config_file} encontrado")
                if config_file == "token.json":
                    # Verificar permisos en token
                    try:
                        import json
                        with open(config_path, 'r') as f:
                            token_data = json.load(f)
                        
                        scopes = token_data.get('scopes', [])
                        print(f"      Scopes: {scopes}")
                        
                        required_scopes = [
                            'https://www.googleapis.com/auth/calendar',
                            'https://www.googleapis.com/auth/calendar.events'
                        ]
                        
                        missing_scopes = [scope for scope in required_scopes if scope not in scopes]
                        if missing_scopes:
                            print(f"      ⚠️ Scopes faltantes: {missing_scopes}")
                        else:
                            print(f"      ✅ Todos los scopes necesarios presentes")
                            
                    except Exception as e:
                        print(f"      ⚠️ Error leyendo token: {e}")
            else:
                print(f"   ❌ {config_file} NO encontrado")
        
        # Cleanup
        await client.stop()
        print("\n✅ Cliente MCP cerrado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en test directo: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_direct())
    if success:
        print("\n🎉 Test directo completado")
    else:
        print("\n💥 Test directo falló")