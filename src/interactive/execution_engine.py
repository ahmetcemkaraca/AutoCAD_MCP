"""
Secure Code Execution Engine for Interactive Development
=======================================================

Provides secure, monitored execution of Python code in AutoCAD context
with performance tracking, resource monitoring, and comprehensive error handling.
Integrates with security manager and context manager for safe interactive development.
"""

import logging
import time
import threading
import psutil
import os
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# Try to import resource module (Unix only)
try:
    import resource
    RESOURCE_AVAILABLE = True
except ImportError:
    RESOURCE_AVAILABLE = False

# Import security and monitoring components
from ..mcp_integration.security_manager import SecurityManager, SecurityError
from ..enhanced_autocad.performance_monitor import PerformanceMonitor
from ..enhanced_autocad.error_handler import ErrorHandler, ErrorCategory

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """Result of code execution."""
    execution_id: str
    status: ExecutionStatus
    code: str
    output: str
    error_message: Optional[str] = None
    execution_time: float = 0.0
    memory_used: float = 0.0
    cpu_time: float = 0.0
    result_value: Any = None
    security_violations: List[str] = None


class ExecutionEngine:
    """
    Secure code execution engine with monitoring and resource management.
    """

    def __init__(self, security_manager=None, performance_monitor=None, error_handler=None):
        """
        Initialize execution engine.

        Args:
            security_manager: Security manager for code validation
            performance_monitor: Performance monitor for tracking
            error_handler: Error handler for comprehensive error management
        """
        self.security_manager = security_manager or SecurityManager()
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.error_handler = error_handler or ErrorHandler()
        
        # Execution tracking
        self.active_executions = {}
        self.execution_history = []
        self.execution_counter = 0
        
        # Resource limits
        self.max_execution_time = 30.0  # seconds
        self.max_memory_mb = 500  # MB
        self.max_cpu_time = 20.0  # seconds
        
        # Callbacks
        self.pre_execution_callbacks = []
        self.post_execution_callbacks = []
        
        logger.info("Execution Engine initialized with security and monitoring")

    def execute_code(self, code: str, context: Dict[str, Any], 
                    execution_id: Optional[str] = None,
                    timeout: Optional[float] = None) -> ExecutionResult:
        """
        Execute Python code securely with full monitoring.

        Args:
            code: Python code to execute
            context: Execution context (globals)
            execution_id: Optional execution identifier
            timeout: Optional timeout override

        Returns:
            ExecutionResult containing execution details
        """
        if execution_id is None:
            self.execution_counter += 1
            execution_id = f"exec_{self.execution_counter}_{int(time.time())}"

        if timeout is None:
            timeout = self.max_execution_time

        start_time = time.time()
        
        # Create execution result
        result = ExecutionResult(
            execution_id=execution_id,
            status=ExecutionStatus.PENDING,
            code=code,
            output="",
            security_violations=[]
        )

        try:
            # Pre-execution validation and setup
            result = self._pre_execution_validation(result, context)
            if result.status == ExecutionStatus.FAILED:
                return result

            # Track active execution
            self.active_executions[execution_id] = {
                "start_time": start_time,
                "timeout": timeout,
                "thread": None,
                "result": result
            }

            # Execute with monitoring
            result = self._execute_with_monitoring(result, context, timeout)
            
            # Post-execution cleanup and analysis
            result = self._post_execution_analysis(result)
            
            # Record execution time
            result.execution_time = time.time() - start_time
            
            # Add to history
            self._add_to_history(result)
            
            logger.info(f"Code execution {execution_id} completed: {result.status}")
            
            return result

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = f"Execution engine error: {str(e)}"
            result.execution_time = time.time() - start_time
            
            logger.error(f"Execution engine error for {execution_id}: {str(e)}")
            return result
            
        finally:
            # Clean up active execution
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]

    def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running execution.

        Args:
            execution_id: Execution to cancel

        Returns:
            True if cancellation was successful
        """
        if execution_id not in self.active_executions:
            return False

        execution_info = self.active_executions[execution_id]
        thread = execution_info.get("thread")
        
        if thread and thread.is_alive():
            # Mark as cancelled (thread cleanup handled by daemon=True)
            execution_info["result"].status = ExecutionStatus.CANCELLED
            execution_info["result"].error_message = "Execution cancelled by user"
            
            logger.info(f"Execution {execution_id} cancelled")
            return True
        
        return False

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific execution."""
        if execution_id in self.active_executions:
            execution_info = self.active_executions[execution_id]
            return {
                "execution_id": execution_id,
                "status": execution_info["result"].status.value,
                "start_time": execution_info["start_time"],
                "elapsed_time": time.time() - execution_info["start_time"],
                "timeout": execution_info["timeout"]
            }
        
        # Check history
        for result in reversed(self.execution_history):
            if result.execution_id == execution_id:
                return {
                    "execution_id": execution_id,
                    "status": result.status.value,
                    "execution_time": result.execution_time,
                    "memory_used": result.memory_used,
                    "completed": True
                }
        
        return None

    def get_active_executions(self) -> List[Dict[str, Any]]:
        """Get information about all active executions."""
        active = []
        current_time = time.time()
        
        for exec_id, execution_info in self.active_executions.items():
            active.append({
                "execution_id": exec_id,
                "status": execution_info["result"].status.value,
                "elapsed_time": current_time - execution_info["start_time"],
                "timeout": execution_info["timeout"]
            })
        
        return active

    def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        history = []
        
        for result in self.execution_history[-limit:]:
            history.append({
                "execution_id": result.execution_id,
                "status": result.status.value,
                "execution_time": result.execution_time,
                "memory_used": result.memory_used,
                "cpu_time": result.cpu_time,
                "had_errors": bool(result.error_message),
                "security_violations": len(result.security_violations or [])
            })
        
        return history

    def add_pre_execution_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback to execute before code execution."""
        self.pre_execution_callbacks.append(callback)

    def add_post_execution_callback(self, callback: Callable[[ExecutionResult], None]):
        """Add callback to execute after code execution."""
        self.post_execution_callbacks.append(callback)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get execution engine performance metrics."""
        if not self.execution_history:
            return {"total_executions": 0}

        total_executions = len(self.execution_history)
        successful_executions = sum(1 for r in self.execution_history if r.status == ExecutionStatus.COMPLETED)
        failed_executions = sum(1 for r in self.execution_history if r.status == ExecutionStatus.FAILED)
        timeout_executions = sum(1 for r in self.execution_history if r.status == ExecutionStatus.TIMEOUT)
        
        execution_times = [r.execution_time for r in self.execution_history if r.execution_time > 0]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        memory_usage = [r.memory_used for r in self.execution_history if r.memory_used > 0]
        avg_memory_usage = sum(memory_usage) / len(memory_usage) if memory_usage else 0

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "timeout_executions": timeout_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "average_execution_time": avg_execution_time,
            "average_memory_usage_mb": avg_memory_usage,
            "active_executions": len(self.active_executions)
        }

    def _pre_execution_validation(self, result: ExecutionResult, context: Dict[str, Any]) -> ExecutionResult:
        """Validate code before execution."""
        # Security validation
        is_valid, violations = self.security_manager.validate_python_code(result.code)
        if not is_valid:
            result.status = ExecutionStatus.FAILED
            result.error_message = f"Security validation failed: {'; '.join(violations)}"
            result.security_violations = violations
            return result

        # Run pre-execution callbacks
        for callback in self.pre_execution_callbacks:
            try:
                callback(result.code, context)
            except Exception as e:
                logger.warning(f"Pre-execution callback failed: {str(e)}")

        result.status = ExecutionStatus.RUNNING
        return result

    def _execute_with_monitoring(self, result: ExecutionResult, context: Dict[str, Any], 
                                timeout: float) -> ExecutionResult:
        """Execute code with resource monitoring."""
        execution_thread = None
        monitor_thread = None
        
        try:
            # Get initial resource usage
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            initial_cpu_time = process.cpu_times().user
            
            # Execute with security manager
            success, exec_result, error_message = self.security_manager.execute_with_timeout(
                result.code, context, timeout
            )
            
            # Get final resource usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            final_cpu_time = process.cpu_times().user
            
            # Update result
            result.memory_used = max(0, final_memory - initial_memory)
            result.cpu_time = max(0, final_cpu_time - initial_cpu_time)
            
            if success:
                result.status = ExecutionStatus.COMPLETED
                result.result_value = exec_result
                result.output = str(exec_result) if exec_result is not None else ""
            else:
                result.status = ExecutionStatus.FAILED
                result.error_message = error_message
                
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = f"Execution monitoring error: {str(e)}"
        
        return result

    def _post_execution_analysis(self, result: ExecutionResult) -> ExecutionResult:
        """Analyze execution results and run post-execution callbacks."""
        # Run post-execution callbacks
        for callback in self.post_execution_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.warning(f"Post-execution callback failed: {str(e)}")

        # Performance tracking
        if result.status == ExecutionStatus.COMPLETED:
            self.performance_monitor.record_operation(
                "code_execution",
                result.execution_time,
                success=True,
                metadata={
                    "memory_used_mb": result.memory_used,
                    "cpu_time": result.cpu_time
                }
            )
        else:
            self.performance_monitor.record_operation(
                "code_execution",
                result.execution_time,
                success=False,
                metadata={
                    "error": result.error_message,
                    "status": result.status.value
                }
            )

        return result

    def _add_to_history(self, result: ExecutionResult):
        """Add execution result to history."""
        self.execution_history.append(result)
        
        # Keep history manageable (last 1000 executions)
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]

    def cleanup_expired_executions(self, max_age_seconds: int = 3600):
        """Clean up old execution data."""
        current_time = time.time()
        
        # Clean up history
        self.execution_history = [
            result for result in self.execution_history
            if (current_time - time.time()) < max_age_seconds
        ]
        
        logger.info(f"Cleaned up expired executions, {len(self.execution_history)} remaining")