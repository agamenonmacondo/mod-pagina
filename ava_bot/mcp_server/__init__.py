"""
MCP Server para Ava Bot Tools
=============================

Este módulo convierte los adapters existentes de Ava Bot en un servidor MCP
(Model Context Protocol) compatible con cualquier cliente MCP.

Arquitectura:
- server.py: Core del servidor MCP (protocolo JSON-RPC)
- tool_registry.py: Registro automático de herramientas
- adapters/: Wrappers MCP para adapters existentes
"""

__version__ = "1.0.0"
__author__ = "Ava Bot Team"
