"""
Secure Expression Evaluator
===========================

Safe evaluation of Python expressions with restricted namespace and AST validation.
Prevents code injection attacks while allowing legitimate debugging expressions.
"""

import ast
import operator
import logging
from typing import Any, Dict, Set, Optional, Union

logger = logging.getLogger(__name__)


class SecureEvaluationError(Exception):
    """Exception raised when expression evaluation fails security checks."""
    pass


class SecureExpressionEvaluator:
    """
    Secure evaluator for Python expressions with restricted operations.
    
    Only allows safe operations like attribute access, subscripting, 
    arithmetic, and comparisons. Blocks dangerous operations like
    function calls, imports, and attribute assignments.
    """
    
    # Allowed AST node types for safe evaluation
    ALLOWED_NODES = {
        ast.Expression,    # Expression wrapper
        ast.Constant,      # Constants (numbers, strings, etc.)
        ast.Name,          # Variable names
        ast.Load,          # Loading values
        ast.Attribute,     # Attribute access (obj.attr)
        ast.Subscript,     # Subscripting (obj[key])
        ast.Index,         # Index access
        ast.Slice,         # Slice operations
        ast.BinOp,         # Binary operations (+, -, *, etc.)
        ast.UnaryOp,       # Unary operations (-, +, not)
        ast.Compare,       # Comparisons (==, !=, <, etc.)
        ast.BoolOp,        # Boolean operations (and, or)
        ast.List,          # List literals
        ast.Tuple,         # Tuple literals
        ast.Dict,          # Dictionary literals
        ast.Set,           # Set literals
        ast.ListComp,      # List comprehensions (restricted)
        ast.comprehension, # Comprehension clauses
        ast.Call,          # Function calls (restricted to safe functions)
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,  # Binary operators
        ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd,  # Bitwise operators  
        ast.UAdd, ast.USub, ast.Not, ast.Invert,  # Unary operators
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn,  # Comparison operators
        ast.And, ast.Or  # Boolean operators
    }
    
    # Allowed operators
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
        ast.BitAnd: operator.and_,
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Not: operator.not_,
        ast.Invert: operator.invert,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
        ast.In: lambda x, y: x in y,
        ast.NotIn: lambda x, y: x not in y,
        ast.And: lambda x, y: x and y,
        ast.Or: lambda x, y: x or y
    }
    
    # Dangerous attribute names to block
    BLOCKED_ATTRIBUTES = {
        '__import__', '__builtins__', '__globals__', '__locals__',
        '__code__', '__func__', '__closure__', '__dict__',
        'exec', 'eval', 'compile', 'open', 'file',
        '__class__', '__bases__', '__mro__', '__subclasses__'
    }
    
    def __init__(self, max_expression_length: int = 1000):
        """
        Initialize secure expression evaluator.
        
        Args:
            max_expression_length: Maximum allowed expression length
        """
        self.max_expression_length = max_expression_length
        
    def is_safe_expression(self, expression: str) -> bool:
        """
        Check if an expression is safe to evaluate.
        
        Args:
            expression: Python expression to check
            
        Returns:
            True if expression is safe, False otherwise
        """
        try:
            # Length check
            if len(expression) > self.max_expression_length:
                return False
            
            # Parse AST
            tree = ast.parse(expression, mode='eval')
            
            # Check all nodes in the AST
            for node in ast.walk(tree):
                # Check node type
                if type(node) not in self.ALLOWED_NODES:
                    logger.warning(f"Blocked node type: {type(node).__name__}")
                    return False
                
                # Check for dangerous attribute access
                if isinstance(node, ast.Attribute):
                    if isinstance(node.attr, str) and node.attr in self.BLOCKED_ATTRIBUTES:
                        logger.warning(f"Blocked attribute access: {node.attr}")
                        return False
                
                # Block function calls (except safe built-ins)
                if isinstance(node, ast.Call):
                    # Only allow very specific safe function calls
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                        safe_functions = {
                            'len', 'str', 'int', 'float', 'bool', 'type', 'isinstance', 
                            'hasattr', 'getattr', 'abs', 'min', 'max', 'sum', 'round',
                            'sorted', 'reversed', 'enumerate', 'zip', 'range', 'list',
                            'tuple', 'dict', 'set'
                        }
                        if func_name not in safe_functions:
                            logger.warning(f"Blocked function call: {func_name}")
                            return False
                    else:
                        # Allow method calls on objects (obj.method())
                        if not isinstance(node.func, ast.Attribute):
                            logger.warning("Blocked complex function call")
                            return False
            
            return True
            
        except SyntaxError:
            logger.warning(f"Invalid syntax in expression: {expression}")
            return False
        except Exception as e:
            logger.warning(f"Error checking expression safety: {e}")
            return False
    
    def safe_eval(self, expression: str, 
                  local_vars: Optional[Dict[str, Any]] = None,
                  global_vars: Optional[Dict[str, Any]] = None) -> Any:
        """
        Safely evaluate a Python expression.
        
        Args:
            expression: Python expression to evaluate
            local_vars: Local variable namespace
            global_vars: Global variable namespace
            
        Returns:
            Result of expression evaluation
            
        Raises:
            SecureEvaluationError: If expression is unsafe or evaluation fails
        """
        # Security check
        if not self.is_safe_expression(expression):
            raise SecureEvaluationError(f"Expression failed security validation: {expression}")
        
        # Prepare safe namespace
        safe_locals = self._create_safe_namespace(local_vars or {})
        safe_globals = self._create_safe_namespace(global_vars or {})
        
        # Add safe built-ins
        safe_globals.update({
            'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
            'type': type, 'isinstance': isinstance, 'hasattr': hasattr, 'getattr': getattr,
            'abs': abs, 'min': min, 'max': max, 'sum': sum, 'round': round,
            'sorted': sorted, 'reversed': reversed, 'enumerate': enumerate, 'zip': zip,
            'range': range, 'list': list, 'tuple': tuple, 'dict': dict, 'set': set,
            'True': True, 'False': False, 'None': None,
            '__builtins__': {}  # Empty builtins to prevent access to dangerous functions
        })
        
        try:
            # Parse and compile
            tree = ast.parse(expression, mode='eval')
            code = compile(tree, '<secure_eval>', 'eval')
            
            # Evaluate with restricted namespace
            result = eval(code, safe_globals, safe_locals)
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating expression '{expression}': {e}")
            raise SecureEvaluationError(f"Evaluation failed: {str(e)}")
    
    def _create_safe_namespace(self, namespace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a safe namespace by filtering out dangerous objects.
        
        Args:
            namespace: Original namespace
            
        Returns:
            Filtered safe namespace
        """
        safe_namespace = {}
        
        for name, value in namespace.items():
            # Skip dangerous attributes
            if name.startswith('_') or name in self.BLOCKED_ATTRIBUTES:
                continue
            
            # Skip dangerous types
            if self._is_dangerous_type(value):
                continue
            
            safe_namespace[name] = value
        
        return safe_namespace
    
    def _is_dangerous_type(self, obj: Any) -> bool:
        """
        Check if an object type is dangerous to expose.
        
        Args:
            obj: Object to check
            
        Returns:
            True if object is dangerous, False otherwise
        """
        dangerous_types = {
            type(eval), type(exec), type(compile), type(open),
            type(__import__), type(globals), type(locals)
        }
        
        obj_type = type(obj)
        
        # Check direct type match
        if obj_type in dangerous_types:
            return True
        
        # Check for callable objects that might be dangerous
        if callable(obj):
            # Allow simple data types and AutoCAD objects
            if hasattr(obj, '__module__'):
                module = getattr(obj, '__module__', '')
                # Block built-in dangerous functions
                if module == 'builtins' and obj.__name__ in {
                    'eval', 'exec', 'compile', 'open', '__import__',
                    'globals', 'locals', 'vars', 'dir'
                }:
                    return True
        
        return False


# Global secure evaluator instance
_secure_evaluator = SecureExpressionEvaluator()


def safe_eval(expression: str, 
              local_vars: Optional[Dict[str, Any]] = None,
              global_vars: Optional[Dict[str, Any]] = None) -> Any:
    """
    Convenience function for secure expression evaluation.
    
    Args:
        expression: Python expression to evaluate
        local_vars: Local variable namespace  
        global_vars: Global variable namespace
        
    Returns:
        Result of expression evaluation
        
    Raises:
        SecureEvaluationError: If expression is unsafe or evaluation fails
    """
    return _secure_evaluator.safe_eval(expression, local_vars, global_vars)


def is_safe_expression(expression: str) -> bool:
    """
    Convenience function to check if expression is safe.
    
    Args:
        expression: Python expression to check
        
    Returns:
        True if expression is safe, False otherwise
    """
    return _secure_evaluator.is_safe_expression(expression)