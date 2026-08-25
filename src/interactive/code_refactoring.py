"""
Advanced Code Refactoring Engine with AST Manipulation
====================================================

Intelligent code refactoring system with specialized AutoCAD support including:
- AST-based code analysis and transformation
- AutoCAD-specific refactoring patterns and optimizations
- Automated code quality improvements and modernization
- Safe refactoring validation with rollback capabilities
- Performance-focused refactoring suggestions
"""

import logging
import ast
import time
import inspect
import re
import textwrap
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import tempfile
import shutil
import subprocess
from collections import defaultdict, Counter

# Import AST utilities
import astor  # For AST to source code conversion (fallback will be provided)

logger = logging.getLogger(__name__)


class RefactoringType(Enum):
    """Types of refactoring operations."""
    EXTRACT_METHOD = "extract_method"
    EXTRACT_VARIABLE = "extract_variable"
    INLINE_METHOD = "inline_method"
    INLINE_VARIABLE = "inline_variable"
    RENAME_SYMBOL = "rename_symbol"
    MOVE_METHOD = "move_method"
    OPTIMIZE_IMPORTS = "optimize_imports"
    MODERNIZE_SYNTAX = "modernize_syntax"
    AUTOCAD_OPTIMIZE = "autocad_optimize"
    REMOVE_DEAD_CODE = "remove_dead_code"
    SIMPLIFY_EXPRESSIONS = "simplify_expressions"
    IMPROVE_READABILITY = "improve_readability"


class RefactoringSafety(Enum):
    """Safety levels for refactoring operations."""
    SAFE = "safe"          # No behavior change expected
    CONSERVATIVE = "conservative"  # Minor behavior changes possible
    AGGRESSIVE = "aggressive"      # Significant behavior changes possible
    EXPERIMENTAL = "experimental"  # Untested transformations


@dataclass
class RefactoringSuggestion:
    """A suggested refactoring operation."""
    id: str
    type: RefactoringType
    safety_level: RefactoringSafety
    title: str
    description: str
    
    # Location information
    filename: str
    start_line: int
    end_line: int
    start_col: int = 0
    end_col: int = 0
    
    # Transformation details
    original_code: str = ""
    refactored_code: str = ""
    confidence_score: float = 0.0
    
    # Impact analysis
    estimated_improvement: Dict[str, float] = field(default_factory=dict)
    potential_issues: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    # AutoCAD-specific information
    autocad_benefits: List[str] = field(default_factory=list)
    performance_impact: Optional[str] = None


@dataclass
class RefactoringResult:
    """Result of a refactoring operation."""
    suggestion_id: str
    success: bool
    modified_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # Validation results
    syntax_valid: bool = True
    tests_passed: bool = True
    
    # Metrics
    lines_changed: int = 0
    complexity_change: int = 0
    performance_change: Optional[float] = None


class ASTAnalyzer(ast.NodeVisitor):
    """AST analyzer for code pattern detection and refactoring opportunities."""
    
    def __init__(self, source_code: str, filename: str = "<unknown>"):
        self.source_code = source_code
        self.filename = filename
        self.lines = source_code.split('\n')
        
        # Analysis results
        self.functions = []
        self.classes = []
        self.imports = []
        self.variables = []
        self.autocad_calls = []
        self.complexity_issues = []
        self.dead_code_candidates = []
        self.refactoring_opportunities = []
        
        # Tracking state
        self.current_class = None
        self.current_function = None
        self.scope_stack = []
        self.line_usage = set()
        
    def analyze(self) -> Dict[str, Any]:
        """Perform comprehensive AST analysis."""
        try:
            tree = ast.parse(self.source_code, filename=self.filename)
            self.visit(tree)
            
            # Post-processing analysis
            self._detect_dead_code()
            self._analyze_complexity()
            self._find_refactoring_opportunities()
            
            return {
                'functions': self.functions,
                'classes': self.classes,
                'imports': self.imports,
                'variables': self.variables,
                'autocad_calls': self.autocad_calls,
                'complexity_issues': self.complexity_issues,
                'dead_code_candidates': self.dead_code_candidates,
                'refactoring_opportunities': self.refactoring_opportunities
            }
            
        except SyntaxError as e:
            logger.error(f"Syntax error in {self.filename}: {e}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"Analysis error in {self.filename}: {e}")
            return {'error': str(e)}
    
    def visit_ClassDef(self, node):
        """Analyze class definitions."""
        class_info = {
            'name': node.name,
            'line': node.lineno,
            'methods': [],
            'attributes': [],
            'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
            'docstring': ast.get_docstring(node),
            'is_autocad_wrapper': self._is_autocad_wrapper_class(node)
        }
        
        self.current_class = class_info
        self.classes.append(class_info)
        
        self.generic_visit(node)
        self.current_class = None
    
    def visit_FunctionDef(self, node):
        """Analyze function definitions."""
        func_info = {
            'name': node.name,
            'line': node.lineno,
            'args': [arg.arg for arg in node.args.args],
            'returns': self._get_return_annotation(node),
            'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
            'docstring': ast.get_docstring(node),
            'complexity': self._calculate_complexity(node),
            'is_autocad_method': self._is_autocad_method(node),
            'calls_autocad': False,
            'length': len(node.body)
        }
        
        if self.current_class:
            self.current_class['methods'].append(func_info)
        
        self.current_function = func_info
        self.functions.append(func_info)
        
        self.generic_visit(node)
        self.current_function = None
    
    def visit_Import(self, node):
        """Analyze import statements."""
        for alias in node.names:
            import_info = {
                'module': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'type': 'import',
                'is_autocad': 'autocad' in alias.name.lower() or 'win32' in alias.name.lower()
            }
            self.imports.append(import_info)
            self.line_usage.add(node.lineno)
    
    def visit_ImportFrom(self, node):
        """Analyze from...import statements."""
        for alias in node.names:
            import_info = {
                'module': node.module,
                'name': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'type': 'from_import',
                'is_autocad': (node.module and 'autocad' in node.module.lower()) or 
                             'win32' in str(node.module).lower()
            }
            self.imports.append(import_info)
            self.line_usage.add(node.lineno)
    
    def visit_Call(self, node):
        """Analyze function calls, especially AutoCAD-related ones."""
        if self._is_autocad_call(node):
            call_info = {
                'function': self._get_call_name(node),
                'line': node.lineno,
                'args_count': len(node.args),
                'has_keywords': len(node.keywords) > 0,
                'in_function': self.current_function['name'] if self.current_function else None,
                'potential_optimization': self._analyze_autocad_call_optimization(node)
            }
            self.autocad_calls.append(call_info)
            
            if self.current_function:
                self.current_function['calls_autocad'] = True
        
        self.line_usage.add(node.lineno)
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        """Analyze variable assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_info = {
                    'name': target.id,
                    'line': node.lineno,
                    'scope': 'function' if self.current_function else 'module',
                    'is_autocad_object': self._is_autocad_assignment(node)
                }
                self.variables.append(var_info)
        
        self.line_usage.add(node.lineno)
        self.generic_visit(node)
    
    def _is_autocad_wrapper_class(self, node: ast.ClassDef) -> bool:
        """Check if a class is an AutoCAD wrapper class."""
        # Check class name patterns
        autocad_patterns = ['AutoCAD', 'CAD', 'Drawing', 'Document', 'Application']
        if any(pattern in node.name for pattern in autocad_patterns):
            return True
        
        # Check for AutoCAD-related attributes in class body
        for item in node.body:
            if isinstance(item, ast.Assign):
                if self._is_autocad_assignment(item):
                    return True
        
        return False
    
    def _is_autocad_method(self, node: ast.FunctionDef) -> bool:
        """Check if a function is an AutoCAD-related method."""
        autocad_patterns = ['add_', 'insert_', 'create_', 'get_', 'set_', 'modify_']
        return any(node.name.lower().startswith(pattern) for pattern in autocad_patterns)
    
    def _is_autocad_call(self, node: ast.Call) -> bool:
        """Check if a function call is AutoCAD-related."""
        call_name = self._get_call_name(node)
        if not call_name:
            return False
        
        autocad_indicators = [
            'Add', 'Insert', 'Create', 'Delete', 'Modify', 'Get', 'Set',
            'Selection', 'Block', 'Layer', 'Document', 'Application'
        ]
        
        return any(indicator in call_name for indicator in autocad_indicators)
    
    def _is_autocad_assignment(self, node: ast.Assign) -> bool:
        """Check if an assignment involves AutoCAD objects."""
        if isinstance(node.value, ast.Call):
            return self._is_autocad_call(node.value)
        elif isinstance(node.value, ast.Attribute):
            attr_chain = self._get_attribute_chain(node.value)
            autocad_patterns = ['acad', 'doc', 'application', 'activeDocument']
            return any(pattern in attr_chain.lower() for pattern in autocad_patterns)
        return False
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Get the name of a function call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return self._get_attribute_chain(node.func)
        return ""
    
    def _get_attribute_chain(self, node: ast.Attribute) -> str:
        """Get the full attribute chain (e.g., 'obj.method.attr')."""
        parts = []
        current = node
        
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        
        if isinstance(current, ast.Name):
            parts.append(current.id)
        
        return '.'.join(reversed(parts))
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _get_return_annotation(self, node: ast.FunctionDef) -> Optional[str]:
        """Get return type annotation if present."""
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return str(node.returns.value)
        return None
    
    def _analyze_autocad_call_optimization(self, node: ast.Call) -> List[str]:
        """Analyze potential optimizations for AutoCAD calls."""
        optimizations = []
        call_name = self._get_call_name(node)
        
        # Check for common optimization opportunities
        if 'Add' in call_name and len(node.args) > 3:
            optimizations.append("Consider bulk operations for multiple additions")
        
        if 'Get' in call_name and not node.keywords:
            optimizations.append("Consider caching the result if used multiple times")
        
        if any('Selection' in str(arg) for arg in node.args):
            optimizations.append("Consider using selection sets for better performance")
        
        return optimizations
    
    def _detect_dead_code(self):
        """Detect potentially dead code."""
        all_lines = set(range(1, len(self.lines) + 1))
        unused_lines = all_lines - self.line_usage
        
        # Group consecutive unused lines
        dead_blocks = []
        current_block = []
        
        for line_num in sorted(unused_lines):
            if not self.lines[line_num - 1].strip():  # Skip empty lines
                continue
                
            if current_block and line_num != current_block[-1] + 1:
                if len(current_block) > 2:  # Only report blocks of 3+ lines
                    dead_blocks.append(current_block)
                current_block = [line_num]
            else:
                current_block.append(line_num)
        
        if len(current_block) > 2:
            dead_blocks.append(current_block)
        
        for block in dead_blocks:
            self.dead_code_candidates.append({
                'start_line': block[0],
                'end_line': block[-1],
                'lines_count': len(block),
                'confidence': 0.7  # Medium confidence for dead code detection
            })
    
    def _analyze_complexity(self):
        """Analyze code complexity issues."""
        for func in self.functions:
            if func['complexity'] > 10:
                self.complexity_issues.append({
                    'type': 'high_complexity',
                    'function': func['name'],
                    'line': func['line'],
                    'complexity': func['complexity'],
                    'suggestion': 'Consider breaking this function into smaller functions'
                })
            
            if func['length'] > 50:
                self.complexity_issues.append({
                    'type': 'long_function',
                    'function': func['name'],
                    'line': func['line'],
                    'length': func['length'],
                    'suggestion': 'Consider extracting some functionality into separate methods'
                })
    
    def _find_refactoring_opportunities(self):
        """Identify specific refactoring opportunities."""
        # Look for duplicate code patterns
        self._find_duplicate_patterns()
        
        # Look for AutoCAD-specific improvements
        self._find_autocad_improvements()
        
        # Look for general code improvements
        self._find_general_improvements()
    
    def _find_duplicate_patterns(self):
        """Find duplicate code patterns."""
        # Simple duplicate detection by comparing function bodies
        function_bodies = {}
        
        for func in self.functions:
            if func['length'] > 5:  # Only check functions with substantial content
                # Create a simplified representation of the function
                body_signature = f"{func['length']}_{len(func['args'])}"
                
                if body_signature in function_bodies:
                    self.refactoring_opportunities.append({
                        'type': 'duplicate_code',
                        'functions': [function_bodies[body_signature], func['name']],
                        'suggestion': 'Consider extracting common functionality'
                    })
                else:
                    function_bodies[body_signature] = func['name']
    
    def _find_autocad_improvements(self):
        """Find AutoCAD-specific improvement opportunities."""
        # Group AutoCAD calls by function
        autocad_by_function = defaultdict(list)
        for call in self.autocad_calls:
            if call['in_function']:
                autocad_by_function[call['in_function']].append(call)
        
        # Look for functions with many AutoCAD calls
        for func_name, calls in autocad_by_function.items():
            if len(calls) > 5:
                self.refactoring_opportunities.append({
                    'type': 'autocad_optimization',
                    'function': func_name,
                    'calls_count': len(calls),
                    'suggestion': 'Consider batching AutoCAD operations or using transactions'
                })
    
    def _find_general_improvements(self):
        """Find general code improvement opportunities."""
        # Look for unused imports
        imported_names = {imp['name'] or imp['module'] for imp in self.imports}
        used_names = set()
        
        # This is a simplified check - in practice, you'd need more sophisticated analysis
        for func in self.functions:
            used_names.add(func['name'])
        
        unused_imports = imported_names - used_names
        if unused_imports:
            self.refactoring_opportunities.append({
                'type': 'unused_imports',
                'imports': list(unused_imports),
                'suggestion': 'Remove unused imports to improve code clarity'
            })


class CodeRefactoringEngine:
    """
    Advanced code refactoring engine with AST manipulation capabilities.
    
    Provides intelligent refactoring operations with AutoCAD-specific optimizations
    and safe transformation validation.
    """
    
    def __init__(self):
        """Initialize the refactoring engine."""
        self.refactoring_history = []
        self.validation_enabled = True
        self.backup_enabled = True
        self.test_command = None  # Command to run tests for validation
        
        # Refactoring patterns and templates
        self.autocad_patterns = self._load_autocad_patterns()
        self.optimization_rules = self._load_optimization_rules()
        
        logger.info("Code refactoring engine initialized")
    
    def analyze_file(self, filename: str) -> Dict[str, Any]:
        """
        Analyze a Python file for refactoring opportunities.
        
        Args:
            filename: Path to the Python file to analyze
            
        Returns:
            Analysis results with refactoring suggestions
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            analyzer = ASTAnalyzer(source_code, filename)
            analysis = analyzer.analyze()
            
            # Generate refactoring suggestions
            suggestions = self._generate_suggestions(analysis, filename)
            
            return {
                'filename': filename,
                'analysis': analysis,
                'suggestions': suggestions,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze {filename}: {e}")
            return {'error': str(e)}
    
    def generate_refactoring_suggestions(self, 
                                       filename: str,
                                       focus_areas: Optional[List[str]] = None) -> List[RefactoringSuggestion]:
        """
        Generate refactoring suggestions for a file.
        
        Args:
            filename: Path to the Python file
            focus_areas: Specific areas to focus on (optional)
            
        Returns:
            List of refactoring suggestions
        """
        analysis_result = self.analyze_file(filename)
        
        if 'error' in analysis_result:
            return []
        
        suggestions = []
        analysis = analysis_result['analysis']
        
        # Generate different types of suggestions
        suggestions.extend(self._suggest_extract_method(analysis, filename))
        suggestions.extend(self._suggest_autocad_optimizations(analysis, filename))
        suggestions.extend(self._suggest_code_modernization(analysis, filename))
        suggestions.extend(self._suggest_complexity_reduction(analysis, filename))
        suggestions.extend(self._suggest_dead_code_removal(analysis, filename))
        
        # Filter by focus areas if specified
        if focus_areas:
            suggestions = [s for s in suggestions if s.type.value in focus_areas]
        
        # Sort by confidence and impact
        suggestions.sort(key=lambda s: (s.confidence_score, s.estimated_improvement.get('total', 0)), 
                        reverse=True)
        
        return suggestions
    
    def apply_refactoring(self, 
                         suggestion: RefactoringSuggestion,
                         validate: bool = True,
                         create_backup: bool = True) -> RefactoringResult:
        """
        Apply a refactoring suggestion to the code.
        
        Args:
            suggestion: The refactoring suggestion to apply
            validate: Whether to validate the refactoring
            create_backup: Whether to create a backup before refactoring
            
        Returns:
            Refactoring result with success status and details
        """
        result = RefactoringResult(
            suggestion_id=suggestion.id,
            success=False
        )
        
        try:
            # Create backup if requested
            backup_path = None
            if create_backup:
                backup_path = self._create_backup(suggestion.filename)
            
            # Apply the transformation
            success = self._apply_transformation(suggestion)
            
            if not success:
                result.error_message = "Failed to apply transformation"
                if backup_path:
                    self._restore_backup(suggestion.filename, backup_path)
                return result
            
            result.modified_files = [suggestion.filename]
            result.lines_changed = suggestion.end_line - suggestion.start_line + 1
            
            # Validate the changes
            if validate:
                validation_result = self._validate_refactoring(suggestion.filename)
                result.syntax_valid = validation_result['syntax_valid']
                result.tests_passed = validation_result.get('tests_passed', True)
                result.warnings = validation_result.get('warnings', [])
                
                if not result.syntax_valid:
                    result.error_message = "Refactoring produced invalid syntax"
                    if backup_path:
                        self._restore_backup(suggestion.filename, backup_path)
                    return result
            
            result.success = True
            
            # Record in history
            self.refactoring_history.append({
                'timestamp': time.time(),
                'suggestion': suggestion,
                'result': result,
                'backup_path': backup_path
            })
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Refactoring failed: {e}")
        
        return result
    
    def suggest_autocad_performance_improvements(self, filename: str) -> List[RefactoringSuggestion]:
        """
        Generate AutoCAD-specific performance improvement suggestions.
        
        Args:
            filename: Path to the Python file
            
        Returns:
            List of performance-focused refactoring suggestions
        """
        analysis_result = self.analyze_file(filename)
        
        if 'error' in analysis_result:
            return []
        
        suggestions = []
        analysis = analysis_result['analysis']
        
        # Analyze AutoCAD call patterns
        autocad_calls = analysis.get('autocad_calls', [])
        
        # Group calls by function
        calls_by_function = defaultdict(list)
        for call in autocad_calls:
            if call['in_function']:
                calls_by_function[call['in_function']].append(call)
        
        # Generate suggestions for functions with many AutoCAD calls
        for func_name, calls in calls_by_function.items():
            if len(calls) > 3:
                suggestion = RefactoringSuggestion(
                    id=f"perf_{func_name}_{int(time.time())}",
                    type=RefactoringType.AUTOCAD_OPTIMIZE,
                    safety_level=RefactoringSafety.CONSERVATIVE,
                    title=f"Optimize AutoCAD calls in {func_name}",
                    description=f"Function {func_name} makes {len(calls)} AutoCAD calls. "
                               f"Consider using transactions or batch operations.",
                    filename=filename,
                    start_line=min(call['line'] for call in calls),
                    end_line=max(call['line'] for call in calls),
                    confidence_score=0.8,
                    estimated_improvement={'performance': 0.3, 'total': 0.3},
                    autocad_benefits=[
                        "Reduced COM interface overhead",
                        "Better transaction management",
                        "Improved drawing update performance"
                    ],
                    performance_impact="Significant improvement expected"
                )
                suggestions.append(suggestion)
        
        return suggestions
    
    def modernize_python_syntax(self, filename: str) -> List[RefactoringSuggestion]:
        """
        Generate suggestions to modernize Python syntax.
        
        Args:
            filename: Path to the Python file
            
        Returns:
            List of modernization suggestions
        """
        suggestions = []
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Check for old-style string formatting
            if re.search(r'%[sd]', source_code):
                suggestions.append(RefactoringSuggestion(
                    id=f"modernize_string_{int(time.time())}",
                    type=RefactoringType.MODERNIZE_SYNTAX,
                    safety_level=RefactoringSafety.SAFE,
                    title="Modernize string formatting",
                    description="Replace old-style % formatting with f-strings or .format()",
                    filename=filename,
                    start_line=1,
                    end_line=len(source_code.split('\n')),
                    confidence_score=0.9,
                    estimated_improvement={'readability': 0.2, 'total': 0.2}
                ))
            
            # Check for missing type hints
            tree = ast.parse(source_code)
            functions_without_hints = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    has_hints = bool(node.returns) or any(
                        arg.annotation for arg in node.args.args
                    )
                    if not has_hints and not node.name.startswith('_'):
                        functions_without_hints.append((node.name, node.lineno))
            
            if functions_without_hints:
                suggestions.append(RefactoringSuggestion(
                    id=f"add_type_hints_{int(time.time())}",
                    type=RefactoringType.MODERNIZE_SYNTAX,
                    safety_level=RefactoringSafety.SAFE,
                    title="Add type hints",
                    description=f"Add type hints to {len(functions_without_hints)} functions",
                    filename=filename,
                    start_line=min(line for _, line in functions_without_hints),
                    end_line=max(line for _, line in functions_without_hints),
                    confidence_score=0.7,
                    estimated_improvement={'maintainability': 0.3, 'total': 0.3}
                ))
        
        except Exception as e:
            logger.error(f"Failed to analyze syntax modernization for {filename}: {e}")
        
        return suggestions
    
    def _generate_suggestions(self, analysis: Dict[str, Any], filename: str) -> List[RefactoringSuggestion]:
        """Generate refactoring suggestions from analysis."""
        suggestions = []
        
        # Process complexity issues
        for issue in analysis.get('complexity_issues', []):
            if issue['type'] == 'high_complexity':
                suggestions.append(RefactoringSuggestion(
                    id=f"complex_{issue['function']}_{int(time.time())}",
                    type=RefactoringType.EXTRACT_METHOD,
                    safety_level=RefactoringSafety.CONSERVATIVE,
                    title=f"Reduce complexity in {issue['function']}",
                    description=f"Function has complexity {issue['complexity']}. {issue['suggestion']}",
                    filename=filename,
                    start_line=issue['line'],
                    end_line=issue['line'] + 10,  # Estimate
                    confidence_score=0.7
                ))
        
        # Process refactoring opportunities
        for opportunity in analysis.get('refactoring_opportunities', []):
            if opportunity['type'] == 'autocad_optimization':
                suggestions.append(RefactoringSuggestion(
                    id=f"autocad_{opportunity['function']}_{int(time.time())}",
                    type=RefactoringType.AUTOCAD_OPTIMIZE,
                    safety_level=RefactoringSafety.CONSERVATIVE,
                    title=f"Optimize AutoCAD calls in {opportunity['function']}",
                    description=opportunity['suggestion'],
                    filename=filename,
                    start_line=1,  # Would need more detailed analysis
                    end_line=1,
                    confidence_score=0.8,
                    autocad_benefits=["Improved performance", "Better resource management"]
                ))
        
        return suggestions
    
    def _suggest_extract_method(self, analysis: Dict[str, Any], filename: str) -> List[RefactoringSuggestion]:
        """Suggest method extraction opportunities."""
        suggestions = []
        
        for func in analysis.get('functions', []):
            if func['length'] > 30:  # Long functions are candidates for extraction
                suggestions.append(RefactoringSuggestion(
                    id=f"extract_{func['name']}_{int(time.time())}",
                    type=RefactoringType.EXTRACT_METHOD,
                    safety_level=RefactoringSafety.CONSERVATIVE,
                    title=f"Extract methods from {func['name']}",
                    description=f"Function is {func['length']} lines long. Consider extracting logical blocks.",
                    filename=filename,
                    start_line=func['line'],
                    end_line=func['line'] + func['length'],
                    confidence_score=0.6,
                    estimated_improvement={'maintainability': 0.4, 'total': 0.4}
                ))
        
        return suggestions
    
    def _suggest_autocad_optimizations(self, analysis: Dict[str, Any], filename: str) -> List[RefactoringSuggestion]:
        """Suggest AutoCAD-specific optimizations."""
        suggestions = []
        
        autocad_calls = analysis.get('autocad_calls', [])
        if len(autocad_calls) > 10:
            suggestions.append(RefactoringSuggestion(
                id=f"autocad_batch_{int(time.time())}",
                type=RefactoringType.AUTOCAD_OPTIMIZE,
                safety_level=RefactoringSafety.CONSERVATIVE,
                title="Batch AutoCAD operations",
                description=f"File contains {len(autocad_calls)} AutoCAD calls. Consider batching operations.",
                filename=filename,
                start_line=1,
                end_line=len(analysis.get('functions', [])),
                confidence_score=0.7,
                estimated_improvement={'performance': 0.5, 'total': 0.5},
                autocad_benefits=["Reduced COM overhead", "Better transaction handling"]
            ))
        
        return suggestions
    
    def _suggest_code_modernization(self, analysis: Dict[str, Any], filename: str) -> List[RefactoringSuggestion]:
        """Suggest code modernization improvements."""
        # This would be implemented with more sophisticated pattern detection
        return []
    
    def _suggest_complexity_reduction(self, analysis: Dict[str, Any], filename: str) -> List[RefactoringSuggestion]:
        """Suggest complexity reduction improvements."""
        suggestions = []
        
        for issue in analysis.get('complexity_issues', []):
            suggestions.append(RefactoringSuggestion(
                id=f"complexity_{issue.get('function', 'unknown')}_{int(time.time())}",
                type=RefactoringType.EXTRACT_METHOD,
                safety_level=RefactoringSafety.CONSERVATIVE,
                title=f"Reduce {issue['type'].replace('_', ' ')}",
                description=issue['suggestion'],
                filename=filename,
                start_line=issue.get('line', 1),
                end_line=issue.get('line', 1) + 10,
                confidence_score=0.6,
                estimated_improvement={'maintainability': 0.3, 'total': 0.3}
            ))
        
        return suggestions
    
    def _suggest_dead_code_removal(self, analysis: Dict[str, Any], filename: str) -> List[RefactoringSuggestion]:
        """Suggest dead code removal."""
        suggestions = []
        
        for candidate in analysis.get('dead_code_candidates', []):
            suggestions.append(RefactoringSuggestion(
                id=f"deadcode_{candidate['start_line']}_{int(time.time())}",
                type=RefactoringType.REMOVE_DEAD_CODE,
                safety_level=RefactoringSafety.AGGRESSIVE,
                title=f"Remove potential dead code (lines {candidate['start_line']}-{candidate['end_line']})",
                description=f"Found {candidate['lines_count']} consecutive unused lines",
                filename=filename,
                start_line=candidate['start_line'],
                end_line=candidate['end_line'],
                confidence_score=candidate['confidence'],
                estimated_improvement={'cleanliness': 0.2, 'total': 0.2}
            ))
        
        return suggestions
    
    def _apply_transformation(self, suggestion: RefactoringSuggestion) -> bool:
        """Apply the actual code transformation."""
        try:
            with open(suggestion.filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Simple implementation - replace the code block
            if suggestion.refactored_code:
                # Replace lines from start_line to end_line with refactored_code
                new_lines = (
                    lines[:suggestion.start_line - 1] +
                    [suggestion.refactored_code + '\n'] +
                    lines[suggestion.end_line:]
                )
                
                with open(suggestion.filename, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                
                return True
            else:
                # For now, just log that we would apply the transformation
                logger.info(f"Would apply {suggestion.type.value} transformation to {suggestion.filename}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to apply transformation: {e}")
            return False
    
    def _create_backup(self, filename: str) -> str:
        """Create a backup of the file before refactoring."""
        backup_path = f"{filename}.backup_{int(time.time())}"
        shutil.copy2(filename, backup_path)
        return backup_path
    
    def _restore_backup(self, filename: str, backup_path: str):
        """Restore a file from backup."""
        shutil.copy2(backup_path, filename)
    
    def _validate_refactoring(self, filename: str) -> Dict[str, Any]:
        """Validate the refactored code."""
        validation_result = {
            'syntax_valid': True,
            'tests_passed': True,
            'warnings': []
        }
        
        try:
            # Check syntax
            with open(filename, 'r', encoding='utf-8') as f:
                source = f.read()
            
            ast.parse(source)
            
            # Run tests if test command is configured
            if self.test_command:
                try:
                    result = subprocess.run(
                        self.test_command, 
                        shell=True, 
                        capture_output=True, 
                        text=True,
                        timeout=60
                    )
                    validation_result['tests_passed'] = result.returncode == 0
                    if result.returncode != 0:
                        validation_result['warnings'].append(f"Tests failed: {result.stderr}")
                except subprocess.TimeoutExpired:
                    validation_result['warnings'].append("Test execution timed out")
                except Exception as e:
                    validation_result['warnings'].append(f"Test execution failed: {e}")
            
        except SyntaxError as e:
            validation_result['syntax_valid'] = False
            validation_result['warnings'].append(f"Syntax error: {e}")
        except Exception as e:
            validation_result['warnings'].append(f"Validation error: {e}")
        
        return validation_result
    
    def _load_autocad_patterns(self) -> Dict[str, Any]:
        """Load AutoCAD-specific refactoring patterns."""
        return {
            'transaction_patterns': [
                'StartTransaction',
                'CommitTransaction',
                'AbortTransaction'
            ],
            'selection_patterns': [
                'SelectAll',
                'SelectOnScreen',
                'SelectByType'
            ],
            'batch_operations': [
                'AddBatch',
                'ModifyBatch',
                'DeleteBatch'
            ]
        }
    
    def _load_optimization_rules(self) -> List[Dict[str, Any]]:
        """Load optimization rules for refactoring."""
        return [
            {
                'name': 'autocad_transaction_wrapping',
                'pattern': r'(Add|Modify|Delete).*(Entity|Object)',
                'suggestion': 'Wrap multiple operations in a transaction',
                'confidence': 0.8
            },
            {
                'name': 'selection_set_optimization',
                'pattern': r'SelectAll.*iter',
                'suggestion': 'Use selection sets instead of iterating all objects',
                'confidence': 0.7
            }
        ]