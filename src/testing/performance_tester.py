"""
Performance Testing for AutoCAD Automation.

Provides tools for measuring and analyzing performance of AutoCAD operations,
including benchmarking, profiling, and performance regression detection.
"""

import time
import logging
import statistics

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
import gc

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance measurement."""
    name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceBenchmark:
    """Performance benchmark results."""
    operation_name: str
    iterations: int
    metrics: List[PerformanceMetric] = field(default_factory=list)
    
    @property
    def average_time(self) -> float:
        """Average execution time."""
        return statistics.mean(m.execution_time for m in self.metrics)
    
    @property
    def median_time(self) -> float:
        """Median execution time."""
        return statistics.median(m.execution_time for m in self.metrics)
    
    @property
    def std_deviation(self) -> float:
        """Standard deviation of execution times."""
        return statistics.stdev(m.execution_time for m in self.metrics) if len(self.metrics) > 1 else 0
    
    @property
    def min_time(self) -> float:
        """Minimum execution time."""
        return min(m.execution_time for m in self.metrics)
    
    @property
    def max_time(self) -> float:
        """Maximum execution time."""
        return max(m.execution_time for m in self.metrics)


class PerformanceTester:
    """Performance testing and benchmarking for AutoCAD operations."""
    
    def __init__(self):
        self.benchmarks: Dict[str, PerformanceBenchmark] = {}
        self.baseline: Optional[Dict[str, PerformanceBenchmark]] = None
        self.monitoring_active = False
        self.monitor_thread = None
        self.system_metrics = []
    
    @contextmanager
    def measure_performance(self, operation_name: str):
        """Context manager for measuring performance of operations."""
        # Force garbage collection before measurement
        gc.collect()
        
        # Get initial system state
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent = process.cpu_percent()
        
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Get final system state
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_usage = final_memory - initial_memory
            final_cpu = process.cpu_percent()
            
            # Create metric
            metric = PerformanceMetric(
                name=operation_name,
                execution_time=execution_time,
                memory_usage=memory_usage,
                cpu_usage=final_cpu,
                timestamp=time.time()
            )
            
            # Store metric
            if operation_name not in self.benchmarks:
                self.benchmarks[operation_name] = PerformanceBenchmark(
                    operation_name=operation_name,
                    iterations=0
                )
            
            self.benchmarks[operation_name].metrics.append(metric)
            self.benchmarks[operation_name].iterations += 1
            
            logger.debug(f"Performance measurement: {operation_name} took {execution_time:.4f}s")
    
    def benchmark_operation(self, operation: Callable, operation_name: str, 
                          iterations: int = 100, warmup_iterations: int = 5) -> PerformanceBenchmark:
        """Benchmark an operation multiple times."""
        logger.info(f"Benchmarking {operation_name} with {iterations} iterations")
        
        # Warmup runs
        for _ in range(warmup_iterations):
            try:
                operation()
            except Exception as e:
                logger.warning(f"Warmup iteration failed: {e}")
        
        # Clear any existing metrics for this operation
        if operation_name in self.benchmarks:
            self.benchmarks[operation_name].metrics.clear()
        
        # Perform benchmark iterations
        for i in range(iterations):
            try:
                with self.measure_performance(operation_name):
                    operation()
            except Exception as e:
                logger.error(f"Benchmark iteration {i+1} failed: {e}")
                # Continue with remaining iterations
        
        benchmark = self.benchmarks.get(operation_name)
        if benchmark:
            logger.info(f"Benchmark completed: {operation_name}")
            logger.info(f"  Average time: {benchmark.average_time:.4f}s")
            logger.info(f"  Min time: {benchmark.min_time:.4f}s")
            logger.info(f"  Max time: {benchmark.max_time:.4f}s")
            logger.info(f"  Std deviation: {benchmark.std_deviation:.4f}s")
        
        return benchmark
    
    def benchmark_autocad_operations(self, mock_mode: bool = True) -> Dict[str, PerformanceBenchmark]:
        """Benchmark common AutoCAD operations."""
        if mock_mode:
            from .mock_autocad import MockAutoCAD
            acad = MockAutoCAD()
        else:
            from src.utils import get_autocad_instance
            acad = get_autocad_instance()
        
        operations = {
            'draw_line': lambda: acad.model.AddLine([0, 0, 0], [100, 100, 0]),
            'draw_circle': lambda: acad.model.AddCircle([50, 50, 0], 25),
            'draw_polyline': lambda: acad.model.AddPolyline([[0, 0, 0], [50, 0, 0], [50, 50, 0], [0, 50, 0]]),
        }
        
        # Add 3D operations if supported
        if hasattr(acad.model, 'AddExtrudedSolid'):
            operations['extrude_solid'] = lambda: self._benchmark_extrusion(acad)
        
        results = {}
        for op_name, op_func in operations.items():
            try:
                benchmark = self.benchmark_operation(op_func, op_name, iterations=50)
                results[op_name] = benchmark
            except Exception as e:
                logger.error(f"Failed to benchmark {op_name}: {e}")
        
        return results
    
    def _benchmark_extrusion(self, acad):
        """Helper for benchmarking extrusion operations."""
        # Create profile
        profile = acad.model.AddPolyline([[0, 0, 0], [25, 0, 0], [25, 25, 0], [0, 25, 0]])
        # Create extrusion
        return acad.model.AddExtrudedSolid(profile, 10.0)
    
    def set_baseline(self, baseline_name: str = "default"):
        """Set current benchmarks as baseline for comparison."""
        self.baseline = self.benchmarks.copy()
        logger.info(f"Performance baseline '{baseline_name}' established with {len(self.baseline)} operations")
    
    def compare_to_baseline(self) -> Dict[str, Dict[str, float]]:
        """Compare current performance to baseline."""
        if not self.baseline:
            raise ValueError("No baseline established. Call set_baseline() first.")
        
        comparison = {}
        
        for op_name, current_benchmark in self.benchmarks.items():
            if op_name in self.baseline:
                baseline_benchmark = self.baseline[op_name]
                
                # Calculate performance ratios
                time_ratio = current_benchmark.average_time / baseline_benchmark.average_time
                memory_ratio = (statistics.mean(m.memory_usage for m in current_benchmark.metrics) / 
                              statistics.mean(m.memory_usage for m in baseline_benchmark.metrics))
                
                comparison[op_name] = {
                    'time_ratio': time_ratio,
                    'time_change_percent': (time_ratio - 1) * 100,
                    'memory_ratio': memory_ratio,
                    'memory_change_percent': (memory_ratio - 1) * 100,
                    'baseline_avg_time': baseline_benchmark.average_time,
                    'current_avg_time': current_benchmark.average_time
                }
        
        return comparison
    
    def start_system_monitoring(self, interval: float = 1.0):
        """Start continuous system monitoring."""
        if self.monitoring_active:
            logger.warning("System monitoring already active")
            return
        
        self.monitoring_active = True
        self.system_metrics = []
        
        def monitor():
            while self.monitoring_active:
                try:
                    process = psutil.Process()
                    metric = {
                        'timestamp': time.time(),
                        'cpu_percent': process.cpu_percent(),
                        'memory_mb': process.memory_info().rss / 1024 / 1024,
                        'memory_percent': process.memory_percent(),
                        'threads': process.num_threads()
                    }
                    self.system_metrics.append(metric)
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"System monitoring error: {e}")
                    break
        
        self.monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.monitor_thread.start()
        logger.info("System monitoring started")
    
    def stop_system_monitoring(self) -> List[Dict[str, Any]]:
        """Stop system monitoring and return collected metrics."""
        if not self.monitoring_active:
            return []
        
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread = None
        
        logger.info(f"System monitoring stopped. Collected {len(self.system_metrics)} metrics")
        return self.system_metrics.copy()
    
    def analyze_performance_trends(self, operation_name: str) -> Dict[str, Any]:
        """Analyze performance trends for a specific operation."""
        if operation_name not in self.benchmarks:
            raise ValueError(f"No benchmark data for operation: {operation_name}")
        
        benchmark = self.benchmarks[operation_name]
        metrics = benchmark.metrics
        
        if len(metrics) < 3:
            return {"error": "Insufficient data for trend analysis"}
        
        # Calculate trends
        times = [m.execution_time for m in metrics]
        memory_usage = [m.memory_usage for m in metrics]
        
        # Simple linear trend analysis
        n = len(times)
        x_values = list(range(n))
        
        # Time trend
        time_slope = self._calculate_slope(x_values, times)
        memory_slope = self._calculate_slope(x_values, memory_usage)
        
        # Performance stability (coefficient of variation)
        time_cv = statistics.stdev(times) / statistics.mean(times) if statistics.mean(times) > 0 else 0
        
        return {
            'operation': operation_name,
            'total_measurements': n,
            'time_trend': 'improving' if time_slope < -0.001 else 'degrading' if time_slope > 0.001 else 'stable',
            'time_slope': time_slope,
            'memory_trend': 'increasing' if memory_slope > 0.1 else 'decreasing' if memory_slope < -0.1 else 'stable',
            'memory_slope': memory_slope,
            'stability': 'stable' if time_cv < 0.1 else 'variable' if time_cv < 0.3 else 'unstable',
            'coefficient_of_variation': time_cv,
            'average_time': benchmark.average_time,
            'time_range': benchmark.max_time - benchmark.min_time
        }
    
    def _calculate_slope(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate linear regression slope."""
        n = len(x_values)
        if n < 2:
            return 0.0
        
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def generate_performance_report(self, include_system_metrics: bool = True) -> str:
        """Generate comprehensive performance report."""
        report = []
        report.append("AutoCAD Performance Test Report")
        report.append("=" * 50)
        report.append("")
        
        if not self.benchmarks:
            report.append("No performance data available.")
            return "\\n".join(report)
        
        # Summary statistics
        total_operations = sum(b.iterations for b in self.benchmarks.values())
        report.append(f"Total Operations Tested: {len(self.benchmarks)}")
        report.append(f"Total Measurements: {total_operations}")
        report.append("")
        
        # Individual operation results
        for op_name, benchmark in self.benchmarks.items():
            report.append(f"Operation: {op_name}")
            report.append("-" * 30)
            report.append(f"  Iterations: {benchmark.iterations}")
            report.append(f"  Average Time: {benchmark.average_time:.4f}s")
            report.append(f"  Median Time: {benchmark.median_time:.4f}s")
            report.append(f"  Min Time: {benchmark.min_time:.4f}s")
            report.append(f"  Max Time: {benchmark.max_time:.4f}s")
            report.append(f"  Std Deviation: {benchmark.std_deviation:.4f}s")
            
            # Memory usage
            if benchmark.metrics:
                avg_memory = statistics.mean(m.memory_usage for m in benchmark.metrics)
                report.append(f"  Avg Memory Usage: {avg_memory:.2f} MB")
            
            # Trend analysis
            try:
                trends = self.analyze_performance_trends(op_name)
                report.append(f"  Performance Trend: {trends['time_trend']}")
                report.append(f"  Stability: {trends['stability']}")
            except:
                pass
            
            report.append("")
        
        # Baseline comparison
        if self.baseline:
            report.append("Baseline Comparison")
            report.append("-" * 30)
            try:
                comparison = self.compare_to_baseline()
                for op_name, comp_data in comparison.items():
                    change = comp_data['time_change_percent']
                    status = "improved" if change < -5 else "degraded" if change > 5 else "similar"
                    report.append(f"  {op_name}: {change:+.1f}% ({status})")
                report.append("")
            except Exception as e:
                report.append(f"  Baseline comparison failed: {e}")
                report.append("")
        
        # System metrics summary
        if include_system_metrics and self.system_metrics:
            report.append("System Metrics Summary")
            report.append("-" * 30)
            cpu_values = [m['cpu_percent'] for m in self.system_metrics]
            memory_values = [m['memory_mb'] for m in self.system_metrics]
            
            report.append(f"  Average CPU Usage: {statistics.mean(cpu_values):.1f}%")
            report.append(f"  Peak CPU Usage: {max(cpu_values):.1f}%")
            report.append(f"  Average Memory Usage: {statistics.mean(memory_values):.1f} MB")
            report.append(f"  Peak Memory Usage: {max(memory_values):.1f} MB")
            report.append("")
        
        return "\\n".join(report)
    
    def export_metrics(self, filepath: str, format: str = 'csv'):
        """Export performance metrics to file."""
        import csv
        import json
        
        if format.lower() == 'csv':
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Operation', 'Execution_Time', 'Memory_Usage', 'CPU_Usage', 'Timestamp'])
                
                for benchmark in self.benchmarks.values():
                    for metric in benchmark.metrics:
                        writer.writerow([
                            metric.name,
                            metric.execution_time,
                            metric.memory_usage,
                            metric.cpu_usage,
                            metric.timestamp
                        ])
        
        elif format.lower() == 'json':
            data = {
                'benchmarks': {
                    name: {
                        'operation_name': benchmark.operation_name,
                        'iterations': benchmark.iterations,
                        'average_time': benchmark.average_time,
                        'median_time': benchmark.median_time,
                        'min_time': benchmark.min_time,
                        'max_time': benchmark.max_time,
                        'std_deviation': benchmark.std_deviation,
                        'metrics': [
                            {
                                'execution_time': m.execution_time,
                                'memory_usage': m.memory_usage,
                                'cpu_usage': m.cpu_usage,
                                'timestamp': m.timestamp
                            }
                            for m in benchmark.metrics
                        ]
                    }
                    for name, benchmark in self.benchmarks.items()
                },
                'system_metrics': self.system_metrics
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        
        logger.info(f"Performance metrics exported to {filepath}")
    
    def clear_metrics(self):
        """Clear all performance metrics."""
        self.benchmarks.clear()
        self.system_metrics.clear()
        logger.info("Performance metrics cleared")
    
    def load_baseline(self, filepath: str):
        """Load baseline metrics from file."""
        import json
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            baseline = {}
            for name, benchmark_data in data.get('benchmarks', {}).items():
                benchmark = PerformanceBenchmark(
                    operation_name=benchmark_data['operation_name'],
                    iterations=benchmark_data['iterations']
                )
                
                for metric_data in benchmark_data['metrics']:
                    metric = PerformanceMetric(
                        name=benchmark_data['operation_name'],
                        execution_time=metric_data['execution_time'],
                        memory_usage=metric_data['memory_usage'],
                        cpu_usage=metric_data['cpu_usage'],
                        timestamp=metric_data['timestamp']
                    )
                    benchmark.metrics.append(metric)
                
                baseline[name] = benchmark
            
            self.baseline = baseline
            logger.info(f"Baseline loaded from {filepath} with {len(baseline)} operations")
            
        except Exception as e:
            logger.error(f"Failed to load baseline from {filepath}: {e}")
            raise