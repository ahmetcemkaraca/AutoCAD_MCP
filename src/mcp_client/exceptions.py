"""
Exception classes for MCP Client Library.
"""

from typing import Optional, Dict, Any


class McpError(Exception):
    """Base exception for MCP client errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {super().__str__()}"
        return super().__str__()


class McpConnectionError(McpError):
    """Raised when server connection fails."""
    pass


class McpOperationError(McpError):
    """Raised when AutoCAD operation fails."""
    pass


class McpTimeoutError(McpError):
    """Raised when operation times out."""
    pass


class McpValidationError(McpError):
    """Raised when input validation fails."""
    pass