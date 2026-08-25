"""
Security Manager for Code Execution
==================================

Provides security validation and sandboxing for interactive Python code
execution in AutoCAD context. Ensures safe execution while preventing
dangerous operations.
"""

import logging
import ast
import re
import signal
import time
import threading
from typing import Dict, Any, List, Set, Optional, Callable

logger = logging.getLogger(__name__)


class SecurityManager:
    """
    Manages security for interactive code execution.
    """

    def __init__(self):
        """Initialize security manager."""
        # Dangerous modules and functions to block
        self.blocked_imports = {
            "os",
            "sys",
            "subprocess",
            "shutil",
            "glob",
            "pathlib",
            "urllib",
            "requests",
            "socket",
            "ftplib",
            "smtplib",
            "pickle",
            "marshal",
            "shelve",
            "dbm",
            "ctypes",
            "faulthandler",
            "gc",
            "importlib",
            "multiprocessing",
            "threading",
            "concurrent",
            "tempfile",
            "atexit",
            "signal",
            "resource",
        }

        # Dangerous built-in functions to block
        self.blocked_builtins = {
            "eval",
            "exec",
            "compile",
            "__import__",
            "open",
            "input",
            "raw_input",
            "exit",
            "quit",
            "help",
            "vars",
            "locals",
            "globals",
            "breakpoint",
        }

        # Dangerous attribute patterns
        self.blocked_attributes = {
            "__class__",
            "__bases__",
            "__subclasses__",
            "__import__",
            "__builtin__",
            "__builtins__",
            "__file__",
            "__name__",
            "__package__",
            "func_globals",
            "f_globals",
            "gi_frame",
        }

        # Allowed safe built-ins for execution environment
        self.safe_builtins = {
            "abs",
            "all",
            "any",
            "bool",
            "bytes",
            "callable",
            "chr",
            "complex",
            "dict",
            "dir",
            "divmod",
            "enumerate",
            "filter",
            "float",
            "format",
            "frozenset",
            "getattr",
            "hasattr",
            "hash",
            "hex",
            "id",
            "int",
            "isinstance",
            "issubclass",
            "iter",
            "len",
            "list",
            "map",
            "max",
            "memoryview",
            "min",
            "next",
            "oct",
            "ord",
            "pow",
            "print",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "setattr",
            "slice",
            "sorted",
            "str",
            "sum",
            "tuple",
            "type",
            "zip",
        }
        
        # Resource limits for safe execution
        self.max_execution_time = 30.0  # seconds
        self.max_code_length = 10000    # characters
        self.max_output_length = 50000  # characters

        logger.info("Security Manager initialized with enhanced protections")

    def validate_python_code(self, code: str) -> tuple[bool, List[str]]:
        """
        Validate Python code for security risks.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_safe, list_of_violations)
        """
        violations = []
        
        try:
            # Check code length
            if len(code) > self.max_code_length:
                violations.append(f"Code too long: {len(code)} > {self.max_code_length} characters")
                return False, violations
            
            # Check for empty or whitespace-only code
            if not code.strip():
                violations.append("Empty code not allowed")
                return False, violations

            # Parse code into AST
            tree = ast.parse(code)

            # Check for dangerous constructs
            validator = CodeValidator(self)
            validator.visit(tree)

            if validator.violations:
                violations.extend(validator.violations)
                logger.warning(f"Security violations found in code: {validator.violations}")
                return False, violations

            # Additional string-based checks
            string_violations = self._validate_code_strings(code)
            if string_violations:
                violations.extend(string_violations)
                return False, violations

            logger.debug("Code validation passed")
            return True, []

        except SyntaxError as e:
            violations.append(f"Syntax error in code: {str(e)}")
            logger.warning(f"Syntax error in code: {str(e)}")
            return False, violations
        except Exception as e:
            violations.append(f"Error validating code: {str(e)}")
            logger.error(f"Error validating code: {str(e)}")
            return False, violations

    def _validate_code_strings(self, code: str) -> List[str]:
        """
        Additional string-based validation for dangerous patterns.

        Args:
            code: Code to validate

        Returns:
            List of violations found (empty if code is safe)
        """
        violations = []
        
        # Check for dangerous patterns (case-insensitive)
        dangerous_patterns = [
            (r"(?i)__import__\s*\(", "Dynamic import detected"),
            (r"(?i)exec\s*\(", "exec() function call detected"),
            (r"(?i)eval\s*\(", "eval() function call detected"),
            (r"(?i)compile\s*\(", "compile() function call detected"),
            (r"(?i)open\s*\(", "file open() call detected"),
            (r"(?i)file\s*\(", "file() constructor detected"),
            (r"(?i)input\s*\(", "input() function detected"),
            (r"(?i)raw_input\s*\(", "raw_input() function detected"),
            (r"(?i)import\s+os\b", "os module import detected"),
            (r"(?i)import\s+sys\b", "sys module import detected"),
            (r"(?i)import\s+subprocess\b", "subprocess module import detected"),
            (r"(?i)from\s+os\s+import", "import from os module detected"),
            (r"(?i)from\s+sys\s+import", "import from sys module detected"),
            (r"(?i)\.system\s*\(", "system() method call detected"),
            (r"(?i)\.popen\s*\(", "popen() method call detected"),
            (r"(?i)\.call\s*\(", "call() method detected"),
            (r"(?i)\.run\s*\(", "run() method detected"),
            (r"(?i)while\s+True\s*:", "Potential infinite loop detected"),
            (r"(?i)for\s+\w+\s+in\s+iter\s*\(", "Potential infinite iterator detected"),
            (r"(?i)__[a-zA-Z_][a-zA-Z0-9_]*__", "Dunder attribute access detected"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, code):
                violations.append(message)
                logger.warning(f"Dangerous pattern found: {message}")

        return violations

    def get_safe_builtins(self) -> Dict[str, Any]:
        """
        Get dictionary of safe built-in functions for execution.

        Returns:
            Dictionary of safe built-ins
        """
        import builtins

        safe_dict = {}

        for name in self.safe_builtins:
            if hasattr(builtins, name):
                safe_dict[name] = getattr(builtins, name)

        return safe_dict

    def create_safe_globals(self, autocad_wrapper=None) -> Dict[str, Any]:
        """
        Create safe global namespace for code execution.

        Args:
            autocad_wrapper: AutoCAD wrapper instance

        Returns:
            Safe globals dictionary
        """
        safe_globals = {
            "__builtins__": self.get_safe_builtins(),
            "__name__": "__main__",
            "__doc__": None,
        }

        # Add AutoCAD objects if provided
        if autocad_wrapper:
            safe_globals.update(
                {
                    "acad": autocad_wrapper,
                    "app": autocad_wrapper.app,
                    "doc": autocad_wrapper.doc,
                    "model": autocad_wrapper.model,
                }
            )

        # Add safe math functions
        import math

        safe_math_functions = [
            "sin",
            "cos",
            "tan",
            "asin",
            "acos",
            "atan",
            "atan2",
            "sinh",
            "cosh",
            "tanh",
            "asinh",
            "acosh",
            "atanh",
            "sqrt",
            "pow",
            "exp",
            "log",
            "log10",
            "log2",
            "ceil",
            "floor",
            "trunc",
            "fabs",
            "fmod",
            "pi",
            "e",
            "tau",
            "inf",
            "nan",
            "degrees",
            "radians",
            "isnan",
            "isinf",
            "isfinite",
        ]

        safe_globals["math"] = type(
            "SafeMath",
            (),
            {name: getattr(math, name) for name in safe_math_functions if hasattr(math, name)},
        )()

        return safe_globals

    def get_security_report(self) -> Dict[str, Any]:
        """
        Get security configuration report.

        Returns:
            Dictionary containing security settings
        """
        return {
            "blocked_imports_count": len(self.blocked_imports),
            "blocked_builtins_count": len(self.blocked_builtins),
            "blocked_attributes_count": len(self.blocked_attributes),
            "safe_builtins_count": len(self.safe_builtins),
            "validation_enabled": True,
            "sandboxing_enabled": True,
        }


class CodeValidator(ast.NodeVisitor):
    """AST visitor to validate code for security risks."""

    def __init__(self, security_manager: SecurityManager):
        """Initialize validator."""
        self.security_manager = security_manager
        self.violations = []

    def visit_Import(self, node):
        """Check import statements."""
        for alias in node.names:
            if alias.name in self.security_manager.blocked_imports:
                self.violations.append(f"Blocked import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Check from-import statements."""
        if node.module in self.security_manager.blocked_imports:
            self.violations.append(f"Blocked import from: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        """Check function calls."""
        # Check for blocked built-in functions
        if isinstance(node.func, ast.Name):
            if node.func.id in self.security_manager.blocked_builtins:
                self.violations.append(f"Blocked function call: {node.func.id}")

        # Check for attribute calls that might be dangerous
        elif isinstance(node.func, ast.Attribute):
            dangerous_methods = ["system", "popen", "call", "run", "spawn", "fork", "kill"]
            if node.func.attr in dangerous_methods:
                self.violations.append(f"Blocked method call: {node.func.attr}")

        self.generic_visit(node)
    
    def visit_While(self, node):
        """Check while loops for potential infinite loops."""
        # Check for while True: constructs
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            self.violations.append("Potential infinite loop: while True")
        elif isinstance(node.test, ast.NameConstant) and node.test.value is True:
            self.violations.append("Potential infinite loop: while True")
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Check for loops for potential infinite loops."""
        # Check for dangerous iterator patterns
        if isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "iter":
                self.violations.append("Potential infinite loop: for ... in iter(...)")
        self.generic_visit(node)
    
    def visit_ListComp(self, node):
        """Check list comprehensions for dangerous patterns."""
        self._check_comprehension(node, "list comprehension")
        self.generic_visit(node)
    
    def visit_SetComp(self, node):
        """Check set comprehensions for dangerous patterns."""
        self._check_comprehension(node, "set comprehension")
        self.generic_visit(node)
    
    def visit_DictComp(self, node):
        """Check dict comprehensions for dangerous patterns."""
        self._check_comprehension(node, "dict comprehension")
        self.generic_visit(node)
    
    def visit_GeneratorExp(self, node):
        """Check generator expressions for dangerous patterns."""
        self._check_comprehension(node, "generator expression")
        self.generic_visit(node)
    
    def _check_comprehension(self, node, comp_type: str):
        """Check comprehensions for dangerous iterator patterns."""
        for generator in node.generators:
            if isinstance(generator.iter, ast.Call):
                if isinstance(generator.iter.func, ast.Name) and generator.iter.func.id == "iter":
                    self.violations.append(f"Potential infinite loop in {comp_type}: iter(...)")
    
    def visit_Lambda(self, node):
        """Check lambda functions for dangerous patterns."""
        # Lambda functions can be used to bypass restrictions, validate their body
        self.generic_visit(node)

    def visit_Attribute(self, node):
        """Check attribute access."""
        if node.attr in self.security_manager.blocked_attributes:
            self.violations.append(f"Blocked attribute access: {node.attr}")
        self.generic_visit(node)

    def visit_Name(self, node):
        """Check name references."""
        if node.id in self.security_manager.blocked_builtins:
            if isinstance(node.ctx, ast.Load):  # Only flag when loading/reading
                self.violations.append(f"Blocked name reference: {node.id}")
        self.generic_visit(node)
    
    def visit_Subscript(self, node):
        """Check subscript access for dangerous patterns."""
        # Check for potential __getitem__ abuse
        if isinstance(node.value, ast.Name):
            dangerous_subscripts = ["__builtins__", "__globals__", "__locals__"]
            if hasattr(node.slice, 'value') and isinstance(node.slice.value, ast.Str):
                if node.slice.value.s in dangerous_subscripts:
                    self.violations.append(f"Dangerous subscript access: {node.slice.value.s}")
        self.generic_visit(node)


class SecurityError(Exception):
    """Custom exception for security violations."""
    pass
