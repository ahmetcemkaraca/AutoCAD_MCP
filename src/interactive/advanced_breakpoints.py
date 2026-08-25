"""
Advanced Breakpoint Management System
===================================

Enhanced breakpoint management with intelligent features including:
- Smart conditional breakpoints with AutoCAD object state tracking
- Hierarchical breakpoint groups and profiles
- Performance-aware breakpoint optimization
- Automated breakpoint suggestions based on code analysis
- Remote debugging support with synchronization
"""

import logging
import time
import ast
import inspect
import re
from typing import Dict, Any, List, Optional, Set, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import threading
from collections import defaultdict, deque

# Import core debugging components
from .debugger import Breakpoint, BreakpointType, AutoCADDebugger
from ..inspection.object_inspector import ObjectInspector, InspectionDepth
from .secure_evaluator import safe_eval, SecureEvaluationError

logger = logging.getLogger(__name__)


class BreakpointTrigger(Enum):
    """Advanced breakpoint trigger conditions."""
    IMMEDIATE = "immediate"              # Trigger immediately when hit
    COUNT_THRESHOLD = "count_threshold"  # Trigger after N hits
    TIME_INTERVAL = "time_interval"      # Trigger based on time intervals
    VALUE_CHANGE = "value_change"        # Trigger when tracked value changes
    PATTERN_MATCH = "pattern_match"      # Trigger on regex pattern match
    PERFORMANCE_THRESHOLD = "perf_threshold"  # Trigger on performance metrics
    OBJECT_STATE_CHANGE = "obj_state_change"  # Trigger on AutoCAD object changes


class BreakpointPriority(Enum):
    """Breakpoint execution priority levels."""
    CRITICAL = 1    # Always execute, highest priority
    HIGH = 2        # Execute unless resource constraints
    NORMAL = 3      # Standard execution priority
    LOW = 4         # Execute when resources available
    BACKGROUND = 5  # Execute in background only


@dataclass
class BreakpointAction:
    """Actions to execute when breakpoint is triggered."""
    action_type: str  # 'log', 'evaluate', 'inspect', 'notify', 'script'
    action_data: Dict[str, Any]
    enabled: bool = True
    execution_order: int = 0


@dataclass
class BreakpointMetrics:
    """Performance and usage metrics for breakpoints."""
    hit_count: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_hit_timestamp: float = 0.0
    impact_score: float = 0.0  # Performance impact score
    effectiveness_score: float = 0.0  # How useful the breakpoint is


@dataclass
class SmartBreakpoint:
    """Enhanced breakpoint with intelligent features."""
    # Core properties (inherits from base Breakpoint)
    id: str
    type: BreakpointType
    enabled: bool = True
    
    # Advanced properties
    priority: BreakpointPriority = BreakpointPriority.NORMAL
    trigger: BreakpointTrigger = BreakpointTrigger.IMMEDIATE
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    
    # Location and targeting
    filename: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    module_pattern: Optional[str] = None
    
    # Conditions and filters
    condition: Optional[str] = None
    context_filters: List[str] = field(default_factory=list)
    autocad_object_filters: List[str] = field(default_factory=list)
    
    # Actions and behaviors
    actions: List[BreakpointAction] = field(default_factory=list)
    auto_continue: bool = False
    temporary: bool = False
    disabled_after_hits: Optional[int] = None
    
    # Grouping and organization
    group_id: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    description: Optional[str] = None
    
    # Metrics and analysis
    metrics: BreakpointMetrics = field(default_factory=BreakpointMetrics)
    creation_timestamp: float = field(default_factory=time.time)
    created_by: Optional[str] = None
    
    # Advanced features
    learning_enabled: bool = False  # Enable ML-based optimization
    adaptive_conditions: bool = False  # Auto-adjust conditions based on usage


@dataclass
class BreakpointGroup:
    """Group of related breakpoints for batch management."""
    id: str
    name: str
    description: Optional[str] = None
    enabled: bool = True
    breakpoints: Set[str] = field(default_factory=set)
    priority: BreakpointPriority = BreakpointPriority.NORMAL
    tags: Set[str] = field(default_factory=set)
    created_timestamp: float = field(default_factory=time.time)


@dataclass
class BreakpointProfile:
    """Saved configuration profile for breakpoint sets."""
    id: str
    name: str
    description: Optional[str] = None
    breakpoint_configs: List[Dict[str, Any]] = field(default_factory=list)
    groups: List[Dict[str, Any]] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    created_timestamp: float = field(default_factory=time.time)
    version: str = "1.0"


class AdvancedBreakpointManager:
    """
    Advanced breakpoint management system with intelligent features.
    
    Provides enhanced breakpoint capabilities including smart conditions,
    performance optimization, automated suggestions, and profile management.
    """
    
    def __init__(self, debugger: Optional[AutoCADDebugger] = None):
        """
        Initialize advanced breakpoint manager.
        
        Args:
            debugger: AutoCAD debugger instance to integrate with
        """
        self.debugger = debugger
        self.object_inspector = ObjectInspector()
        
        # Breakpoint storage
        self.smart_breakpoints: Dict[str, SmartBreakpoint] = {}
        self.breakpoint_groups: Dict[str, BreakpointGroup] = {}
        self.breakpoint_profiles: Dict[str, BreakpointProfile] = {}
        
        # Performance tracking
        self.execution_metrics: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.performance_history: deque = deque(maxlen=1000)
        
        # Threading and synchronization
        self.lock = threading.RLock()
        self.active_evaluations: Dict[str, threading.Thread] = {}
        
        # Configuration
        self.max_concurrent_evaluations = 5
        self.performance_threshold = 0.1  # seconds
        self.auto_optimization_enabled = True
        self.learning_mode = True
        
        # Code analysis cache
        self.code_analysis_cache: Dict[str, Dict[str, Any]] = {}
        self.suggestion_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        logger.info("Advanced breakpoint manager initialized")

    def create_smart_breakpoint(self,
                              breakpoint_type: str,
                              priority: str = "normal",
                              trigger: str = "immediate",
                              **kwargs) -> str:
        """
        Create an enhanced smart breakpoint with advanced features.
        
        Args:
            breakpoint_type: Type of breakpoint ('line', 'function', etc.)
            priority: Breakpoint priority ('critical', 'high', 'normal', 'low', 'background')
            trigger: Trigger condition ('immediate', 'count_threshold', etc.)
            **kwargs: Additional breakpoint configuration
            
        Returns:
            Breakpoint ID
        """
        with self.lock:
            # Generate unique ID
            bp_id = f"smart_bp_{int(time.time() * 1000000) % 1000000:06d}"
            
            # Parse enums
            try:
                bp_type = BreakpointType(breakpoint_type)
                bp_priority = BreakpointPriority[priority.upper()]
                bp_trigger = BreakpointTrigger(trigger)
            except (ValueError, KeyError) as e:
                raise ValueError(f"Invalid breakpoint parameter: {e}")
            
            # Create smart breakpoint
            smart_bp = SmartBreakpoint(
                id=bp_id,
                type=bp_type,
                priority=bp_priority,
                trigger=bp_trigger,
                **{k: v for k, v in kwargs.items() if hasattr(SmartBreakpoint, k)}
            )
            
            # Configure trigger-specific settings
            self._configure_breakpoint_trigger(smart_bp, kwargs)
            
            # Add default actions based on type
            self._add_default_actions(smart_bp)
            
            # Store breakpoint
            self.smart_breakpoints[bp_id] = smart_bp
            
            # Add to group if specified
            if 'group_id' in kwargs:
                self.add_breakpoint_to_group(bp_id, kwargs['group_id'])
            
            logger.info(f"Created smart breakpoint {bp_id}: {breakpoint_type} with {priority} priority")
            return bp_id

    def create_conditional_breakpoint(self,
                                    filename: str,
                                    line_number: int,
                                    condition: str,
                                    autocad_context: bool = True,
                                    performance_aware: bool = True) -> str:
        """
        Create a conditional breakpoint with AutoCAD context awareness.
        
        Args:
            filename: Source file name
            line_number: Line number for breakpoint
            condition: Python condition expression
            autocad_context: Include AutoCAD objects in condition evaluation
            performance_aware: Enable performance impact monitoring
            
        Returns:
            Breakpoint ID
        """
        # Analyze condition for AutoCAD object references
        autocad_objects = self._extract_autocad_references(condition)
        
        # Create base configuration
        config = {
            'filename': filename,
            'line_number': line_number,
            'condition': condition,
            'autocad_object_filters': autocad_objects,
            'trigger_config': {
                'performance_monitoring': performance_aware,
                'autocad_context': autocad_context
            }
        }
        
        # Add performance monitoring action if enabled
        if performance_aware:
            config['actions'] = [
                BreakpointAction(
                    action_type='performance_check',
                    action_data={'threshold': self.performance_threshold}
                )
            ]
        
        return self.create_smart_breakpoint('conditional', **config)

    def create_function_entry_breakpoint(self,
                                       function_name: str,
                                       class_name: Optional[str] = None,
                                       inspect_parameters: bool = True,
                                       trace_autocad_objects: bool = True) -> str:
        """
        Create a function entry breakpoint with parameter inspection.
        
        Args:
            function_name: Name of function to break on
            class_name: Optional class name for method breakpoints
            inspect_parameters: Automatically inspect function parameters
            trace_autocad_objects: Track AutoCAD objects in parameters
            
        Returns:
            Breakpoint ID
        """
        actions = []
        
        # Add parameter inspection action
        if inspect_parameters:
            actions.append(
                BreakpointAction(
                    action_type='inspect_parameters',
                    action_data={
                        'depth': 'detailed',
                        'autocad_objects': trace_autocad_objects
                    }
                )
            )
        
        # Add call stack logging
        actions.append(
            BreakpointAction(
                action_type='log_call_stack',
                action_data={'max_depth': 10}
            )
        )
        
        config = {
            'function_name': function_name,
            'class_name': class_name,
            'actions': actions,
            'trigger': 'immediate',
            'priority': 'high'
        }
        
        return self.create_smart_breakpoint('function', **config)

    def create_variable_watch_breakpoint(self,
                                       variable_name: str,
                                       watch_expression: str,
                                       change_threshold: Optional[float] = None,
                                       track_autocad_state: bool = True) -> str:
        """
        Create a variable watch breakpoint that triggers on value changes.
        
        Args:
            variable_name: Name of variable to watch
            watch_expression: Expression to evaluate and watch
            change_threshold: Threshold for numeric change detection
            track_autocad_state: Track AutoCAD object state changes
            
        Returns:
            Breakpoint ID
        """
        trigger_config = {
            'expression': watch_expression,
            'change_threshold': change_threshold,
            'autocad_state_tracking': track_autocad_state
        }
        
        actions = [
            BreakpointAction(
                action_type='log_variable_change',
                action_data={
                    'variable_name': variable_name,
                    'expression': watch_expression,
                    'include_autocad_state': track_autocad_state
                }
            )
        ]
        
        config = {
            'variable_name': variable_name,
            'trigger': 'value_change',
            'trigger_config': trigger_config,
            'actions': actions,
            'auto_continue': True  # Don't stop execution by default
        }
        
        return self.create_smart_breakpoint('variable', **config)

    def create_performance_breakpoint(self,
                                    filename: str,
                                    function_name: str,
                                    performance_threshold: float,
                                    metric_type: str = 'execution_time') -> str:
        """
        Create a performance-based breakpoint that triggers on performance issues.
        
        Args:
            filename: Source file name
            function_name: Function to monitor
            performance_threshold: Performance threshold to trigger on
            metric_type: Type of metric ('execution_time', 'memory_usage', 'autocad_calls')
            
        Returns:
            Breakpoint ID
        """
        trigger_config = {
            'metric_type': metric_type,
            'threshold': performance_threshold,
            'measurement_window': 10  # Last 10 calls
        }
        
        actions = [
            BreakpointAction(
                action_type='performance_analysis',
                action_data={
                    'capture_call_stack': True,
                    'capture_variables': True,
                    'capture_autocad_state': True,
                    'generate_optimization_hints': True
                }
            )
        ]
        
        config = {
            'filename': filename,
            'function_name': function_name,
            'trigger': 'performance_threshold',
            'trigger_config': trigger_config,
            'actions': actions,
            'priority': 'high'
        }
        
        return self.create_smart_breakpoint('function', **config)

    def create_breakpoint_group(self, 
                              name: str,
                              description: Optional[str] = None,
                              priority: str = "normal") -> str:
        """
        Create a breakpoint group for batch management.
        
        Args:
            name: Group name
            description: Optional group description
            priority: Group priority level
            
        Returns:
            Group ID
        """
        group_id = f"group_{int(time.time() * 1000) % 1000000:06d}"
        
        try:
            group_priority = BreakpointPriority[priority.upper()]
        except KeyError:
            group_priority = BreakpointPriority.NORMAL
        
        group = BreakpointGroup(
            id=group_id,
            name=name,
            description=description,
            priority=group_priority
        )
        
        self.breakpoint_groups[group_id] = group
        logger.info(f"Created breakpoint group: {name} ({group_id})")
        
        return group_id

    def add_breakpoint_to_group(self, breakpoint_id: str, group_id: str) -> bool:
        """
        Add a breakpoint to a group.
        
        Args:
            breakpoint_id: ID of breakpoint to add
            group_id: ID of group to add to
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            if group_id not in self.breakpoint_groups:
                logger.error(f"Group {group_id} not found")
                return False
                
            if breakpoint_id not in self.smart_breakpoints:
                logger.error(f"Breakpoint {breakpoint_id} not found")
                return False
            
            # Add to group
            self.breakpoint_groups[group_id].breakpoints.add(breakpoint_id)
            
            # Update breakpoint group reference
            self.smart_breakpoints[breakpoint_id].group_id = group_id
            
            logger.info(f"Added breakpoint {breakpoint_id} to group {group_id}")
            return True

    def enable_group(self, group_id: str) -> bool:
        """Enable all breakpoints in a group."""
        return self._set_group_enabled(group_id, True)

    def disable_group(self, group_id: str) -> bool:
        """Disable all breakpoints in a group."""
        return self._set_group_enabled(group_id, False)

    def _set_group_enabled(self, group_id: str, enabled: bool) -> bool:
        """Set enabled state for all breakpoints in a group."""
        with self.lock:
            if group_id not in self.breakpoint_groups:
                return False
            
            group = self.breakpoint_groups[group_id]
            group.enabled = enabled
            
            # Update all breakpoints in group
            for bp_id in group.breakpoints:
                if bp_id in self.smart_breakpoints:
                    self.smart_breakpoints[bp_id].enabled = enabled
            
            action = "enabled" if enabled else "disabled"
            logger.info(f"Group {group_id} {action} with {len(group.breakpoints)} breakpoints")
            return True

    def analyze_code_for_breakpoint_suggestions(self, filename: str) -> List[Dict[str, Any]]:
        """
        Analyze code to suggest optimal breakpoint locations.
        
        Args:
            filename: Python file to analyze
            
        Returns:
            List of breakpoint suggestions with rationale
        """
        # Check cache first
        if filename in self.suggestion_cache:
            cache_time = self.suggestion_cache[filename][0].get('cache_time', 0)
            if time.time() - cache_time < 300:  # 5 minute cache
                return self.suggestion_cache[filename]
        
        suggestions = []
        
        try:
            # Read and parse file
            with open(filename, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code)
            
            # Analyze AST for interesting locations
            analyzer = BreakpointSuggestionAnalyzer()
            analyzer.visit(tree)
            
            # Generate suggestions based on analysis
            for suggestion in analyzer.suggestions:
                suggestion_dict = {
                    'filename': filename,
                    'line_number': suggestion['line_number'],
                    'type': suggestion['type'],
                    'rationale': suggestion['rationale'],
                    'priority': suggestion['priority'],
                    'suggested_config': suggestion.get('config', {}),
                    'cache_time': time.time()
                }
                suggestions.append(suggestion_dict)
            
            # Cache suggestions
            self.suggestion_cache[filename] = suggestions
            
        except Exception as e:
            logger.error(f"Failed to analyze {filename} for breakpoint suggestions: {e}")
            suggestions = [{
                'error': f"Analysis failed: {e}",
                'cache_time': time.time()
            }]
        
        return suggestions

    def optimize_breakpoint_performance(self) -> Dict[str, Any]:
        """
        Analyze and optimize breakpoint performance impact.
        
        Returns:
            Optimization report with recommendations
        """
        with self.lock:
            optimization_report = {
                'timestamp': time.time(),
                'total_breakpoints': len(self.smart_breakpoints),
                'active_breakpoints': 0,
                'performance_issues': [],
                'optimization_actions': [],
                'recommendations': []
            }
            
            high_impact_breakpoints = []
            underused_breakpoints = []
            
            # Analyze each breakpoint
            for bp_id, breakpoint in self.smart_breakpoints.items():
                if not breakpoint.enabled:
                    continue
                    
                optimization_report['active_breakpoints'] += 1
                metrics = breakpoint.metrics
                
                # Check for performance issues
                if metrics.average_execution_time > self.performance_threshold:
                    high_impact_breakpoints.append({
                        'id': bp_id,
                        'type': breakpoint.type.value,
                        'avg_time': metrics.average_execution_time,
                        'hit_count': metrics.hit_count,
                        'impact_score': metrics.impact_score
                    })
                
                # Check for underused breakpoints
                if (metrics.hit_count > 0 and 
                    time.time() - metrics.last_hit_timestamp > 3600 and  # 1 hour
                    metrics.effectiveness_score < 0.3):
                    underused_breakpoints.append({
                        'id': bp_id,
                        'type': breakpoint.type.value,
                        'last_hit': metrics.last_hit_timestamp,
                        'effectiveness': metrics.effectiveness_score
                    })
            
            # Generate optimization actions
            if high_impact_breakpoints:
                optimization_report['performance_issues'] = high_impact_breakpoints
                optimization_report['recommendations'].append(
                    "Consider disabling or optimizing high-impact breakpoints"
                )
            
            if underused_breakpoints:
                optimization_report['recommendations'].append(
                    "Consider removing underused breakpoints to improve performance"
                )
                
                # Auto-optimize if enabled
                if self.auto_optimization_enabled:
                    for bp_info in underused_breakpoints:
                        bp_id = bp_info['id']
                        if bp_id in self.smart_breakpoints:
                            self.smart_breakpoints[bp_id].enabled = False
                            optimization_report['optimization_actions'].append(
                                f"Auto-disabled underused breakpoint {bp_id}"
                            )
            
            return optimization_report

    def export_breakpoint_profile(self, 
                                profile_name: str,
                                include_groups: bool = True,
                                include_metrics: bool = False) -> str:
        """
        Export current breakpoint configuration as a profile.
        
        Args:
            profile_name: Name for the profile
            include_groups: Include breakpoint groups in export
            include_metrics: Include performance metrics
            
        Returns:
            Profile ID
        """
        profile_id = f"profile_{int(time.time() * 1000) % 1000000:06d}"
        
        # Export breakpoint configurations
        breakpoint_configs = []
        for bp_id, breakpoint in self.smart_breakpoints.items():
            config = {
                'type': breakpoint.type.value,
                'priority': breakpoint.priority.name.lower(),
                'trigger': breakpoint.trigger.value,
                'enabled': breakpoint.enabled,
                'filename': breakpoint.filename,
                'line_number': breakpoint.line_number,
                'function_name': breakpoint.function_name,
                'condition': breakpoint.condition,
                'actions': [
                    {
                        'action_type': action.action_type,
                        'action_data': action.action_data,
                        'enabled': action.enabled
                    }
                    for action in breakpoint.actions
                ],
                'tags': list(breakpoint.tags),
                'description': breakpoint.description
            }
            
            if include_metrics:
                config['metrics'] = {
                    'hit_count': breakpoint.metrics.hit_count,
                    'average_execution_time': breakpoint.metrics.average_execution_time,
                    'impact_score': breakpoint.metrics.impact_score,
                    'effectiveness_score': breakpoint.metrics.effectiveness_score
                }
            
            breakpoint_configs.append(config)
        
        # Export groups if requested
        group_configs = []
        if include_groups:
            for group_id, group in self.breakpoint_groups.items():
                group_config = {
                    'name': group.name,
                    'description': group.description,
                    'enabled': group.enabled,
                    'priority': group.priority.name.lower(),
                    'tags': list(group.tags)
                }
                group_configs.append(group_config)
        
        # Create profile
        profile = BreakpointProfile(
            id=profile_id,
            name=profile_name,
            breakpoint_configs=breakpoint_configs,
            groups=group_configs,
            settings={
                'auto_optimization_enabled': self.auto_optimization_enabled,
                'performance_threshold': self.performance_threshold,
                'learning_mode': self.learning_mode
            }
        )
        
        self.breakpoint_profiles[profile_id] = profile
        logger.info(f"Exported breakpoint profile: {profile_name} ({profile_id})")
        
        return profile_id

    def import_breakpoint_profile(self, profile_id: str, merge_mode: str = "replace") -> bool:
        """
        Import breakpoint configuration from a profile.
        
        Args:
            profile_id: Profile ID to import
            merge_mode: How to merge ('replace', 'merge', 'append')
            
        Returns:
            True if successful, False otherwise
        """
        if profile_id not in self.breakpoint_profiles:
            logger.error(f"Profile {profile_id} not found")
            return False
        
        profile = self.breakpoint_profiles[profile_id]
        
        with self.lock:
            # Handle merge mode
            if merge_mode == "replace":
                self.smart_breakpoints.clear()
                self.breakpoint_groups.clear()
            
            # Import breakpoints
            for bp_config in profile.breakpoint_configs:
                try:
                    # Create breakpoint from config
                    bp_id = self.create_smart_breakpoint(**bp_config)
                    
                    # Restore metrics if available
                    if 'metrics' in bp_config and bp_id in self.smart_breakpoints:
                        metrics_data = bp_config['metrics']
                        breakpoint = self.smart_breakpoints[bp_id]
                        breakpoint.metrics.hit_count = metrics_data.get('hit_count', 0)
                        breakpoint.metrics.average_execution_time = metrics_data.get('average_execution_time', 0.0)
                        breakpoint.metrics.impact_score = metrics_data.get('impact_score', 0.0)
                        breakpoint.metrics.effectiveness_score = metrics_data.get('effectiveness_score', 0.0)
                        
                except Exception as e:
                    logger.error(f"Failed to import breakpoint from profile: {e}")
            
            # Import groups
            for group_config in profile.groups:
                try:
                    self.create_breakpoint_group(**group_config)
                except Exception as e:
                    logger.error(f"Failed to import group from profile: {e}")
            
            # Apply settings
            settings = profile.settings
            self.auto_optimization_enabled = settings.get('auto_optimization_enabled', self.auto_optimization_enabled)
            self.performance_threshold = settings.get('performance_threshold', self.performance_threshold)
            self.learning_mode = settings.get('learning_mode', self.learning_mode)
        
        logger.info(f"Imported breakpoint profile: {profile.name}")
        return True

    def get_breakpoint_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive analytics about breakpoint usage and performance.
        
        Returns:
            Analytics report
        """
        with self.lock:
            analytics = {
                'timestamp': time.time(),
                'summary': {
                    'total_breakpoints': len(self.smart_breakpoints),
                    'active_breakpoints': sum(1 for bp in self.smart_breakpoints.values() if bp.enabled),
                    'total_groups': len(self.breakpoint_groups),
                    'total_profiles': len(self.breakpoint_profiles)
                },
                'type_distribution': defaultdict(int),
                'priority_distribution': defaultdict(int),
                'trigger_distribution': defaultdict(int),
                'performance_metrics': {
                    'total_hits': 0,
                    'total_execution_time': 0.0,
                    'average_execution_time': 0.0,
                    'high_impact_count': 0
                },
                'top_performers': [],
                'problem_breakpoints': []
            }
            
            total_hits = 0
            total_time = 0.0
            high_impact_threshold = self.performance_threshold * 2
            
            # Analyze each breakpoint
            for bp_id, breakpoint in self.smart_breakpoints.items():
                # Count distributions
                analytics['type_distribution'][breakpoint.type.value] += 1
                analytics['priority_distribution'][breakpoint.priority.name] += 1
                analytics['trigger_distribution'][breakpoint.trigger.value] += 1
                
                # Performance metrics
                metrics = breakpoint.metrics
                total_hits += metrics.hit_count
                total_time += metrics.total_execution_time
                
                if metrics.average_execution_time > high_impact_threshold:
                    analytics['performance_metrics']['high_impact_count'] += 1
                    analytics['problem_breakpoints'].append({
                        'id': bp_id,
                        'type': breakpoint.type.value,
                        'avg_time': metrics.average_execution_time,
                        'hit_count': metrics.hit_count,
                        'impact_score': metrics.impact_score
                    })
                
                # Top performers (effective breakpoints)
                if metrics.effectiveness_score > 0.7 and metrics.hit_count > 5:
                    analytics['top_performers'].append({
                        'id': bp_id,
                        'type': breakpoint.type.value,
                        'effectiveness': metrics.effectiveness_score,
                        'hit_count': metrics.hit_count
                    })
            
            # Calculate overall metrics
            analytics['performance_metrics']['total_hits'] = total_hits
            analytics['performance_metrics']['total_execution_time'] = total_time
            if total_hits > 0:
                analytics['performance_metrics']['average_execution_time'] = total_time / total_hits
            
            # Sort results
            analytics['top_performers'].sort(key=lambda x: x['effectiveness'], reverse=True)
            analytics['problem_breakpoints'].sort(key=lambda x: x['impact_score'], reverse=True)
            
            return analytics

    def _configure_breakpoint_trigger(self, breakpoint: SmartBreakpoint, config: Dict[str, Any]):
        """Configure trigger-specific settings for a breakpoint."""
        trigger_config = config.get('trigger_config', {})
        
        if breakpoint.trigger == BreakpointTrigger.COUNT_THRESHOLD:
            trigger_config.setdefault('threshold', 10)
        elif breakpoint.trigger == BreakpointTrigger.TIME_INTERVAL:
            trigger_config.setdefault('interval', 1.0)
        elif breakpoint.trigger == BreakpointTrigger.PERFORMANCE_THRESHOLD:
            trigger_config.setdefault('metric_type', 'execution_time')
            trigger_config.setdefault('threshold', self.performance_threshold)
        
        breakpoint.trigger_config = trigger_config

    def _add_default_actions(self, breakpoint: SmartBreakpoint):
        """Add default actions based on breakpoint type and configuration."""
        if not breakpoint.actions:
            # Add basic logging action
            breakpoint.actions.append(
                BreakpointAction(
                    action_type='log',
                    action_data={
                        'message': f'Breakpoint {breakpoint.id} hit',
                        'include_context': True
                    }
                )
            )
            
            # Add context inspection for high priority breakpoints
            if breakpoint.priority in [BreakpointPriority.CRITICAL, BreakpointPriority.HIGH]:
                breakpoint.actions.append(
                    BreakpointAction(
                        action_type='inspect_context',
                        action_data={'depth': 'detailed'},
                        execution_order=1
                    )
                )

    def _extract_autocad_references(self, condition: str) -> List[str]:
        """Extract AutoCAD object references from a condition expression."""
        # Simple pattern matching for common AutoCAD object patterns
        patterns = [
            r'\b(acad_app|application)\b',
            r'\b(active_document|doc)\b',
            r'\b(model_space|paper_space)\b',
            r'\b(selection_set|sel_set)\b',
            r'\b(block_table|layer_table)\b'
        ]
        
        references = []
        for pattern in patterns:
            matches = re.findall(pattern, condition, re.IGNORECASE)
            references.extend(matches)
        
        return list(set(references))  # Remove duplicates


class BreakpointSuggestionAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze code and suggest breakpoint locations."""
    
    def __init__(self):
        self.suggestions = []
        self.current_line = 1
        self.in_function = False
        self.function_depth = 0
        
    def visit_FunctionDef(self, node):
        """Analyze function definitions for breakpoint suggestions."""
        self.in_function = True
        self.function_depth += 1
        
        # Suggest function entry breakpoint
        self.suggestions.append({
            'line_number': node.lineno,
            'type': 'function_entry',
            'rationale': f'Function entry point: {node.name}',
            'priority': 'normal',
            'config': {
                'function_name': node.name,
                'inspect_parameters': True
            }
        })
        
        # Look for complex functions (many lines or branches)
        if len(node.body) > 20:
            self.suggestions.append({
                'line_number': node.lineno + len(node.body) // 2,
                'type': 'line',
                'rationale': f'Mid-point of complex function: {node.name}',
                'priority': 'low'
            })
        
        self.generic_visit(node)
        self.function_depth -= 1
        if self.function_depth == 0:
            self.in_function = False
    
    def visit_For(self, node):
        """Suggest breakpoints for loop constructs."""
        self.suggestions.append({
            'line_number': node.lineno,
            'type': 'line',
            'rationale': 'Loop entry point - useful for iteration debugging',
            'priority': 'normal'
        })
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Suggest breakpoints for while loops."""
        self.suggestions.append({
            'line_number': node.lineno,
            'type': 'line',
            'rationale': 'While loop entry - monitor loop conditions',
            'priority': 'normal'
        })
        self.generic_visit(node)
    
    def visit_Try(self, node):
        """Suggest breakpoints for exception handling."""
        self.suggestions.append({
            'line_number': node.lineno,
            'type': 'line',
            'rationale': 'Try block - monitor exception-prone code',
            'priority': 'high'
        })
        
        # Suggest breakpoints in exception handlers
        for handler in node.handlers:
            self.suggestions.append({
                'line_number': handler.lineno,
                'type': 'line',
                'rationale': f'Exception handler: {handler.type.id if handler.type else "all"}',
                'priority': 'high'
            })
        
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Analyze function calls for AutoCAD-related breakpoints."""
        if hasattr(node.func, 'attr'):
            # Look for potential AutoCAD method calls
            autocad_patterns = ['Add', 'Insert', 'Delete', 'Modify', 'Select']
            if any(pattern in str(node.func.attr) for pattern in autocad_patterns):
                self.suggestions.append({
                    'line_number': node.lineno,
                    'type': 'line',
                    'rationale': f'AutoCAD operation: {node.func.attr}',
                    'priority': 'high',
                    'config': {
                        'trace_autocad_objects': True
                    }
                })
        
        self.generic_visit(node)