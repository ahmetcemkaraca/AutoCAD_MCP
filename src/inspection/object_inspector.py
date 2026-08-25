"""
Core AutoCAD Object Inspector
============================

Provides comprehensive inspection of AutoCAD objects with multi-level depth,
hierarchical navigation, and detailed property/method analysis. Supports
real-time object inspection and code generation assistance.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass
from enum import Enum
import inspect
import sys

# Optional Windows COM imports - graceful degradation if not available
try:
    import pythoncom
    import win32com.client
    COM_AVAILABLE = True
except ImportError:
    COM_AVAILABLE = False

logger = logging.getLogger(__name__)


class InspectionDepth(Enum):
    """Inspection depth levels."""
    BASIC = "basic"           # Basic properties and methods
    DETAILED = "detailed"     # Full properties, methods, and documentation
    COMPREHENSIVE = "comprehensive"  # Everything including internal attributes
    HIERARCHICAL = "hierarchical"   # Include parent/child relationships


@dataclass
class PropertyInfo:
    """Information about an object property."""
    name: str
    value: Any
    type_name: str
    is_readable: bool
    is_writable: bool
    description: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class MethodInfo:
    """Information about an object method."""
    name: str
    signature: str
    description: Optional[str] = None
    parameters: List[Dict[str, Any]] = None
    return_type: Optional[str] = None
    is_static: bool = False


@dataclass
class InspectionResult:
    """Result of object inspection."""
    object_id: Union[int, str]
    object_type: str
    object_name: Optional[str]
    depth: InspectionDepth
    properties: List[PropertyInfo]
    methods: List[MethodInfo]
    hierarchy: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    inspection_time: float = 0.0


class ObjectInspector:
    """
    Core AutoCAD object inspector with comprehensive analysis capabilities.
    """

    def __init__(self, autocad_wrapper=None):
        """
        Initialize object inspector.

        Args:
            autocad_wrapper: AutoCAD wrapper for object access
        """
        self.autocad_wrapper = autocad_wrapper
        self.inspection_cache = {}
        self.cache_timeout = 300  # 5 minutes
        
        # AutoCAD object type mappings
        self.autocad_types = self._initialize_autocad_types()
        
        # Property/method filters
        self.system_properties = {
            '__class__', '__doc__', '__dict__', '__module__', '__weakref__',
            '__getattribute__', '__setattr__', '__delattr__', '__hash__',
            '__repr__', '__str__', '__sizeof__', '__format__'
        }
        
        logger.info("ObjectInspector initialized")

    def inspect_object(self, obj: Any, depth: InspectionDepth = InspectionDepth.BASIC,
                      object_id: Optional[Union[int, str]] = None) -> InspectionResult:
        """
        Inspect an AutoCAD object with specified depth.

        Args:
            obj: Object to inspect
            depth: Inspection depth level
            object_id: Optional object identifier

        Returns:
            Comprehensive inspection result
        """
        start_time = time.time()
        
        if object_id is None:
            object_id = id(obj)

        try:
            # Check cache first
            cache_key = f"{object_id}_{depth.value}"
            if cache_key in self.inspection_cache:
                cached_result, cache_time = self.inspection_cache[cache_key]
                if time.time() - cache_time < self.cache_timeout:
                    logger.debug(f"Returning cached inspection for {object_id}")
                    return cached_result

            # Perform inspection
            result = self._perform_inspection(obj, depth, object_id)
            result.inspection_time = time.time() - start_time

            # Cache result
            self.inspection_cache[cache_key] = (result, time.time())

            logger.info(f"Inspected object {object_id} with depth {depth.value} in {result.inspection_time:.3f}s")
            return result

        except Exception as e:
            logger.error(f"Error inspecting object {object_id}: {str(e)}")
            # Return minimal result on error
            return InspectionResult(
                object_id=object_id,
                object_type="Unknown",
                object_name=None,
                depth=depth,
                properties=[],
                methods=[],
                metadata={"error": str(e)},
                inspection_time=time.time() - start_time
            )

    def inspect_by_name(self, object_name: str, depth: InspectionDepth = InspectionDepth.BASIC) -> InspectionResult:
        """
        Inspect object by name from AutoCAD context.

        Args:
            object_name: Name of object to inspect (e.g., 'app', 'doc', 'model')
            depth: Inspection depth level

        Returns:
            Inspection result
        """
        if not self.autocad_wrapper:
            raise ValueError("AutoCAD wrapper not available for object lookup")

        # Get object from AutoCAD wrapper
        obj = None
        if object_name == 'app':
            obj = getattr(self.autocad_wrapper, 'app', None)
        elif object_name == 'doc':
            obj = getattr(self.autocad_wrapper, 'doc', None)
        elif object_name == 'model':
            obj = getattr(self.autocad_wrapper, 'model', None)
        elif object_name == 'acad':
            obj = self.autocad_wrapper
        else:
            # Try to get from wrapper attributes
            obj = getattr(self.autocad_wrapper, object_name, None)

        if obj is None:
            raise ValueError(f"Object '{object_name}' not found in AutoCAD context")

        return self.inspect_object(obj, depth, object_name)

    def get_object_hierarchy(self, obj: Any) -> Dict[str, Any]:
        """
        Get object hierarchy information.

        Args:
            obj: Object to analyze

        Returns:
            Hierarchy information dictionary
        """
        try:
            hierarchy = {
                "type": type(obj).__name__,
                "module": getattr(type(obj), '__module__', 'unknown'),
                "mro": [cls.__name__ for cls in type(obj).mro()],
                "bases": [cls.__name__ for cls in type(obj).__bases__],
            }

            # Add COM-specific hierarchy if available
            if COM_AVAILABLE and hasattr(obj, '_oleobj_'):
                try:
                    # Get COM type info
                    typeinfo = obj._oleobj_.GetTypeInfo()
                    if typeinfo:
                        hierarchy["com_type"] = "COM Object"
                        hierarchy["com_class"] = getattr(obj, '_oleobj_class_', 'Unknown')
                except:
                    pass

            return hierarchy

        except Exception as e:
            logger.warning(f"Error getting object hierarchy: {str(e)}")
            return {"error": str(e)}

    def search_objects(self, search_term: str, search_type: str = "all") -> List[Dict[str, Any]]:
        """
        Search for objects matching criteria.

        Args:
            search_term: Term to search for
            search_type: Type of search ('properties', 'methods', 'all')

        Returns:
            List of matching objects/members
        """
        results = []
        search_lower = search_term.lower()

        if not self.autocad_wrapper:
            return results

        # Search in main AutoCAD objects
        objects_to_search = {
            'app': getattr(self.autocad_wrapper, 'app', None),
            'doc': getattr(self.autocad_wrapper, 'doc', None),
            'model': getattr(self.autocad_wrapper, 'model', None),
            'acad': self.autocad_wrapper
        }

        for obj_name, obj in objects_to_search.items():
            if obj is None:
                continue

            try:
                # Search properties
                if search_type in ['properties', 'all']:
                    for prop_name in dir(obj):
                        if search_lower in prop_name.lower():
                            try:
                                value = getattr(obj, prop_name)
                                results.append({
                                    "object": obj_name,
                                    "type": "property",
                                    "name": prop_name,
                                    "value_type": type(value).__name__,
                                    "match_score": self._calculate_match_score(search_term, prop_name)
                                })
                            except:
                                pass

                # Search methods
                if search_type in ['methods', 'all']:
                    for method_name in dir(obj):
                        if search_lower in method_name.lower():
                            try:
                                method = getattr(obj, method_name)
                                if callable(method):
                                    results.append({
                                        "object": obj_name,
                                        "type": "method",
                                        "name": method_name,
                                        "signature": self._get_method_signature(method),
                                        "match_score": self._calculate_match_score(search_term, method_name)
                                    })
                            except:
                                pass

            except Exception as e:
                logger.warning(f"Error searching object {obj_name}: {str(e)}")

        # Sort by match score
        results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return results[:50]  # Limit results

    def get_code_completion_data(self, context: str) -> Dict[str, Any]:
        """
        Get code completion data for context.

        Args:
            context: Code context for completion

        Returns:
            Completion data for IntelliSense
        """
        completions = {
            "properties": [],
            "methods": [],
            "objects": []
        }

        if not self.autocad_wrapper:
            return completions

        # Parse context to determine what to complete
        if '.' in context:
            # Object member completion
            parts = context.split('.')
            if len(parts) >= 2:
                obj_name = parts[0]
                partial_member = parts[-1] if len(parts) > 1 else ""
                
                obj = self._get_object_by_name(obj_name)
                if obj:
                    completions = self._get_member_completions(obj, partial_member)
        else:
            # Top-level object completion
            completions["objects"] = [
                {"name": "acad", "type": "object", "description": "AutoCAD wrapper instance"},
                {"name": "app", "type": "object", "description": "AutoCAD Application object"},
                {"name": "doc", "type": "object", "description": "Active AutoCAD document"},
                {"name": "model", "type": "object", "description": "Model space object"}
            ]

        return completions

    def clear_cache(self):
        """Clear inspection cache."""
        self.inspection_cache.clear()
        logger.info("Inspection cache cleared")

    def _perform_inspection(self, obj: Any, depth: InspectionDepth, object_id: Union[int, str]) -> InspectionResult:
        """Perform the actual object inspection."""
        # Get basic object information
        object_type = type(obj).__name__
        object_name = getattr(obj, '__name__', None) or str(object_id)

        # Analyze properties
        properties = self._analyze_properties(obj, depth)
        
        # Analyze methods
        methods = self._analyze_methods(obj, depth)

        # Get hierarchy if requested
        hierarchy = None
        if depth in [InspectionDepth.COMPREHENSIVE, InspectionDepth.HIERARCHICAL]:
            hierarchy = self.get_object_hierarchy(obj)

        # Collect metadata
        metadata = {
            "module": getattr(type(obj), '__module__', 'unknown'),
            "class_name": type(obj).__name__,
            "memory_address": hex(id(obj)),
            "property_count": len(properties),
            "method_count": len(methods)
        }

        # Add COM-specific metadata
        if COM_AVAILABLE and hasattr(obj, '_oleobj_'):
            metadata["com_object"] = True
            metadata["com_class"] = getattr(obj, '_oleobj_class_', 'Unknown')

        return InspectionResult(
            object_id=object_id,
            object_type=object_type,
            object_name=object_name,
            depth=depth,
            properties=properties,
            methods=methods,
            hierarchy=hierarchy,
            metadata=metadata
        )

    def _analyze_properties(self, obj: Any, depth: InspectionDepth) -> List[PropertyInfo]:
        """Analyze object properties."""
        properties = []
        
        for name in dir(obj):
            if name in self.system_properties and depth == InspectionDepth.BASIC:
                continue

            try:
                # Get property value safely
                try:
                    value = getattr(obj, name)
                except Exception as e:
                    value = f"<Error: {str(e)}>"

                # Skip methods for property analysis
                if callable(value):
                    continue

                # Determine type and accessibility
                type_name = type(value).__name__
                is_readable = True  # If we got here, it's readable
                is_writable = True  # Assume writable unless we can determine otherwise

                # Try to determine if writable
                try:
                    # This is a heuristic - not always accurate
                    descriptor = getattr(type(obj), name, None)
                    if descriptor and hasattr(descriptor, 'fset'):
                        is_writable = descriptor.fset is not None
                except:
                    pass

                # Get description if available
                description = None
                if depth in [InspectionDepth.DETAILED, InspectionDepth.COMPREHENSIVE]:
                    try:
                        doc = getattr(getattr(type(obj), name, None), '__doc__', None)
                        if doc:
                            description = doc.strip()
                    except:
                        pass

                properties.append(PropertyInfo(
                    name=name,
                    value=value,
                    type_name=type_name,
                    is_readable=is_readable,
                    is_writable=is_writable,
                    description=description
                ))

            except Exception as e:
                logger.debug(f"Error analyzing property {name}: {str(e)}")

        return sorted(properties, key=lambda p: p.name)

    def _analyze_methods(self, obj: Any, depth: InspectionDepth) -> List[MethodInfo]:
        """Analyze object methods."""
        methods = []

        for name in dir(obj):
            if name in self.system_properties and depth == InspectionDepth.BASIC:
                continue

            try:
                method = getattr(obj, name)
                if not callable(method):
                    continue

                # Get method signature
                signature = self._get_method_signature(method)
                
                # Get description if available
                description = None
                if depth in [InspectionDepth.DETAILED, InspectionDepth.COMPREHENSIVE]:
                    description = getattr(method, '__doc__', None)
                    if description:
                        description = description.strip()

                # Get parameter information
                parameters = None
                if depth == InspectionDepth.COMPREHENSIVE:
                    parameters = self._get_method_parameters(method)

                methods.append(MethodInfo(
                    name=name,
                    signature=signature,
                    description=description,
                    parameters=parameters,
                    is_static=isinstance(inspect.getattr_static(type(obj), name, None), staticmethod)
                ))

            except Exception as e:
                logger.debug(f"Error analyzing method {name}: {str(e)}")

        return sorted(methods, key=lambda m: m.name)

    def _get_method_signature(self, method) -> str:
        """Get method signature string."""
        try:
            sig = inspect.signature(method)
            return f"{method.__name__}{sig}"
        except (ValueError, TypeError):
            # Fallback for built-in methods or COM objects
            return f"{method.__name__}(...)"

    def _get_method_parameters(self, method) -> List[Dict[str, Any]]:
        """Get detailed method parameter information."""
        try:
            sig = inspect.signature(method)
            parameters = []
            
            for param_name, param in sig.parameters.items():
                param_info = {
                    "name": param_name,
                    "kind": param.kind.name,
                    "default": param.default if param.default != inspect.Parameter.empty else None,
                    "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else None
                }
                parameters.append(param_info)
            
            return parameters
        except (ValueError, TypeError):
            return []

    def _initialize_autocad_types(self) -> Dict[str, Dict[str, Any]]:
        """Initialize AutoCAD object type information."""
        return {
            "Application": {
                "description": "AutoCAD Application object",
                "common_properties": ["Documents", "Version", "Visible"],
                "common_methods": ["Quit", "Update", "GetAcadState"]
            },
            "Document": {
                "description": "AutoCAD Document object",
                "common_properties": ["ModelSpace", "PaperSpace", "Name"],
                "common_methods": ["Save", "Close", "SendCommand"]
            },
            "ModelSpace": {
                "description": "AutoCAD Model Space collection",
                "common_properties": ["Count"],
                "common_methods": ["AddLine", "AddCircle", "AddText", "Item"]
            }
        }

    def _get_object_by_name(self, obj_name: str) -> Optional[Any]:
        """Get object by name from AutoCAD context."""
        if not self.autocad_wrapper:
            return None

        obj_map = {
            'acad': self.autocad_wrapper,
            'app': getattr(self.autocad_wrapper, 'app', None),
            'doc': getattr(self.autocad_wrapper, 'doc', None),
            'model': getattr(self.autocad_wrapper, 'model', None)
        }

        return obj_map.get(obj_name)

    def _get_member_completions(self, obj: Any, partial: str) -> Dict[str, Any]:
        """Get member completions for an object."""
        completions = {"properties": [], "methods": []}
        partial_lower = partial.lower()

        try:
            for name in dir(obj):
                if partial_lower in name.lower():
                    try:
                        member = getattr(obj, name)
                        if callable(member):
                            completions["methods"].append({
                                "name": name,
                                "signature": self._get_method_signature(member),
                                "description": getattr(member, '__doc__', '')
                            })
                        else:
                            completions["properties"].append({
                                "name": name,
                                "type": type(member).__name__,
                                "value": str(member)[:100] if str(member) else ""
                            })
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Error getting member completions: {str(e)}")

        return completions

    def _calculate_match_score(self, search_term: str, name: str) -> float:
        """Calculate match score for search results."""
        search_lower = search_term.lower()
        name_lower = name.lower()
        
        if name_lower == search_lower:
            return 1.0
        elif name_lower.startswith(search_lower):
            return 0.8
        elif search_lower in name_lower:
            return 0.6
        else:
            # Use basic string similarity
            return len(set(search_lower) & set(name_lower)) / len(set(search_lower) | set(name_lower))