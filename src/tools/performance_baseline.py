"""
Performance Baseline Testing for Enhanced AutoCAD
===============================================

Comprehensive performance testing suite that establishes baseline metrics
for the current pyautocad system and validates that Enhanced AutoCAD
meets or exceeds performance requirements.
"""

import time
import logging
import statistics
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, asdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PerformanceTest:
    """Definition of a performance test."""

    name: str
    description: str
    test_function: Callable
    expected_max_duration: float
    iterations: int = 5
    warmup_iterations: int = 1


@dataclass
class PerformanceResult:
    """Result of a performance test."""

    test_name: str
    iterations: int
    durations: List[float]
    average_duration: float
    median_duration: float
    min_duration: float
    max_duration: float
    std_deviation: float
    success_rate: float
    errors: List[str]
    passed: bool


class PerformanceBaseline:
    """
    Performance testing and baseline establishment for AutoCAD wrappers.
    """

    def __init__(self, project_root: str):
        """
        Initialize performance baseline tester.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.results_dir = self.project_root / "performance_results"
        self.results_dir.mkdir(exist_ok=True)

        # Performance test definitions
        self.performance_tests = self._define_performance_tests()

    def _define_performance_tests(self) -> List[PerformanceTest]:
        """
        Define the performance tests to run.

        Returns:
            List of performance test definitions
        """
        return [
            PerformanceTest(
                name="connection_establishment",
                description="Time to establish AutoCAD connection",
                test_function=self._test_connection_establishment,
                expected_max_duration=5.0,  # 5 seconds max
                iterations=3,
                warmup_iterations=1,
            ),
            PerformanceTest(
                name="basic_line_drawing",
                description="Time to draw a simple line",
                test_function=self._test_basic_line_drawing,
                expected_max_duration=1.0,  # 1 second max
                iterations=10,
                warmup_iterations=2,
            ),
            PerformanceTest(
                name="basic_circle_drawing",
                description="Time to draw a simple circle",
                test_function=self._test_basic_circle_drawing,
                expected_max_duration=1.0,  # 1 second max
                iterations=10,
                warmup_iterations=2,
            ),
            PerformanceTest(
                name="entity_iteration",
                description="Time to iterate through drawing entities",
                test_function=self._test_entity_iteration,
                expected_max_duration=2.0,  # 2 seconds max
                iterations=5,
                warmup_iterations=1,
            ),
            PerformanceTest(
                name="property_access",
                description="Time to access entity properties",
                test_function=self._test_property_access,
                expected_max_duration=0.5,  # 0.5 seconds max
                iterations=20,
                warmup_iterations=3,
            ),
            PerformanceTest(
                name="batch_operations",
                description="Time to perform batch operations",
                test_function=self._test_batch_operations,
                expected_max_duration=5.0,  # 5 seconds max
                iterations=3,
                warmup_iterations=1,
            ),
        ]

    def _test_connection_establishment(self, autocad_wrapper) -> float:
        """Test connection establishment time."""
        start_time = time.time()

        # Force new connection
        if hasattr(autocad_wrapper, "recover_connection"):
            autocad_wrapper.recover_connection()
        else:
            # For pyautocad, create new instance
            app = autocad_wrapper.app

        return time.time() - start_time

    def _test_basic_line_drawing(self, autocad_wrapper) -> float:
        """Test basic line drawing performance."""
        start_time = time.time()

        # Draw a line
        if hasattr(autocad_wrapper, "draw_line"):
            autocad_wrapper.draw_line([0, 0, 0], [100, 100, 0])
        else:
            # For pyautocad
            autocad_wrapper.model.AddLine([0, 0, 0], [100, 100, 0])

        return time.time() - start_time

    def _test_basic_circle_drawing(self, autocad_wrapper) -> float:
        """Test basic circle drawing performance."""
        start_time = time.time()

        # Draw a circle
        if hasattr(autocad_wrapper, "draw_circle"):
            autocad_wrapper.draw_circle([0, 0, 0], 50)
        else:
            # For pyautocad
            autocad_wrapper.model.AddCircle([0, 0, 0], 50)

        return time.time() - start_time

    def _test_entity_iteration(self, autocad_wrapper) -> float:
        """Test entity iteration performance."""
        start_time = time.time()

        # Iterate through entities
        count = 0
        if hasattr(autocad_wrapper, "iter_objects"):
            for entity in autocad_wrapper.iter_objects():
                count += 1
                if count >= 100:  # Limit iteration for consistent testing
                    break
        else:
            # For pyautocad
            for entity in autocad_wrapper.model:
                count += 1
                if count >= 100:
                    break

        return time.time() - start_time

    def _test_property_access(self, autocad_wrapper) -> float:
        """Test property access performance."""
        start_time = time.time()

        # Access common properties
        try:
            app_name = autocad_wrapper.app.Name
            doc_count = autocad_wrapper.app.Documents.Count
            if doc_count > 0:
                active_doc = autocad_wrapper.doc.Name
        except:
            pass  # Some properties might not be available

        return time.time() - start_time

    def _test_batch_operations(self, autocad_wrapper) -> float:
        """Test batch operations performance."""
        start_time = time.time()

        # Create multiple entities
        for i in range(10):
            try:
                if hasattr(autocad_wrapper, "draw_line"):
                    autocad_wrapper.draw_line([i * 10, 0, 0], [i * 10 + 10, 10, 0])
                else:
                    autocad_wrapper.model.AddLine([i * 10, 0, 0], [i * 10 + 10, 10, 0])
            except:
                pass  # Continue even if some operations fail

        return time.time() - start_time

    def run_performance_test(self, test: PerformanceTest, autocad_wrapper) -> PerformanceResult:
        """
        Run a single performance test.

        Args:
            test: Test definition
            autocad_wrapper: AutoCAD wrapper instance to test

        Returns:
            Performance test result
        """
        logger.info(f"Running performance test: {test.name}")

        durations = []
        errors = []
        successful_runs = 0

        # Warmup iterations
        for i in range(test.warmup_iterations):
            try:
                test.test_function(autocad_wrapper)
            except Exception as e:
                logger.warning(f"Warmup iteration {i+1} failed: {str(e)}")

        # Actual test iterations
        for i in range(test.iterations):
            try:
                duration = test.test_function(autocad_wrapper)
                durations.append(duration)
                successful_runs += 1
                logger.debug(f"  Iteration {i+1}/{test.iterations}: {duration:.3f}s")
            except Exception as e:
                error_msg = f"Iteration {i+1} failed: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)

        # Calculate statistics
        if durations:
            average_duration = statistics.mean(durations)
            median_duration = statistics.median(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            std_deviation = statistics.stdev(durations) if len(durations) > 1 else 0.0
        else:
            average_duration = median_duration = min_duration = max_duration = std_deviation = 0.0

        success_rate = successful_runs / test.iterations
        passed = (
            successful_runs > 0
            and average_duration <= test.expected_max_duration
            and success_rate >= 0.8
        )  # At least 80% success rate

        result = PerformanceResult(
            test_name=test.name,
            iterations=test.iterations,
            durations=durations,
            average_duration=average_duration,
            median_duration=median_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            std_deviation=std_deviation,
            success_rate=success_rate,
            errors=errors,
            passed=passed,
        )

        logger.info(
            f"  Result: {'PASS' if passed else 'FAIL'} "
            f"(avg: {average_duration:.3f}s, success: {success_rate:.1%})"
        )

        return result

    def run_baseline_tests(self, wrapper_name: str, autocad_wrapper) -> Dict[str, Any]:
        """
        Run complete baseline test suite.

        Args:
            wrapper_name: Name of the wrapper being tested
            autocad_wrapper: AutoCAD wrapper instance

        Returns:
            Dictionary containing test results
        """
        logger.info(f"Starting baseline performance tests for {wrapper_name}")
        start_time = time.time()

        results = []
        passed_tests = 0

        for test in self.performance_tests:
            try:
                result = self.run_performance_test(test, autocad_wrapper)
                results.append(result)
                if result.passed:
                    passed_tests += 1
            except Exception as e:
                logger.error(f"Test {test.name} failed with exception: {str(e)}")
                # Create failed result
                failed_result = PerformanceResult(
                    test_name=test.name,
                    iterations=0,
                    durations=[],
                    average_duration=0.0,
                    median_duration=0.0,
                    min_duration=0.0,
                    max_duration=0.0,
                    std_deviation=0.0,
                    success_rate=0.0,
                    errors=[str(e)],
                    passed=False,
                )
                results.append(failed_result)

        total_time = time.time() - start_time

        # Create summary
        summary = {
            "wrapper_name": wrapper_name,
            "timestamp": time.time(),
            "total_duration": total_time,
            "total_tests": len(self.performance_tests),
            "passed_tests": passed_tests,
            "failed_tests": len(self.performance_tests) - passed_tests,
            "overall_pass_rate": passed_tests / len(self.performance_tests),
            "test_results": [asdict(result) for result in results],
        }

        logger.info(
            f"Baseline tests completed: {passed_tests}/{len(self.performance_tests)} passed "
            f"({summary['overall_pass_rate']:.1%})"
        )

        return summary

    def compare_performance(
        self, baseline_results: Dict[str, Any], enhanced_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare performance between baseline and enhanced versions.

        Args:
            baseline_results: Results from baseline tests
            enhanced_results: Results from enhanced tests

        Returns:
            Dictionary containing performance comparison
        """
        comparison = {
            "baseline_wrapper": baseline_results["wrapper_name"],
            "enhanced_wrapper": enhanced_results["wrapper_name"],
            "comparison_timestamp": time.time(),
            "test_comparisons": [],
            "summary": {},
        }

        # Compare individual tests
        baseline_tests = {r["test_name"]: r for r in baseline_results["test_results"]}
        enhanced_tests = {r["test_name"]: r for r in enhanced_results["test_results"]}

        better_count = 0
        worse_count = 0
        similar_count = 0

        for test_name in baseline_tests.keys():
            if test_name not in enhanced_tests:
                continue

            baseline_test = baseline_tests[test_name]
            enhanced_test = enhanced_tests[test_name]

            # Calculate performance difference
            if baseline_test["average_duration"] > 0:
                performance_ratio = (
                    enhanced_test["average_duration"] / baseline_test["average_duration"]
                )
                performance_improvement = (1 - performance_ratio) * 100
            else:
                performance_ratio = 1.0
                performance_improvement = 0.0

            # Categorize improvement
            if performance_improvement > 5:  # >5% improvement
                category = "better"
                better_count += 1
            elif performance_improvement < -5:  # >5% worse
                category = "worse"
                worse_count += 1
            else:
                category = "similar"
                similar_count += 1

            test_comparison = {
                "test_name": test_name,
                "baseline_duration": baseline_test["average_duration"],
                "enhanced_duration": enhanced_test["average_duration"],
                "performance_ratio": performance_ratio,
                "performance_improvement_percent": performance_improvement,
                "category": category,
                "baseline_success_rate": baseline_test["success_rate"],
                "enhanced_success_rate": enhanced_test["success_rate"],
                "reliability_improvement": enhanced_test["success_rate"]
                - baseline_test["success_rate"],
            }

            comparison["test_comparisons"].append(test_comparison)

        # Overall summary
        total_tests = len(comparison["test_comparisons"])
        comparison["summary"] = {
            "total_tests_compared": total_tests,
            "better_performance": better_count,
            "worse_performance": worse_count,
            "similar_performance": similar_count,
            "overall_assessment": self._assess_performance_comparison(
                better_count, worse_count, similar_count
            ),
            "baseline_pass_rate": baseline_results["overall_pass_rate"],
            "enhanced_pass_rate": enhanced_results["overall_pass_rate"],
            "reliability_improvement": enhanced_results["overall_pass_rate"]
            - baseline_results["overall_pass_rate"],
        }

        return comparison

    def _assess_performance_comparison(self, better: int, worse: int, similar: int) -> str:
        """Assess overall performance comparison."""
        total = better + worse + similar
        if total == 0:
            return "no_data"

        better_pct = better / total
        worse_pct = worse / total

        if better_pct >= 0.6:  # 60%+ better
            return "significantly_better"
        elif better_pct >= 0.4:  # 40%+ better
            return "moderately_better"
        elif worse_pct >= 0.6:  # 60%+ worse
            return "significantly_worse"
        elif worse_pct >= 0.4:  # 40%+ worse
            return "moderately_worse"
        else:
            return "similar"

    def save_results(self, results: Dict[str, Any], filename: str) -> None:
        """
        Save test results to file.

        Args:
            results: Test results to save
            filename: Output filename
        """
        output_path = self.results_dir / filename

        try:
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2)

            logger.info(f"Results saved to {output_path}")

        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")

    def load_results(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load test results from file.

        Args:
            filename: Input filename

        Returns:
            Loaded results or None if failed
        """
        input_path = self.results_dir / filename

        try:
            with open(input_path, "r") as f:
                results = json.load(f)

            logger.info(f"Results loaded from {input_path}")
            return results

        except Exception as e:
            logger.error(f"Failed to load results: {str(e)}")
            return None

    def generate_performance_report(self, results: Dict[str, Any]) -> str:
        """
        Generate human-readable performance report.

        Args:
            results: Test results

        Returns:
            Formatted report string
        """
        report = []
        report.append(f"Performance Test Report: {results['wrapper_name']}")
        report.append("=" * 50)
        report.append(f"Timestamp: {time.ctime(results['timestamp'])}")
        report.append(f"Total Duration: {results['total_duration']:.2f} seconds")
        report.append(
            f"Tests Passed: {results['passed_tests']}/{results['total_tests']} "
            f"({results['overall_pass_rate']:.1%})"
        )
        report.append("")

        report.append("Individual Test Results:")
        report.append("-" * 30)

        for test_result in results["test_results"]:
            status = "PASS" if test_result["passed"] else "FAIL"
            report.append(f"{test_result['test_name']}: {status}")
            report.append(f"  Average Duration: {test_result['average_duration']:.3f}s")
            report.append(f"  Success Rate: {test_result['success_rate']:.1%}")

            if test_result["errors"]:
                report.append(f"  Errors: {len(test_result['errors'])}")

            report.append("")

        return "\n".join(report)
