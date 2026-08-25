"""
Advanced Variable Inspector and Call Stack Analyzer
=================================================

Enhanced variable inspection system with deep analysis capabilities including:
- Multi-level variable introspection with AutoCAD object specialization
- Dynamic call stack analysis with performance tracking
- Variable change tracking with history and diff analysis
- Memory usage monitoring and leak detection
- Cross-reference analysis for complex object relationships
"""

import logging
import time
import sys
import gc
import inspect
import threading
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import weakref
import traceback
import ast

# Import core components
from ..inspection.object_inspector import ObjectInspector, InspectionDepth
from ..inspection.property_analyzer import PropertyAnalyzer
from ..inspection.method_discoverer import MethodDiscoverer
from .secure_evaluator import safe_eval, SecureEvaluationError

logger = logging.getLogger(__name__)


class VariableType(Enum):
    """Classification of variable types for specialized handling."""
    PRIMITIVE = "primitive"          # int, str, bool, float
    COLLECTION = "collection"        # list, dict, set, tuple
    AUTOCAD_OBJECT = "autocad"       # AutoCAD COM objects
    CUSTOM_CLASS = "custom_class"    # User-defined classes
    BUILTIN_CLASS = "builtin_class"  # Built-in Python classes
    FUNCTION = "function"            # Functions and methods
    MODULE = "module"                # Module objects
    UNKNOWN = "unknown"              # Unclassified objects


class ChangeType(Enum):
    """Types of variable changes to track."""
    VALUE_CHANGE = "value_change"    # Variable value changed
    TYPE_CHANGE = "type_change"      # Variable type changed
    REFERENCE_CHANGE = "ref_change"  # Object reference changed
    ATTRIBUTE_CHANGE = "attr_change" # Object attribute changed
    COLLECTION_CHANGE = "coll_change" # Collection contents changed


@dataclass
class VariableChange:
    """Record of a variable change event."""
    timestamp: float
    change_type: ChangeType
    variable_name: str
    old_value: Any
    new_value: Any
    old_type: str
    new_type: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CallStackFrame:
    """Enhanced call stack frame with detailed analysis."""
    frame_id: str
    filename: str
    line_number: int
    function_name: str
    code_context: List[str]
    
    # Variable analysis
    local_variables: Dict[str, Any]
    global_variables: Dict[str, Any]
    builtin_variables: Dict[str, Any]
    
    # Performance data
    execution_time: float = 0.0
    memory_usage: int = 0
    cpu_time: float = 0.0
    
    # Context information
    is_autocad_frame: bool = False
    autocad_objects: Dict[str, Any] = field(default_factory=dict)
    error_state: Optional[str] = None
    
    # Analysis metadata
    complexity_score: float = 0.0
    variable_count: int = 0
    object_count: int = 0


@dataclass
class VariableSnapshot:
    """Comprehensive snapshot of a variable's state."""
    name: str
    value: Any
    type_name: str
    size_bytes: int
    variable_type: VariableType
    
    # Detailed analysis
    attributes: Dict[str, Any] = field(default_factory=dict)
    methods: List[str] = field(default_factory=list)
    memory_address: Optional[str] = None
    reference_count: int = 0
    
    # AutoCAD-specific analysis
    autocad_properties: Dict[str, Any] = field(default_factory=dict)
    autocad_methods: List[str] = field(default_factory=list)
    
    # Change tracking
    change_history: List[VariableChange] = field(default_factory=list)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    
    # Relationships
    references_to: Set[str] = field(default_factory=set)
    referenced_by: Set[str] = field(default_factory=set)


class AdvancedVariableInspector:
    """
    Advanced variable inspection system with deep analysis capabilities.
    
    Provides comprehensive variable analysis including AutoCAD object
    inspection, change tracking, memory monitoring, and relationship analysis.
    """
    
    def __init__(self, object_inspector: Optional[ObjectInspector] = None):
        """
        Initialize advanced variable inspector.
        
        Args:
            object_inspector: Object inspector for detailed analysis
        """
        self.object_inspector = object_inspector or ObjectInspector()
        self.property_analyzer = PropertyAnalyzer()
        self.method_discoverer = MethodDiscoverer()
        
        # Variable tracking
        self.variable_snapshots: Dict[str, VariableSnapshot] = {}
        self.variable_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.watched_variables: Set[str] = set()
        
        # Memory tracking
        self.memory_snapshots: deque = deque(maxlen=1000)
        self.memory_baselines: Dict[str, int] = {}
        self.leak_candidates: Dict[str, Dict[str, Any]] = {}
        
        # Call stack analysis
        self.call_stack_history: deque = deque(maxlen=500)
        self.function_performance: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Threading and synchronization
        self.lock = threading.RLock()
        self.inspection_threads: Dict[str, threading.Thread] = {}
        
        # Configuration
        self.max_inspection_depth = 5
        self.memory_threshold_mb = 100
        self.performance_tracking = True
        self.auto_gc_analysis = True
        
        logger.info("Advanced variable inspector initialized")

    def inspect_variable(self, 
                        variable_name: str,
                        variable_value: Any,
                        context: Optional[Dict[str, Any]] = None,
                        depth: str = "detailed") -> VariableSnapshot:
        """
        Perform comprehensive inspection of a variable.
        
        Args:
            variable_name: Name of the variable
            variable_value: Value of the variable
            context: Optional context information
            depth: Inspection depth ('basic', 'detailed', 'comprehensive')
            
        Returns:
            Comprehensive variable snapshot
        """
        start_time = time.time()
        
        try:
            inspection_depth = InspectionDepth(depth)
        except ValueError:
            inspection_depth = InspectionDepth.DETAILED
        
        # Classify variable type
        var_type = self._classify_variable_type(variable_value)
        
        # Create base snapshot
        snapshot = VariableSnapshot(
            name=variable_name,
            value=variable_value,
            type_name=type(variable_value).__name__,
            size_bytes=self._calculate_size(variable_value),
            variable_type=var_type
        )
        
        # Get memory information
        try:
            snapshot.memory_address = hex(id(variable_value))
            snapshot.reference_count = sys.getrefcount(variable_value)
        except Exception:
            pass
        
        # Perform type-specific analysis
        if var_type == VariableType.AUTOCAD_OBJECT:
            self._analyze_autocad_variable(snapshot, variable_value, inspection_depth)
        elif var_type == VariableType.CUSTOM_CLASS:
            self._analyze_custom_class_variable(snapshot, variable_value, inspection_depth)
        elif var_type == VariableType.COLLECTION:
            self._analyze_collection_variable(snapshot, variable_value, inspection_depth)
        elif var_type == VariableType.FUNCTION:
            self._analyze_function_variable(snapshot, variable_value, inspection_depth)
        
        # Analyze relationships if comprehensive inspection
        if inspection_depth == InspectionDepth.COMPREHENSIVE:
            self._analyze_variable_relationships(snapshot, variable_value, context)
        
        # Update change history if variable is being tracked
        if variable_name in self.variable_snapshots:
            old_snapshot = self.variable_snapshots[variable_name]
            change = self._detect_variable_change(old_snapshot, snapshot)
            if change:
                snapshot.change_history.append(change)
        
        # Store snapshot
        with self.lock:
            self.variable_snapshots[variable_name] = snapshot
            self.variable_history[variable_name].append({
                'timestamp': time.time(),
                'snapshot': snapshot,
                'inspection_time': time.time() - start_time
            })
        
        # Update access tracking
        snapshot.access_count += 1
        snapshot.last_accessed = time.time()
        
        return snapshot

    def inspect_call_stack(self, 
                          current_frame: Optional[Any] = None,
                          max_depth: int = 20,
                          include_variables: bool = True,
                          performance_analysis: bool = True) -> List[CallStackFrame]:
        """
        Analyze the current call stack with detailed frame information.
        
        Args:
            current_frame: Starting frame (defaults to current frame)
            max_depth: Maximum stack depth to analyze
            include_variables: Include variable analysis for each frame
            performance_analysis: Include performance metrics
            
        Returns:
            List of analyzed call stack frames
        """
        if current_frame is None:
            current_frame = inspect.currentframe().f_back
        
        stack_frames = []
        frame_count = 0
        
        while current_frame and frame_count < max_depth:
            try:
                frame_info = self._analyze_stack_frame(
                    current_frame, 
                    include_variables=include_variables,
                    performance_analysis=performance_analysis
                )
                stack_frames.append(frame_info)
                
                # Move to previous frame
                current_frame = current_frame.f_back
                frame_count += 1
                
            except Exception as e:
                logger.warning(f"Error analyzing stack frame {frame_count}: {e}")
                break
        
        # Store call stack for historical analysis
        with self.lock:
            self.call_stack_history.append({
                'timestamp': time.time(),
                'frames': stack_frames,
                'depth': len(stack_frames)
            })
        
        return stack_frames

    def track_variable_changes(self, 
                             variable_names: List[str],
                             change_threshold: Optional[float] = None,
                             track_attributes: bool = True) -> str:
        """
        Start tracking changes for specified variables.
        
        Args:
            variable_names: List of variable names to track
            change_threshold: Threshold for detecting significant changes
            track_attributes: Track attribute changes for objects
            
        Returns:
            Tracking session ID
        """
        session_id = f"track_{int(time.time() * 1000) % 1000000:06d}"
        
        with self.lock:
            for var_name in variable_names:
                self.watched_variables.add(var_name)
                
                # Initialize tracking history if needed
                if var_name not in self.variable_history:
                    self.variable_history[var_name] = deque(maxlen=100)
        
        logger.info(f"Started tracking {len(variable_names)} variables (session: {session_id})")
        return session_id

    def analyze_memory_usage(self, 
                           include_gc_analysis: bool = True,
                           detect_leaks: bool = True) -> Dict[str, Any]:
        """
        Analyze current memory usage and detect potential issues.
        
        Args:
            include_gc_analysis: Include garbage collection analysis
            detect_leaks: Attempt to detect memory leaks
            
        Returns:
            Memory analysis report
        """
        import psutil
        import os
        
        # Get current process memory info
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        analysis = {
            'timestamp': time.time(),
            'memory_usage': {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percent': process.memory_percent()
            },
            'object_counts': {},
            'large_objects': [],
            'potential_leaks': []
        }
        
        # Analyze object counts by type
        object_counts = defaultdict(int)
        large_objects = []
        
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            object_counts[obj_type] += 1
            
            # Check for large objects
            try:
                obj_size = self._calculate_size(obj)
                if obj_size > 1024 * 1024:  # Objects larger than 1MB
                    large_objects.append({
                        'type': obj_type,
                        'size_mb': obj_size / 1024 / 1024,
                        'id': hex(id(obj))
                    })
            except Exception:
                pass
        
        analysis['object_counts'] = dict(object_counts)
        analysis['large_objects'] = sorted(large_objects, key=lambda x: x['size_mb'], reverse=True)[:20]
        
        # Garbage collection analysis
        if include_gc_analysis:
            analysis['gc_stats'] = {
                'collections': gc.get_stats(),
                'threshold': gc.get_threshold(),
                'counts': gc.get_count()
            }
            
            # Force garbage collection and measure impact
            before_count = len(gc.get_objects())
            collected = gc.collect()
            after_count = len(gc.get_objects())
            
            analysis['gc_impact'] = {
                'objects_before': before_count,
                'objects_after': after_count,
                'objects_collected': collected,
                'objects_freed': before_count - after_count
            }
        
        # Leak detection
        if detect_leaks:
            analysis['potential_leaks'] = self._detect_memory_leaks()
        
        # Store memory snapshot
        with self.lock:
            self.memory_snapshots.append(analysis)
        
        return analysis

    def get_variable_diff(self, 
                         variable_name: str, 
                         timestamp1: Optional[float] = None,
                         timestamp2: Optional[float] = None) -> Dict[str, Any]:
        """
        Compare variable states between two points in time.
        
        Args:
            variable_name: Name of variable to compare
            timestamp1: First timestamp (defaults to earliest)
            timestamp2: Second timestamp (defaults to latest)
            
        Returns:
            Detailed diff analysis
        """
        if variable_name not in self.variable_history:
            return {'error': f'No history found for variable: {variable_name}'}
        
        history = self.variable_history[variable_name]
        
        if len(history) < 2:
            return {'error': 'Insufficient history for comparison'}
        
        # Find snapshots for comparison
        if timestamp1 is None:
            snapshot1 = history[0]['snapshot']
        else:
            snapshot1 = self._find_snapshot_by_timestamp(history, timestamp1)
        
        if timestamp2 is None:
            snapshot2 = history[-1]['snapshot']
        else:
            snapshot2 = self._find_snapshot_by_timestamp(history, timestamp2)
        
        if not snapshot1 or not snapshot2:
            return {'error': 'Could not find snapshots for specified timestamps'}
        
        # Perform diff analysis
        diff_analysis = {
            'variable_name': variable_name,
            'comparison_timestamps': {
                'earlier': timestamp1 or history[0]['timestamp'],
                'later': timestamp2 or history[-1]['timestamp']
            },
            'value_changed': snapshot1.value != snapshot2.value,
            'type_changed': snapshot1.type_name != snapshot2.type_name,
            'size_changed': snapshot1.size_bytes != snapshot2.size_bytes,
            'changes': []
        }
        
        # Analyze specific changes
        if diff_analysis['value_changed']:
            diff_analysis['changes'].append({
                'type': 'value',
                'old_value': str(snapshot1.value),
                'new_value': str(snapshot2.value)
            })
        
        if diff_analysis['type_changed']:
            diff_analysis['changes'].append({
                'type': 'type',
                'old_type': snapshot1.type_name,
                'new_type': snapshot2.type_name
            })
        
        if diff_analysis['size_changed']:
            diff_analysis['changes'].append({
                'type': 'size',
                'old_size': snapshot1.size_bytes,
                'new_size': snapshot2.size_bytes,
                'size_diff': snapshot2.size_bytes - snapshot1.size_bytes
            })
        
        # Attribute-level diff for objects
        if hasattr(snapshot1, 'attributes') and hasattr(snapshot2, 'attributes'):
            attr_changes = self._diff_attributes(snapshot1.attributes, snapshot2.attributes)
            if attr_changes:
                diff_analysis['changes'].append({
                    'type': 'attributes',
                    'changes': attr_changes
                })
        
        return diff_analysis

    def get_performance_analysis(self, 
                               function_name: Optional[str] = None,
                               time_window: float = 3600.0) -> Dict[str, Any]:
        """
        Analyze performance metrics from call stack history.
        
        Args:
            function_name: Specific function to analyze (optional)
            time_window: Time window in seconds for analysis
            
        Returns:
            Performance analysis report
        """
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        analysis = {
            'timestamp': current_time,
            'time_window': time_window,
            'function_metrics': {},
            'slowest_functions': [],
            'most_called_functions': [],
            'memory_intensive_functions': []
        }
        
        # Analyze call stack history
        function_stats = defaultdict(lambda: {
            'call_count': 0,
            'total_time': 0.0,
            'max_time': 0.0,
            'min_time': float('inf'),
            'total_memory': 0,
            'max_memory': 0
        })
        
        with self.lock:
            for stack_entry in self.call_stack_history:
                if stack_entry['timestamp'] < cutoff_time:
                    continue
                
                for frame in stack_entry['frames']:
                    func_key = f"{frame.filename}:{frame.function_name}"
                    
                    # Skip if filtering by specific function
                    if function_name and frame.function_name != function_name:
                        continue
                    
                    stats = function_stats[func_key]
                    stats['call_count'] += 1
                    stats['total_time'] += frame.execution_time
                    stats['max_time'] = max(stats['max_time'], frame.execution_time)
                    stats['min_time'] = min(stats['min_time'], frame.execution_time)
                    stats['total_memory'] += frame.memory_usage
                    stats['max_memory'] = max(stats['max_memory'], frame.memory_usage)
        
        # Calculate derived metrics
        for func_key, stats in function_stats.items():
            if stats['call_count'] > 0:
                stats['avg_time'] = stats['total_time'] / stats['call_count']
                stats['avg_memory'] = stats['total_memory'] / stats['call_count']
                stats['function_name'] = func_key.split(':')[-1]
                stats['filename'] = func_key.split(':')[0]
        
        analysis['function_metrics'] = dict(function_stats)
        
        # Generate top lists
        all_functions = list(function_stats.items())
        
        analysis['slowest_functions'] = sorted(
            all_functions, key=lambda x: x[1]['avg_time'], reverse=True
        )[:10]
        
        analysis['most_called_functions'] = sorted(
            all_functions, key=lambda x: x[1]['call_count'], reverse=True
        )[:10]
        
        analysis['memory_intensive_functions'] = sorted(
            all_functions, key=lambda x: x[1]['avg_memory'], reverse=True
        )[:10]
        
        return analysis

    def _classify_variable_type(self, value: Any) -> VariableType:
        """Classify a variable's type for specialized handling."""
        if value is None or isinstance(value, (int, str, bool, float, bytes)):
            return VariableType.PRIMITIVE
        elif isinstance(value, (list, dict, set, tuple, frozenset)):
            return VariableType.COLLECTION
        elif self._is_autocad_object(value):
            return VariableType.AUTOCAD_OBJECT
        elif callable(value):
            return VariableType.FUNCTION
        elif inspect.ismodule(value):
            return VariableType.MODULE
        elif hasattr(value, '__dict__') or hasattr(value, '__slots__'):
            # Check if it's a built-in class
            if value.__class__.__module__ in ('builtins', '__builtin__'):
                return VariableType.BUILTIN_CLASS
            else:
                return VariableType.CUSTOM_CLASS
        else:
            return VariableType.UNKNOWN

    def _analyze_autocad_variable(self, 
                                snapshot: VariableSnapshot, 
                                value: Any, 
                                depth: InspectionDepth):
        """Perform specialized analysis for AutoCAD objects."""
        try:
            # Use object inspector for detailed AutoCAD analysis
            inspection_result = self.object_inspector.inspect_object(value, depth=depth)
            
            snapshot.autocad_properties = inspection_result.get('properties', {})
            snapshot.autocad_methods = list(inspection_result.get('methods', {}).keys())
            
            # Extract additional AutoCAD-specific information
            if hasattr(value, 'ObjectName'):
                snapshot.autocad_properties['ObjectName'] = str(value.ObjectName)
            if hasattr(value, 'Handle'):
                snapshot.autocad_properties['Handle'] = str(value.Handle)
            if hasattr(value, 'Document'):
                snapshot.autocad_properties['Document'] = str(value.Document)
            
        except Exception as e:
            logger.warning(f"Failed to analyze AutoCAD variable: {e}")
            snapshot.autocad_properties = {'analysis_error': str(e)}

    def _analyze_custom_class_variable(self, 
                                     snapshot: VariableSnapshot, 
                                     value: Any, 
                                     depth: InspectionDepth):
        """Analyze custom class instances."""
        try:
            # Get class attributes
            if hasattr(value, '__dict__'):
                snapshot.attributes = dict(value.__dict__)
            elif hasattr(value, '__slots__'):
                snapshot.attributes = {
                    slot: getattr(value, slot, '<not set>')
                    for slot in value.__slots__
                }
            
            # Get methods
            snapshot.methods = [
                name for name, method in inspect.getmembers(value)
                if inspect.ismethod(method) or inspect.isfunction(method)
            ]
            
            # Class hierarchy information
            snapshot.attributes['__class__'] = value.__class__.__name__
            snapshot.attributes['__module__'] = getattr(value.__class__, '__module__', 'unknown')
            snapshot.attributes['__mro__'] = [cls.__name__ for cls in value.__class__.__mro__]
            
        except Exception as e:
            logger.warning(f"Failed to analyze custom class variable: {e}")
            snapshot.attributes = {'analysis_error': str(e)}

    def _analyze_collection_variable(self, 
                                   snapshot: VariableSnapshot, 
                                   value: Any, 
                                   depth: InspectionDepth):
        """Analyze collection types (list, dict, set, tuple)."""
        try:
            snapshot.attributes = {
                'length': len(value),
                'type': type(value).__name__
            }
            
            if isinstance(value, dict):
                snapshot.attributes['keys'] = list(value.keys())[:50]  # Limit for large dicts
                snapshot.attributes['has_nested_dicts'] = any(isinstance(v, dict) for v in value.values())
            elif isinstance(value, (list, tuple)):
                snapshot.attributes['element_types'] = list(set(type(item).__name__ for item in value))
                snapshot.attributes['has_nested_collections'] = any(
                    isinstance(item, (list, dict, set, tuple)) for item in value
                )
            elif isinstance(value, set):
                snapshot.attributes['element_types'] = list(set(type(item).__name__ for item in value))
            
            # Sample of contents for inspection (limit size)
            if len(value) <= 10:
                snapshot.attributes['contents'] = str(value)
            else:
                snapshot.attributes['sample_contents'] = str(list(value)[:5]) + '...'
                
        except Exception as e:
            logger.warning(f"Failed to analyze collection variable: {e}")
            snapshot.attributes = {'analysis_error': str(e)}

    def _analyze_function_variable(self, 
                                 snapshot: VariableSnapshot, 
                                 value: Any, 
                                 depth: InspectionDepth):
        """Analyze function and method objects."""
        try:
            snapshot.attributes = {
                'name': getattr(value, '__name__', 'unknown'),
                'module': getattr(value, '__module__', 'unknown'),
                'qualname': getattr(value, '__qualname__', 'unknown')
            }
            
            # Get function signature if possible
            try:
                sig = inspect.signature(value)
                snapshot.attributes['signature'] = str(sig)
                snapshot.attributes['parameters'] = list(sig.parameters.keys())
            except (ValueError, TypeError):
                pass
            
            # Get docstring
            doc = inspect.getdoc(value)
            if doc:
                snapshot.attributes['docstring'] = doc[:200] + ('...' if len(doc) > 200 else '')
            
            # Source file information
            try:
                source_file = inspect.getfile(value)
                source_lines = inspect.getsourcelines(value)
                snapshot.attributes['source_file'] = source_file
                snapshot.attributes['source_line'] = source_lines[1]
            except (OSError, TypeError):
                pass
                
        except Exception as e:
            logger.warning(f"Failed to analyze function variable: {e}")
            snapshot.attributes = {'analysis_error': str(e)}

    def _analyze_stack_frame(self, 
                           frame: Any, 
                           include_variables: bool = True,
                           performance_analysis: bool = True) -> CallStackFrame:
        """Analyze a single call stack frame."""
        frame_info = CallStackFrame(
            frame_id=f"frame_{id(frame)}",
            filename=frame.f_code.co_filename,
            line_number=frame.f_lineno,
            function_name=frame.f_code.co_name,
            code_context=[],
            local_variables={},
            global_variables={},
            builtin_variables={}
        )
        
        # Get code context
        try:
            import linecache
            for i in range(max(1, frame_info.line_number - 2), frame_info.line_number + 3):
                line = linecache.getline(frame_info.filename, i).rstrip()
                if line:
                    prefix = ">>> " if i == frame_info.line_number else "    "
                    frame_info.code_context.append(f"{prefix}{i:4d}: {line}")
        except Exception:
            pass
        
        # Analyze variables if requested
        if include_variables:
            try:
                # Local variables
                for name, value in frame.f_locals.items():
                    if not name.startswith('__'):
                        frame_info.local_variables[name] = self._safe_repr(value)
                        
                        # Check for AutoCAD objects
                        if self._is_autocad_object(value):
                            frame_info.is_autocad_frame = True
                            frame_info.autocad_objects[name] = self._safe_repr(value)
                
                # Global variables (limit to avoid clutter)
                global_count = 0
                for name, value in frame.f_globals.items():
                    if not name.startswith('__') and global_count < 20:
                        frame_info.global_variables[name] = self._safe_repr(value)
                        global_count += 1
                
                # Built-in variables
                if hasattr(frame, 'f_builtins'):
                    builtin_count = 0
                    for name, value in frame.f_builtins.items():
                        if not name.startswith('__') and builtin_count < 10:
                            frame_info.builtin_variables[name] = self._safe_repr(value)
                            builtin_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to analyze frame variables: {e}")
        
        # Performance analysis
        if performance_analysis:
            try:
                frame_info.memory_usage = self._estimate_frame_memory(frame)
                frame_info.variable_count = len(frame_info.local_variables)
                frame_info.object_count = sum(
                    1 for value in frame.f_locals.values()
                    if hasattr(value, '__dict__') or hasattr(value, '__slots__')
                )
                
                # Calculate complexity score based on variable count and types
                frame_info.complexity_score = min(10.0, 
                    (frame_info.variable_count * 0.1) + 
                    (frame_info.object_count * 0.5) +
                    (len(frame_info.autocad_objects) * 1.0)
                )
                
            except Exception as e:
                logger.warning(f"Failed to analyze frame performance: {e}")
        
        return frame_info

    def _analyze_variable_relationships(self, 
                                      snapshot: VariableSnapshot, 
                                      value: Any, 
                                      context: Optional[Dict[str, Any]]):
        """Analyze relationships between variables."""
        if not context:
            return
        
        try:
            # Find variables that reference this object
            value_id = id(value)
            
            for var_name, var_value in context.items():
                if var_name == snapshot.name:
                    continue
                
                # Check if this variable references our object
                if id(var_value) == value_id:
                    snapshot.referenced_by.add(var_name)
                
                # Check if our object references this variable
                if hasattr(value, '__dict__'):
                    for attr_name, attr_value in value.__dict__.items():
                        if id(attr_value) == id(var_value):
                            snapshot.references_to.add(f"{var_name}.{attr_name}")
                
        except Exception as e:
            logger.warning(f"Failed to analyze variable relationships: {e}")

    def _detect_variable_change(self, 
                              old_snapshot: VariableSnapshot, 
                              new_snapshot: VariableSnapshot) -> Optional[VariableChange]:
        """Detect and categorize changes between variable snapshots."""
        change_type = None
        
        if old_snapshot.value != new_snapshot.value:
            if old_snapshot.type_name != new_snapshot.type_name:
                change_type = ChangeType.TYPE_CHANGE
            else:
                change_type = ChangeType.VALUE_CHANGE
        elif old_snapshot.memory_address != new_snapshot.memory_address:
            change_type = ChangeType.REFERENCE_CHANGE
        elif old_snapshot.attributes != new_snapshot.attributes:
            change_type = ChangeType.ATTRIBUTE_CHANGE
        
        if change_type:
            return VariableChange(
                timestamp=time.time(),
                change_type=change_type,
                variable_name=new_snapshot.name,
                old_value=old_snapshot.value,
                new_value=new_snapshot.value,
                old_type=old_snapshot.type_name,
                new_type=new_snapshot.type_name,
                context={'old_address': old_snapshot.memory_address, 
                        'new_address': new_snapshot.memory_address}
            )
        
        return None

    def _detect_memory_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks by analyzing object growth patterns."""
        if len(self.memory_snapshots) < 10:
            return []
        
        # Analyze recent snapshots for growing object types
        recent_snapshots = list(self.memory_snapshots)[-10:]
        object_growth = defaultdict(list)
        
        for snapshot in recent_snapshots:
            for obj_type, count in snapshot['object_counts'].items():
                object_growth[obj_type].append(count)
        
        # Find object types with consistent growth
        leak_candidates = []
        for obj_type, counts in object_growth.items():
            if len(counts) >= 5:
                # Check if consistently growing
                growth_rate = (counts[-1] - counts[0]) / len(counts)
                if growth_rate > 10:  # Growing by more than 10 objects per snapshot
                    leak_candidates.append({
                        'object_type': obj_type,
                        'growth_rate': growth_rate,
                        'current_count': counts[-1],
                        'start_count': counts[0],
                        'confidence': min(1.0, growth_rate / 100.0)
                    })
        
        return sorted(leak_candidates, key=lambda x: x['confidence'], reverse=True)

    def _calculate_size(self, obj: Any) -> int:
        """Calculate approximate size of an object in bytes."""
        try:
            return sys.getsizeof(obj)
        except Exception:
            return 0

    def _estimate_frame_memory(self, frame: Any) -> int:
        """Estimate memory usage of a stack frame."""
        try:
            total_size = 0
            for value in frame.f_locals.values():
                total_size += self._calculate_size(value)
            return total_size
        except Exception:
            return 0

    def _is_autocad_object(self, obj: Any) -> bool:
        """Check if an object is an AutoCAD COM object."""
        try:
            obj_type = type(obj).__name__
            return (
                'AutoCAD' in obj_type or
                'COM' in obj_type or
                hasattr(obj, 'Application') or
                hasattr(obj, 'ActiveDocument') or
                hasattr(obj, 'ObjectName')
            )
        except Exception:
            return False

    def _safe_repr(self, value: Any, max_length: int = 200) -> str:
        """Get a safe string representation of a value."""
        try:
            repr_str = repr(value)
            if len(repr_str) > max_length:
                return repr_str[:max_length] + '...'
            return repr_str
        except Exception:
            return f'<{type(value).__name__} object at {hex(id(value))}>'

    def _find_snapshot_by_timestamp(self, 
                                   history: deque, 
                                   timestamp: float) -> Optional[VariableSnapshot]:
        """Find the snapshot closest to a given timestamp."""
        closest_entry = None
        min_diff = float('inf')
        
        for entry in history:
            diff = abs(entry['timestamp'] - timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_entry = entry
        
        return closest_entry['snapshot'] if closest_entry else None

    def _diff_attributes(self, 
                        old_attrs: Dict[str, Any], 
                        new_attrs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare two attribute dictionaries and return differences."""
        changes = []
        
        # Find added attributes
        for name, value in new_attrs.items():
            if name not in old_attrs:
                changes.append({
                    'action': 'added',
                    'attribute': name,
                    'new_value': str(value)
                })
        
        # Find removed attributes
        for name, value in old_attrs.items():
            if name not in new_attrs:
                changes.append({
                    'action': 'removed',
                    'attribute': name,
                    'old_value': str(value)
                })
        
        # Find changed attributes
        for name, new_value in new_attrs.items():
            if name in old_attrs and old_attrs[name] != new_value:
                changes.append({
                    'action': 'changed',
                    'attribute': name,
                    'old_value': str(old_attrs[name]),
                    'new_value': str(new_value)
                })
        
        return changes