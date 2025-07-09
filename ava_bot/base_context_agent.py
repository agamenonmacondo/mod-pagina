from ava_graph_state import AgentState
from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, List, Any
import re

class BaseContextAgent:
    """Clase base para manejo estandarizado de contexto"""
    
    def get_complete_context(self, state: AgentState) -> Dict[str, Any]:
        """Extraer contexto completo"""
        return {
            'messages': state.get("messages", []),
            'conversation_history': state.get("conversation_history", []),
            'context_memory': state.get("context_memory", []),
            'tool_result': state.get("tool_result", ""),
            'session_id': state.get("session_id", "unknown"),
            'user_id': state.get("user_id", "default"),
            'execution_plan': state.get("execution_plan", {}),
            'plan_status': state.get("plan_status", {}),
            'available_tools': state.get("available_tools", {}),
            'timestamp': state.get("timestamp", "")
        }

    def format_full_conversation_context(self, conversation_history: List) -> str:
        """Formateo estándar de contexto conversacional"""
        if not conversation_history:
            return "📝 **ESTADO:** Primera conversación\n"
        
        context_text = "📚 **HISTORIAL COMPLETO DE CONVERSACIÓN:**\n"
        context_text += "=" * 70 + "\n"
        
        for i, msg in enumerate(conversation_history):
            if hasattr(msg, 'content') and msg.content:
                role = "👤 USUARIO" if isinstance(msg, HumanMessage) else "🤖 AVA"
                content = str(msg.content)
                
                if len(content) > 800:
                    content = content[:800] + "..."
                
                context_text += f"{role}: {content}\n"
                context_text += "-" * 60 + "\n"
        
        context_text += "=" * 70 + "\n"
        
        return context_text

    def extract_all_specific_data(self, context: Dict[str, Any]) -> Dict[str, List]:
        """Extracción de datos específicos"""
        extracted = {
            'queries': [],
            'tools_executed': [],
            'urls': [],
            'prices': [],
            'dates': [],
            'locations': [],
            'hotels': [],
            'activities': [],
            'models': [],
            'specific_info': []
        }
        
        # Procesar conversation_history
        for msg in context['conversation_history']:
            if hasattr(msg, 'content') and msg.content:
                content = str(msg.content)
                self._extract_from_text(content, extracted)
        
        # Procesar context_memory
        if isinstance(context['context_memory'], list):
            for mem in context['context_memory']:
                if isinstance(mem, dict):
                    extracted['queries'].append(mem.get('user_query', ''))
                    tools = mem.get('tools_executed', [])
                    if isinstance(tools, list):
                        extracted['tools_executed'].extend(tools)
        
        # Procesar tool_result
        if context['tool_result']:
            self._extract_from_text(context['tool_result'], extracted)
        
        return extracted
    
    def _extract_from_text(self, text: str, extracted: Dict[str, List]):
        """Extraer información específica"""
        urls = re.findall(r'https?://[^\s\'"]+', text)
        extracted['urls'].extend(urls)
        
        prices = re.findall(r'\$[\d,]+\.?\d*', text)
        extracted['prices'].extend(prices)
        
        dates = re.findall(r'\d{1,2}\s+de\s+\w+|\d{1,2}/\d{1,2}/\d{4}|17\s+de\s+julio', text)
        extracted['dates'].extend(dates)
        
        hotels = re.findall(r'(Hotel\s+\w+(?:\s+\w+)*|Casa\s+de\s+Alba|GHL\s+San\s+Lazaro)', text, re.IGNORECASE)
        extracted['hotels'].extend(hotels)
        
        activities = re.findall(r'(Ciudad Amurallada|Castillo San Felipe|Torre del Reloj|Plaza de la Aduana|Bocagrande|Getsemaní|Cartagena)', text, re.IGNORECASE)
        extracted['activities'].extend(activities)

    def format_extracted_data(self, extracted: Dict[str, List]) -> str:
        """Formatear datos extraídos"""
        formatted = "📊 **DATOS ESPECÍFICOS:**\n\n"
        
        if extracted['urls']:
            formatted += f"🔗 **URLs:** {chr(10).join(list(set(extracted['urls'][:5])))}\n\n"
        
        if extracted['prices']:
            formatted += f"💰 **PRECIOS:** {', '.join(list(set(extracted['prices'])))}\n\n"
        
        if extracted['dates']:
            formatted += f"📅 **FECHAS:** {', '.join(list(set(extracted['dates'])))}\n\n"
        
        if extracted['hotels']:
            formatted += f"🏨 **HOTELES:** {', '.join(list(set(extracted['hotels'])))}\n\n"
        
        if extracted['activities']:
            formatted += f"🎯 **ACTIVIDADES:** {', '.join(list(set(extracted['activities'])))}\n\n"
        
        if extracted['tools_executed']:
            formatted += f"🔧 **HERRAMIENTAS:** {', '.join(list(set(extracted['tools_executed'])))}\n\n"
        
        return formatted