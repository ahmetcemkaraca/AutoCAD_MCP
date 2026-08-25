"""
Performance Monitor for Enhanced AutoCAD Wrapper
==============================================

Tracks performance metrics for AutoCAD operations including response times,
operation counts, and resource usage. Provides detailed analytics for both
manufacturing workflows and interactive development sessions.
"""

import logging
import time
import threading
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""

    operation_name: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PerformanceMonitor:
    """
    Monitors and tracks performance metrics for AutoCAD operations.
    """

    def __init__(self, max_history_size: int = 1000):
        """
        Initialize performance monitor.

        Args:
            max_history_size: Maximum number of operations to keep in history
        """
        self._max_history_size = max_history_size
        self._metrics_lock = threading.Lock()

        # Operation history and statistics
        self._operation_history = deque(maxlen=max_history_size)
        self._operation_stats = defaultdict(
            lambda: {
                "count": 0,
                "total_duration": 0.0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
                "success_count": 0,
                "error_count": 0,
                "recent_errors": deque(maxlen=10),
            }
        )

        # Real-time metrics
        self._current_operations = {}
        self._start_time = time.time()

    @contextmanager
    def measure_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager to measure operation performance.

        Args:
            operation_name: Name of the operation being measured
            metadata: Additional metadata to store with metrics

        Yields:
            Operation context for timing
        """
        operation_id = id(threading.current_thread())
        start_time = time.time()

        try:
            with self._metrics_lock:
                self._current_operations[operation_id] = {
                    "name": operation_name,
                    "start_time": start_time,
                    "metadata": metadata or {},
                }

            yield

            # Operation completed successfully
            end_time = time.time()
            duration = end_time - start_time

            metrics = OperationMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=True,
                metadata=metadata,
            )

            self._record_metrics(metrics)

        except Exception as e:
            # Operation failed
            end_time = time.time()
            duration = end_time - start_time

            metrics = OperationMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=False,
                error_message=str(e),
                metadata=metadata,
            )

            self._record_metrics(metrics)
            raise

        finally:
            with self._metrics_lock:
                self._current_operations.pop(operation_id, None)

    def _record_metrics(self, metrics: OperationMetrics) -> None:
        """
        Record operation metrics and update statistics.

        Args:
            metrics: Operation metrics to record
        """
        with self._metrics_lock:
            # Add to history
            self._operation_history.append(metrics)

            # Update statistics
            stats = self._operation_stats[metrics.operation_name]
            stats["count"] += 1
            stats["total_duration"] += metrics.duration

            if metrics.success:
                stats["success_count"] += 1
                stats["min_duration"] = min(stats["min_duration"], metrics.duration)
                stats["max_duration"] = max(stats["max_duration"], metrics.duration)
            else:
                stats["error_count"] += 1
                stats["recent_errors"].append(
                    {"timestamp": metrics.end_time, "error": metrics.error_message}
                )

    def get_operation_statistics(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance statistics for operations.

        Args:
            operation_name: Specific operation to get stats for (None for all)

        Returns:
            Dictionary containing performance statistics
        """
        with self._metrics_lock:
            if operation_name:
                if operation_name not in self._operation_stats:
                    return {}

                stats = self._operation_stats[operation_name].copy()
                if stats["count"] > 0:
                    stats["average_duration"] = stats["total_duration"] / stats["count"]
                    stats["success_rate"] = stats["success_count"] / stats["count"]
                    if stats["min_duration"] == float("inf"):
                        stats["min_duration"] = 0.0
                else:
                    stats["average_duration"] = 0.0
                    stats["success_rate"] = 0.0
                    stats["min_duration"] = 0.0

                return {operation_name: stats}
            else:
                # Return statistics for all operations
                all_stats = {}
                for op_name, stats in self._operation_stats.items():
                    processed_stats = stats.copy()
                    if processed_stats["count"] > 0:
                        processed_stats["average_duration"] = (
                            processed_stats["total_duration"] / processed_stats["count"]
                        )
                        processed_stats["success_rate"] = (
                            processed_stats["success_count"] / processed_stats["count"]
                        )
                        if processed_stats["min_duration"] == float("inf"):
                            processed_stats["min_duration"] = 0.0
                    else:
                        processed_stats["average_duration"] = 0.0
                        processed_stats["success_rate"] = 0.0
                        processed_stats["min_duration"] = 0.0

                    all_stats[op_name] = processed_stats

                return all_stats

    def get_recent_operations(
        self, count: int = 10, operation_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent operation metrics.

        Args:
            count: Number of recent operations to return
            operation_name: Filter by specific operation name

        Returns:
            List of recent operation metrics
        """
        with self._metrics_lock:
            operations = list(self._operation_history)

            # Filter by operation name if specified
            if operation_name:
                operations = [op for op in operations if op.operation_name == operation_name]

            # Return most recent operations
            recent_ops = operations[-count:] if count > 0 else operations
            return [asdict(op) for op in reversed(recent_ops)]

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.

        Returns:
            Dictionary containing performance summary
        """
        with self._metrics_lock:
            current_time = time.time()
            uptime = current_time - self._start_time

            total_operations = len(self._operation_history)
            successful_operations = sum(1 for op in self._operation_history if op.success)
            failed_operations = total_operations - successful_operations

            if total_operations > 0:
                overall_success_rate = successful_operations / total_operations
                average_duration = (
                    sum(op.duration for op in self._operation_history) / total_operations
                )
            else:
                overall_success_rate = 0.0
                average_duration = 0.0

            # Performance thresholds for warnings
            slow_operations = [
                op for op in self._operation_history if op.duration > 5.0
            ]  # > 5 seconds
            very_slow_operations = [
                op for op in self._operation_history if op.duration > 30.0
            ]  # > 30 seconds

            summary = {
                "uptime_seconds": uptime,
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "overall_success_rate": overall_success_rate,
                "average_operation_duration": average_duration,
                "operations_per_second": total_operations / uptime if uptime > 0 else 0.0,
                "slow_operations_count": len(slow_operations),
                "very_slow_operations_count": len(very_slow_operations),
                "current_active_operations": len(self._current_operations),
                "memory_usage_operations": len(self._operation_history),
            }

            # Add performance warnings
            warnings = []
            if overall_success_rate < 0.95:  # Less than 95% success rate
                warnings.append(f"Low success rate: {overall_success_rate:.1%}")

            if average_duration > 2.0:  # Average operation > 2 seconds
                warnings.append(f"High average duration: {average_duration:.2f}s")

            if len(very_slow_operations) > 0:
                warnings.append(f"{len(very_slow_operations)} operations exceeded 30 seconds")

            summary["performance_warnings"] = warnings

            return summary

    def get_current_operations(self) -> List[Dict[str, Any]]:
        """
        Get currently running operations.

        Returns:
            List of currently active operations
        """
        with self._metrics_lock:
            current_time = time.time()
            current_ops = []

            for op_id, op_info in self._current_operations.items():
                duration = current_time - op_info["start_time"]
                current_ops.append(
                    {
                        "operation_name": op_info["name"],
                        "start_time": op_info["start_time"],
                        "current_duration": duration,
                        "metadata": op_info["metadata"],
                    }
                )

            return current_ops

    def clear_metrics(self) -> None:
        """Clear all performance metrics and statistics."""
        with self._metrics_lock:
            self._operation_history.clear()
            self._operation_stats.clear()
            self._current_operations.clear()
            self._start_time = time.time()
            logger.info("Performance metrics cleared")

    def export_metrics(self, include_history: bool = True) -> Dict[str, Any]:
        """
        Export all performance metrics for analysis.

        Args:
            include_history: Whether to include full operation history

        Returns:
            Dictionary containing all performance data
        """
        export_data = {
            "summary": self.get_performance_summary(),
            "statistics": self.get_operation_statistics(),
            "current_operations": self.get_current_operations(),
        }

        if include_history:
            with self._metrics_lock:
                export_data["operation_history"] = [asdict(op) for op in self._operation_history]

        return export_data
