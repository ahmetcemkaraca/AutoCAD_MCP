"""
Interactive Development Module
=============================

Interactive Python REPL, debugging, diagnostics, and performance analysis 
for Master AutoCAD Coder. Provides secure, session-based interactive 
development with AutoCAD context pre-loaded and variable persistence.

Phase 2 Implementation: Interactive Development Tools
Week 5 Complete: Advanced Interactive Features
"""

from .python_repl import PythonREPL
from .execution_engine import ExecutionEngine
from .session_manager import SessionManager
from .security_sandbox import SecuritySandbox
from .debugger import AutoCADDebugger
from .error_diagnostics import ErrorDiagnostics
from .performance_analyzer import PerformanceAnalyzer

__all__ = [
    "PythonREPL", 
    "ExecutionEngine", 
    "SessionManager", 
    "SecuritySandbox",
    "AutoCADDebugger",
    "ErrorDiagnostics", 
    "PerformanceAnalyzer"
]

# Version information
__version__ = "1.0.0"
__author__ = "AutoCAD MCP Contributors"