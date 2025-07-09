from ava_client import get_global_ava_client
from ava_graph_state import AgentState
from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, Any, List
import json
import re
from groq import Groq
import os
from base_context_agent import BaseContextAgent

# ✅ IMPORTACIÓN CORRECTA - Importa la clase, no la función
from mcp_server.run_server import CleanMCPServer

class OrchestratorNode(BaseContextAgent):
    """Nodo coordinador que ejecuta planes paso a paso"""
    
    def __init__(self):
        self.name = "orchestrator"
        self.groq_client = Groq(
            api_key=os.getenv("GROQ_API_KEY", "your-groq-api-key"),
            base_url=os.getenv("GROQ_API_URL", "https://api.groq.com")
        )
        
        # ✅ SOLO INICIALIZAR MCP SERVER PARA SCHEMAS
        try:
            self.mcp_server = CleanMCPServer()
            tools_list = self.mcp_server.get_available_tools()
            
            self.tool_schemas = {}
            if isinstance(tools_list, list):
                for tool in tools_list:
                    if isinstance(tool, dict) and 'name' in tool:
                        tool_name = tool['name']
                        self.tool_schemas[tool_name] = tool
                
                print(f"✅ Schemas cargados: {list(self.tool_schemas.keys())}")
        except Exception as e:
            print(f"❌ Error cargando schemas: {e}")
            self.tool_schemas = {}

    def process(self, state: AgentState) -> AgentState:
        """🎯 PROCESO PRINCIPAL del orchestrator - CON LLM"""
        try:
            print("ORCHESTRATOR INICIANDO COORDINACION DE EJECUCION")
            
            # OBTENER PLAN ACTUAL
            execution_plan = state.get("execution_plan", {})
            
            if not execution_plan or "execution_plan" not in execution_plan:
                print("❌ No hay plan de ejecución disponible")
                state["node"] = "orchestrator_error"
                return state
            
            plan_data = execution_plan["execution_plan"]
            steps = plan_data.get("steps", [])
            total_steps = len(steps)
            project_type = plan_data.get("project_type", "")

            # 🔧 DETECTAR SI ES UN PLAN COMPLETAMENTE NUEVO
            current_project = state.get("plan_status", {}).get("project_type", "")
            if current_project != project_type:
                print(f"🔄 NUEVO TIPO DE PLAN DETECTADO: {project_type} (anterior: {current_project})")
                print("🔄 RESETEANDO PLAN STATUS PARA NUEVO PROYECTO...")
                state["plan_status"] = {
                    "current_step": 0,
                    "completed": False,
                    "results": [],
                    "step_results": {},
                    "project_type": project_type  # ← NUEVO CAMPO
                }
            elif "plan_status" not in state:
                print("🆕 INICIALIZANDO PLAN STATUS")
                state["plan_status"] = {
                    "current_step": 0,
                    "completed": False, 
                    "results": [],
                    "step_results": {},
                    "project_type": project_type  # ← NUEVO CAMPO
                }
            else:
                print("📍 CONTINUANDO CON PLAN EXISTENTE")
            
            # 🔧 LÓGICA SIMPLE SIN VALIDACIONES EXCESIVAS
            if not state.get("plan_status"):
                state["plan_status"] = {
                    "current_step": 0,
                    "completed": False,
                    "results": [],
                    "step_results": {}
                }

            plan_status = state["plan_status"]
            current_step_index = plan_status.get("current_step", 0)
            
            print(f"ORCHESTRATOR: Procesando paso {current_step_index + 1} de {total_steps} pasos totales")
            print(f"DEBUG: current_step_index={current_step_index}, total_steps={total_steps}")
            
            # VERIFICAR SI EL PLAN ESTÁ COMPLETADO
            if current_step_index >= total_steps:
                print("ORCHESTRATOR: Todos los pasos han sido ejecutados")
                state["plan_status"]["completed"] = True
                state["node"] = "orchestrator_completed"
                return state
            
            # OBTENER PASO ACTUAL
            current_step = steps[current_step_index]
            step_number = current_step.get("step_number", current_step_index + 1)
            objective = current_step.get("objective", "Sin objetivo")
            tool_name = current_step.get("tool", "").lower()
            arguments = current_step.get("arguments", {})
            
            print(f"   Ejecutando paso {step_number}: {objective}")
            print(f"   Herramienta: {tool_name}")
            print(f"   Argumentos originales: {arguments}")
            
            # 🤖 USAR LLM PARA OPTIMIZAR ARGUMENTOS
            optimized_arguments = self._optimize_arguments_with_llm(
                arguments, state, tool_name, objective
            )
            
            # ✅ CONFIGURAR HERRAMIENTA PARA EJECUCIÓN
            state["tool_to_execute"] = tool_name  
            state["tool_arguments"] = optimized_arguments
            state["current_step_info"] = {
                "step_number": step_number,
                "objective": objective,
                "tool": tool_name
            }
            state["node"] = "orchestrator_step_ready"
            
            print(f"✅ PASO CONFIGURADO PARA EJECUCIÓN:")
            print(f"   🔧 Herramienta: {tool_name}")
            print(f"   📝 Argumentos optimizados: {optimized_arguments}")
            
            return state
        
        except Exception as e:
            print(f"❌ Error en orchestrator: {e}")
            import traceback
            traceback.print_exc()
            state["node"] = "orchestrator_error"
            state["error_message"] = f"Error en orchestrator: {e}"
            return state
    
    def _build_context_for_llm(self, state: AgentState, tool_name: str, objective: str) -> str:
        """CONTEXTO COMPLETO PARA OPTIMIZACIÓN"""
        
        # ✅ AGREGAR: USAR BaseContextAgent PARA EXTRAER DATOS
        context = self.get_complete_context(state)
        extracted_data = self.extract_all_specific_data(context)
        formatted_data = self.format_extracted_data(extracted_data)
        
        conversation_history = state.get("conversation_history", [])
        context_memory = state.get("context_memory", {})

        context_parts = [
            "=== CONTEXTO DE CONVERSACIÓN ===",
            ""
        ]
        
        # ✅ AGREGAR: INCLUIR DATOS EXTRAÍDOS
        if formatted_data.strip() != "📊 **DATOS ESPECÍFICOS:**":
            context_parts.append("=== INFORMACIÓN ESPECÍFICA DISPONIBLE ===")
            context_parts.append(formatted_data)
        
        # Existing logic for conversation_history and context_memory
        if conversation_history:
            context_parts.append("HISTORIAL DE CONVERSACIÓN:")
            for i, message in enumerate(conversation_history[-3:]):
                if hasattr(message, 'content'):
                    role = "Usuario" if isinstance(message, HumanMessage) else "Asistente"
                    content = str(message.content)[:200]
                    context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)

    def _optimize_arguments_with_llm(self, arguments: dict, state: AgentState, tool_name: str, objective: str) -> dict:
        """USAR LLM GROQ + LLAMA MAVERICK PARA OPTIMIZAR ARGUMENTOS"""
        try:
            # ⚠️ EXCEPCIÓN ESPECIAL PARA VISION: NO OPTIMIZAR RUTAS DE ARCHIVOS
            if tool_name.lower() == "vision" and "image_path" in arguments:
                image_path = arguments.get("image_path", "")
                # Si la ruta contiene una ruta completa, NO optimizar
                if os.path.sep in image_path or ":" in image_path:
                    print(f"🔒 VISION: Preservando ruta completa sin optimización: {image_path}")
                    return arguments
            
            # Construir contexto para el LLM
            context_text = self._build_context_for_llm(state, tool_name, objective)
            
            # ✅ OBTENER SCHEMA ESPECÍFICO DE LA HERRAMIENTA
            tool_schema_info = self._get_tool_schema_formatted(tool_name)

            conversation_history = state.get("conversation_history", [])
            context_memory = state.get("context_memory", {})
            
            # ✅ AGREGAR: EXTRAER INFORMACIÓN PARA EL PROMPT
            context = self.get_complete_context(state)
            extracted_data = self.extract_all_specific_data(context)
            
            # ✅ CREAR SECCIÓN DE INFORMACIÓN PARA INCLUIR EN EL PROMPT
            info_for_email = ""
            if tool_name.lower() == "gmail" and any(extracted_data.values()):
                info_for_email = f"""
=== INFORMACIÓN PARA INCLUIR EN EL EMAIL ===
INFORMACIÓN DEL HISTORIAL:
Información sobre la consulta realizada.

RESULTADOS DE HERRAMIENTAS EJECUTADAS:
{self._format_tool_results_for_email(state)}

=== FIN INFORMACIÓN PARA EMAIL ===
"""
            
            # PROMPT ESPECÍFICO PARA OPTIMIZACIÓN DE ARGUMENTOS
            system_prompt = f"""Eres un asistente experto en optimizar argumentos para herramientas automatizadas.

TU TAREA:
1. Analizar el contexto de la conversación
2. Optimizar los argumentos de la herramienta {tool_name.upper()}
3. USAR ÚNICAMENTE los campos especificados en el schema
4. Para Gmail: SIEMPRE extraer información relevante del historial y crear un email completo
5. Para Search: Mejorar las queries con contexto específico
6. Para Playwright: Optimizar URLs y queries de extracción
7. Para Vision: NUNCA modificar rutas completas de archivos (image_path)

SCHEMA DE LA HERRAMIENTA {tool_name.upper()}:
{tool_schema_info}

INSTRUCCIONES ESPECÍFICAS PARA GMAIL:
- USAR ÚNICAMENTE los campos del schema: "to", "subject", "body"
- NO incluir campo "action" - no está en el schema de Gmail
- El body DEBE incluir información detallada del historial y resultados
- Usar formato profesional con saludo y despedida
- Subject debe ser descriptivo y específico

INSTRUCCIONES ESPECÍFICAS PARA VISION:
- Si image_path contiene una ruta completa (con \\ o /), NO la modifiques
- Solo optimiza otros campos como "task" o "action"
- PRESERVA EXACTAMENTE las rutas de archivos

CONTEXTO DE LA CONVERSACIÓN:
{context_text}

{info_for_email}

ARGUMENTOS ORIGINALES:
{json.dumps(arguments, indent=2)}

HERRAMIENTA: {tool_name.upper()}
OBJETIVO: {objective}

RESPONDE SOLO CON UN JSON VÁLIDO CON LOS ARGUMENTOS OPTIMIZADOS USANDO ÚNICAMENTE LOS CAMPOS DEL SCHEMA:"""
            
            user_prompt = f"Optimiza estos argumentos para {tool_name} considerando el contexto completo de la conversación."
            
            print("Consultando LLM para optimizar argumentos...")
            
            # IMPRIMIR PROMPT ENVIADO AL LLM
            print("=" * 80)
            print("SYSTEM PROMPT ENVIADO AL LLM:")
            print("=" * 80)
            print(system_prompt)
            print("=" * 80)
            print("USER PROMPT ENVIADO AL LLM:")
            print("=" * 80)
            print(user_prompt)
            print("=" * 80)
            
            # Llamar a Groq con Llama Maverick
            response = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            llm_response = response.choices[0].message.content.strip()
            
            # IMPRIMIR RESPUESTA COMPLETA EN TERMINAL
            print("=" * 80)
            print("RESPUESTA COMPLETA DEL LLM ORCHESTRATOR:")
            print("=" * 80)
            print(llm_response)
            print("=" * 80)
            print("FIN RESPUESTA LLM")
            print("=" * 80)
            
            # Parsear la respuesta JSON
            optimized_args = self._parse_llm_response(llm_response, arguments)
            
            # ⚠️ VERIFICACIÓN ADICIONAL PARA VISION: Restaurar ruta original si fue modificada
            if tool_name.lower() == "vision" and "image_path" in arguments and "image_path" in optimized_args:
                original_path = arguments["image_path"]
                optimized_path = optimized_args["image_path"]
                
                # Si la ruta original era completa pero la optimizada no, restaurar
                if (os.path.sep in original_path or ":" in original_path) and original_path != optimized_path:
                    print(f"🔧 VISION: Restaurando ruta original: {original_path}")
                    optimized_args["image_path"] = original_path
            
            print("Argumentos optimizados por LLM")
            return optimized_args
        
        except Exception as e:
            print(f"Error al optimizar con LLM: {e}")
            print("Usando optimización de respaldo...")
            return self._fallback_optimization(arguments, state, tool_name)

    def _format_tool_results_for_email(self, state: AgentState) -> str:
        """Formatear resultados de herramientas para emails"""
        tool_result = state.get("tool_result", "")
        if not tool_result:
            return "No hay resultados disponibles."
        
        # ✅ USAR BaseContextAgent PARA EXTRAER DATOS
        context = self.get_complete_context(state)
        extracted_data = self.extract_all_specific_data(context)
        
        formatted = ""
        if extracted_data['urls']:
            formatted += f"Enlaces encontrados: {chr(10).join(extracted_data['urls'][:3])}\n"
        if extracted_data['prices']:
            formatted += f"Precios mencionados: {', '.join(extracted_data['prices'])}\n"
        if extracted_data['hotels']:
            formatted += f"Hoteles encontrados: {', '.join(extracted_data['hotels'])}\n"
        
        return formatted if formatted else tool_result[:500]

    def _get_tool_schema_formatted(self, tool_name: str) -> str:
        """Obtener schema formateado de una herramienta específica"""
        if tool_name not in self.tool_schemas:
            return f"Schema para {tool_name} no encontrado - usar campos básicos disponibles"
        
        schema = self.tool_schemas[tool_name]
        input_schema = schema.get('inputSchema', {})
        required_fields = input_schema.get('required', [])
        properties = input_schema.get('properties', {})
        
        formatted_schema = f"""
HERRAMIENTA: {tool_name}
DESCRIPCIÓN: {schema.get('description', 'Sin descripción')}

CAMPOS REQUERIDOS: {required_fields}

PROPIEDADES DISPONIBLES:"""
        
        for field_name, field_info in properties.items():
            field_type = field_info.get('type', 'unknown')
            field_desc = field_info.get('description', 'Sin descripción')
            formatted_schema += f"\n  - {field_name} ({field_type}): {field_desc}"
        
        # Corregir el schema de Playwright para usar acciones reales:
        if tool_name == "playwright":
            return """
HERRAMIENTA: playwright
DESCRIPCIÓN: Automatización web universal con JavaScript inteligente

CAMPOS REQUERIDOS: ["action"]
CAMPOS OPCIONALES: ["url", "search_query", "max_results", "selector"]

Para la herramienta vision, cuando recibas un image_path que sea solo un nombre de archivo:
- Directorio base de trabajo: c:\\Users\\h\\Downloads\\pagina ava\\ava_bot\\
- Buscar primero en: shared_files/[filename]
- Si no existe, buscar en: [filename] 
- Si no existe, buscar en: ../uploads/images/[filename]

Ejemplo: si image_path es "imagen.png", usar "shared_files/imagen.png" como ruta preferida.

ACCIONES INTELIGENTES DISPONIBLES:
• smart_extract - Extracción automática adaptada al sitio (RECOMENDADO)
• auto_search - Búsqueda automática con query
• analyze_site - Análisis completo de sitio web

ACCIONES TRADICIONALES:
• navigate - Navegar a URL
• extract_text - Extraer texto (requiere url + selector)
• take_screenshot - Capturar pantalla
• execute_js - Ejecutar JavaScript

EJEMPLO CORRECTO PARA VUELOS:
{
    "action": "smart_extract",
    "url": "https://www.despegar.com.co",
    "search_query": "vuelos Bogotá Cartagena mañana",
    "max_results": 10
}

⚠️ NUNCA USAR: fill_input, click_element, extract_prices (NO EXISTEN)
"""
        
        return formatted_schema

    def _validate_arguments(self, tool_name: str, arguments: dict) -> dict:
        """Validar argumentos contra schema real - SIN OPTIMIZACIÓN"""
        if tool_name not in self.tool_schemas:
            print(f"⚠️ Schema para {tool_name} no encontrado")
            # 🔧 SCHEMAS BÁSICOS PARA HERRAMIENTAS CRÍTICAS
            if tool_name == "playwright":
                print("   Usando schema básico de Playwright: url requerido")
                if "url" not in arguments and ("action" in arguments or not arguments):
                    # Si no hay URL pero hay action o está vacío, es inválido
                    print("   ❌ Argumentos inválidos para Playwright - se requiere URL")
                    return {"url": "https://www.google.com/search?q=busqueda+general"}
            return arguments
        
        schema = self.tool_schemas[tool_name]
        input_schema = schema.get('inputSchema', {})
        required_fields = input_schema.get('required', [])
        properties = input_schema.get('properties', {})
        
        print(f"📋 Schema {tool_name}:")
        print(f"   Campos requeridos: {required_fields}")
        print(f"   Propiedades disponibles: {list(properties.keys())}")
        
        validated_args = {}
        validation_errors = []
        
        # ✅ Verificar campos requeridos
        for required_field in required_fields:
            if required_field in arguments:
                validated_args[required_field] = arguments[required_field]
            else:
                validation_errors.append(f"Campo requerido '{required_field}' faltante")
        
        # ✅ Agregar campos opcionales válidos
        for arg_name, arg_value in arguments.items():
            if arg_name in properties:
                validated_args[arg_name] = arg_value
            else:
                print(f"⚠️ Campo '{arg_name}' no está en schema - removido")
        
        if validation_errors:
            print(f"❌ ERRORES DE VALIDACIÓN para {tool_name}:")
            for error in validation_errors:
                print(f"   - {error}")
            
            # 🔧 CORRECCIÓN AUTOMÁTICA PARA CASOS CRÍTICOS
            if tool_name == "playwright" and "url" not in validated_args:
                print("   🔧 Auto-corrección: agregando URL por defecto")
                validated_args["url"] = "https://www.google.com/search?q=busqueda+web"
        
        print(f"✅ Argumentos validados: {validated_args}")
        return validated_args

    def _fallback_optimization(self, arguments: dict, state: AgentState, tool_name: str) -> dict:
        """Optimización de respaldo sin LLM"""
        print(f"   🔄 Usando optimización de respaldo para {tool_name}")
        optimized = arguments.copy()
        
        if tool_name == "gmail":
            # Extraer información del state
            conversation_history = state.get("conversation_history", [])
            plan_status = state.get("plan_status", {})
            results = plan_status.get("results", [])
            
            # Crear contenido detallado del email
            email_content = self._create_comprehensive_email_content(conversation_history, results)
            
            # ✅ USAR SOLO LOS CAMPOS QUE ACEPTA GMAIL (según schema)
            optimized = {
                "to": optimized.get("to", "agamenonmacondo@gmail.com"),
                "subject": optimized.get("subject", "Resultados de búsqueda"),
                "body": email_content,
                # ❌ NO incluir "action" - no está en el schema
            }
            
            print(f"   📧 Email optimizado con fallback - Body: {len(email_content)} chars")
        
        elif tool_name == "search":
            if "query" in optimized:
                original_query = optimized["query"]
                optimized["query"] = f"{original_query} precio características"
                print(f"   🔍 Query mejorada: {optimized['query']}")
        
        return optimized

    def _format_tool_result_for_email(self, tool_name: str, tool_data: str) -> str:
        """Formatear resultado de herramienta para incluir en email"""
        try:
            if tool_name == "SEARCH":
                # 🔧 EXTRAER DATOS REALES DE LA BÚSQUEDA
                lines = tool_data.split('\n')
                relevant_lines = []
                
                for line in lines:
                    line = line.strip()
                    # Buscar líneas con información útil
                    if any(keyword in line.lower() for keyword in 
                           ['ltd', 'ec-', 'amazon', 'precio', 'price', '$', 'usd', 'cop', 'http', 'enlace', 'link']):
                        if len(line) > 20:  # Evitar líneas muy cortas
                            relevant_lines.append(f"  • {line}")
                    
                    # También buscar modelos específicos
                    elif any(model in line.lower() for model in 
                             ['ec-1000', 'ec-400', 'ec-256', 'esp ltd']):
                        if len(line) > 15:
                            relevant_lines.append(f"  • {line}")
                
                if relevant_lines:
                    return f"Resultados específicos encontrados:\n" + "\n".join(relevant_lines[:12])
                else:
                    # Si no encuentra líneas específicas, usar más del contenido original
                    return f"Datos de búsqueda:\n{tool_data[:800]}..."
            
            elif tool_name == "PLAYWRIGHT":
                # Extraer datos reales de playwright
                if "Error" not in tool_data and len(tool_data) > 30:
                    return f"Información extraída del sitio web:\n{tool_data[:600]}..."
                else:
                    return "Extracción web completada con algunos problemas técnicos"
            
            else:
                # Otros tipos de herramientas - usar contenido real
                return f"Resultado de {tool_name}:\n{tool_data[:400]}..."
        
        except Exception as e:
            print(f"Error formateando resultado: {e}")
            return f"Datos procesados de {tool_name} (error en formateo)"

    def _create_comprehensive_email_content(self, conversation_history: list, results: list) -> str:
        """Crear contenido completo del email basado en resultados reales"""
        email_parts = []
        
        email_parts.append("¡Hola!")
        email_parts.append("")
        email_parts.append("Te envío los resultados de tu búsqueda de guitarra LTD en Amazon:")
        email_parts.append("")
        
        # 🔧 PROCESAR RESULTADOS REALES DE HERRAMIENTAS
        if results:
            search_found = False
            playwright_found = False
            
            for i, result in enumerate(results, 1):
                tool_used = result.get('tool', 'UNKNOWN').upper()
                success = result.get('success', False)
                tool_data = result.get('result', '')
                
                if success and tool_data and len(tool_data) > 20:
                    if tool_used == 'SEARCH':
                        search_found = True
                        email_parts.append(f"🔍 **RESULTADOS DE BÚSQUEDA EN AMAZON:**")
                        
                        # 🔧 EXTRAER INFORMACIÓN ESPECÍFICA DE LTD
                        lines = tool_data.split('\n')
                        guitar_info = []
                        
                        for line in lines:
                            line = line.strip()
                            if any(keyword in line.lower() for keyword in 
                                   ['ltd', 'ec-', 'esp', 'amazon', 'precio', '$']):
                                if len(line) > 25:
                                    guitar_info.append(f"• {line}")
                        
                        if guitar_info:
                            email_parts.extend(guitar_info[:8])  # Máximo 8 líneas
                        else:
                            # Si no encuentra guitarras específicas, usar contenido general
                            email_parts.append("• Búsqueda completada - se encontraron varios resultados")
                            email_parts.append(f"• Contenido: {tool_data[:300]}...")
                        
                        email_parts.append("")
                    
                    elif tool_used == 'PLAYWRIGHT':
                        playwright_found = True
                        email_parts.append(f"🎭 **EXTRACCIÓN DE PRECIOS Y ENLACES:**")
                        
                        if "Error" not in tool_data:
                            # Usar datos reales de playwright
                            email_parts.append(f"• {tool_data[:400]}...")
                        else:
                            email_parts.append("• Se encontraron algunos problemas técnicos")
                        
                        email_parts.append("")
        
        # Si no se encontraron datos específicos
        if not search_found and not playwright_found:
            email_parts.append("⚠️ **NOTA:** Los resultados de búsqueda están disponibles pero requieren procesamiento manual.")
            email_parts.append("")
        
        # 🔧 AGREGAR ENLACES Y RECOMENDACIONES
        email_parts.append("🔗 **ENLACES RECOMENDADOS:**")
        email_parts.append("• Amazon: https://amazon.com/s?k=ESP+LTD+guitarra")
        email_parts.append("• Buscar EC-1000: https://amazon.com/s?k=ESP+LTD+EC-1000")
        email_parts.append("• Buscar EC-400: https://amazon.com/s?k=ESP+LTD+EC-400")
        email_parts.append("")
        
        # Cierre del email
        email_parts.append("Espero que esta información te sea útil para tu compra.")
        email_parts.append("Si necesitas más detalles específicos, no dudes en contactarme.")
        email_parts.append("")
        email_parts.append("Saludos cordiales,")
        email_parts.append("Ava Assistant")
        
        return "\n".join(email_parts)

    def _parse_llm_response(self, llm_response: str, fallback_arguments: dict) -> dict:
        """Parsear respuesta JSON del LLM"""
        try:
            # Buscar JSON en la respuesta
            import re
            
            # Buscar bloques de código JSON
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Buscar JSON directo
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No se encontró JSON en la respuesta")
            
            # Parsear JSON
            parsed_json = json.loads(json_str)
            print(f"   ✅ JSON parseado exitosamente")
            return parsed_json
            
        except Exception as e:
            print(f"   ❌ Error parseando JSON: {e}")
            print(f"   🔄 Usando argumentos originales como fallback")
            return fallback_arguments

def create_orchestrator_node():
    """Crear nodo orchestrator"""
    orchestrator = OrchestratorNode()
    return orchestrator.process