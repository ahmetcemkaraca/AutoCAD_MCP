"""
Interactive Performance Analyzer
===============================

Advanced performance analysis system for AutoCAD Python development
with real-time monitoring, bottleneck detection, and optimization
recommendations. Integrates with debugging and inspection systems.
"""

import logging
import time
import threading
import psutil
import gc
import sys
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics

# Try to import resource module (Unix only)
try:
    import resource
    RESOURCE_AVAILABLE = True
except ImportError:
    RESOURCE_AVAILABLE = False

# Import monitoring and inspection components
from ..enhanced_autocad.performance_monitor import PerformanceMonitor, OperationMetrics
from ..inspection.object_inspector import ObjectInspector
from ..inspection.method_discoverer import MethodDiscoverer

logger = logging.getLogger(__name__)


class PerformanceCategory(Enum):
    """Categories of performance analysis."""
    AUTOCAD_COM = "autocad_com"
    PYTHON_EXECUTION = "python_execution"
    MEMORY_USAGE = "memory_usage"
    IO_OPERATIONS = "io_operations"
    DATABASE_ACCESS = "database_access"
    NETWORK_CALLS = "network_calls"
    ALGORITHM_EFFICIENCY = "algorithm_efficiency"


class AlertSeverity(Enum):
    """Performance alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Individual performance metric data."""
    name: str
    value: float
    unit: str
    timestamp: float
    category: PerformanceCategory
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert with recommended actions."""
    id: str
    severity: AlertSeverity
    category: PerformanceCategory
    title: str
    description: str
    metric_value: float
    threshold: float
    recommendations: List[str]
    timestamp: float
    resolved: bool = False


@dataclass
class BottleneckAnalysis:
    """Analysis of performance bottlenecks."""
    operation_name: str
    total_time: float
    call_count: int
    average_time: float
    max_time: float
    min_time: float
    percentage_of_total: float
    suggestions: List[str]


class PerformanceAnalyzer:
    """
    Advanced performance analysis system for interactive AutoCAD development.
    
    Provides real-time monitoring, bottleneck detection, optimization
    recommendations, and integration with debugging tools.
    """
    
    def __init__(self, performance_monitor=None, object_inspector=None):
        """
        Initialize performance analyzer.
        
        Args:
            performance_monitor: Base performance monitor
            object_inspector: Object inspector for context analysis
        """
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.object_inspector = object_inspector or ObjectInspector()
        self.method_discoverer = MethodDiscoverer()
        
        # Analysis state
        self.analysis_active = False
        self.analysis_lock = threading.Lock()
        self.session_id = None
        
        # Metrics and alerts
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.active_alerts: Dict[str, PerformanceAlert] = {}
        self.resolved_alerts: List[PerformanceAlert] = []
        
        # Real-time monitoring
        self.monitoring_thread = None
        self.monitoring_interval = 1.0  # seconds
        self.system_metrics_enabled = True
        
        # Thresholds and configuration
        self.thresholds = self._initialize_thresholds()
        self.profiling_overhead_limit = 0.05  # 5% max overhead
        
        # Bottleneck tracking
        self.operation_times: Dict[str, List[float]] = defaultdict(list)
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.autocad_operation_stats: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Performance analyzer initialized")

    def start_analysis_session(self, session_id: Optional[str] = None) -> str:
        """
        Start performance analysis session with real-time monitoring.
        
        Args:
            session_id: Optional session identifier
            
        Returns:
            Session ID for tracking
        """
        with self.analysis_lock:
            if self.analysis_active:
                raise RuntimeError("Performance analysis already active")
            
            self.session_id = session_id or f"perf_{int(time.time())}"
            self.analysis_active = True
            
            # Clear previous session data
            self.metrics_history.clear()
            self.active_alerts.clear()
            self.operation_times.clear()
            self.call_counts.clear()
            
            # Start real-time monitoring
            if self.system_metrics_enabled:
                self._start_monitoring_thread()
            
            logger.info(f"Performance analysis session started: {self.session_id}")
            return self.session_id

    def stop_analysis_session(self) -> Dict[str, Any]:
        """
        Stop performance analysis session and generate summary.
        
        Returns:
            Session summary with performance statistics
        """
        with self.analysis_lock:
            if not self.analysis_active:
                return {"message": "No active analysis session"}
            
            # Stop monitoring
            self._stop_monitoring_thread()
            
            # Generate session summary
            summary = self._generate_session_summary()
            
            # Reset state
            self.analysis_active = False
            self.session_id = None
            
            logger.info("Performance analysis session stopped")
            return summary

    def record_operation(self, operation_name: str, duration: float, context: Optional[Dict[str, Any]] = None):
        """
        Record an operation performance metric.
        
        Args:
            operation_name: Name of the operation
            duration: Operation duration in seconds
            context: Additional context information
        """
        if not self.analysis_active:
            return
        
        # Record timing
        self.operation_times[operation_name].append(duration)
        self.call_counts[operation_name] += 1
        
        # Create metric
        metric = PerformanceMetric(
            name=operation_name,
            value=duration,
            unit="seconds",
            timestamp=time.time(),
            category=self._categorize_operation(operation_name),
            context=context or {}
        )
        
        self.metrics_history[operation_name].append(metric)
        
        # Check for alerts
        self._check_performance_alerts(metric)

    def analyze_bottlenecks(self, top_n: int = 10) -> List[BottleneckAnalysis]:
        """
        Analyze performance bottlenecks and identify optimization opportunities.
        
        Args:
            top_n: Number of top bottlenecks to return
            
        Returns:
            List of bottleneck analyses sorted by impact
        """
        bottlenecks = []
        total_time = sum(sum(times) for times in self.operation_times.values())
        
        if total_time == 0:
            return []
        
        for operation, times in self.operation_times.items():
            if not times:
                continue
                
            operation_total = sum(times)
            analysis = BottleneckAnalysis(
                operation_name=operation,
                total_time=operation_total,
                call_count=len(times),
                average_time=statistics.mean(times),
                max_time=max(times),
                min_time=min(times),
                percentage_of_total=(operation_total / total_time) * 100,
                suggestions=self._generate_optimization_suggestions(operation, times)
            )
            bottlenecks.append(analysis)
        
        # Sort by percentage of total time and return top N
        bottlenecks.sort(key=lambda x: x.percentage_of_total, reverse=True)
        return bottlenecks[:top_n]

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """
        Get current real-time performance metrics.
        
        Returns:
            Dictionary of current performance metrics
        """
        if not self.analysis_active:
            return {"message": "Analysis not active"}
        
        current_time = time.time()
        metrics = {
            "timestamp": current_time,
            "session_id": self.session_id,
            "system_metrics": self._get_system_metrics(),
            "operation_metrics": self._get_operation_metrics(),
            "active_alerts": len(self.active_alerts),
            "memory_usage": self._get_memory_metrics(),
            "autocad_stats": self._get_autocad_performance_stats()
        }
        
        return metrics

    def profile_function(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """
        Profile a specific function execution with detailed analysis.
        
        Args:
            func: Function to profile
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Detailed profiling results
        """
        if not self.analysis_active:
            return {"error": "Analysis session not active"}
        
        start_time = time.time()
        start_memory = psutil.virtual_memory().used
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        end_memory = psutil.virtual_memory().used
        
        duration = end_time - start_time
        memory_delta = end_memory - start_memory
        
        # Create profiling result
        profile_result = {
            "function_name": func.__name__,
            "duration": duration,
            "memory_delta": memory_delta,
            "success": success,
            "error": error,
            "timestamp": start_time,
            "result_available": result is not None,
            "performance_category": self._categorize_operation(func.__name__),
            "optimization_suggestions": self._generate_function_suggestions(func.__name__, duration)
        }
        
        # Record the operation
        self.record_operation(func.__name__, duration, {
            "profiled": True,
            "memory_delta": memory_delta,
            "success": success
        })
        
        return profile_result

    def compare_performance(self, baseline_session: str, current_session: str) -> Dict[str, Any]:
        """
        Compare performance between two analysis sessions.
        
        Args:
            baseline_session: Baseline session ID
            current_session: Current session ID for comparison
            
        Returns:
            Performance comparison results
        """
        # This would typically load historical session data
        # For now, provide a structure for comparison results
        comparison = {
            "baseline_session": baseline_session,
            "current_session": current_session,
            "performance_delta": {},
            "improvement_areas": [],
            "regression_areas": [],
            "recommendations": []
        }
        
        return comparison

    def get_optimization_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive optimization report with actionable recommendations.
        
        Returns:
            Detailed optimization report
        """
        bottlenecks = self.analyze_bottlenecks()
        alerts = list(self.active_alerts.values())
        
        report = {
            "report_timestamp": time.time(),
            "session_id": self.session_id,
            "analysis_active": self.analysis_active,
            "executive_summary": self._generate_executive_summary(bottlenecks, alerts),
            "top_bottlenecks": [
                {
                    "operation": b.operation_name,
                    "impact": f"{b.percentage_of_total:.1f}%",
                    "average_time": f"{b.average_time:.3f}s",
                    "call_count": b.call_count,
                    "suggestions": b.suggestions[:3]  # Top 3 suggestions
                }
                for b in bottlenecks[:5]
            ],
            "active_alerts": [
                {
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "description": alert.description,
                    "recommendations": alert.recommendations[:2]  # Top 2 recommendations
                }
                for alert in alerts if alert.severity != AlertSeverity.INFO
            ],
            "system_health": self._assess_system_health(),
            "autocad_performance": self._assess_autocad_performance(),
            "memory_analysis": self._analyze_memory_patterns(),
            "recommendations": self._generate_top_recommendations(bottlenecks, alerts)
        }
        
        return report

    def _initialize_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Initialize performance alert thresholds."""
        return {
            "response_time": {
                "warning": 1.0,    # 1 second
                "critical": 5.0    # 5 seconds
            },
            "memory_usage": {
                "warning": 0.8,    # 80% of available memory
                "critical": 0.9    # 90% of available memory
            },
            "cpu_usage": {
                "warning": 0.8,    # 80% CPU
                "critical": 0.95   # 95% CPU
            },
            "autocad_calls": {
                "warning": 100,    # 100 calls per second
                "critical": 500    # 500 calls per second
            }
        }

    def _start_monitoring_thread(self):
        """Start background monitoring thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
            
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()

    def _stop_monitoring_thread(self):
        """Stop background monitoring thread."""
        self.analysis_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2.0)

    def _monitoring_loop(self):
        """Background monitoring loop for system metrics."""
        while self.analysis_active:
            try:
                # Collect system metrics
                system_metrics = self._get_system_metrics()
                
                # Record key metrics
                for metric_name, value in system_metrics.items():
                    if isinstance(value, (int, float)):
                        metric = PerformanceMetric(
                            name=f"system_{metric_name}",
                            value=value,
                            unit=self._get_metric_unit(metric_name),
                            timestamp=time.time(),
                            category=PerformanceCategory.PYTHON_EXECUTION
                        )
                        self.metrics_history[f"system_{metric_name}"].append(metric)
                
                # Check system-level alerts
                self._check_system_alerts(system_metrics)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.warning(f"Monitoring loop error: {e}")
                time.sleep(self.monitoring_interval)

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_available": memory.available,
                "active_threads": threading.active_count(),
                "gc_collections": sum(gc.get_stats(), [])
            }
        except Exception as e:
            logger.warning(f"Could not get system metrics: {e}")
            return {}

    def _get_operation_metrics(self) -> Dict[str, Any]:
        """Get current operation performance metrics."""
        metrics = {}
        
        for operation, times in self.operation_times.items():
            if times:
                metrics[operation] = {
                    "call_count": len(times),
                    "total_time": sum(times),
                    "average_time": statistics.mean(times),
                    "recent_calls": len([t for t in times if time.time() - t < 60])  # Last minute
                }
        
        return metrics

    def _get_memory_metrics(self) -> Dict[str, Any]:
        """Get memory usage metrics."""
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            
            return {
                "system_total": memory.total,
                "system_used": memory.used,
                "system_available": memory.available,
                "process_memory": process.memory_info().rss,
                "process_percent": process.memory_percent(),
                "gc_objects": len(gc.get_objects())
            }
        except Exception:
            return {}

    def _get_autocad_performance_stats(self) -> Dict[str, Any]:
        """Get AutoCAD-specific performance statistics."""
        autocad_ops = {
            op: stats for op, stats in self.operation_times.items()
            if 'autocad' in op.lower() or 'com' in op.lower()
        }
        
        if not autocad_ops:
            return {"message": "No AutoCAD operations recorded"}
        
        total_autocad_time = sum(sum(times) for times in autocad_ops.values())
        total_autocad_calls = sum(len(times) for times in autocad_ops.values())
        
        return {
            "total_operations": total_autocad_calls,
            "total_time": total_autocad_time,
            "average_time_per_call": total_autocad_time / max(total_autocad_calls, 1),
            "operations_per_second": total_autocad_calls / max(total_autocad_time, 0.001),
            "slowest_operations": sorted(
                [(op, max(times)) for op, times in autocad_ops.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    def _categorize_operation(self, operation_name: str) -> PerformanceCategory:
        """Categorize an operation for performance analysis."""
        op_lower = operation_name.lower()
        
        if any(term in op_lower for term in ['autocad', 'com', 'dispatch']):
            return PerformanceCategory.AUTOCAD_COM
        elif any(term in op_lower for term in ['read', 'write', 'file', 'io']):
            return PerformanceCategory.IO_OPERATIONS
        elif any(term in op_lower for term in ['db', 'database', 'query']):
            return PerformanceCategory.DATABASE_ACCESS
        elif any(term in op_lower for term in ['http', 'request', 'network']):
            return PerformanceCategory.NETWORK_CALLS
        elif any(term in op_lower for term in ['sort', 'search', 'algorithm']):
            return PerformanceCategory.ALGORITHM_EFFICIENCY
        else:
            return PerformanceCategory.PYTHON_EXECUTION

    def _check_performance_alerts(self, metric: PerformanceMetric):
        """Check if a metric triggers any performance alerts."""
        if metric.category == PerformanceCategory.AUTOCAD_COM:
            if metric.value > self.thresholds["response_time"]["critical"]:
                self._create_alert(
                    AlertSeverity.CRITICAL,
                    metric.category,
                    "Slow AutoCAD Operation",
                    f"AutoCAD operation '{metric.name}' took {metric.value:.2f}s",
                    metric.value,
                    self.thresholds["response_time"]["critical"],
                    [
                        "Review AutoCAD operation for optimization opportunities",
                        "Consider batching multiple operations",
                        "Check for unnecessary object refreshes"
                    ]
                )

    def _check_system_alerts(self, system_metrics: Dict[str, Any]):
        """Check system metrics for alert conditions."""
        if "memory_percent" in system_metrics:
            memory_percent = system_metrics["memory_percent"] / 100.0
            if memory_percent > self.thresholds["memory_usage"]["critical"]:
                self._create_alert(
                    AlertSeverity.CRITICAL,
                    PerformanceCategory.MEMORY_USAGE,
                    "High Memory Usage",
                    f"System memory usage at {memory_percent*100:.1f}%",
                    memory_percent,
                    self.thresholds["memory_usage"]["critical"],
                    [
                        "Review memory usage patterns",
                        "Consider implementing object pooling",
                        "Check for memory leaks in loops"
                    ]
                )

    def _create_alert(self, severity: AlertSeverity, category: PerformanceCategory,
                     title: str, description: str, value: float, threshold: float,
                     recommendations: List[str]):
        """Create a new performance alert."""
        alert_id = f"{category.value}_{int(time.time())}"
        
        alert = PerformanceAlert(
            id=alert_id,
            severity=severity,
            category=category,
            title=title,
            description=description,
            metric_value=value,
            threshold=threshold,
            recommendations=recommendations,
            timestamp=time.time()
        )
        
        self.active_alerts[alert_id] = alert
        logger.warning(f"Performance alert: {title} - {description}")

    def _generate_optimization_suggestions(self, operation: str, times: List[float]) -> List[str]:
        """Generate optimization suggestions for an operation."""
        suggestions = []
        
        if 'autocad' in operation.lower():
            suggestions.extend([
                "Consider using bulk operations instead of individual calls",
                "Minimize object property access in loops",
                "Cache frequently accessed AutoCAD objects",
                "Use transaction management for multiple operations"
            ])
        
        if len(times) > 10 and max(times) > statistics.mean(times) * 3:
            suggestions.append("Operation shows high variance - investigate inconsistent performance")
        
        if statistics.mean(times) > 1.0:
            suggestions.append("Average execution time is high - consider algorithm optimization")
        
        return suggestions

    def _generate_function_suggestions(self, func_name: str, duration: float) -> List[str]:
        """Generate optimization suggestions for a specific function."""
        suggestions = []
        
        if duration > 1.0:
            suggestions.append("Function execution time is high - consider profiling with cProfile")
        
        if 'loop' in func_name.lower() or 'iterate' in func_name.lower():
            suggestions.append("Consider vectorization or bulk operations for loop-based functions")
        
        return suggestions

    def _generate_session_summary(self) -> Dict[str, Any]:
        """Generate comprehensive session summary."""
        total_operations = sum(self.call_counts.values())
        total_time = sum(sum(times) for times in self.operation_times.values())
        
        return {
            "session_id": self.session_id,
            "duration": time.time() - (self.session_id and int(self.session_id.split('_')[1]) or time.time()),
            "total_operations": total_operations,
            "total_execution_time": total_time,
            "unique_operations": len(self.operation_times),
            "alerts_generated": len(self.active_alerts) + len(self.resolved_alerts),
            "top_bottlenecks": [b.operation_name for b in self.analyze_bottlenecks()[:3]],
            "performance_score": self._calculate_performance_score()
        }

    def _generate_executive_summary(self, bottlenecks: List[BottleneckAnalysis], alerts: List[PerformanceAlert]) -> str:
        """Generate executive summary of performance analysis."""
        if not bottlenecks and not alerts:
            return "Performance analysis shows no significant issues detected."
        
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        
        summary_parts = []
        
        if critical_alerts:
            summary_parts.append(f"{len(critical_alerts)} critical performance issues require immediate attention.")
        
        if bottlenecks:
            top_bottleneck = bottlenecks[0]
            summary_parts.append(f"Top bottleneck: {top_bottleneck.operation_name} ({top_bottleneck.percentage_of_total:.1f}% of total time).")
        
        return " ".join(summary_parts) if summary_parts else "Performance analysis completed successfully."

    def _assess_system_health(self) -> str:
        """Assess overall system health based on metrics."""
        if not self.metrics_history:
            return "insufficient_data"
        
        critical_alerts = [a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL]
        warning_alerts = [a for a in self.active_alerts.values() if a.severity == AlertSeverity.WARNING]
        
        if critical_alerts:
            return "critical"
        elif len(warning_alerts) > 5:
            return "degraded"
        elif warning_alerts:
            return "warning"
        else:
            return "healthy"

    def _assess_autocad_performance(self) -> str:
        """Assess AutoCAD-specific performance."""
        autocad_stats = self._get_autocad_performance_stats()
        
        if "message" in autocad_stats:
            return "no_data"
        
        avg_time = autocad_stats.get("average_time_per_call", 0)
        
        if avg_time > 2.0:
            return "slow"
        elif avg_time > 0.5:
            return "moderate"
        else:
            return "fast"

    def _analyze_memory_patterns(self) -> Dict[str, Any]:
        """Analyze memory usage patterns."""
        memory_metrics = [m for metrics in self.metrics_history.values() 
                         for m in metrics if 'memory' in m.name]
        
        if not memory_metrics:
            return {"status": "no_data"}
        
        memory_values = [m.value for m in memory_metrics if isinstance(m.value, (int, float))]
        
        if not memory_values:
            return {"status": "no_numeric_data"}
        
        return {
            "trend": "increasing" if memory_values[-1] > memory_values[0] else "stable",
            "peak_usage": max(memory_values),
            "average_usage": statistics.mean(memory_values),
            "volatility": "high" if statistics.stdev(memory_values) > statistics.mean(memory_values) * 0.2 else "low"
        }

    def _generate_top_recommendations(self, bottlenecks: List[BottleneckAnalysis], alerts: List[PerformanceAlert]) -> List[str]:
        """Generate top optimization recommendations."""
        recommendations = []
        
        # From bottlenecks
        for bottleneck in bottlenecks[:3]:
            if bottleneck.suggestions:
                recommendations.append(f"{bottleneck.operation_name}: {bottleneck.suggestions[0]}")
        
        # From alerts
        for alert in alerts[:2]:
            if alert.recommendations:
                recommendations.append(f"{alert.title}: {alert.recommendations[0]}")
        
        return recommendations

    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)."""
        score = 100.0
        
        # Deduct for active alerts
        critical_alerts = [a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL]
        warning_alerts = [a for a in self.active_alerts.values() if a.severity == AlertSeverity.WARNING]
        
        score -= len(critical_alerts) * 20
        score -= len(warning_alerts) * 5
        
        # Deduct for slow operations
        bottlenecks = self.analyze_bottlenecks()
        if bottlenecks:
            top_bottleneck = bottlenecks[0]
            if top_bottleneck.percentage_of_total > 50:
                score -= 20
            elif top_bottleneck.percentage_of_total > 25:
                score -= 10
        
        return max(0.0, score)

    def _get_metric_unit(self, metric_name: str) -> str:
        """Get appropriate unit for a metric."""
        if 'percent' in metric_name:
            return '%'
        elif 'memory' in metric_name or 'used' in metric_name:
            return 'bytes'
        elif 'time' in metric_name:
            return 'seconds'
        else:
            return 'count'