"""
Enhanced Error Handler for AutoCAD Wrapper
========================================

Provides comprehensive error handling with detailed diagnostics, recovery strategies,
and intelligent error categorization for both manufacturing workflows and development sessions.
"""

import logging
import traceback
import time
from typing import Dict, Any, Optional, List, Callable, Type
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of AutoCAD errors for intelligent handling."""

    CONNECTION_ERROR = "connection_error"
    COM_INTERFACE_ERROR = "com_interface_error"
    AUTOCAD_COMMAND_ERROR = "autocad_command_error"
    VALIDATION_ERROR = "validation_error"
    PERFORMANCE_ERROR = "performance_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Context information for an error occurrence."""

    error_category: ErrorCategory
    original_exception: Exception
    operation_name: str
    timestamp: float
    recovery_suggestion: Optional[str] = None
    diagnostic_info: Optional[Dict[str, Any]] = None
    is_recoverable: bool = False


class ErrorHandler:
    """
    Enhanced error handler with diagnostics and recovery strategies.
    """

    def __init__(self):
        """Initialize error handler."""
        self._error_history = []
        self._error_patterns = self._initialize_error_patterns()
        self._recovery_strategies = self._initialize_recovery_strategies()

    def _initialize_error_patterns(self) -> Dict[str, ErrorCategory]:
        """
        Initialize error pattern recognition.

        Returns:
            Dictionary mapping error patterns to categories
        """
        return {
            # Connection errors
            "could not connect": ErrorCategory.CONNECTION_ERROR,
            "autocad is not running": ErrorCategory.CONNECTION_ERROR,
            "no autocad application": ErrorCategory.CONNECTION_ERROR,
            "connection lost": ErrorCategory.CONNECTION_ERROR,
            "connection timeout": ErrorCategory.CONNECTION_ERROR,
            # COM interface errors
            "com error": ErrorCategory.COM_INTERFACE_ERROR,
            "dispatch error": ErrorCategory.COM_INTERFACE_ERROR,
            "automation error": ErrorCategory.COM_INTERFACE_ERROR,
            "invalid handle": ErrorCategory.COM_INTERFACE_ERROR,
            "ole error": ErrorCategory.COM_INTERFACE_ERROR,
            # AutoCAD command errors
            "command failed": ErrorCategory.AUTOCAD_COMMAND_ERROR,
            "invalid entity": ErrorCategory.AUTOCAD_COMMAND_ERROR,
            "entity not found": ErrorCategory.AUTOCAD_COMMAND_ERROR,
            "invalid selection": ErrorCategory.AUTOCAD_COMMAND_ERROR,
            "drawing error": ErrorCategory.AUTOCAD_COMMAND_ERROR,
            # Validation errors
            "invalid point": ErrorCategory.VALIDATION_ERROR,
            "invalid coordinates": ErrorCategory.VALIDATION_ERROR,
            "parameter out of range": ErrorCategory.VALIDATION_ERROR,
            "invalid input": ErrorCategory.VALIDATION_ERROR,
            # Performance errors
            "timeout": ErrorCategory.PERFORMANCE_ERROR,
            "memory error": ErrorCategory.PERFORMANCE_ERROR,
            "operation too slow": ErrorCategory.PERFORMANCE_ERROR,
        }

    def _initialize_recovery_strategies(self) -> Dict[ErrorCategory, List[str]]:
        """
        Initialize recovery strategies for different error categories.

        Returns:
            Dictionary mapping error categories to recovery suggestions
        """
        return {
            ErrorCategory.CONNECTION_ERROR: [
                "Ensure AutoCAD 2025 is running and visible",
                "Check if AutoCAD has an open drawing document",
                "Restart AutoCAD if connection issues persist",
                "Verify no other applications are blocking COM interface",
            ],
            ErrorCategory.COM_INTERFACE_ERROR: [
                "Restart the application to reset COM interface",
                "Check AutoCAD version compatibility",
                "Verify Windows COM registration is intact",
                "Try running as administrator if permission issues",
            ],
            ErrorCategory.AUTOCAD_COMMAND_ERROR: [
                "Verify entity exists in current drawing",
                "Check if entity is in correct space (model/paper)",
                "Ensure entity is not locked or on frozen layer",
                "Validate entity type supports requested operation",
            ],
            ErrorCategory.VALIDATION_ERROR: [
                "Check input parameter formats and ranges",
                "Verify coordinate values are numeric",
                "Ensure required parameters are provided",
                "Validate parameter types match expected format",
            ],
            ErrorCategory.PERFORMANCE_ERROR: [
                "Reduce operation complexity or batch size",
                "Check available system memory",
                "Consider breaking large operations into smaller chunks",
                "Optimize AutoCAD settings for better performance",
            ],
            ErrorCategory.UNKNOWN_ERROR: [
                "Check application logs for additional details",
                "Try operation again after brief delay",
                "Restart application if error persists",
                "Contact support with error details",
            ],
        }

    def categorize_error(self, exception: Exception, operation_name: str) -> ErrorContext:
        """
        Categorize error and create context with recovery suggestions.

        Args:
            exception: The exception that occurred
            operation_name: Name of operation that failed

        Returns:
            ErrorContext with categorization and recovery info
        """
        error_message = str(exception).lower()
        error_category = ErrorCategory.UNKNOWN_ERROR

        # Pattern matching for error categorization
        for pattern, category in self._error_patterns.items():
            if pattern in error_message:
                error_category = category
                break

        # Determine if error is recoverable
        is_recoverable = error_category in [
            ErrorCategory.CONNECTION_ERROR,
            ErrorCategory.COM_INTERFACE_ERROR,
            ErrorCategory.PERFORMANCE_ERROR,
        ]

        # Get recovery suggestions
        recovery_suggestions = self._recovery_strategies.get(error_category, [])
        recovery_suggestion = "; ".join(recovery_suggestions[:2])  # Limit to first 2 suggestions

        # Gather diagnostic information
        diagnostic_info = self._gather_diagnostic_info(exception, operation_name)

        error_context = ErrorContext(
            error_category=error_category,
            original_exception=exception,
            operation_name=operation_name,
            timestamp=time.time(),
            recovery_suggestion=recovery_suggestion,
            diagnostic_info=diagnostic_info,
            is_recoverable=is_recoverable,
        )

        # Record error in history
        self._error_history.append(error_context)

        # Keep only last 100 errors
        if len(self._error_history) > 100:
            self._error_history = self._error_history[-100:]

        return error_context

    def _gather_diagnostic_info(self, exception: Exception, operation_name: str) -> Dict[str, Any]:
        """
        Gather diagnostic information for error context.

        Args:
            exception: The exception that occurred
            operation_name: Name of operation that failed

        Returns:
            Dictionary containing diagnostic information
        """
        diagnostic_info = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "operation_name": operation_name,
            "stack_trace": traceback.format_exc(),
            "timestamp": time.time(),
        }

        # Add additional context based on exception type
        if hasattr(exception, "errno"):
            diagnostic_info["error_code"] = exception.errno

        if hasattr(exception, "strerror"):
            diagnostic_info["system_error"] = exception.strerror

        return diagnostic_info

    def handle_error(
        self, exception: Exception, operation_name: str, raise_exception: bool = True
    ) -> ErrorContext:
        """
        Handle error with comprehensive logging and context creation.

        Args:
            exception: The exception that occurred
            operation_name: Name of operation that failed
            raise_exception: Whether to re-raise the exception

        Returns:
            ErrorContext containing error details and recovery info

        Raises:
            Exception: Re-raises original exception if raise_exception is True
        """
        error_context = self.categorize_error(exception, operation_name)

        # Log error with appropriate level based on category
        log_level = logging.ERROR
        if error_context.error_category == ErrorCategory.VALIDATION_ERROR:
            log_level = logging.WARNING
        elif error_context.error_category == ErrorCategory.PERFORMANCE_ERROR:
            log_level = logging.INFO

        logger.log(
            log_level,
            f"AutoCAD operation '{operation_name}' failed: {error_context.error_category.value} - {str(exception)}",
        )

        if error_context.recovery_suggestion:
            logger.info(f"Recovery suggestion: {error_context.recovery_suggestion}")

        if raise_exception:
            raise exception

        return error_context

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive error statistics.

        Returns:
            Dictionary containing error statistics and patterns
        """
        if not self._error_history:
            return {
                "total_errors": 0,
                "error_categories": {},
                "recent_errors": [],
                "error_trends": {},
            }

        # Calculate statistics
        total_errors = len(self._error_history)
        category_counts = {}
        operation_errors = {}

        for error_context in self._error_history:
            # Category statistics
            category = error_context.error_category.value
            category_counts[category] = category_counts.get(category, 0) + 1

            # Operation statistics
            operation = error_context.operation_name
            operation_errors[operation] = operation_errors.get(operation, 0) + 1

        # Recent errors (last 10)
        recent_errors = []
        for error_context in self._error_history[-10:]:
            recent_errors.append(
                {
                    "timestamp": error_context.timestamp,
                    "operation": error_context.operation_name,
                    "category": error_context.error_category.value,
                    "message": str(error_context.original_exception),
                    "recoverable": error_context.is_recoverable,
                }
            )

        # Error trends over time (last hour)
        current_time = time.time()
        hour_ago = current_time - 3600
        recent_hour_errors = [error for error in self._error_history if error.timestamp >= hour_ago]

        return {
            "total_errors": total_errors,
            "error_categories": category_counts,
            "operation_errors": operation_errors,
            "recent_errors": recent_errors,
            "errors_last_hour": len(recent_hour_errors),
            "most_common_category": (
                max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None
            ),
            "most_problematic_operation": (
                max(operation_errors.items(), key=lambda x: x[1])[0] if operation_errors else None
            ),
        }

    def get_recovery_suggestions(self, error_category: ErrorCategory) -> List[str]:
        """
        Get recovery suggestions for specific error category.

        Args:
            error_category: Category of error

        Returns:
            List of recovery suggestions
        """
        return self._recovery_strategies.get(error_category, [])

    def clear_error_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()
        logger.info("Error history cleared")

    def create_error_report(self) -> Dict[str, Any]:
        """
        Create comprehensive error report for troubleshooting.

        Returns:
            Dictionary containing detailed error report
        """
        statistics = self.get_error_statistics()

        report = {
            "report_timestamp": time.time(),
            "statistics": statistics,
            "diagnostic_summary": {
                "total_errors": statistics["total_errors"],
                "dominant_error_category": statistics.get("most_common_category", "None"),
                "problematic_operation": statistics.get("most_problematic_operation", "None"),
                "recent_error_rate": statistics.get("errors_last_hour", 0),
            },
            "recommendations": self._generate_recommendations(statistics),
        }

        return report

    def _generate_recommendations(self, statistics: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on error patterns.

        Args:
            statistics: Error statistics

        Returns:
            List of recommendations
        """
        recommendations = []

        if statistics["total_errors"] == 0:
            recommendations.append("No errors detected - system operating normally")
            return recommendations

        # Connection error recommendations
        connection_errors = statistics["error_categories"].get("connection_error", 0)
        if connection_errors > statistics["total_errors"] * 0.3:  # >30% connection errors
            recommendations.append(
                "High connection error rate - verify AutoCAD stability and COM interface"
            )

        # Performance error recommendations
        performance_errors = statistics["error_categories"].get("performance_error", 0)
        if performance_errors > 0:
            recommendations.append(
                "Performance issues detected - consider optimizing operations or system resources"
            )

        # Validation error recommendations
        validation_errors = statistics["error_categories"].get("validation_error", 0)
        if validation_errors > statistics["total_errors"] * 0.5:  # >50% validation errors
            recommendations.append(
                "High validation error rate - review input data quality and validation logic"
            )

        # Recent error rate recommendations
        if statistics.get("errors_last_hour", 0) > 10:
            recommendations.append(
                "High recent error rate - investigate recent changes or system issues"
            )

        if not recommendations:
            recommendations.append("Error patterns within normal ranges - continue monitoring")

        return recommendations
