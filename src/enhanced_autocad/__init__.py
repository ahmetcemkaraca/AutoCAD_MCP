"""
Enhanced AutoCAD Module
=====================

Master AutoCAD Coder enhanced COM wrapper with 100% pyautocad compatibility.
Provides improved reliability, performance monitoring, and development features
while maintaining complete backward compatibility with existing manufacturing system.

Features:
- 100% pyautocad API compatibility
- Automatic connection recovery
- Performance monitoring and metrics
- Enhanced error handling and diagnostics
- Development-focused interactive tools
"""

from .enhanced_wrapper import EnhancedAutoCAD

# Export main interface for compatibility
__all__ = ["EnhancedAutoCAD"]

# Version information
__version__ = "1.0.0"
__author__ = "AutoCAD MCP Contributors"
