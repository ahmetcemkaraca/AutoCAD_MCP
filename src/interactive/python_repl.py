"""
Interactive Python REPL for AutoCAD Development
===============================================

Provides interactive Python REPL with AutoCAD context pre-loaded,
variable persistence, multi-line support, and comprehensive history management.
Integrates with VS Code and supports secure code execution.
"""

import logging
import time
import sys
import traceback
from typing import Dict, Any, List, Optional, Tuple
from io import StringIO
import contextlib

# Import enhanced AutoCAD and security components
from ..enhanced_autocad.compatibility_layer import Autocad
from ..mcp_integration.security_manager import SecurityManager
from ..mcp_integration.context_manager import ContextManager

logger = logging.getLogger(__name__)


class PythonREPL:
    """
    Interactive Python REPL with AutoCAD context and session management.
    """

    def __init__(self, autocad_wrapper=None, security_manager=None, context_manager=None):
        """
        Initialize Python REPL.

        Args:
            autocad_wrapper: EnhancedAutoCAD wrapper instance
            security_manager: Security manager for code validation
            context_manager: Context manager for session persistence
        """
        self.autocad_wrapper = autocad_wrapper or Autocad()
        self.security_manager = security_manager or SecurityManager()
        self.context_manager = context_manager or ContextManager()
        
        # REPL state
        self.active_sessions = {}
        self.command_counter = 0
        self.startup_imports = self._get_startup_imports()
        
        logger.info("Python REPL initialized with AutoCAD context")

    def start_repl_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new REPL session with AutoCAD context pre-loaded.

        Args:
            session_id: Optional session identifier (auto-generated if None)

        Returns:
            Dictionary containing session information
        """
        if session_id is None:
            session_id = f"repl_{int(time.time())}_{len(self.active_sessions)}"

        if session_id in self.active_sessions:
            return {
                "success": False,
                "error": f"Session {session_id} already exists",
                "session_id": session_id
            }

        try:
            # Create session context
            session_context = self.context_manager.create_session(session_id)
            
            # Initialize AutoCAD context
            autocad_globals = self._initialize_autocad_context()
            
            # Create REPL session
            repl_session = {
                "session_id": session_id,
                "created_at": time.time(),
                "last_executed": time.time(),
                "command_count": 0,
                "globals": autocad_globals,
                "locals": {},
                "history": [],
                "multi_line_buffer": "",
                "status": "active"
            }
            
            self.active_sessions[session_id] = repl_session
            
            # Execute startup imports
            startup_result = self._execute_startup_code(session_id)
            
            logger.info(f"REPL session {session_id} started")
            
            return {
                "success": True,
                "session_id": session_id,
                "startup_output": startup_result.get("output", ""),
                "autocad_status": self._get_autocad_status(),
                "available_objects": list(autocad_globals.keys()),
                "message": "Interactive Python REPL started with AutoCAD context"
            }

        except Exception as e:
            logger.error(f"Failed to start REPL session: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to start REPL session: {str(e)}",
                "session_id": session_id
            }

    def execute_code(self, code: str, session_id: str) -> Dict[str, Any]:
        """
        Execute Python code in REPL session with AutoCAD context.

        Args:
            code: Python code to execute
            session_id: REPL session identifier

        Returns:
            Execution result dictionary
        """
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": f"Session {session_id} not found",
                "output": "",
                "execution_time": 0
            }

        session = self.active_sessions[session_id]
        start_time = time.time()

        try:
            # Handle multi-line input
            if self._is_incomplete_statement(code):
                session["multi_line_buffer"] += code + "\n"
                return {
                    "success": True,
                    "output": "",
                    "continuation": True,
                    "prompt": "... ",
                    "execution_time": time.time() - start_time
                }

            # Combine with any buffered multi-line input
            full_code = session["multi_line_buffer"] + code
            session["multi_line_buffer"] = ""

            # Security validation
            is_valid, violations = self.security_manager.validate_python_code(full_code)
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Security validation failed: {'; '.join(violations)}",
                    "output": "",
                    "execution_time": time.time() - start_time
                }

            # Execute code with timeout and capture output
            result = self._execute_with_context(
                full_code, 
                session["globals"], 
                session["locals"],
                session_id
            )
            
            # Update session state
            session["last_executed"] = time.time()
            session["command_count"] += 1
            
            # Add to history
            history_entry = {
                "command_number": session["command_count"],
                "timestamp": time.time(),
                "code": full_code,
                "output": result["output"],
                "success": result["success"],
                "execution_time": time.time() - start_time
            }
            
            session["history"].append(history_entry)
            
            # Keep history manageable (last 100 commands)
            if len(session["history"]) > 100:
                session["history"] = session["history"][-100:]

            logger.debug(f"Code executed in session {session_id}: {result['success']}")

            return {
                "success": result["success"],
                "output": result["output"],
                "error": result.get("error", ""),
                "command_number": session["command_count"],
                "execution_time": time.time() - start_time,
                "continuation": False,
                "prompt": ">>> "
            }

        except Exception as e:
            logger.error(f"Code execution failed in session {session_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "output": "",
                "execution_time": time.time() - start_time
            }

    def get_session_history(self, session_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get command history for a REPL session.

        Args:
            session_id: REPL session identifier
            limit: Maximum number of history entries to return

        Returns:
            Dictionary containing history information
        """
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": f"Session {session_id} not found",
                "history": []
            }

        session = self.active_sessions[session_id]
        history = session["history"][-limit:] if limit > 0 else session["history"]

        return {
            "success": True,
            "session_id": session_id,
            "history": history,
            "total_commands": session["command_count"],
            "session_age": time.time() - session["created_at"]
        }

    def clear_session(self, session_id: str) -> Dict[str, Any]:
        """
        Clear REPL session variables and history.

        Args:
            session_id: REPL session identifier

        Returns:
            Clear operation result
        """
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": f"Session {session_id} not found"
            }

        session = self.active_sessions[session_id]
        
        # Reset session state but keep AutoCAD context
        autocad_globals = self._initialize_autocad_context()
        session["globals"] = autocad_globals
        session["locals"] = {}
        session["history"] = []
        session["multi_line_buffer"] = ""
        session["command_count"] = 0
        
        # Re-execute startup code
        self._execute_startup_code(session_id)
        
        logger.info(f"REPL session {session_id} cleared")
        
        return {
            "success": True,
            "message": f"Session {session_id} cleared and AutoCAD context reloaded"
        }

    def stop_session(self, session_id: str) -> Dict[str, Any]:
        """
        Stop and remove REPL session.

        Args:
            session_id: REPL session identifier

        Returns:
            Stop operation result
        """
        if session_id not in self.active_sessions:
            return {
                "success": False,
                "error": f"Session {session_id} not found"
            }

        # Clean up session
        del self.active_sessions[session_id]
        
        # Clean up context manager session
        self.context_manager.remove_session(session_id)
        
        logger.info(f"REPL session {session_id} stopped")
        
        return {
            "success": True,
            "message": f"Session {session_id} stopped successfully"
        }

    def get_active_sessions(self) -> Dict[str, Any]:
        """
        Get information about all active REPL sessions.

        Returns:
            Dictionary containing active sessions information
        """
        sessions_info = {}
        
        for session_id, session in self.active_sessions.items():
            sessions_info[session_id] = {
                "session_id": session_id,
                "created_at": session["created_at"],
                "last_executed": session["last_executed"],
                "command_count": session["command_count"],
                "status": session["status"],
                "age_seconds": time.time() - session["created_at"]
            }
        
        return {
            "active_sessions": sessions_info,
            "total_sessions": len(self.active_sessions),
            "oldest_session": min(sessions_info.values(), key=lambda x: x["created_at"])["session_id"] if sessions_info else None
        }

    def _initialize_autocad_context(self) -> Dict[str, Any]:
        """Initialize AutoCAD context for REPL session."""
        context = {
            "__builtins__": self.security_manager.get_safe_builtins(),
            "__name__": "__repl__",
            "__doc__": "Interactive AutoCAD Python REPL",
        }
        
        # Add AutoCAD objects
        if self.autocad_wrapper:
            context.update({
                "acad": self.autocad_wrapper,
                "app": getattr(self.autocad_wrapper, 'app', None),
                "doc": getattr(self.autocad_wrapper, 'doc', None),
                "model": getattr(self.autocad_wrapper, 'model', None),
            })
        
        # Add useful modules
        import math
        context["math"] = math
        
        return context

    def _execute_startup_code(self, session_id: str) -> Dict[str, Any]:
        """Execute startup imports and setup code."""
        startup_code = self.startup_imports
        
        if startup_code.strip():
            return self.execute_code(startup_code, session_id)
        
        return {"success": True, "output": ""}

    def _get_startup_imports(self) -> str:
        """Get startup imports and setup code."""
        return """# AutoCAD REPL Startup
print("AutoCAD Interactive Python REPL")
print("Available objects: acad, app, doc, model, math")
print("Type help() for assistance")
"""

    def _is_incomplete_statement(self, code: str) -> bool:
        """Check if Python statement is incomplete (needs continuation)."""
        try:
            compile(code, '<repl>', 'exec')
            return False
        except SyntaxError as e:
            # Check if it's an incomplete statement
            return "unexpected EOF" in str(e) or "incomplete" in str(e).lower()

    def _execute_with_context(self, code: str, globals_dict: Dict[str, Any], 
                            locals_dict: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Execute code with proper context and output capture."""
        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        captured_output = StringIO()
        
        try:
            sys.stdout = captured_output
            sys.stderr = captured_output
            
            # Use security manager for safe execution
            success, result, error_message = self.security_manager.execute_with_timeout(
                code, globals_dict
            )
            
            # Get captured output
            output = captured_output.getvalue()
            
            if success:
                # If there's a result and no output, show the result
                if result is not None and not output.strip():
                    output = repr(result)
                
                return {
                    "success": True,
                    "output": output,
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "output": output,
                    "error": error_message
                }
                
        except Exception as e:
            return {
                "success": False,
                "output": captured_output.getvalue(),
                "error": f"Execution error: {str(e)}"
            }
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _get_autocad_status(self) -> Dict[str, Any]:
        """Get current AutoCAD connection status."""
        if not self.autocad_wrapper:
            return {"connected": False, "message": "No AutoCAD wrapper available"}
        
        try:
            # This would call the actual connection status method
            return {
                "connected": True,
                "message": "AutoCAD connection active",
                "version": "2025"  # Would be dynamic
            }
        except Exception as e:
            return {
                "connected": False,
                "message": f"AutoCAD connection error: {str(e)}"
            }