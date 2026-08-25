"""
MCP Client Library for AutoCAD MCP Server.

This library provides a Python interface for VS Code scripts and Roo Code 
generated code to interact with the AutoCAD MCP Server.
"""

from .client import McpClient
from .exceptions import (
    McpError,
    McpConnectionError,
    McpOperationError,
    McpTimeoutError,
    McpValidationError
)
from .types import (
    Point3D,
    Vector3D,
    EntityId,
    LayerName,
    EntityInfo,
    UnfoldResult,
    LayoutResult
)

__version__ = "1.0.0"
__author__ = "AutoCAD MCP Team"

__all__ = [
    "McpClient",
    "McpError",
    "McpConnectionError", 
    "McpOperationError",
    "McpTimeoutError",
    "McpValidationError",
    "Point3D",
    "Vector3D", 
    "EntityId",
    "LayerName",
    "EntityInfo",
    "UnfoldResult",
    "LayoutResult"
]