"""
Interactive AutoCAD Debugger System
===================================

Provides comprehensive debugging capabilities for AutoCAD Python development
with object state inspection, variable tracking, execution tracing, and
intelligent breakpoint management. Integrates with inspection system for
detailed object analysis.
"""

import logging
import time
import sys
import traceback
import threading
from typing import Dict, Any, List, Optional, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import inspect
import uuid

# Import inspection and interactive components
from ..inspection.object_inspector import ObjectInspector, InspectionDepth
from ..inspection.property_analyzer import PropertyAnalyzer
from ..inspection.method_discoverer import MethodDiscoverer
from ..enhanced_autocad.performance_monitor import PerformanceMonitor
from ..enhanced_autocad.error_handler import ErrorHandler
from .secure_evaluator import safe_eval, SecureEvaluationError

logger = logging.getLogger(__name__)


class BreakpointType(Enum):
    """Types of debugging breakpoints."""
    LINE = "line"                    # Break at specific line
    FUNCTION = "function"            # Break when function is called
    VARIABLE = "variable"            # Break when variable changes
    OBJECT_ACCESS = "object_access"  # Break when AutoCAD object is accessed
    EXCEPTION = "exception"          # Break on exception
    CONDITIONAL = "conditional"      # Break when condition is met


class DebugState(Enum):
    """Debugger execution states."""
    IDLE = "idle"
    RUNNING = "running" 
    PAUSED = "paused"
    STEPPING = "stepping"
    FINISHED = "finished"
    ERROR = "error"


@dataclass
class Breakpoint:
    """Debugging breakpoint definition."""
    id: str
    type: BreakpointType
    enabled: bool = True
    hit_count: int = 0
    condition: Optional[str] = None
    
    # Location-specific properties
    filename: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    variable_name: Optional[str] = None
    object_path: Optional[str] = None
    
    # Action properties
    log_message: Optional[str] = None
    temporary: bool = False
    ignore_count: int = 0


@dataclass
class DebugFrame:
    """Debugging frame information."""
    frame_id: str
    filename: str
    line_number: int
    function_name: str
    local_variables: Dict[str, Any]
    global_variables: Dict[str, Any]
    autocad_objects: Dict[str, Any]
    call_stack: List[str]


@dataclass
class VariableWatch:
    """Variable watch for tracking changes."""
    name: str
    expression: str
    current_value: Any
    previous_value: Any = None
    change_count: int = 0
    last_changed: float = 0.0


class AutoCADDebugger:
    """
    Advanced debugging system for AutoCAD Python development.
    
    Provides comprehensive debugging with object inspection, variable tracking,
    execution tracing, and intelligent breakpoint management.
    """
    
    def __init__(self, object_inspector=None, performance_monitor=None, error_handler=None):
        """
        Initialize AutoCAD debugger.
        
        Args:
            object_inspector: Object inspector for detailed analysis
            performance_monitor: Performance monitoring for execution tracking
            error_handler: Error handler for exception management
        """
        self.object_inspector = object_inspector or ObjectInspector()
        self.property_analyzer = PropertyAnalyzer()
        self.method_discoverer = MethodDiscoverer()
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.error_handler = error_handler or ErrorHandler()
        
        # Debugging state
        self.state = DebugState.IDLE
        self.session_id = None
        self.debug_lock = threading.Lock()
        
        # Breakpoints and watches
        self.breakpoints: Dict[str, Breakpoint] = {}
        self.variable_watches: Dict[str, VariableWatch] = {}
        self.execution_trace: List[Dict[str, Any]] = []
        
        # Current execution context
        self.current_frame: Optional[DebugFrame] = None
        self.call_stack: List[DebugFrame] = []
        self.autocad_context: Dict[str, Any] = {}
        
        # Configuration
        self.max_trace_size = 1000
        self.auto_inspect_objects = True
        self.trace_autocad_calls = True
        
        logger.info("AutoCAD debugger initialized")

    def start_debug_session(self, session_id: Optional[str] = None) -> str:
        """
        Start a new debugging session.
        
        Args:
            session_id: Optional session identifier
            
        Returns:
            Session ID for the debugging session
        """
        with self.debug_lock:
            if self.state != DebugState.IDLE:
                raise RuntimeError(f"Debugger already active in state: {self.state}")
            
            self.session_id = session_id or f"debug_{uuid.uuid4().hex[:8]}"
            self.state = DebugState.RUNNING
            self.execution_trace.clear()
            self.call_stack.clear()
            self.current_frame = None
            
            # Initialize AutoCAD context inspection
            if self.auto_inspect_objects:
                self._update_autocad_context()
                
            logger.info(f"Debug session started: {self.session_id}")
            return self.session_id

    def stop_debug_session(self) -> Dict[str, Any]:
        """
        Stop the current debugging session.
        
        Returns:
            Session summary with statistics
        """
        with self.debug_lock:
            if self.state == DebugState.IDLE:
                return {"message": "No active debug session"}
                
            session_summary = {
                "session_id": self.session_id,
                "total_trace_entries": len(self.execution_trace),
                "breakpoints_hit": sum(bp.hit_count for bp in self.breakpoints.values()),
                "variable_changes": sum(watch.change_count for watch in self.variable_watches.values()),
                "final_state": self.state.value
            }
            
            self.state = DebugState.IDLE
            self.session_id = None
            self.current_frame = None
            self.call_stack.clear()
            
            logger.info(f"Debug session stopped: {session_summary}")
            return session_summary

    def add_breakpoint(self, 
                      breakpoint_type: str,
                      filename: Optional[str] = None,
                      line_number: Optional[int] = None,
                      function_name: Optional[str] = None,
                      variable_name: Optional[str] = None,
                      condition: Optional[str] = None,
                      temporary: bool = False) -> str:
        """
        Add a debugging breakpoint.
        
        Args:
            breakpoint_type: Type of breakpoint ('line', 'function', 'variable', etc.)
            filename: Source filename for line breakpoints
            line_number: Line number for line breakpoints
            function_name: Function name for function breakpoints
            variable_name: Variable name for variable breakpoints
            condition: Optional condition for conditional breakpoints
            temporary: Whether breakpoint is temporary (auto-removed after hit)
            
        Returns:
            Breakpoint ID
        """
        breakpoint_id = f"bp_{uuid.uuid4().hex[:8]}"
        
        try:
            bp_type = BreakpointType(breakpoint_type)
        except ValueError:
            raise ValueError(f"Invalid breakpoint type: {breakpoint_type}")
        
        breakpoint = Breakpoint(
            id=breakpoint_id,
            type=bp_type,
            filename=filename,
            line_number=line_number,
            function_name=function_name,
            variable_name=variable_name,
            condition=condition,
            temporary=temporary
        )
        
        self.breakpoints[breakpoint_id] = breakpoint
        logger.info(f"Added {breakpoint_type} breakpoint: {breakpoint_id}")
        
        return breakpoint_id

    def remove_breakpoint(self, breakpoint_id: str) -> bool:
        """
        Remove a debugging breakpoint.
        
        Args:
            breakpoint_id: ID of breakpoint to remove
            
        Returns:
            True if breakpoint was removed, False if not found
        """
        if breakpoint_id in self.breakpoints:
            del self.breakpoints[breakpoint_id]
            logger.info(f"Removed breakpoint: {breakpoint_id}")
            return True
        return False

    def add_variable_watch(self, name: str, expression: str) -> str:
        """
        Add a variable watch for tracking changes.
        
        Args:
            name: Watch name/identifier
            expression: Python expression to evaluate
            
        Returns:
            Watch ID
        """
        watch = VariableWatch(
            name=name,
            expression=expression,
            current_value=None
        )
        
        # Try to evaluate initial value
        try:
            if self.current_frame:
                local_vars = self.current_frame.local_variables
                global_vars = self.current_frame.global_variables
                watch.current_value = safe_eval(expression, local_vars, global_vars)
        except (SecureEvaluationError, Exception) as e:
            logger.warning(f"Could not evaluate watch expression {expression}: {e}")
            
        self.variable_watches[name] = watch
        logger.info(f"Added variable watch: {name} = {expression}")
        
        return name

    def remove_variable_watch(self, name: str) -> bool:
        """
        Remove a variable watch.
        
        Args:
            name: Watch name to remove
            
        Returns:
            True if watch was removed, False if not found
        """
        if name in self.variable_watches:
            del self.variable_watches[name]
            logger.info(f"Removed variable watch: {name}")
            return True
        return False

    def inspect_current_context(self, depth: str = "detailed") -> Dict[str, Any]:
        """
        Inspect the current debugging context with detailed object analysis.
        
        Args:
            depth: Inspection depth ('basic', 'detailed', 'comprehensive')
            
        Returns:
            Comprehensive context inspection results
        """
        if not self.current_frame:
            return {"error": "No current debug frame available"}
        
        try:
            inspection_depth = InspectionDepth(depth)
        except ValueError:
            inspection_depth = InspectionDepth.DETAILED
            
        context_info = {
            "frame_info": {
                "filename": self.current_frame.filename,
                "line_number": self.current_frame.line_number,
                "function_name": self.current_frame.function_name
            },
            "call_stack": [frame.function_name for frame in self.call_stack],
            "local_variables": {},
            "global_variables": {},
            "autocad_objects": {},
            "variable_watches": {},
            "performance_metrics": {}
        }
        
        # Analyze local variables
        for var_name, var_value in self.current_frame.local_variables.items():
            try:
                if self._is_autocad_object(var_value):
                    # Deep inspection for AutoCAD objects
                    inspection_result = self.object_inspector.inspect_object(
                        var_value, depth=inspection_depth
                    )
                    context_info["local_variables"][var_name] = {
                        "type": type(var_value).__name__,
                        "value": str(var_value),
                        "autocad_inspection": inspection_result
                    }
                else:
                    context_info["local_variables"][var_name] = {
                        "type": type(var_value).__name__,
                        "value": str(var_value)
                    }
            except Exception as e:
                context_info["local_variables"][var_name] = {
                    "type": "unknown",
                    "value": f"<inspection error: {e}>"
                }
        
        # Analyze AutoCAD objects in context
        for obj_name, obj_value in self.autocad_context.items():
            try:
                inspection_result = self.object_inspector.inspect_object(
                    obj_value, depth=inspection_depth
                )
                context_info["autocad_objects"][obj_name] = inspection_result
            except Exception as e:
                context_info["autocad_objects"][obj_name] = {
                    "error": f"Inspection failed: {e}"
                }
        
        # Update variable watches
        for watch_name, watch in self.variable_watches.items():
            try:
                local_vars = self.current_frame.local_variables
                global_vars = self.current_frame.global_variables
                current_value = safe_eval(watch.expression, local_vars, global_vars)
                
                context_info["variable_watches"][watch_name] = {
                    "expression": watch.expression,
                    "current_value": str(current_value),
                    "previous_value": str(watch.previous_value),
                    "change_count": watch.change_count,
                    "type": type(current_value).__name__
                }
                
                # Check for changes
                if current_value != watch.current_value:
                    watch.previous_value = watch.current_value
                    watch.current_value = current_value
                    watch.change_count += 1
                    watch.last_changed = time.time()
                    
            except (SecureEvaluationError, Exception) as e:
                context_info["variable_watches"][watch_name] = {
                    "expression": watch.expression,
                    "error": f"Evaluation failed: {e}"
                }
        
        # Add performance metrics if available
        if hasattr(self.performance_monitor, 'get_current_metrics'):
            try:
                context_info["performance_metrics"] = self.performance_monitor.get_current_metrics()
            except Exception:
                pass
                
        return context_info

    def step_over(self) -> Dict[str, Any]:
        """
        Execute a single step over the current line.
        
        Returns:
            Step execution result with context information
        """
        if self.state != DebugState.PAUSED:
            return {"error": "Debugger not paused - cannot step"}
            
        self.state = DebugState.STEPPING
        
        try:
            # Implementation would hook into Python execution
            # For now, simulate step operation
            step_result = {
                "action": "step_over",
                "success": True,
                "context": self.inspect_current_context("basic")
            }
            
            self.state = DebugState.PAUSED
            return step_result
            
        except Exception as e:
            self.state = DebugState.ERROR
            return {
                "action": "step_over",
                "success": False,
                "error": str(e)
            }

    def step_into(self) -> Dict[str, Any]:
        """
        Execute a single step into function calls.
        
        Returns:
            Step execution result with context information
        """
        if self.state != DebugState.PAUSED:
            return {"error": "Debugger not paused - cannot step"}
            
        self.state = DebugState.STEPPING
        
        try:
            # Implementation would hook into Python execution
            step_result = {
                "action": "step_into",
                "success": True,
                "context": self.inspect_current_context("basic")
            }
            
            self.state = DebugState.PAUSED
            return step_result
            
        except Exception as e:
            self.state = DebugState.ERROR
            return {
                "action": "step_into", 
                "success": False,
                "error": str(e)
            }

    def continue_execution(self) -> Dict[str, Any]:
        """
        Continue execution until next breakpoint.
        
        Returns:
            Execution result
        """
        if self.state != DebugState.PAUSED:
            return {"error": "Debugger not paused - cannot continue"}
            
        self.state = DebugState.RUNNING
        
        # Implementation would resume execution
        return {
            "action": "continue",
            "success": True,
            "state": self.state.value
        }

    def get_call_stack(self) -> List[Dict[str, Any]]:
        """
        Get the current call stack with frame information.
        
        Returns:
            List of call stack frames
        """
        stack_info = []
        
        for i, frame in enumerate(self.call_stack):
            frame_info = {
                "frame_id": frame.frame_id,
                "index": i,
                "filename": frame.filename,
                "line_number": frame.line_number,
                "function_name": frame.function_name,
                "local_variable_count": len(frame.local_variables),
                "autocad_object_count": len(frame.autocad_objects)
            }
            stack_info.append(frame_info)
            
        return stack_info

    def evaluate_expression(self, expression: str) -> Dict[str, Any]:
        """
        Evaluate a Python expression in the current debug context.
        
        Args:
            expression: Python expression to evaluate
            
        Returns:
            Evaluation result with value and type information
        """
        if not self.current_frame:
            return {"error": "No current debug frame for evaluation"}
            
        try:
            local_vars = self.current_frame.local_variables
            global_vars = self.current_frame.global_variables
            
            # Add AutoCAD context to evaluation
            eval_context = {**global_vars, **self.autocad_context}
            
            result_value = safe_eval(expression, local_vars, eval_context)
            
            evaluation_result = {
                "expression": expression,
                "success": True,
                "value": str(result_value),
                "type": type(result_value).__name__,
                "repr": repr(result_value)
            }
            
            # If result is an AutoCAD object, provide inspection
            if self._is_autocad_object(result_value):
                try:
                    inspection = self.object_inspector.inspect_object(
                        result_value, depth=InspectionDepth.BASIC
                    )
                    evaluation_result["autocad_inspection"] = inspection
                except Exception:
                    pass
                    
            return evaluation_result
            
        except (SecureEvaluationError, Exception) as e:
            return {
                "expression": expression,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def get_breakpoints(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all current breakpoints with their status.
        
        Returns:
            Dictionary of breakpoint information
        """
        breakpoint_info = {}
        
        for bp_id, breakpoint in self.breakpoints.items():
            breakpoint_info[bp_id] = {
                "id": breakpoint.id,
                "type": breakpoint.type.value,
                "enabled": breakpoint.enabled,
                "hit_count": breakpoint.hit_count,
                "condition": breakpoint.condition,
                "filename": breakpoint.filename,
                "line_number": breakpoint.line_number,
                "function_name": breakpoint.function_name,
                "variable_name": breakpoint.variable_name,
                "temporary": breakpoint.temporary
            }
            
        return breakpoint_info

    def get_execution_trace(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get the execution trace history.
        
        Args:
            limit: Maximum number of trace entries to return
            
        Returns:
            List of execution trace entries
        """
        return self.execution_trace[-limit:] if self.execution_trace else []

    def _update_autocad_context(self):
        """Update AutoCAD context with current object states."""
        try:
            # This would integrate with the AutoCAD wrapper to get current objects
            # For now, simulate context update
            self.autocad_context.update({
                "last_updated": time.time(),
                "context_available": True
            })
        except Exception as e:
            logger.warning(f"Failed to update AutoCAD context: {e}")

    def _is_autocad_object(self, obj: Any) -> bool:
        """
        Check if an object is an AutoCAD COM object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if object appears to be AutoCAD-related
        """
        try:
            obj_type = type(obj).__name__
            return (
                'AutoCAD' in obj_type or
                'COM' in obj_type or
                hasattr(obj, 'Application') or
                hasattr(obj, 'ActiveDocument')
            )
        except Exception:
            return False

    def _add_trace_entry(self, entry_type: str, details: Dict[str, Any]):
        """Add an entry to the execution trace."""
        trace_entry = {
            "timestamp": time.time(),
            "type": entry_type,
            "session_id": self.session_id,
            **details
        }
        
        self.execution_trace.append(trace_entry)
        
        # Maintain trace size limit
        if len(self.execution_trace) > self.max_trace_size:
            self.execution_trace = self.execution_trace[-self.max_trace_size//2:]