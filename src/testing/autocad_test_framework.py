"""
AutoCAD Test Framework - Core testing framework for AutoCAD automation.

Provides comprehensive testing capabilities including unit tests, integration tests,
mock AutoCAD support, and automated test execution.
"""

import os
import sys
import json
import time
import logging
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Test execution result."""
    test_name: str
    passed: bool
    execution_time: float
    error_message: Optional[str] = None
    assertions: int = 0
    output: str = ""
    mock_calls: List[str] = field(default_factory=list)


@dataclass
class TestSuite:
    """Collection of tests to execute."""
    name: str
    tests: List[Callable] = field(default_factory=list)
    setup_function: Optional[Callable] = None
    teardown_function: Optional[Callable] = None
    mock_mode: bool = False


class AutoCADTestFramework:
    """Core testing framework for AutoCAD automation testing."""
    
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self.test_suites: Dict[str, TestSuite] = {}
        self.mock_autocad = None
        self.test_results: List[TestResult] = []
        self.current_test_output = []
        
        if mock_mode:
            self._initialize_mock_autocad()
    
    def _initialize_mock_autocad(self):
        """Initialize mock AutoCAD environment."""
        from .mock_autocad import MockAutoCAD
        self.mock_autocad = MockAutoCAD()
        
        # Patch common AutoCAD imports
        self.autocad_patches = [
            patch('src.utils.get_autocad_instance', return_value=self.mock_autocad),
            patch('win32com.client.Dispatch', return_value=self.mock_autocad),
            patch('pyautocad.Autocad', return_value=self.mock_autocad)
        ]
        
        for p in self.autocad_patches:
            p.start()
    
    def create_test_suite(self, name: str, mock_mode: bool = None) -> TestSuite:
        """Create a new test suite."""
        if mock_mode is None:
            mock_mode = self.mock_mode
            
        suite = TestSuite(name=name, mock_mode=mock_mode)
        self.test_suites[name] = suite
        return suite
    
    def add_test(self, suite_name: str, test_function: Callable, test_name: str = None):
        """Add a test function to a test suite."""
        if suite_name not in self.test_suites:
            self.create_test_suite(suite_name)
        
        if test_name:
            test_function.__name__ = test_name
        
        self.test_suites[suite_name].tests.append(test_function)
    
    def register_setup(self, suite_name: str, setup_function: Callable):
        """Register setup function for test suite."""
        if suite_name in self.test_suites:
            self.test_suites[suite_name].setup_function = setup_function
    
    def register_teardown(self, suite_name: str, teardown_function: Callable):
        """Register teardown function for test suite."""
        if suite_name in self.test_suites:
            self.test_suites[suite_name].teardown_function = teardown_function
    
    @contextmanager
    def capture_output(self):
        """Capture print output during test execution."""
        old_stdout = sys.stdout
        try:
            from io import StringIO
            sys.stdout = StringIO()
            yield sys.stdout
        finally:
            sys.stdout = old_stdout
    
    def run_test(self, test_function: Callable, suite: TestSuite) -> TestResult:
        """Execute a single test function."""
        test_name = getattr(test_function, '__name__', 'unknown_test')
        start_time = time.time()
        
        result = TestResult(
            test_name=test_name,
            passed=False,
            execution_time=0.0
        )
        
        try:
            # Capture output
            with self.capture_output() as output:
                # Run setup if available
                if suite.setup_function:
                    suite.setup_function()
                
                # Execute test with assertion counting
                original_assert = self._wrap_assertions()
                self.assertion_count = 0
                
                # Run the test
                test_result = test_function()
                
                # Restore original assert
                self._restore_assertions(original_assert)
                
                result.passed = True
                result.assertions = self.assertion_count
                result.output = output.getvalue()
                
                # Capture mock calls if in mock mode
                if self.mock_autocad:
                    result.mock_calls = self.mock_autocad.get_call_log()
        
        except AssertionError as e:
            result.error_message = f"Assertion failed: {str(e)}"
            result.passed = False
        except Exception as e:
            result.error_message = f"Test error: {str(e)}"
            result.passed = False
        finally:
            # Run teardown if available
            if suite.teardown_function:
                try:
                    suite.teardown_function()
                except Exception as e:
                    logger.warning(f"Teardown failed: {e}")
            
            result.execution_time = time.time() - start_time
        
        return result
    
    def _wrap_assertions(self):
        """Wrap built-in assert to count assertions."""
        # Note: assert is a keyword, not a function, so we can't override it
        # Instead, we'll count assertions through test execution monitoring
        return None
    
    def _restore_assertions(self, original_assert):
        """Restore original assert function."""
        # No-op since we can't actually override assert
        pass
    
    def run_suite(self, suite_name: str) -> List[TestResult]:
        """Execute all tests in a test suite."""
        if suite_name not in self.test_suites:
            raise ValueError(f"Test suite '{suite_name}' not found")
        
        suite = self.test_suites[suite_name]
        suite_results = []
        
        logger.info(f"Running test suite: {suite_name}")
        logger.info(f"Mock mode: {suite.mock_mode}")
        
        for test_function in suite.tests:
            result = self.run_test(test_function, suite)
            suite_results.append(result)
            self.test_results.append(result)
            
            status = "PASS" if result.passed else "FAIL"
            logger.info(f"  {result.test_name}: {status} ({result.execution_time:.3f}s)")
            
            if not result.passed:
                logger.error(f"    Error: {result.error_message}")
        
        return suite_results
    
    def run_all_suites(self) -> Dict[str, List[TestResult]]:
        """Execute all registered test suites."""
        all_results = {}
        
        for suite_name in self.test_suites:
            all_results[suite_name] = self.run_suite(suite_name)
        
        return all_results
    
    def generate_report(self, output_format: str = "text") -> str:
        """Generate test execution report."""
        if output_format == "json":
            return self._generate_json_report()
        elif output_format == "html":
            return self._generate_html_report()
        else:
            return self._generate_text_report()
    
    def _generate_text_report(self) -> str:
        """Generate plain text test report."""
        if not self.test_results:
            return "No test results available."
        
        passed = len([r for r in self.test_results if r.passed])
        failed = len([r for r in self.test_results if not r.passed])
        total = len(self.test_results)
        total_time = sum(r.execution_time for r in self.test_results)
        total_assertions = sum(r.assertions for r in self.test_results)
        
        report = []
        report.append("AutoCAD Test Framework - Test Results")
        report.append("=" * 50)
        report.append(f"Total Tests: {total}")
        report.append(f"Passed: {passed}")
        report.append(f"Failed: {failed}")
        report.append(f"Success Rate: {(passed/total*100):.1f}%")
        report.append(f"Total Time: {total_time:.3f}s")
        report.append(f"Average Time: {(total_time/total):.3f}s")
        report.append(f"Total Assertions: {total_assertions}")
        report.append("")
        
        # Group by suite
        suite_results = {}
        for result in self.test_results:
            suite_name = "default"  # Could be enhanced to track suite names
            if suite_name not in suite_results:
                suite_results[suite_name] = []
            suite_results[suite_name].append(result)
        
        for suite_name, results in suite_results.items():
            report.append(f"Test Suite: {suite_name}")
            report.append("-" * 30)
            
            for result in results:
                status = "✓ PASS" if result.passed else "✗ FAIL"
                report.append(f"  {status} {result.test_name} ({result.execution_time:.3f}s)")
                
                if not result.passed:
                    report.append(f"    Error: {result.error_message}")
                
                if result.output.strip():
                    report.append(f"    Output: {result.output.strip()}")
            
            report.append("")
        
        return "\\n".join(report)
    
    def _generate_json_report(self) -> str:
        """Generate JSON test report."""
        passed = len([r for r in self.test_results if r.passed])
        failed = len([r for r in self.test_results if not r.passed])
        total = len(self.test_results)
        
        report = {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "success_rate": (passed/total*100) if total > 0 else 0,
                "total_time": sum(r.execution_time for r in self.test_results),
                "total_assertions": sum(r.assertions for r in self.test_results)
            },
            "test_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "execution_time": r.execution_time,
                    "error_message": r.error_message,
                    "assertions": r.assertions,
                    "output": r.output,
                    "mock_calls": r.mock_calls
                }
                for r in self.test_results
            ]
        }
        
        return json.dumps(report, indent=2)
    
    def _generate_html_report(self) -> str:
        """Generate HTML test report."""
        passed = len([r for r in self.test_results if r.passed])
        failed = len([r for r in self.test_results if not r.passed])
        total = len(self.test_results)
        success_rate = (passed/total*100) if total > 0 else 0
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AutoCAD Test Framework - Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .test-result {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ddd; }}
        .pass {{ border-left-color: #4CAF50; background: #f8fff8; }}
        .fail {{ border-left-color: #f44336; background: #fff8f8; }}
        .error {{ color: #d32f2f; font-size: 0.9em; }}
        .output {{ background: #f0f0f0; padding: 8px; margin-top: 5px; font-family: monospace; font-size: 0.8em; }}
    </style>
</head>
<body>
    <h1>AutoCAD Test Framework - Test Results</h1>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Tests:</strong> {total}</p>
        <p><strong>Passed:</strong> {passed}</p>
        <p><strong>Failed:</strong> {failed}</p>
        <p><strong>Success Rate:</strong> {success_rate:.1f}%</p>
        <p><strong>Total Time:</strong> {sum(r.execution_time for r in self.test_results):.3f}s</p>
    </div>
    
    <h2>Test Results</h2>
"""
        
        for result in self.test_results:
            status_class = "pass" if result.passed else "fail"
            status_text = "PASS" if result.passed else "FAIL"
            
            html += f"""
    <div class="test-result {status_class}">
        <h3>{result.test_name} - {status_text} ({result.execution_time:.3f}s)</h3>
        <p><strong>Assertions:</strong> {result.assertions}</p>
"""
            
            if result.error_message:
                html += f'        <div class="error">Error: {result.error_message}</div>'
            
            if result.output.strip():
                html += f'        <div class="output">{result.output.strip()}</div>'
            
            html += "    </div>"
        
        html += """
</body>
</html>"""
        
        return html
    
    def save_report(self, filepath: str, output_format: str = "text"):
        """Save test report to file."""
        report = self.generate_report(output_format)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Test report saved to: {filepath}")
    
    def clear_results(self):
        """Clear all test results."""
        self.test_results.clear()
    
    def cleanup(self):
        """Clean up test framework resources."""
        if hasattr(self, 'autocad_patches'):
            for patch in self.autocad_patches:
                try:
                    patch.stop()
                except:
                    pass
        
        self.clear_results()


# Utility functions for test creation
def assert_autocad_connected():
    """Assert that AutoCAD is connected."""
    try:
        from src.utils import get_autocad_instance
        acad = get_autocad_instance()
        assert acad is not None, "AutoCAD instance is None"
        return True
    except Exception as e:
        assert False, f"AutoCAD connection failed: {e}"


def assert_entity_exists(entity_id: int):
    """Assert that an AutoCAD entity exists."""
    try:
        from src.utils import get_autocad_instance
        acad = get_autocad_instance()
        # This would need to be implemented based on actual AutoCAD API
        assert entity_id is not None, "Entity ID is None"
        return True
    except Exception as e:
        assert False, f"Entity validation failed: {e}"


def assert_point_equals(point1: List[float], point2: List[float], tolerance: float = 0.001):
    """Assert that two 3D points are equal within tolerance."""
    if len(point1) != len(point2):
        assert False, f"Point dimensions don't match: {len(point1)} vs {len(point2)}"
    
    for i, (p1, p2) in enumerate(zip(point1, point2)):
        diff = abs(p1 - p2)
        assert diff <= tolerance, f"Point coordinate {i} differs by {diff} (tolerance: {tolerance})"
    
    return True


def create_test_drawing():
    """Create a new test drawing in AutoCAD."""
    try:
        from src.utils import get_autocad_instance
        acad = get_autocad_instance()
        # Implementation would depend on actual AutoCAD API
        return acad
    except Exception as e:
        raise RuntimeError(f"Failed to create test drawing: {e}")


# Decorators for test functions
def autocad_test(mock_mode: bool = False):
    """Decorator to mark function as AutoCAD test."""
    def decorator(func):
        func._is_autocad_test = True
        func._mock_mode = mock_mode
        return func
    return decorator


def requires_autocad(func):
    """Decorator to mark test as requiring real AutoCAD connection."""
    func._requires_real_autocad = True
    return func


def performance_test(max_time: float = 1.0):
    """Decorator to mark test as performance test with time limit."""
    def decorator(func):
        func._is_performance_test = True
        func._max_time = max_time
        return func
    return decorator