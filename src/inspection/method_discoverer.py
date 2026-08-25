"""
Method Discoverer for AutoCAD Objects
====================================

Advanced method signature discovery and analysis for AutoCAD objects.
Provides comprehensive method information including parameters, return types,
documentation, and usage examples for enhanced development experience.
"""

import logging
import inspect
import time
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger(__name__)


class MethodType(Enum):
    """Method type classification."""
    INSTANCE = "instance"        # Instance methods
    CLASS = "class"             # Class methods
    STATIC = "static"           # Static methods
    PROPERTY = "property"       # Property methods (getter/setter)
    BUILTIN = "builtin"         # Built-in methods
    COM_METHOD = "com_method"   # COM object methods
    UNKNOWN = "unknown"         # Unknown method type


class ParameterKind(Enum):
    """Parameter kind classification."""
    POSITIONAL_ONLY = "positional_only"
    POSITIONAL_OR_KEYWORD = "positional_or_keyword"
    VAR_POSITIONAL = "var_positional"
    KEYWORD_ONLY = "keyword_only"
    VAR_KEYWORD = "var_keyword"


@dataclass
class ParameterInfo:
    """Method parameter information."""
    name: str
    kind: ParameterKind
    annotation: Optional[str] = None
    default_value: Optional[Any] = None
    has_default: bool = False
    description: Optional[str] = None


@dataclass
class MethodDocumentation:
    """Complete method documentation."""
    description: str
    parameters: Dict[str, str] = field(default_factory=dict)
    return_description: Optional[str] = None
    usage_examples: List[str] = field(default_factory=list)
    related_methods: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    version_info: Optional[str] = None


@dataclass
class DetailedMethodInfo:
    """Detailed method analysis result."""
    name: str
    method_type: MethodType
    signature: str
    parameters: List[ParameterInfo] = field(default_factory=list)
    return_annotation: Optional[str] = None
    documentation: Optional[MethodDocumentation] = None
    is_inherited: bool = False
    source_class: Optional[str] = None
    overload_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MethodDiscoverer:
    """
    Advanced AutoCAD method discoverer with comprehensive analysis capabilities.
    """

    def __init__(self):
        """Initialize method discoverer."""
        # AutoCAD-specific method patterns
        self.autocad_patterns = self._initialize_autocad_patterns()
        
        # Method documentation database
        self.method_docs = self._initialize_method_documentation()
        
        # Parameter pattern recognition
        self.parameter_patterns = self._initialize_parameter_patterns()
        
        logger.info("MethodDiscoverer initialized")

    def discover_method(self, obj: Any, method_name: str) -> DetailedMethodInfo:
        """
        Perform comprehensive method analysis.

        Args:
            obj: Object containing the method
            method_name: Name of method to analyze

        Returns:
            Detailed method analysis result
        """
        try:
            # Get method object
            try:
                method = getattr(obj, method_name)
            except Exception as e:
                raise ValueError(f"Method '{method_name}' not found: {str(e)}")

            if not callable(method):
                raise ValueError(f"'{method_name}' is not a callable method")

            # Classify method type
            method_type = self._classify_method_type(obj, method_name, method)
            
            # Get method signature
            signature = self._get_method_signature(method)
            
            # Analyze parameters
            parameters = self._analyze_parameters(method)
            
            # Get return type annotation
            return_annotation = self._get_return_annotation(method)
            
            # Get documentation
            documentation = self._get_method_documentation(obj, method_name, method)
            
            # Check inheritance
            is_inherited, source_class = self._check_method_inheritance(obj, method_name)
            
            # Count overloads
            overload_count = self._count_method_overloads(obj, method_name)
            
            # Collect metadata
            metadata = self._collect_method_metadata(obj, method_name, method)

            return DetailedMethodInfo(
                name=method_name,
                method_type=method_type,
                signature=signature,
                parameters=parameters,
                return_annotation=return_annotation,
                documentation=documentation,
                is_inherited=is_inherited,
                source_class=source_class,
                overload_count=overload_count,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error discovering method {method_name}: {str(e)}")
            
            # Return minimal info on error
            return DetailedMethodInfo(
                name=method_name,
                method_type=MethodType.UNKNOWN,
                signature=f"{method_name}(...)",
                metadata={"error": str(e)}
            )

    def discover_all_methods(self, obj: Any, include_inherited: bool = True,
                           include_private: bool = False) -> List[DetailedMethodInfo]:
        """
        Discover all methods of an object.

        Args:
            obj: Object to analyze
            include_inherited: Whether to include inherited methods
            include_private: Whether to include private methods

        Returns:
            List of detailed method information
        """
        methods = []
        
        for name in dir(obj):
            # Skip private methods unless requested
            if not include_private and name.startswith('_'):
                continue
                
            try:
                # Check if it's a method
                attr = getattr(obj, name)
                if not callable(attr):
                    continue
                
                # Analyze the method
                method_info = self.discover_method(obj, name)
                
                # Filter inherited methods if requested
                if not include_inherited and method_info.is_inherited:
                    continue
                
                methods.append(method_info)
                
            except Exception as e:
                logger.debug(f"Skipping method {name}: {str(e)}")
        
        return sorted(methods, key=lambda m: m.name)

    def find_methods_by_pattern(self, obj: Any, pattern: str, 
                               search_type: str = "name") -> List[DetailedMethodInfo]:
        """
        Find methods matching a pattern.

        Args:
            obj: Object to search
            pattern: Search pattern (regex supported)
            search_type: Type of search ('name', 'signature', 'documentation')

        Returns:
            List of matching methods
        """
        all_methods = self.discover_all_methods(obj, include_inherited=True)
        matching_methods = []
        
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
        except re.error:
            # If regex fails, use simple string matching
            compiled_pattern = None
        
        for method in all_methods:
            match_found = False
            
            if search_type in ["name", "all"]:
                search_text = method.name
                if compiled_pattern:
                    match_found = compiled_pattern.search(search_text) is not None
                else:
                    match_found = pattern.lower() in search_text.lower()
            
            if not match_found and search_type in ["signature", "all"]:
                search_text = method.signature
                if compiled_pattern:
                    match_found = compiled_pattern.search(search_text) is not None
                else:
                    match_found = pattern.lower() in search_text.lower()
            
            if not match_found and search_type in ["documentation", "all"]:
                if method.documentation and method.documentation.description:
                    search_text = method.documentation.description
                    if compiled_pattern:
                        match_found = compiled_pattern.search(search_text) is not None
                    else:
                        match_found = pattern.lower() in search_text.lower()
            
            if match_found:
                matching_methods.append(method)
        
        return matching_methods

    def get_method_suggestions(self, obj: Any, context: str = "", 
                             operation: str = "") -> List[Dict[str, Any]]:
        """
        Get method suggestions based on context and intended operation.

        Args:
            obj: Object to analyze
            context: Context for suggestions (e.g., "drawing", "selection")
            operation: Intended operation (e.g., "create", "modify", "query")

        Returns:
            List of method suggestions
        """
        suggestions = []
        
        try:
            all_methods = self.discover_all_methods(obj, include_inherited=False)
            
            for method in all_methods:
                # Calculate relevance score
                relevance_score = self._calculate_method_relevance(method, context, operation)
                
                if relevance_score > 0.2:  # Threshold for inclusion
                    suggestions.append({
                        "name": method.name,
                        "signature": method.signature,
                        "description": method.documentation.description if method.documentation else "",
                        "method_type": method.method_type.value,
                        "parameter_count": len(method.parameters),
                        "relevance_score": relevance_score,
                        "has_documentation": method.documentation is not None
                    })
            
            # Sort by relevance score
            suggestions.sort(key=lambda x: x["relevance_score"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting method suggestions: {str(e)}")
        
        return suggestions[:25]  # Limit to top 25

    def generate_method_call_code(self, obj: Any, method_name: str, 
                                 include_parameters: bool = True) -> str:
        """
        Generate code for method call.

        Args:
            obj: Object containing the method
            method_name: Name of method
            include_parameters: Whether to include parameter placeholders

        Returns:
            Generated method call code
        """
        try:
            method_info = self.discover_method(obj, method_name)
            obj_name = getattr(obj, '__name__', 'obj')
            
            if not include_parameters:
                return f"{obj_name}.{method_name}()"
            
            # Generate parameter list
            param_parts = []
            for param in method_info.parameters:
                if param.name in ['self', 'cls']:
                    continue
                
                if param.has_default:
                    param_parts.append(f"{param.name}={self._get_example_parameter_value(param)}")
                else:
                    param_parts.append(self._get_example_parameter_value(param))
            
            param_str = ", ".join(param_parts)
            code = f"{obj_name}.{method_name}({param_str})"
            
            # Add comment with description if available
            if method_info.documentation and method_info.documentation.description:
                code += f"  # {method_info.documentation.description}"
            
            return code
            
        except Exception as e:
            return f"# Error generating method call: {str(e)}"

    def get_method_help(self, obj: Any, method_name: str) -> str:
        """
        Get comprehensive help text for a method.

        Args:
            obj: Object containing the method
            method_name: Name of method

        Returns:
            Formatted help text
        """
        try:
            method_info = self.discover_method(obj, method_name)
            
            help_lines = [
                f"Method: {method_info.name}",
                f"Signature: {method_info.signature}",
                f"Type: {method_info.method_type.value}",
                ""
            ]
            
            if method_info.documentation:
                doc = method_info.documentation
                
                if doc.description:
                    help_lines.extend([
                        "Description:",
                        f"  {doc.description}",
                        ""
                    ])
                
                if method_info.parameters:
                    help_lines.append("Parameters:")
                    for param in method_info.parameters:
                        if param.name in ['self', 'cls']:
                            continue
                        
                        param_line = f"  {param.name}"
                        if param.annotation:
                            param_line += f": {param.annotation}"
                        if param.has_default:
                            param_line += f" = {param.default_value}"
                        
                        param_desc = doc.parameters.get(param.name, "")
                        if param_desc:
                            param_line += f" - {param_desc}"
                        
                        help_lines.append(param_line)
                    help_lines.append("")
                
                if doc.return_description:
                    help_lines.extend([
                        "Returns:",
                        f"  {doc.return_description}",
                        ""
                    ])
                
                if doc.usage_examples:
                    help_lines.append("Examples:")
                    for example in doc.usage_examples:
                        help_lines.append(f"  {example}")
                    help_lines.append("")
                
                if doc.warnings:
                    help_lines.append("Warnings:")
                    for warning in doc.warnings:
                        help_lines.append(f"  ⚠️ {warning}")
                    help_lines.append("")
            
            if method_info.is_inherited:
                help_lines.append(f"Inherited from: {method_info.source_class}")
            
            return "\n".join(help_lines)
            
        except Exception as e:
            return f"Error getting method help: {str(e)}"

    def _classify_method_type(self, obj: Any, method_name: str, method: Callable) -> MethodType:
        """Classify method type."""
        try:
            # Check for built-in methods
            if hasattr(method, '__module__') and method.__module__ == 'builtins':
                return MethodType.BUILTIN
            
            # Check for COM methods
            if hasattr(obj, '_oleobj_'):
                return MethodType.COM_METHOD
            
            # Check for static and class methods
            descriptor = getattr(type(obj), method_name, None)
            if isinstance(descriptor, staticmethod):
                return MethodType.STATIC
            elif isinstance(descriptor, classmethod):
                return MethodType.CLASS
            elif isinstance(descriptor, property):
                return MethodType.PROPERTY
            
            # Default to instance method
            return MethodType.INSTANCE
            
        except Exception:
            return MethodType.UNKNOWN

    def _get_method_signature(self, method: Callable) -> str:
        """Get method signature string."""
        try:
            sig = inspect.signature(method)
            return f"{method.__name__}{sig}"
        except (ValueError, TypeError):
            # Fallback for built-in methods or COM objects
            return f"{method.__name__}(...)"

    def _analyze_parameters(self, method: Callable) -> List[ParameterInfo]:
        """Analyze method parameters."""
        parameters = []
        
        try:
            sig = inspect.signature(method)
            
            for param_name, param in sig.parameters.items():
                # Map inspect parameter kinds to our enum
                kind_mapping = {
                    inspect.Parameter.POSITIONAL_ONLY: ParameterKind.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD: ParameterKind.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.VAR_POSITIONAL: ParameterKind.VAR_POSITIONAL,
                    inspect.Parameter.KEYWORD_ONLY: ParameterKind.KEYWORD_ONLY,
                    inspect.Parameter.VAR_KEYWORD: ParameterKind.VAR_KEYWORD,
                }
                
                param_info = ParameterInfo(
                    name=param_name,
                    kind=kind_mapping.get(param.kind, ParameterKind.POSITIONAL_OR_KEYWORD),
                    annotation=str(param.annotation) if param.annotation != inspect.Parameter.empty else None,
                    default_value=param.default if param.default != inspect.Parameter.empty else None,
                    has_default=param.default != inspect.Parameter.empty
                )
                
                parameters.append(param_info)
                
        except (ValueError, TypeError):
            # Can't get signature for built-in methods
            pass
        
        return parameters

    def _get_return_annotation(self, method: Callable) -> Optional[str]:
        """Get method return type annotation."""
        try:
            sig = inspect.signature(method)
            if sig.return_annotation != inspect.Signature.empty:
                return str(sig.return_annotation)
        except (ValueError, TypeError):
            pass
        
        return None

    def _get_method_documentation(self, obj: Any, method_name: str, 
                                method: Callable) -> Optional[MethodDocumentation]:
        """Get method documentation."""
        try:
            # Check built-in documentation database
            if method_name in self.method_docs:
                doc_info = self.method_docs[method_name]
                return MethodDocumentation(**doc_info)
            
            # Get docstring
            docstring = getattr(method, '__doc__', None)
            if docstring:
                return self._parse_docstring(docstring)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting documentation for {method_name}: {str(e)}")
            return None

    def _parse_docstring(self, docstring: str) -> MethodDocumentation:
        """Parse method docstring into structured documentation."""
        lines = docstring.strip().split('\n')
        
        # Extract description (first paragraph)
        description_lines = []
        for line in lines:
            line = line.strip()
            if not line and description_lines:
                break
            if line:
                description_lines.append(line)
        
        description = ' '.join(description_lines)
        
        # Parse parameters and return information
        parameters = {}
        return_description = None
        usage_examples = []
        warnings = []
        
        current_section = None
        for line in lines:
            line = line.strip()
            
            # Section headers
            if line.lower().startswith(('args:', 'parameters:', 'param:')):
                current_section = 'parameters'
                continue
            elif line.lower().startswith(('returns:', 'return:')):
                current_section = 'returns'
                continue
            elif line.lower().startswith(('examples:', 'example:')):
                current_section = 'examples'
                continue
            elif line.lower().startswith(('warnings:', 'warning:')):
                current_section = 'warnings'
                continue
            
            # Parse content based on current section
            if current_section == 'parameters' and line:
                # Try to parse parameter: description format
                if ':' in line:
                    param_name, param_desc = line.split(':', 1)
                    parameters[param_name.strip()] = param_desc.strip()
            
            elif current_section == 'returns' and line:
                return_description = line
            
            elif current_section == 'examples' and line:
                usage_examples.append(line)
            
            elif current_section == 'warnings' and line:
                warnings.append(line)
        
        return MethodDocumentation(
            description=description,
            parameters=parameters,
            return_description=return_description,
            usage_examples=usage_examples,
            warnings=warnings
        )

    def _check_method_inheritance(self, obj: Any, method_name: str) -> tuple[bool, Optional[str]]:
        """Check if method is inherited."""
        try:
            obj_class = type(obj)
            
            # Check if method exists in base classes
            for base_class in obj_class.mro()[1:]:  # Skip the object's own class
                if hasattr(base_class, method_name):
                    return True, base_class.__name__
            
            return False, None
            
        except Exception:
            return False, None

    def _count_method_overloads(self, obj: Any, method_name: str) -> int:
        """Count method overloads (heuristic)."""
        # This is a simplified implementation
        # Real overload detection would require more sophisticated analysis
        return 0

    def _collect_method_metadata(self, obj: Any, method_name: str, method: Callable) -> Dict[str, Any]:
        """Collect additional method metadata."""
        metadata = {}
        
        try:
            # Source file information
            if hasattr(method, '__code__'):
                code = method.__code__
                metadata["filename"] = code.co_filename
                metadata["line_number"] = code.co_firstlineno
                metadata["argument_count"] = code.co_argcount
            
            # Module information
            if hasattr(method, '__module__'):
                metadata["module"] = method.__module__
            
            # Qualname for nested methods
            if hasattr(method, '__qualname__'):
                metadata["qualname"] = method.__qualname__
            
            # COM-specific metadata
            if hasattr(obj, '_oleobj_'):
                metadata["com_method"] = True
                
        except Exception as e:
            metadata["metadata_error"] = str(e)
        
        return metadata

    def _calculate_method_relevance(self, method: DetailedMethodInfo, 
                                  context: str, operation: str) -> float:
        """Calculate method relevance score."""
        score = 0.0
        method_name_lower = method.name.lower()
        context_lower = context.lower()
        operation_lower = operation.lower()
        
        # Direct name matches
        if context_lower in method_name_lower:
            score += 0.8
        
        if operation_lower in method_name_lower:
            score += 0.7
        
        # Pattern-based scoring
        for pattern_name, pattern_info in self.autocad_patterns.items():
            if re.search(pattern_info["name_pattern"], method_name_lower):
                if pattern_name in context_lower or pattern_name in operation_lower:
                    score += 0.6
        
        # Method type preference
        if method.method_type == MethodType.INSTANCE:
            score += 0.1
        
        # Documentation bonus
        if method.documentation:
            score += 0.1
        
        # Parameter count penalty for complex methods
        if len(method.parameters) > 5:
            score -= 0.1
        
        return min(score, 1.0)

    def _get_example_parameter_value(self, param: ParameterInfo) -> str:
        """Get example parameter value for code generation."""
        if param.has_default:
            return repr(param.default_value)
        
        if param.annotation:
            annotation_lower = param.annotation.lower()
            if "str" in annotation_lower:
                return '"example"'
            elif "int" in annotation_lower:
                return "0"
            elif "float" in annotation_lower:
                return "0.0"
            elif "bool" in annotation_lower:
                return "True"
            elif "list" in annotation_lower:
                return "[]"
        
        # Parameter name-based heuristics
        param_name_lower = param.name.lower()
        if "point" in param_name_lower or "coord" in param_name_lower:
            return "[0.0, 0.0, 0.0]"
        elif "name" in param_name_lower or "text" in param_name_lower:
            return '"example"'
        elif "count" in param_name_lower or "size" in param_name_lower:
            return "1"
        elif "angle" in param_name_lower:
            return "0.0"
        
        return "None"

    def _initialize_autocad_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize AutoCAD-specific method patterns."""
        return {
            "creation": {
                "name_pattern": r"(add|create|new|make)",
                "description": "Object creation methods"
            },
            "modification": {
                "name_pattern": r"(set|update|modify|change|edit)",
                "description": "Object modification methods"
            },
            "query": {
                "name_pattern": r"(get|find|search|query|list)",
                "description": "Object query methods"
            },
            "drawing": {
                "name_pattern": r"(draw|line|circle|arc|text|dimension)",
                "description": "Drawing-related methods"
            },
            "selection": {
                "name_pattern": r"(select|pick|highlight|filter)",
                "description": "Selection-related methods"
            }
        }

    def _initialize_method_documentation(self) -> Dict[str, Dict[str, Any]]:
        """Initialize method documentation database."""
        return {
            "AddLine": {
                "description": "Creates a line object in the drawing",
                "parameters": {
                    "StartPoint": "The start point of the line as [x, y, z]",
                    "EndPoint": "The end point of the line as [x, y, z]"
                },
                "return_description": "The created line object",
                "usage_examples": [
                    "line = model.AddLine([0, 0, 0], [10, 10, 0])",
                    "start = [0, 0, 0]; end = [100, 0, 0]; line = model.AddLine(start, end)"
                ]
            },
            "AddCircle": {
                "description": "Creates a circle object in the drawing",
                "parameters": {
                    "Center": "The center point of the circle as [x, y, z]",
                    "Radius": "The radius of the circle"
                },
                "return_description": "The created circle object",
                "usage_examples": [
                    "circle = model.AddCircle([0, 0, 0], 50)",
                    "center = [10, 10, 0]; radius = 25; circle = model.AddCircle(center, radius)"
                ]
            }
        }

    def _initialize_parameter_patterns(self) -> Dict[str, str]:
        """Initialize parameter pattern recognition."""
        return {
            "coordinate": r"(point|center|origin|location|position)",
            "distance": r"(radius|width|height|length|distance|size)",
            "angle": r"(angle|rotation|orient)",
            "text": r"(text|string|name|label|tag)",
            "boolean": r"(flag|enable|visible|active|show)"
        }