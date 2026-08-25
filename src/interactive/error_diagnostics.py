"""
Advanced Error Diagnostics System
=================================

Provides intelligent error analysis, automated debugging suggestions,
and comprehensive AutoCAD-specific error resolution guidance.
Integrates with inspection system for detailed error context analysis.
"""

import logging
import time
import traceback
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import inspect
import sys

# Import inspection and interactive components
from ..inspection.object_inspector import ObjectInspector, InspectionDepth
from ..inspection.property_analyzer import PropertyAnalyzer
from ..enhanced_autocad.error_handler import ErrorHandler, ErrorCategory
from ..enhanced_autocad.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


class DiagnosticSeverity(Enum):
    """Error diagnostic severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DiagnosticCategory(Enum):
    """Categories of diagnostic issues."""
    AUTOCAD_COM = "autocad_com"
    PYTHON_SYNTAX = "python_syntax"
    RUNTIME_ERROR = "runtime_error"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPATIBILITY = "compatibility"
    RESOURCE = "resource"
    LOGIC = "logic"


@dataclass
class DiagnosticRule:
    """Rule for error pattern detection and resolution."""
    id: str
    name: str
    category: DiagnosticCategory
    severity: DiagnosticSeverity
    pattern: str  # Regex pattern for error matching
    description: str
    resolution_steps: List[str]
    code_examples: List[str] = field(default_factory=list)
    related_docs: List[str] = field(default_factory=list)
    auto_fixable: bool = False


@dataclass
class DiagnosticResult:
    """Result of error diagnostic analysis."""
    id: str
    timestamp: float
    severity: DiagnosticSeverity
    category: DiagnosticCategory
    title: str
    description: str
    error_context: Dict[str, Any]
    resolution_steps: List[str]
    code_suggestions: List[str] = field(default_factory=list)
    object_analysis: Optional[Dict[str, Any]] = None
    performance_impact: Optional[str] = None
    confidence_score: float = 0.0


class ErrorDiagnostics:
    """
    Advanced error diagnostics system for AutoCAD Python development.
    
    Provides intelligent error analysis, automated debugging, and
    comprehensive resolution guidance with AutoCAD-specific expertise.
    """
    
    def __init__(self, object_inspector=None, error_handler=None, performance_monitor=None):
        """
        Initialize error diagnostics system.
        
        Args:
            object_inspector: Object inspector for context analysis
            error_handler: Error handler for integration
            performance_monitor: Performance monitor for impact analysis
        """
        self.object_inspector = object_inspector or ObjectInspector()
        self.property_analyzer = PropertyAnalyzer()
        self.error_handler = error_handler or ErrorHandler()
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        
        # Diagnostic rules and history
        self.diagnostic_rules = self._initialize_diagnostic_rules()
        self.diagnostic_history: List[DiagnosticResult] = []
        self.known_issues: Dict[str, int] = {}  # Pattern -> occurrence count
        
        # Configuration
        self.max_history_size = 500
        self.auto_analyze_objects = True
        self.include_performance_analysis = True
        
        logger.info("Error diagnostics system initialized")

    def analyze_error(self, 
                     error: Exception,
                     context: Optional[Dict[str, Any]] = None,
                     code: Optional[str] = None,
                     local_vars: Optional[Dict[str, Any]] = None) -> DiagnosticResult:
        """
        Perform comprehensive error analysis with diagnostic recommendations.
        
        Args:
            error: Exception to analyze
            context: Additional context information
            code: Source code that caused the error
            local_vars: Local variables at error location
            
        Returns:
            Comprehensive diagnostic result
        """
        analysis_start = time.time()
        
        # Extract error information
        error_info = self._extract_error_info(error)
        
        # Find matching diagnostic rules
        matching_rules = self._find_matching_rules(error_info)
        
        # Analyze error context
        context_analysis = self._analyze_error_context(
            error, context, code, local_vars
        )
        
        # Generate diagnostic result
        diagnostic = self._generate_diagnostic_result(
            error_info, matching_rules, context_analysis
        )
        
        # Add to history and update statistics
        self._update_diagnostic_history(diagnostic)
        
        analysis_duration = time.time() - analysis_start
        logger.info(f"Error analysis completed in {analysis_duration:.3f}s")
        
        return diagnostic

    def analyze_code_issues(self, code: str, context: Optional[Dict[str, Any]] = None) -> List[DiagnosticResult]:
        """
        Analyze code for potential issues without execution.
        
        Args:
            code: Python code to analyze
            context: Optional context information
            
        Returns:
            List of potential issues found
        """
        issues = []
        
        # Syntax analysis
        syntax_issues = self._analyze_syntax(code)
        issues.extend(syntax_issues)
        
        # Pattern-based analysis
        pattern_issues = self._analyze_code_patterns(code)
        issues.extend(pattern_issues)
        
        # AutoCAD-specific analysis
        autocad_issues = self._analyze_autocad_usage(code, context)
        issues.extend(autocad_issues)
        
        # Performance analysis
        if self.include_performance_analysis:
            performance_issues = self._analyze_performance_patterns(code)
            issues.extend(performance_issues)
        
        return issues

    def suggest_fixes(self, diagnostic: DiagnosticResult) -> List[Dict[str, Any]]:
        """
        Generate automated fix suggestions for a diagnostic result.
        
        Args:
            diagnostic: Diagnostic result to generate fixes for
            
        Returns:
            List of fix suggestions with code and descriptions
        """
        fixes = []
        
        # Rule-based fixes
        if diagnostic.category == DiagnosticCategory.AUTOCAD_COM:
            fixes.extend(self._generate_autocad_fixes(diagnostic))
        elif diagnostic.category == DiagnosticCategory.PYTHON_SYNTAX:
            fixes.extend(self._generate_syntax_fixes(diagnostic))
        elif diagnostic.category == DiagnosticCategory.RUNTIME_ERROR:
            fixes.extend(self._generate_runtime_fixes(diagnostic))
        elif diagnostic.category == DiagnosticCategory.PERFORMANCE:
            fixes.extend(self._generate_performance_fixes(diagnostic))
        
        # Generic fixes based on error patterns
        fixes.extend(self._generate_pattern_fixes(diagnostic))
        
        return fixes

    def get_diagnostic_summary(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """
        Get diagnostic summary for recent time range.
        
        Args:
            time_range_hours: Hours to include in summary
            
        Returns:
            Diagnostic summary with statistics and trends
        """
        cutoff_time = time.time() - (time_range_hours * 3600)
        recent_diagnostics = [
            d for d in self.diagnostic_history 
            if d.timestamp >= cutoff_time
        ]
        
        # Calculate statistics
        total_issues = len(recent_diagnostics)
        severity_counts = {}
        category_counts = {}
        
        for diagnostic in recent_diagnostics:
            severity = diagnostic.severity.value
            category = diagnostic.category.value
            
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Find most common issues
        common_issues = sorted(
            self.known_issues.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "time_range_hours": time_range_hours,
            "total_issues": total_issues,
            "severity_distribution": severity_counts,
            "category_distribution": category_counts,
            "most_common_issues": common_issues,
            "resolution_rate": self._calculate_resolution_rate(),
            "performance_impact": self._calculate_performance_impact()
        }

    def search_solutions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for solutions based on error description or pattern.
        
        Args:
            query: Search query for error or issue
            limit: Maximum number of results to return
            
        Returns:
            List of relevant solutions and documentation
        """
        solutions = []
        query_lower = query.lower()
        
        # Search diagnostic rules
        for rule in self.diagnostic_rules:
            relevance_score = self._calculate_relevance(query_lower, rule)
            if relevance_score > 0.3:
                solution = {
                    "title": rule.name,
                    "category": rule.category.value,
                    "description": rule.description,
                    "resolution_steps": rule.resolution_steps,
                    "code_examples": rule.code_examples,
                    "relevance_score": relevance_score
                }
                solutions.append(solution)
        
        # Sort by relevance and limit results
        solutions.sort(key=lambda x: x["relevance_score"], reverse=True)
        return solutions[:limit]

    def _initialize_diagnostic_rules(self) -> List[DiagnosticRule]:
        """Initialize diagnostic rules for error pattern matching."""
        rules = []
        
        # AutoCAD COM-specific rules
        rules.append(DiagnosticRule(
            id="autocad_not_running",
            name="AutoCAD Application Not Running",
            category=DiagnosticCategory.AUTOCAD_COM,
            severity=DiagnosticSeverity.ERROR,
            pattern=r".*(-2147221164|AutoCAD.*not.*running|COM.*exception).*",
            description="AutoCAD application is not running or not accessible",
            resolution_steps=[
                "Start AutoCAD application",
                "Ensure AutoCAD is not in a modal dialog",
                "Check Windows COM registration",
                "Verify AutoCAD version compatibility"
            ],
            code_examples=[
                "# Check if AutoCAD is running\nimport win32com.client\ntry:\n    acad = win32com.client.GetActiveObject('AutoCAD.Application')\nexcept:\n    acad = win32com.client.Dispatch('AutoCAD.Application')"
            ]
        ))
        
        rules.append(DiagnosticRule(
            id="object_deleted",
            name="AutoCAD Object Already Deleted",
            category=DiagnosticCategory.AUTOCAD_COM,
            severity=DiagnosticSeverity.ERROR,
            pattern=r".*(object.*deleted|invalid.*handle|object.*no.*longer.*exists).*",
            description="Attempting to access an AutoCAD object that has been deleted",
            resolution_steps=[
                "Check if object exists before accessing",
                "Refresh object references after operations",
                "Use object handles for persistent references",
                "Implement proper error handling"
            ],
            code_examples=[
                "# Safe object access\nif hasattr(obj, 'ObjectName'):\n    try:\n        result = obj.SomeProperty\n    except:\n        print('Object no longer valid')"
            ]
        ))
        
        rules.append(DiagnosticRule(
            id="property_read_only",
            name="AutoCAD Property is Read-Only",
            category=DiagnosticCategory.AUTOCAD_COM,
            severity=DiagnosticSeverity.WARNING,
            pattern=r".*(read.*only|cannot.*set.*property|property.*not.*writable).*",
            description="Attempting to modify a read-only AutoCAD property",
            resolution_steps=[
                "Check property documentation for write access",
                "Use alternative methods to achieve desired change",
                "Verify object state allows property modification",
                "Consider using different object type"
            ],
            code_examples=[
                "# Check property access before setting\nif hasattr(obj, 'PropertyName'):\n    # Use inspection to check if writable\n    pass"
            ]
        ))
        
        # Python syntax rules
        rules.append(DiagnosticRule(
            id="indentation_error",
            name="Python Indentation Error",
            category=DiagnosticCategory.PYTHON_SYNTAX,
            severity=DiagnosticSeverity.ERROR,
            pattern=r".*(IndentationError|unexpected indent|unindent).*",
            description="Python code has incorrect indentation",
            resolution_steps=[
                "Check for consistent use of spaces or tabs",
                "Ensure proper nesting of code blocks",
                "Use a code editor with indentation guides",
                "Validate indentation with Python formatter"
            ]
        ))
        
        # Performance rules
        rules.append(DiagnosticRule(
            id="slow_loop_operation",
            name="Potentially Slow Loop with AutoCAD Operations",
            category=DiagnosticCategory.PERFORMANCE,
            severity=DiagnosticSeverity.WARNING,
            pattern=r".*(for.*in.*range|while.*true).*",
            description="Loop containing AutoCAD operations may be slow",
            resolution_steps=[
                "Consider batch operations where possible",
                "Use AutoCAD's bulk methods",
                "Minimize object access in loops",
                "Profile code to identify bottlenecks"
            ],
            code_examples=[
                "# Instead of individual operations in loop\n# Use bulk operations when available\nobjects = model_space.AddMultipleObjects(data)"
            ]
        ))
        
        return rules

    def _extract_error_info(self, error: Exception) -> Dict[str, Any]:
        """Extract comprehensive information from an exception."""
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "module": getattr(error, '__module__', 'unknown'),
            "args": error.args if hasattr(error, 'args') else []
        }
        
        # Extract additional COM error information if available
        if hasattr(error, 'excepinfo'):
            error_info["com_info"] = error.excepinfo
        
        if hasattr(error, 'hresult'):
            error_info["hresult"] = error.hresult
            
        return error_info

    def _find_matching_rules(self, error_info: Dict[str, Any]) -> List[DiagnosticRule]:
        """Find diagnostic rules that match the error pattern."""
        matching_rules = []
        error_text = f"{error_info['type']} {error_info['message']} {error_info['traceback']}"
        
        for rule in self.diagnostic_rules:
            if re.search(rule.pattern, error_text, re.IGNORECASE):
                matching_rules.append(rule)
                
        return matching_rules

    def _analyze_error_context(self, 
                             error: Exception,
                             context: Optional[Dict[str, Any]],
                             code: Optional[str],
                             local_vars: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the context in which the error occurred."""
        context_analysis = {
            "code_context": code,
            "local_variables": {},
            "autocad_objects": {},
            "environment_info": {},
            "performance_context": {}
        }
        
        # Analyze local variables
        if local_vars:
            for var_name, var_value in local_vars.items():
                try:
                    if self._is_autocad_object(var_value):
                        # Inspect AutoCAD objects
                        if self.auto_analyze_objects:
                            inspection = self.object_inspector.inspect_object(
                                var_value, depth=InspectionDepth.BASIC
                            )
                            context_analysis["autocad_objects"][var_name] = inspection
                        else:
                            context_analysis["autocad_objects"][var_name] = {
                                "type": type(var_value).__name__,
                                "value": str(var_value)
                            }
                    else:
                        context_analysis["local_variables"][var_name] = {
                            "type": type(var_value).__name__,
                            "value": str(var_value)[:100]  # Truncate long values
                        }
                except Exception:
                    context_analysis["local_variables"][var_name] = {
                        "type": "unknown",
                        "value": "<analysis failed>"
                    }
        
        # Add environment information
        context_analysis["environment_info"] = {
            "python_version": sys.version,
            "platform": sys.platform,
            "error_timestamp": time.time()
        }
        
        return context_analysis

    def _generate_diagnostic_result(self, 
                                  error_info: Dict[str, Any],
                                  matching_rules: List[DiagnosticRule],
                                  context_analysis: Dict[str, Any]) -> DiagnosticResult:
        """Generate comprehensive diagnostic result."""
        
        # Determine primary rule (highest severity, most specific)
        primary_rule = None
        if matching_rules:
            primary_rule = max(matching_rules, key=lambda r: (r.severity.value, len(r.pattern)))
        
        # Generate diagnostic
        if primary_rule:
            diagnostic = DiagnosticResult(
                id=f"diag_{int(time.time()*1000)}",
                timestamp=time.time(),
                severity=primary_rule.severity,
                category=primary_rule.category,
                title=primary_rule.name,
                description=f"{primary_rule.description}: {error_info['message']}",
                error_context=context_analysis,
                resolution_steps=primary_rule.resolution_steps,
                code_suggestions=primary_rule.code_examples,
                confidence_score=0.8
            )
        else:
            # Generic diagnostic for unmatched errors
            diagnostic = DiagnosticResult(
                id=f"diag_{int(time.time()*1000)}",
                timestamp=time.time(),
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.RUNTIME_ERROR,
                title=f"Unclassified {error_info['type']}",
                description=error_info['message'],
                error_context=context_analysis,
                resolution_steps=[
                    "Review the error traceback for specific line",
                    "Check variable values at error location",
                    "Verify object states and accessibility",
                    "Consult documentation for error type"
                ],
                confidence_score=0.3
            )
        
        return diagnostic

    def _analyze_syntax(self, code: str) -> List[DiagnosticResult]:
        """Analyze code for syntax issues."""
        issues = []
        
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            diagnostic = DiagnosticResult(
                id=f"syntax_{int(time.time()*1000)}",
                timestamp=time.time(),
                severity=DiagnosticSeverity.ERROR,
                category=DiagnosticCategory.PYTHON_SYNTAX,
                title="Python Syntax Error",
                description=f"Syntax error at line {e.lineno}: {e.msg}",
                error_context={"line_number": e.lineno, "code": code},
                resolution_steps=[
                    f"Check syntax at line {e.lineno}",
                    "Verify proper parentheses, brackets, and quotes",
                    "Ensure correct indentation",
                    "Use a Python syntax checker"
                ],
                confidence_score=0.9
            )
            issues.append(diagnostic)
            
        return issues

    def _analyze_code_patterns(self, code: str) -> List[DiagnosticResult]:
        """Analyze code for problematic patterns."""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for common problematic patterns
            if re.search(r'except\s*:', line):
                diagnostic = DiagnosticResult(
                    id=f"pattern_{int(time.time()*1000)}_{i}",
                    timestamp=time.time(),
                    severity=DiagnosticSeverity.WARNING,
                    category=DiagnosticCategory.LOGIC,
                    title="Bare Except Clause",
                    description=f"Bare except clause at line {i} may hide important errors",
                    error_context={"line_number": i, "line": line},
                    resolution_steps=[
                        "Specify exception types to catch",
                        "Add proper error handling",
                        "Consider logging caught exceptions"
                    ],
                    confidence_score=0.7
                )
                issues.append(diagnostic)
                
        return issues

    def _analyze_autocad_usage(self, code: str, context: Optional[Dict[str, Any]]) -> List[DiagnosticResult]:
        """Analyze AutoCAD-specific usage patterns."""
        issues = []
        
        # Check for potential AutoCAD performance issues
        if re.search(r'for.*in.*range.*\n.*\.(Add|Create|Delete)', code, re.MULTILINE):
            diagnostic = DiagnosticResult(
                id=f"autocad_perf_{int(time.time()*1000)}",
                timestamp=time.time(),
                severity=DiagnosticSeverity.WARNING,
                category=DiagnosticCategory.PERFORMANCE,
                title="Potential AutoCAD Performance Issue",
                description="Loop with AutoCAD object operations may be slow",
                error_context={"code": code},
                resolution_steps=[
                    "Consider using batch operations",
                    "Minimize AutoCAD object access in loops",
                    "Use bulk methods where available",
                    "Profile the code performance"
                ],
                confidence_score=0.6
            )
            issues.append(diagnostic)
            
        return issues

    def _analyze_performance_patterns(self, code: str) -> List[DiagnosticResult]:
        """Analyze code for performance issues."""
        issues = []
        
        # Check for nested loops
        if re.search(r'for.*in.*:\s*\n.*for.*in.*:', code, re.MULTILINE):
            diagnostic = DiagnosticResult(
                id=f"perf_nested_{int(time.time()*1000)}",
                timestamp=time.time(),
                severity=DiagnosticSeverity.INFO,
                category=DiagnosticCategory.PERFORMANCE,
                title="Nested Loops Detected",
                description="Nested loops may impact performance with large datasets",
                error_context={"code": code},
                resolution_steps=[
                    "Consider algorithm optimization",
                    "Profile with realistic data sizes",
                    "Look for vectorization opportunities",
                    "Consider caching repeated calculations"
                ],
                confidence_score=0.5
            )
            issues.append(diagnostic)
            
        return issues

    def _generate_autocad_fixes(self, diagnostic: DiagnosticResult) -> List[Dict[str, Any]]:
        """Generate AutoCAD-specific fix suggestions."""
        fixes = []
        
        if "not running" in diagnostic.description.lower():
            fixes.append({
                "title": "Start AutoCAD Application",
                "description": "Ensure AutoCAD is running and accessible",
                "code": """
# Safe AutoCAD connection
import win32com.client
try:
    acad = win32com.client.GetActiveObject('AutoCAD.Application')
except:
    acad = win32com.client.Dispatch('AutoCAD.Application')
    acad.Visible = True
"""
            })
            
        return fixes

    def _generate_syntax_fixes(self, diagnostic: DiagnosticResult) -> List[Dict[str, Any]]:
        """Generate syntax error fix suggestions."""
        fixes = []
        
        if "IndentationError" in diagnostic.title:
            fixes.append({
                "title": "Fix Indentation",
                "description": "Ensure consistent indentation using spaces or tabs",
                "code": "# Use consistent indentation (4 spaces recommended)\nif condition:\n    do_something()\n    if nested:\n        do_nested()"
            })
            
        return fixes

    def _generate_runtime_fixes(self, diagnostic: DiagnosticResult) -> List[Dict[str, Any]]:
        """Generate runtime error fix suggestions."""
        fixes = []
        
        fixes.append({
            "title": "Add Error Handling",
            "description": "Wrap risky operations in try-except blocks",
            "code": """
try:
    # Risky operation here
    result = risky_operation()
except SpecificException as e:
    # Handle specific error
    logger.error(f"Operation failed: {e}")
    result = default_value
"""
        })
        
        return fixes

    def _generate_performance_fixes(self, diagnostic: DiagnosticResult) -> List[Dict[str, Any]]:
        """Generate performance optimization suggestions."""
        fixes = []
        
        fixes.append({
            "title": "Optimize Loop Operations",
            "description": "Use bulk operations or optimize loop structure",
            "code": """
# Instead of individual operations
for item in items:
    autocad_obj.AddSingle(item)

# Use bulk operations
autocad_obj.AddMultiple(items)
"""
        })
        
        return fixes

    def _generate_pattern_fixes(self, diagnostic: DiagnosticResult) -> List[Dict[str, Any]]:
        """Generate generic pattern-based fixes."""
        fixes = []
        
        # Add common fix patterns based on diagnostic category
        if diagnostic.category == DiagnosticCategory.LOGIC:
            fixes.append({
                "title": "Improve Error Handling",
                "description": "Use specific exception handling instead of bare except",
                "code": "try:\n    risky_operation()\nexcept SpecificError as e:\n    handle_error(e)\nexcept Exception as e:\n    logger.error(f'Unexpected error: {e}')"
            })
            
        return fixes

    def _update_diagnostic_history(self, diagnostic: DiagnosticResult):
        """Update diagnostic history and statistics."""
        self.diagnostic_history.append(diagnostic)
        
        # Update known issues count
        pattern_key = f"{diagnostic.category.value}_{diagnostic.title}"
        self.known_issues[pattern_key] = self.known_issues.get(pattern_key, 0) + 1
        
        # Maintain history size limit
        if len(self.diagnostic_history) > self.max_history_size:
            self.diagnostic_history = self.diagnostic_history[-self.max_history_size//2:]

    def _calculate_relevance(self, query: str, rule: DiagnosticRule) -> float:
        """Calculate relevance score between query and diagnostic rule."""
        score = 0.0
        
        # Check name match
        if query in rule.name.lower():
            score += 0.5
            
        # Check description match
        if query in rule.description.lower():
            score += 0.3
            
        # Check pattern match (simplified)
        try:
            if re.search(query, rule.pattern, re.IGNORECASE):
                score += 0.4
        except:
            pass
            
        return min(score, 1.0)

    def _calculate_resolution_rate(self) -> float:
        """Calculate the rate of resolved issues."""
        # Placeholder - would track actual resolutions
        return 0.75

    def _calculate_performance_impact(self) -> str:
        """Calculate overall performance impact of diagnosed issues."""
        performance_issues = [
            d for d in self.diagnostic_history
            if d.category == DiagnosticCategory.PERFORMANCE
        ]
        
        if len(performance_issues) > 10:
            return "high"
        elif len(performance_issues) > 5:
            return "medium"
        else:
            return "low"

    def _is_autocad_object(self, obj: Any) -> bool:
        """Check if object is AutoCAD-related."""
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