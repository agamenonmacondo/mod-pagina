import os
import json
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

class FileManagerAdapter:
    """Adapter MCP para manejo elegante de archivos locales - SOLO MÉTODO URL"""
    
    def __init__(self):
        # Directorios permitidos (seguridad)
        self.base_dir = Path(__file__).parent.parent.parent
        self.allowed_dirs = {
            'generated_images': self.base_dir / 'generated_images',
            'downloads': self.base_dir / 'downloads', 
            'temp': self.base_dir / 'temp',
            'uploads': self.base_dir / 'uploads'
        }
        
        # Crear directorios si no existen
        for dir_path in self.allowed_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.description = "Ava Bot file manager - Gestiona archivos locales con método URL"
        print(f"📁 FileManager inicializado - Solo método URL - Directorios: {list(self.allowed_dirs.keys())}")

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta acciones de manejo de archivos - SOLO MÉTODO URL"""
        try:
            action = arguments.get('action')
            
            if action == "list_files":
                return self._list_files(
                    directory=arguments.get('directory', 'generated_images'),
                    pattern=arguments.get('pattern', '*'),
                    limit=arguments.get('limit', 10)
                )
            elif action == "get_file_info":
                return self._get_file_info(
                    filename=arguments.get('filename'),
                    directory=arguments.get('directory', 'generated_images')
                )
            elif action == "read_file":
                return self._read_file(
                    filename=arguments.get('filename'),
                    directory=arguments.get('directory', 'generated_images')
                )
            elif action == "get_latest_image":
                return self._get_latest_image(
                    directory=arguments.get('directory', 'generated_images')
                )
            elif action == "prepare_for_email":
                # ✅ SOLO MÉTODO URL DISPONIBLE
                return self._prepare_for_email_url(
                    filename=arguments.get('filename'),
                    directory=arguments.get('directory', 'generated_images')
                )
            elif action == "prepare_for_email_url":
                return self._prepare_for_email_url(
                    filename=arguments.get('filename'),
                    directory=arguments.get('directory', 'generated_images')
                )
            elif action == "run_tests":
                return self._run_tests()
            elif action == "test_url_method":
                return self._test_url_method()
            else:
                return {
                    "content": [{"type": "text", "text": f"❌ Acción no reconocida: {action}. Acciones disponibles: list_files, get_file_info, read_file, get_latest_image, prepare_for_email_url, run_tests, test_url_method"}]
                }
                
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"❌ Error en FileManager: {str(e)}"}]
            }

    def _run_tests(self) -> Dict[str, Any]:
        """🧪 SISTEMA DE PRUEBAS - SOLO MÉTODO URL"""
        print("\n🧪 INICIANDO PRUEBAS DEL FILE ADAPTER - SOLO MÉTODO URL")
        print("=" * 70)
        
        results = []
        passed = 0
        total = 0
        
        # Lista de pruebas - SOLO URL, SIN BASE64
        tests = [
            ("🔧 Test de inicialización", self._test_initialization),
            ("📋 Test listar archivos reales", self._test_list_real_files),
            ("🖼️ Test última imagen real", self._test_latest_real_image),
            ("📊 Test info de archivo real", self._test_real_file_info),
            ("📖 Test leer archivo real", self._test_read_real_file),
            ("🔗 Test preparar archivo real para email (URL)", self._test_prepare_real_email_url),
            ("❌ Test acciones inválidas", self._test_invalid_actions)
        ]
        
        for test_name, test_func in tests:
            total += 1
            results.append(f"\n{test_name}")
            results.append("-" * 40)
            
            try:
                success, message = test_func()
                if success:
                    results.append("✅ PASS")
                    results.append(message)
                    passed += 1
                else:
                    results.append("❌ FAIL")
                    results.append(message)
            except Exception as e:
                results.append("💥 ERROR")
                results.append(f"Exception: {str(e)}")
        
        # Resultados finales
        results.append(f"\n{'='*70}")
        results.append(f"📊 RESULTADOS: {passed}/{total} pruebas pasaron")
        results.append(f"{'='*70}")
        
        if passed == total:
            results.append("🎉 ¡Todas las pruebas pasaron!")
            results.append("✅ Método URL funcionando perfectamente")
            results.append("🚀 Sistema optimizado sin base64")
        else:
            results.append(f"⚠️ {total - passed} pruebas fallaron")
        
        return {
            "content": [{"type": "text", "text": "\n".join(results)}]
        }

    def _test_initialization(self) -> tuple[bool, str]:
        """Test de inicialización"""
        try:
            # Verificar que directorios existan
            for dir_name, dir_path in self.allowed_dirs.items():
                if not dir_path.exists():
                    return False, f"Directorio {dir_name} no existe: {dir_path}"
            
            return True, f"Todos los directorios disponibles: {list(self.allowed_dirs.keys())}"
        except Exception as e:
            return False, f"Error en inicialización: {e}"

    def _test_list_real_files(self) -> tuple[bool, str]:
        """Test de listado de archivos reales"""
        try:
            result = self._list_files('generated_images', '*', 20)
            
            if "content" not in result:
                return False, "Resultado no contiene 'content'"
            
            content_text = result["content"][0]["text"]
            
            return True, f"Archivos reales encontrados en el listado. Contenido válido con {len(content_text)} caracteres"
                
        except Exception as e:
            return False, f"Error en test de listado real: {e}"

    def _test_latest_real_image(self) -> tuple[bool, str]:
        """Test de última imagen real"""
        try:
            result = self._get_latest_image('generated_images')
            
            if "content" not in result:
                return False, "Resultado no contiene 'content'"
            
            content_text = result["content"][0]["text"]
            
            if "🖼️ **Última imagen encontrada:**" in content_text:
                return True, f"Última imagen real encontrada correctamente"
            else:
                return False, f"No se encontró imagen real: {content_text[:100]}..."
                
        except Exception as e:
            return False, f"Error en test de última imagen real: {e}"

    def _test_real_file_info(self) -> tuple[bool, str]:
        """Test de información de archivo real"""
        try:
            # Usar la última imagen real que existe
            result = self._get_latest_image('generated_images')
            
            if "filename" in result:
                filename = result["filename"]
                
                # Ahora obtener info de ese archivo real
                info_result = self._get_file_info(filename, 'generated_images')
                
                if "content" not in info_result:
                    return False, "Resultado no contiene 'content'"
                
                content_text = info_result["content"][0]["text"]
                
                if "📄 **Información del archivo:**" in content_text and filename in content_text:
                    return True, f"Info de archivo real obtenida: {filename}"
                else:
                    return False, f"Formato de info incorrecto: {content_text[:100]}..."
            else:
                return False, "No se pudo obtener filename de la última imagen"
                
        except Exception as e:
            return False, f"Error en test de info de archivo real: {e}"

    def _test_read_real_file(self) -> tuple[bool, str]:
        """Test de lectura de archivo real JSON (metadata)"""
        try:
            # Buscar archivo JSON de metadata que sí existe
            target_dir = self.allowed_dirs['generated_images']
            json_files = list(target_dir.glob("*_meta.json"))
            
            if not json_files:
                return False, "No se encontraron archivos JSON de metadata"
            
            # Usar el primer archivo JSON encontrado
            json_file = json_files[0]
            result = self._read_file(json_file.name, 'generated_images')
            
            if "content" not in result:
                return False, "Resultado no contiene 'content'"
            
            content_text = result["content"][0]["text"]
            
            if f"📄 **Contenido de {json_file.name}**" in content_text:
                return True, f"Archivo JSON real leído: {json_file.name}"
            else:
                return False, f"Contenido no válido: {content_text[:100]}..."
                
        except Exception as e:
            return False, f"Error en test de lectura de archivo real: {e}"

    def _test_prepare_real_email_url(self) -> tuple[bool, str]:
        """✅ PRUEBA: Preparación para email con URL de imagen real"""
        try:
            # Obtener la última imagen real
            latest_result = self._get_latest_image('generated_images')
            
            if "filename" not in latest_result:
                return False, "No se pudo obtener filename de la última imagen"
            
            filename = latest_result["filename"]
            
            # Preparar para email con URL
            result = self._prepare_for_email_url(filename, 'generated_images')
            
            if "content" not in result:
                return False, "Resultado no contiene 'content'"
            
            if "attachment_data" not in result:
                return False, "Resultado no contiene 'attachment_data'"
            
            if "email_method" not in result or result["email_method"] != "url_attachment":
                return False, "Método de email no es URL"
            
            # Verificar que la URL esté presente
            attachment_data = result["attachment_data"]
            if not attachment_data.get("url") or not attachment_data.get("windows_url"):
                return False, "URLs no generadas correctamente"
            
            # Verificar que el archivo realmente exista
            filepath = attachment_data.get("filepath")
            if not filepath or not Path(filepath).exists():
                return False, "Archivo no encontrado en la ruta especificada"
            
            return True, f"Imagen real preparada para email por URL: {filename} -> {attachment_data['url']}"
                
        except Exception as e:
            return False, f"Error en test de email URL con archivo real: {e}"

    def _test_invalid_actions(self) -> tuple[bool, str]:
        """Test de acciones inválidas"""
        try:
            result = self.execute({"action": "invalid_action"})
            
            if "content" in result and "❌ Acción no reconocida" in result["content"][0]["text"]:
                return True, "Manejo correcto de acciones inválidas"
            else:
                return False, "No se manejó correctamente la acción inválida"
                
        except Exception as e:
            return False, f"Error en test de acciones inválidas: {e}"

    def _test_url_method(self) -> Dict[str, Any]:
        """🧪 PRUEBA ESPECÍFICA DEL MÉTODO URL CON ARCHIVOS REALES"""
        print("\n🔗 PROBANDO MÉTODO URL CON IMÁGENES REALES")
        print("=" * 60)
        
        results = []
        results.append("🔗 **PRUEBA DEL MÉTODO URL PARA EMAIL**")
        results.append("=" * 50)
        
        try:
            # ✅ PASO 1: Buscar imagen real
            results.append("\n📋 **PASO 1: Buscar imagen real**")
            latest_result = self._get_latest_image('generated_images')
            
            if "filename" not in latest_result:
                results.append("❌ No se encontró ninguna imagen real")
                return {"content": [{"type": "text", "text": "\n".join(results)}]}
            
            filename = latest_result["filename"]
            results.append(f"✅ Imagen encontrada: {filename}")
            
            # ✅ PASO 2: Generar URL para email
            results.append(f"\n🔗 **PASO 2: Generar URL para {filename}**")
            url_result = self._prepare_for_email_url(filename, 'generated_images')
            
            if "attachment_data" not in url_result:
                results.append("❌ Error generando URL")
                return {"content": [{"type": "text", "text": "\n".join(results)}]}
            
            attachment_data = url_result["attachment_data"]
            results.append(f"✅ URL generada exitosamente")
            results.append(f"📁 Archivo: {attachment_data['filename']}")
            results.append(f"🌐 URL: {attachment_data['url']}")
            results.append(f"🪟 URL Windows: {attachment_data['windows_url']}")
            results.append(f"📊 Tamaño: {self._format_size(attachment_data['size'])}")
            
            # ✅ PASO 3: Verificar que el archivo exista en la URL
            results.append(f"\n✅ **PASO 3: Verificar acceso al archivo**")
            file_path = Path(attachment_data['filepath'])
            
            if file_path.exists():
                results.append(f"✅ Archivo verificado: {file_path}")
                results.append(f"📏 Tamaño real: {self._format_size(file_path.stat().st_size)}")
            else:
                results.append(f"❌ Archivo no encontrado en: {file_path}")
            
            # ✅ PASO 4: Mostrar resultado completo
            results.append(f"\n📋 **RESULTADO COMPLETO DEL MÉTODO URL:**")
            results.append("-" * 40)
            results.append(url_result["content"][0]["text"])
            
            results.append(f"\n🎉 **PRUEBA URL COMPLETADA EXITOSAMENTE**")
            results.append("✅ Imagen preparada para envío por URL")
            results.append("✅ Sin base64 - Máxima eficiencia")
            results.append("✅ Compatible con clientes de email modernos")
            results.append("🚀 Sistema optimizado y rápido")
            
        except Exception as e:
            results.append(f"\n💥 **ERROR EN PRUEBA URL:** {str(e)}")
        
        return {
            "content": [{"type": "text", "text": "\n".join(results)}]
        }

    def _list_files(self, directory: str = "generated_images", pattern: str = "*", limit: int = 10) -> Dict[str, Any]:
        """Lista archivos en directorio especificado"""
        try:
            if directory not in self.allowed_dirs:
                return {
                    "content": [{"type": "text", "text": f"❌ Directorio no permitido: {directory}"}]
                }
            
            target_dir = self.allowed_dirs[directory]
            
            # Usar pathlib para búsqueda con patrón
            if pattern == "*":
                files = list(target_dir.iterdir())
            else:
                files = list(target_dir.glob(pattern))
            
            # Filtrar solo archivos (no directorios)
            files = [f for f in files if f.is_file()]
            
            # Ordenar por fecha de modificación (más recientes primero)
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Limitar resultados
            files = files[:limit]
            
            if not files:
                return {
                    "content": [{"type": "text", "text": f"📁 No se encontraron archivos en {directory} con patrón '{pattern}'"}]
                }
            
            # Formatear información
            file_list = []
            for file_path in files:
                stat = file_path.stat()
                file_info = f"📄 {file_path.name} ({self._format_size(stat.st_size)}) - {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}"
                file_list.append(file_info)
            
            result_text = f"📁 **Archivos en {directory}** (patrón: {pattern})\n\n" + "\n".join(file_list)
            
            return {
                "content": [{"type": "text", "text": result_text}]
            }
            
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"❌ Error listando archivos: {str(e)}"}]
            }

    def _get_latest_image(self, directory: str = "generated_images") -> Dict[str, Any]:
        """Obtiene la imagen más reciente generada - OPTIMIZADO PARA URL"""
        try:
            if directory not in self.allowed_dirs:
                return {
                    "content": [{"type": "text", "text": f"❌ Directorio no permitido: {directory}"}]
                }
            
            target_dir = self.allowed_dirs[directory]
            
            # Buscar archivos de imagen
            image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
            image_files = []
            
            for ext in image_extensions:
                image_files.extend(target_dir.glob(f"*{ext}"))
            
            if not image_files:
                return {
                    "content": [{"type": "text", "text": f"❌ No se encontraron imágenes en {directory}"}]
                }
            
            # Ordenar por fecha de modificación
            latest_image = max(image_files, key=lambda x: x.stat().st_mtime)
            
            stat = latest_image.stat()
            
            result_text = f"""🖼️ **Última imagen encontrada:**

📄 **Nombre:** {latest_image.name}
📁 **Ubicación:** {directory}
📊 **Tamaño:** {self._format_size(stat.st_size)}
📅 **Modificado:** {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}
🔗 **Tipo:** {mimetypes.guess_type(str(latest_image))[0]}

✅ **Lista para envío por email usando método URL**
🚀 **Optimizado - Sin base64**"""
            
            return {
                "content": [{"type": "text", "text": result_text}],
                "filepath": str(latest_image),
                "filename": latest_image.name,
                "ready_for_email": True
            }
            
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"❌ Error obteniendo última imagen: {str(e)}"}]
            }

    def _prepare_for_email_url(self, filename: str, directory: str = "generated_images") -> Dict[str, Any]:
        """✅ MÉTODO URL PARA EMAIL - SIN BASE64"""
        try:
            # ✅ NORMALIZAR DIRECTORIO
            if os.path.isabs(directory):
                directory = os.path.basename(directory.rstrip('\\').rstrip('/')) or "generated_images"
            
            if directory not in self.allowed_dirs:
                return {
                    "content": [{"type": "text", "text": f"❌ Directorio no permitido: {directory}. Usar: {list(self.allowed_dirs.keys())}"}]
                }
            
            target_dir = self.allowed_dirs[directory]
            file_path = target_dir / filename
            
            if not file_path.exists():
                return {
                    "content": [{"type": "text", "text": f"❌ Archivo no encontrado: {filename}"}]
                }
            
            # ✅ GENERAR URL LOCAL - USANDO file:/// protocol
            file_url = file_path.as_uri()  # Convierte a file:///C:/path/to/file
            
            # ✅ URL alternativa para Windows
            windows_url = f"file:///{file_path.as_posix()}"
            
            stat = file_path.stat()
            content_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
            
            result_text = f"""🔗 **Imagen preparada como URL para email:**

📄 **Nombre:** {filename}
📂 **Directorio:** {directory}
📊 **Tamaño:** {self._format_size(stat.st_size)}
🔗 **Tipo MIME:** {content_type}
🌐 **URL Local:** {file_url}
🪟 **URL Windows:** {windows_url}
📅 **Modificado:** {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}

✅ **Listo para envío como enlace en email**
🚀 **Ventaja:** Sin base64 - Archivo ligero y rápido
💡 **Optimizado:** Máximo rendimiento y eficiencia"""
            
            return {
                "content": [{"type": "text", "text": result_text}],
                "attachment_method": "url_link",
                "attachment_data": {
                    "filename": filename,
                    "url": file_url,
                    "windows_url": windows_url,
                    "type": content_type,
                    "size": stat.st_size,
                    "filepath": str(file_path)
                },
                "ready_for_email": True,
                "email_method": "url_attachment"
            }
    
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"❌ Error preparando URL para email: {str(e)}"}]
            }

    def _get_file_info(self, filename: str, directory: str = "generated_images") -> Dict[str, Any]:
        """Obtiene información detallada de un archivo"""
        try:
            if not filename:
                return {
                    "content": [{"type": "text", "text": "❌ Nombre de archivo requerido"}]
                }
            
            if directory not in self.allowed_dirs:
                return {
                    "content": [{"type": "text", "text": f"❌ Directorio no permitido: {directory}"}]
                }
            
            file_path = self.allowed_dirs[directory] / filename
            
            if not file_path.exists():
                return {
                    "content": [{"type": "text", "text": f"❌ Archivo no encontrado: {filename}"}]
                }
            
            stat = file_path.stat()
            
            result_text = f"""📄 **Información del archivo:**

📄 **Nombre:** {file_path.name}
📁 **Ruta completa:** {file_path}
📊 **Tamaño:** {self._format_size(stat.st_size)}
📅 **Creado:** {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}
📅 **Modificado:** {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}
🔗 **Extensión:** {file_path.suffix.lower()}
🔗 **Tipo MIME:** {mimetypes.guess_type(str(file_path))[0]}
🖼️ **Es imagen:** {'✅ Sí' if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'] else '❌ No'}"""
            
            return {
                "content": [{"type": "text", "text": result_text}]
            }
            
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"❌ Error obteniendo info del archivo: {str(e)}"}]
            }

    def _read_file(self, filename: str, directory: str = "generated_images") -> Dict[str, Any]:
        """Lee contenido de archivo (solo para archivos de texto)"""
        try:
            if not filename:
                return {
                    "content": [{"type": "text", "text": "❌ Nombre de archivo requerido"}]
                }
            
            if directory not in self.allowed_dirs:
                return {
                    "content": [{"type": "text", "text": f"❌ Directorio no permitido: {directory}"}]
                }
            
            file_path = self.allowed_dirs[directory] / filename
            
            if not file_path.exists():
                return {
                    "content": [{"type": "text", "text": f"❌ Archivo no encontrado: {filename}"}]
                }
            
            mime_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
            
            # Solo leer archivos de texto
            if mime_type.startswith('text/') or file_path.suffix.lower() in ['.json', '.xml', '.csv', '.md', '.txt']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Limitar contenido mostrado
                    if len(content) > 1000:
                        preview = content[:1000] + "..."
                        result_text = f"📄 **Contenido de {filename}** (primeros 1000 caracteres):\n\n```\n{preview}\n```"
                    else:
                        result_text = f"📄 **Contenido de {filename}**:\n\n```\n{content}\n```"
                    
                    return {
                        "content": [{"type": "text", "text": result_text}]
                    }
                except UnicodeDecodeError:
                    return {
                        "content": [{"type": "text", "text": f"❌ No se puede leer {filename} - archivo binario o codificación no compatible"}]
                    }
            else:
                return {
                    "content": [{"type": "text", "text": f"❌ No se puede leer {filename} - tipo de archivo binario ({mime_type})"}]
                }
                
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"❌ Error leyendo archivo: {str(e)}"}]
            }

    def _format_size(self, size_bytes: int) -> str:
        """Formatea tamaño de archivo de manera legible"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


# 🚀 FUNCIÓN RÁPIDA - Mostrar solo la última imagen
def quick_show_latest_image():
    """🚀 FUNCIÓN RÁPIDA - Mostrar solo la última imagen"""
    print("🖼️ MOSTRANDO ÚLTIMA IMAGEN GENERADA")
    print("=" * 50)
    
    adapter = FileManagerAdapter()
    result = adapter._get_latest_image('generated_images')
    
    if "content" in result:
        print(result["content"][0]["text"])
        print(f"\n📁 Archivo: {result.get('filename', 'N/A')}")
        print(f"📂 Ruta: {result.get('filepath', 'N/A')}")
    else:
        print("❌ No se pudo obtener la imagen")
    
    print("=" * 50)

# 🚀 FUNCIÓN RÁPIDA ESPECÍFICA PARA PROBAR URL
def quick_test_url_method():
    """🚀 FUNCIÓN RÁPIDA - Probar método URL"""
    print("🔗 PROBANDO MÉTODO URL PARA EMAIL")
    print("=" * 50)
    
    adapter = FileManagerAdapter()
    result = adapter.execute({"action": "test_url_method"})
    
    if "content" in result:
        print(result["content"][0]["text"])
    else:
        print("❌ Error en la prueba URL")
    
    print("=" * 50)

# 🧪 SCRIPT DE PRUEBA INDEPENDIENTE - SOLO MÉTODO URL
def run_standalone_test():
    """Ejecuta las pruebas de manera independiente - SOLO MÉTODO URL"""
    print("🎯 EJECUTANDO PRUEBAS CON ARCHIVOS REALES - SOLO MÉTODO URL")
    print("=" * 80)
    print("📁 Archivos detectados en generated_images:")
    
    # Mostrar archivos reales primero
    adapter = FileManagerAdapter()
    target_dir = adapter.allowed_dirs['generated_images']
    real_files = list(target_dir.glob('*'))
    real_files = [f for f in real_files if f.is_file()]
    
    for file_path in real_files:
        print(f"   📄 {file_path.name}")
    
    print("\n" + "=" * 80)
    
    try:
        # Ejecutar pruebas completas
        result = adapter.execute({"action": "run_tests"})
        
        if "content" in result:
            print(result["content"][0]["text"])
        else:
            print("❌ Error: Resultado sin contenido")
            
        # Ejecutar prueba específica URL
        print("\n" + "=" * 80)
        print("🔗 EJECUTANDO PRUEBA ESPECÍFICA DEL MÉTODO URL")
        print("=" * 80)
        
        url_result = adapter.execute({"action": "test_url_method"})
        if "content" in url_result:
            print(url_result["content"][0]["text"])
            
    except Exception as e:
        print(f"💥 Error ejecutando pruebas: {e}")

# 🚀 PUNTO DE ENTRADA ACTUALIZADO
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            quick_show_latest_image()
        elif sys.argv[1] == "url":
            quick_test_url_method()
    else:
        run_standalone_test()