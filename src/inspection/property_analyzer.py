"""
Property Analyzer for AutoCAD Objects
====================================

Advanced property analysis with constraint detection, value validation,
and documentation extraction. Provides detailed property information
for enhanced development experience and code generation.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger(__name__)


class PropertyType(Enum):
    """Property type classification."""
    PRIMITIVE = "primitive"          # int, float, str, bool
    COLLECTION = "collection"        # list, tuple, dict
    OBJECT = "object"               # Custom objects
    COM_OBJECT = "com_object"       # COM objects
    ENUM = "enum"                   # Enumeration values
    COORDINATE = "coordinate"       # 3D coordinates
    MATRIX = "matrix"              # Transformation matrices
    UNKNOWN = "unknown"            # Unknown type


class AccessLevel(Enum):
    """Property access level."""
    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    READ_WRITE = "read_write"
    NO_ACCESS = "no_access"


@dataclass
class PropertyConstraint:
    """Property constraint information."""
    constraint_type: str
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None
    description: Optional[str] = None


@dataclass
class PropertyDocumentation:
    """Complete property documentation."""
    description: str
    usage_examples: List[str] = field(default_factory=list)
    related_properties: List[str] = field(default_factory=list)
    related_methods: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    version_info: Optional[str] = None


@dataclass
class DetailedPropertyInfo:
    """Detailed property analysis result."""
    name: str
    current_value: Any
    property_type: PropertyType
    access_level: AccessLevel
    data_type: str
    constraints: List[PropertyConstraint] = field(default_factory=list)
    documentation: Optional[PropertyDocumentation] = None
    is_inherited: bool = False
    source_class: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PropertyAnalyzer:
    """
    Advanced AutoCAD property analyzer with comprehensive analysis capabilities.
    """

    def __init__(self):
        """Initialize property analyzer."""
        # AutoCAD-specific property patterns
        self.autocad_patterns = self._initialize_autocad_patterns()
        
        # Type inference patterns
        self.type_patterns = self._initialize_type_patterns()
        
        # Constraint detection patterns
        self.constraint_patterns = self._initialize_constraint_patterns()
        
        # Property documentation database
        self.property_docs = self._initialize_property_documentation()
        
        logger.info("PropertyAnalyzer initialized")

    def analyze_property(self, obj: Any, property_name: str) -> DetailedPropertyInfo:
        """
        Perform comprehensive property analysis.

        Args:
            obj: Object containing the property
            property_name: Name of property to analyze

        Returns:
            Detailed property analysis result
        """
        try:
            # Get property value
            try:
                current_value = getattr(obj, property_name)
            except Exception as e:
                current_value = f"<Error accessing property: {str(e)}>"

            # Classify property type
            property_type = self._classify_property_type(current_value)
            
            # Determine access level
            access_level = self._determine_access_level(obj, property_name)
            
            # Get data type information
            data_type = self._get_data_type(current_value)
            
            # Detect constraints
            constraints = self._detect_constraints(obj, property_name, current_value)
            
            # Get documentation
            documentation = self._get_property_documentation(obj, property_name)
            
            # Check inheritance
            is_inherited, source_class = self._check_inheritance(obj, property_name)
            
            # Collect metadata
            metadata = self._collect_metadata(obj, property_name, current_value)

            return DetailedPropertyInfo(
                name=property_name,
                current_value=current_value,
                property_type=property_type,
                access_level=access_level,
                data_type=data_type,
                constraints=constraints,
                documentation=documentation,
                is_inherited=is_inherited,
                source_class=source_class,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error analyzing property {property_name}: {str(e)}")
            
            # Return minimal info on error
            return DetailedPropertyInfo(
                name=property_name,
                current_value=f"<Analysis Error: {str(e)}>",
                property_type=PropertyType.UNKNOWN,
                access_level=AccessLevel.NO_ACCESS,
                data_type="unknown",
                metadata={"error": str(e)}
            )

    def analyze_all_properties(self, obj: Any, include_inherited: bool = True) -> List[DetailedPropertyInfo]:
        """
        Analyze all properties of an object.

        Args:
            obj: Object to analyze
            include_inherited: Whether to include inherited properties

        Returns:
            List of detailed property information
        """
        properties = []
        
        for name in dir(obj):
            # Skip private attributes unless specifically requested
            if name.startswith('__'):
                continue
                
            try:
                # Check if it's a property (not a method)
                value = getattr(obj, name)
                if callable(value):
                    continue
                
                # Analyze the property
                prop_info = self.analyze_property(obj, name)
                
                # Filter inherited properties if requested
                if not include_inherited and prop_info.is_inherited:
                    continue
                
                properties.append(prop_info)
                
            except Exception as e:
                logger.debug(f"Skipping property {name}: {str(e)}")
        
        return sorted(properties, key=lambda p: p.name)

    def get_property_suggestions(self, obj: Any, context: str = "") -> List[Dict[str, Any]]:
        """
        Get property suggestions based on context.

        Args:
            obj: Object to analyze
            context: Context for suggestions (e.g., "coordinate", "color")

        Returns:
            List of property suggestions
        """
        suggestions = []
        
        try:
            all_properties = self.analyze_all_properties(obj, include_inherited=False)
            
            for prop in all_properties:
                # Calculate relevance score based on context
                relevance_score = self._calculate_property_relevance(prop, context)
                
                if relevance_score > 0.3:  # Threshold for inclusion
                    suggestions.append({
                        "name": prop.name,
                        "type": prop.data_type,
                        "description": prop.documentation.description if prop.documentation else "",
                        "current_value": str(prop.current_value)[:50],
                        "relevance_score": relevance_score,
                        "access_level": prop.access_level.value,
                        "constraints": len(prop.constraints) > 0
                    })
            
            # Sort by relevance score
            suggestions.sort(key=lambda x: x["relevance_score"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting property suggestions: {str(e)}")
        
        return suggestions[:20]  # Limit to top 20

    def validate_property_value(self, obj: Any, property_name: str, new_value: Any) -> Dict[str, Any]:
        """
        Validate a new property value against constraints.

        Args:
            obj: Object containing the property
            property_name: Name of property to validate
            new_value: New value to validate

        Returns:
            Validation result dictionary
        """
        try:
            prop_info = self.analyze_property(obj, property_name)
            
            # Check access level
            if prop_info.access_level in [AccessLevel.READ_ONLY, AccessLevel.NO_ACCESS]:
                return {
                    "valid": False,
                    "error": f"Property '{property_name}' is {prop_info.access_level.value}",
                    "severity": "error"
                }
            
            # Check type compatibility
            type_valid, type_error = self._validate_type(new_value, prop_info.data_type)
            if not type_valid:
                return {
                    "valid": False,
                    "error": f"Type mismatch: {type_error}",
                    "severity": "error"
                }
            
            # Check constraints
            for constraint in prop_info.constraints:
                constraint_valid, constraint_error = self._validate_constraint(new_value, constraint)
                if not constraint_valid:
                    return {
                        "valid": False,
                        "error": f"Constraint violation: {constraint_error}",
                        "severity": "warning"
                    }
            
            return {
                "valid": True,
                "message": "Value is valid for this property"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "severity": "error"
            }

    def generate_property_code(self, obj: Any, property_name: str, 
                              operation: str = "get") -> str:
        """
        Generate code for property operations.

        Args:
            obj: Object containing the property
            property_name: Name of property
            operation: Operation type ('get', 'set', 'info')

        Returns:
            Generated code string
        """
        try:
            prop_info = self.analyze_property(obj, property_name)
            obj_name = getattr(obj, '__name__', 'obj')
            
            if operation == "get":
                code = f"value = {obj_name}.{property_name}"
                if prop_info.documentation and prop_info.documentation.description:
                    code += f"  # {prop_info.documentation.description}"
                
            elif operation == "set":
                if prop_info.access_level == AccessLevel.READ_ONLY:
                    code = f"# ERROR: {property_name} is read-only"
                else:
                    example_value = self._get_example_value(prop_info)
                    code = f"{obj_name}.{property_name} = {example_value}"
                    
            elif operation == "info":
                lines = [
                    f"# Property: {property_name}",
                    f"# Type: {prop_info.data_type}",
                    f"# Access: {prop_info.access_level.value}",
                    f"# Current Value: {prop_info.current_value}"
                ]
                
                if prop_info.constraints:
                    lines.append(f"# Constraints: {len(prop_info.constraints)} defined")
                
                if prop_info.documentation:
                    lines.append(f"# Description: {prop_info.documentation.description}")
                
                code = "\n".join(lines)
            
            else:
                code = f"# Unknown operation: {operation}"
            
            return code
            
        except Exception as e:
            return f"# Error generating code: {str(e)}"

    def _classify_property_type(self, value: Any) -> PropertyType:
        """Classify property type based on value."""
        if value is None:
            return PropertyType.UNKNOWN
        
        value_type = type(value)
        
        # Check for primitives
        if value_type in [int, float, str, bool]:
            return PropertyType.PRIMITIVE
        
        # Check for collections
        if value_type in [list, tuple, dict, set]:
            return PropertyType.COLLECTION
        
        # Check for coordinates (common AutoCAD pattern)
        if (isinstance(value, (list, tuple)) and len(value) == 3 and 
            all(isinstance(x, (int, float)) for x in value)):
            return PropertyType.COORDINATE
        
        # Check for COM objects
        if hasattr(value, '_oleobj_'):
            return PropertyType.COM_OBJECT
        
        # Check for enums
        try:
            if hasattr(value, '__class__') and hasattr(value.__class__, '__members__'):
                return PropertyType.ENUM
        except:
            pass
        
        return PropertyType.OBJECT

    def _determine_access_level(self, obj: Any, property_name: str) -> AccessLevel:
        """Determine property access level."""
        try:
            # Try to get the property descriptor
            descriptor = getattr(type(obj), property_name, None)
            
            if descriptor is None:
                # If no descriptor, assume read-write for simple attributes
                return AccessLevel.READ_WRITE
            
            if isinstance(descriptor, property):
                has_getter = descriptor.fget is not None
                has_setter = descriptor.fset is not None
                
                if has_getter and has_setter:
                    return AccessLevel.READ_WRITE
                elif has_getter:
                    return AccessLevel.READ_ONLY
                elif has_setter:
                    return AccessLevel.WRITE_ONLY
                else:
                    return AccessLevel.NO_ACCESS
            
            # For other descriptors, try to determine access
            # This is heuristic and may not always be accurate
            return AccessLevel.READ_WRITE
            
        except Exception:
            # Default to read-write if we can't determine
            return AccessLevel.READ_WRITE

    def _get_data_type(self, value: Any) -> str:
        """Get detailed data type information."""
        if value is None:
            return "NoneType"
        
        value_type = type(value)
        type_name = value_type.__name__
        
        # Add module information for non-built-ins
        if hasattr(value_type, '__module__') and value_type.__module__ != 'builtins':
            type_name = f"{value_type.__module__}.{type_name}"
        
        # Add generic type information for collections
        if isinstance(value, (list, tuple)):
            if value:
                element_types = {type(item).__name__ for item in value[:5]}  # Sample first 5
                if len(element_types) == 1:
                    type_name += f"[{element_types.pop()}]"
                elif len(element_types) <= 3:
                    type_name += f"[{', '.join(sorted(element_types))}]"
                else:
                    type_name += "[mixed]"
        
        return type_name

    def _detect_constraints(self, obj: Any, property_name: str, value: Any) -> List[PropertyConstraint]:
        """Detect property constraints."""
        constraints = []
        
        try:
            # Check AutoCAD-specific patterns
            for pattern_name, pattern_info in self.constraint_patterns.items():
                if re.search(pattern_info["name_pattern"], property_name, re.IGNORECASE):
                    constraint = PropertyConstraint(
                        constraint_type=pattern_name,
                        description=pattern_info["description"]
                    )
                    
                    if "min_value" in pattern_info:
                        constraint.min_value = pattern_info["min_value"]
                    if "max_value" in pattern_info:
                        constraint.max_value = pattern_info["max_value"]
                    if "allowed_values" in pattern_info:
                        constraint.allowed_values = pattern_info["allowed_values"]
                    
                    constraints.append(constraint)
            
            # Value-based constraint detection
            if isinstance(value, (int, float)):
                if 0 <= value <= 1:
                    constraints.append(PropertyConstraint(
                        constraint_type="normalized_value",
                        min_value=0.0,
                        max_value=1.0,
                        description="Value appears to be normalized (0-1 range)"
                    ))
                elif value >= 0:
                    constraints.append(PropertyConstraint(
                        constraint_type="positive_value",
                        min_value=0,
                        description="Value appears to be non-negative"
                    ))
            
        except Exception as e:
            logger.debug(f"Error detecting constraints for {property_name}: {str(e)}")
        
        return constraints

    def _get_property_documentation(self, obj: Any, property_name: str) -> Optional[PropertyDocumentation]:
        """Get property documentation."""
        try:
            # Check built-in property docs
            if property_name in self.property_docs:
                doc_info = self.property_docs[property_name]
                return PropertyDocumentation(**doc_info)
            
            # Try to get docstring from property descriptor
            descriptor = getattr(type(obj), property_name, None)
            if descriptor and hasattr(descriptor, '__doc__') and descriptor.__doc__:
                return PropertyDocumentation(
                    description=descriptor.__doc__.strip()
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting documentation for {property_name}: {str(e)}")
            return None

    def _check_inheritance(self, obj: Any, property_name: str) -> tuple[bool, Optional[str]]:
        """Check if property is inherited."""
        try:
            obj_class = type(obj)
            
            # Check if property exists in base classes
            for base_class in obj_class.mro()[1:]:  # Skip the object's own class
                if hasattr(base_class, property_name):
                    return True, base_class.__name__
            
            return False, None
            
        except Exception:
            return False, None

    def _collect_metadata(self, obj: Any, property_name: str, value: Any) -> Dict[str, Any]:
        """Collect additional property metadata."""
        metadata = {}
        
        try:
            # Size information for collections
            if hasattr(value, '__len__'):
                metadata["length"] = len(value)
            
            # Memory size estimation
            if hasattr(value, '__sizeof__'):
                metadata["memory_size_bytes"] = value.__sizeof__()
            
            # String representation length
            str_repr = str(value)
            metadata["string_length"] = len(str_repr)
            metadata["string_preview"] = str_repr[:100] + "..." if len(str_repr) > 100 else str_repr
            
            # AutoCAD-specific metadata
            if hasattr(value, '_oleobj_'):
                metadata["com_object"] = True
                metadata["com_class"] = getattr(value, '_oleobj_class_', 'Unknown')
            
        except Exception as e:
            metadata["metadata_error"] = str(e)
        
        return metadata

    def _initialize_autocad_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize AutoCAD-specific property patterns."""
        return {
            "coordinate": {
                "pattern": r"(center|point|origin|position|location)",
                "description": "3D coordinate property"
            },
            "angle": {
                "pattern": r"(angle|rotation|orient)",
                "description": "Angular measurement property"
            },
            "color": {
                "pattern": r"(color|colour)",
                "description": "Color property"
            },
            "layer": {
                "pattern": r"layer",
                "description": "Layer assignment property"
            }
        }

    def _initialize_type_patterns(self) -> Dict[str, str]:
        """Initialize type inference patterns."""
        return {
            "coordinate": r"^\[?\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\s*\]?$",
            "color_rgb": r"^\[?\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\]?$",
            "angle_degrees": r"^\d+\.?\d*°?$",
            "boolean_text": r"^(true|false|yes|no|on|off)$"
        }

    def _initialize_constraint_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize constraint detection patterns."""
        return {
            "angle_constraint": {
                "name_pattern": r"angle|rotation",
                "min_value": 0.0,
                "max_value": 360.0,
                "description": "Angle in degrees (0-360)"
            },
            "normalized_constraint": {
                "name_pattern": r"opacity|alpha|factor|ratio",
                "min_value": 0.0,
                "max_value": 1.0,
                "description": "Normalized value (0.0-1.0)"
            },
            "positive_constraint": {
                "name_pattern": r"width|height|radius|size|scale|distance",
                "min_value": 0.0,
                "description": "Must be non-negative"
            }
        }

    def _initialize_property_documentation(self) -> Dict[str, Dict[str, Any]]:
        """Initialize property documentation database."""
        return {
            "Name": {
                "description": "The name of the object",
                "usage_examples": ["obj.Name = 'MyObject'", "print(obj.Name)"],
                "related_properties": ["ObjectName", "Label"]
            },
            "Visible": {
                "description": "Controls the visibility of the object",
                "usage_examples": ["obj.Visible = True", "if obj.Visible: print('Object is visible')"],
                "related_methods": ["Show", "Hide"]
            },
            "Layer": {
                "description": "The layer on which the object resides",
                "usage_examples": ["obj.Layer = '0'", "current_layer = obj.Layer"],
                "related_properties": ["LayerName"]
            }
        }

    def _calculate_property_relevance(self, prop: DetailedPropertyInfo, context: str) -> float:
        """Calculate property relevance score for suggestions."""
        score = 0.0
        context_lower = context.lower()
        prop_name_lower = prop.name.lower()
        
        # Exact match
        if context_lower == prop_name_lower:
            score += 1.0
        
        # Contains context
        elif context_lower in prop_name_lower:
            score += 0.8
        
        # Context contains property name
        elif prop_name_lower in context_lower:
            score += 0.6
        
        # Type-based relevance
        if context_lower in ["coordinate", "point"] and prop.property_type == PropertyType.COORDINATE:
            score += 0.7
        elif context_lower in ["color"] and "color" in prop_name_lower:
            score += 0.7
        elif context_lower in ["size", "dimension"] and any(word in prop_name_lower for word in ["width", "height", "size", "radius"]):
            score += 0.6
        
        # Access level bonus (prefer read-write properties)
        if prop.access_level == AccessLevel.READ_WRITE:
            score += 0.1
        
        return min(score, 1.0)

    def _validate_type(self, value: Any, expected_type: str) -> tuple[bool, str]:
        """Validate value type against expected type."""
        try:
            value_type = type(value).__name__
            
            # Simple type check
            if expected_type.split('.')[-1] == value_type:
                return True, ""
            
            # Special cases
            if expected_type in ["int", "float"] and isinstance(value, (int, float)):
                return True, ""
            
            if expected_type.startswith("list") and isinstance(value, list):
                return True, ""
            
            return False, f"Expected {expected_type}, got {value_type}"
            
        except Exception as e:
            return False, f"Type validation error: {str(e)}"

    def _validate_constraint(self, value: Any, constraint: PropertyConstraint) -> tuple[bool, str]:
        """Validate value against constraint."""
        try:
            if constraint.min_value is not None and value < constraint.min_value:
                return False, f"Value {value} below minimum {constraint.min_value}"
            
            if constraint.max_value is not None and value > constraint.max_value:
                return False, f"Value {value} above maximum {constraint.max_value}"
            
            if constraint.allowed_values is not None and value not in constraint.allowed_values:
                return False, f"Value {value} not in allowed values: {constraint.allowed_values}"
            
            if constraint.pattern is not None and isinstance(value, str):
                if not re.match(constraint.pattern, value):
                    return False, f"Value does not match required pattern"
            
            return True, ""
            
        except Exception as e:
            return False, f"Constraint validation error: {str(e)}"

    def _get_example_value(self, prop_info: DetailedPropertyInfo) -> str:
        """Get example value for code generation."""
        if prop_info.property_type == PropertyType.PRIMITIVE:
            if prop_info.data_type == "str":
                return '"example_string"'
            elif prop_info.data_type == "int":
                return "42"
            elif prop_info.data_type == "float":
                return "3.14"
            elif prop_info.data_type == "bool":
                return "True"
        
        elif prop_info.property_type == PropertyType.COORDINATE:
            return "[0.0, 0.0, 0.0]"
        
        elif prop_info.property_type == PropertyType.COLLECTION:
            return "[]"
        
        return "None"