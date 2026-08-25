"""
Configuration management for AutoCAD MCP Server.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration from environment variables."""
    
    # Server configuration
    HOST: str = "localhost"
    PORT: int = 5001
    DEBUG: bool = False
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/mcp.log"
    
    # AutoCAD configuration
    AUTOCAD_TIMEOUT: float = 30.0
    AUTOCAD_VISIBLE: bool = True
    
    # Surface unfolding configuration
    UNFOLD_MAX_FACES: int = 10000
    UNFOLD_DEFAULT_TOLERANCE: float = 0.01
    
    # Performance limits
    MAX_CONCURRENT_REQUESTS: int = 5
    REQUEST_TIMEOUT: float = 300.0  # 5 minutes for complex operations
    
    @classmethod
    def from_environment(cls) -> 'Config':
        """Create configuration from environment variables."""
        return cls(
            HOST=os.getenv('MCP_HOST', 'localhost'),
            PORT=int(os.getenv('MCP_PORT', '5001')),
            DEBUG=os.getenv('MCP_DEBUG', 'false').lower() == 'true',
            LOG_LEVEL=os.getenv('MCP_LOG_LEVEL', 'INFO'),
            LOG_FILE=os.getenv('MCP_LOG_FILE', 'logs/mcp.log'),
            AUTOCAD_TIMEOUT=float(os.getenv('AUTOCAD_TIMEOUT', '30.0')),
            AUTOCAD_VISIBLE=os.getenv('AUTOCAD_VISIBLE', 'true').lower() == 'true',
            UNFOLD_MAX_FACES=int(os.getenv('UNFOLD_MAX_FACES', '10000')),
            UNFOLD_DEFAULT_TOLERANCE=float(os.getenv('UNFOLD_DEFAULT_TOLERANCE', '0.01')),
            MAX_CONCURRENT_REQUESTS=int(os.getenv('MAX_CONCURRENT_REQUESTS', '5')),
            REQUEST_TIMEOUT=float(os.getenv('REQUEST_TIMEOUT', '300.0'))
        )


# Global configuration instance
config = Config.from_environment()