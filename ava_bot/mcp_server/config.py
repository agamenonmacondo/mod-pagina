"""
MCP Server Configuration
========================

Configuración para el servidor MCP de Ava Bot
"""

# Server Configuration
SERVER_CONFIG = {
    "name": "ava-bot-mcp-server",
    "version": "1.0.0",
    "description": "Ava Bot Tools MCP Server - Calendar, Gmail, Search, Meet, Drive, Images",
    "protocol_version": "2024-11-05"
}

# Tools Configuration
TOOLS_CONFIG = {
    "auto_discovery": True,
    "adapters_directory": "tools/adapters",
    "enabled_tools": [
        "calendar",
        "meet", 
        "gmail",
        "search",
        "drive",
        "image",
        "calendar_check"
    ]
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "handlers": ["console", "file"],
    "file_path": "mcp_server.log"
}

# Security Configuration
SECURITY_CONFIG = {
    "require_authentication": False,  # Para desarrollo
    "allowed_origins": ["*"],
    "rate_limiting": {
        "enabled": False,
        "requests_per_minute": 60
    }
}

# Feature Flags
FEATURES = {
    "resources": False,      # Implementación futura
    "prompts": False,        # Implementación futura
    "progress": False,       # Implementación futura
    "sampling": False,       # Implementación futura
    "logging": True
}
