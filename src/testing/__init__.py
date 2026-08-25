"""
Testing Framework for AutoCAD Automation.

This module provides comprehensive testing capabilities for AutoCAD automation code,
including mock AutoCAD support, automatic test generation, and performance testing.
"""

from .autocad_test_framework import AutoCADTestFramework
from .mock_autocad import MockAutoCAD
from .test_generators import TestGenerator
from .performance_tester import PerformanceTester
from .ci_integration import CIIntegration

__all__ = [
    'AutoCADTestFramework',
    'MockAutoCAD', 
    'TestGenerator',
    'PerformanceTester',
    'CIIntegration',
]