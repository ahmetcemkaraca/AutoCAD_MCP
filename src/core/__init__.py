"""
Core utilities and infrastructure for AutoCAD MCP platform.

This module provides essential infrastructure components including:
- Lazy loading framework for optional dependencies
- Configuration management
- Logging utilities
- Performance monitoring base classes
"""

from .lazy_loader import LazyLoader, lazy_import

__all__ = ['LazyLoader', 'lazy_import']