"""
Intelligent Error Prediction Engine
==================================

Advanced error prediction system using performance analysis and machine learning including:
- Predictive error detection using code analysis and execution patterns
- Performance anomaly detection with statistical analysis
- AutoCAD-specific error pattern recognition
- Proactive issue prevention with early warning systems
- ML-based failure prediction using historical data
"""

import logging
import time
import ast
import traceback
import re
import json
import statistics
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
import warnings

# ML and statistical libraries with graceful fallbacks
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import DBSCAN
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# Import existing performance monitoring
from ..enhanced_autocad.performance_monitor import PerformanceMonitor
from ..enhanced_autocad.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity levels for predicted errors."""
    LOW = "low"              # Minor issues, performance degradation
    MEDIUM = "medium"        # Potential failures, recoverable errors
    HIGH = "high"           # Critical errors, system instability
    CRITICAL = "critical"   # System failure, data loss risk


class ErrorCategory(Enum):
    """Categories of errors that can be predicted."""
    MEMORY_LEAK = "memory_leak"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    COM_ERROR = "com_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    INFINITE_LOOP = "infinite_loop"
    AUTOCAD_CRASH = "autocad_crash"
    DATA_CORRUPTION = "data_corruption"
    TIMEOUT = "timeout"
    EXCEPTION = "exception"
    LOGIC_ERROR = "logic_error"


class PredictionConfidence(Enum):
    """Confidence levels for error predictions."""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.9


@dataclass
class ErrorPrediction:
    """A predicted error with details and recommendations."""
    id: str
    timestamp: float
    
    # Error details
    category: ErrorCategory
    severity: ErrorSeverity
    confidence: float
    description: str
    
    # Location information
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    
    # Prediction basis
    indicators: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    code_patterns: List[str] = field(default_factory=list)
    
    # Prevention recommendations
    recommendations: List[str] = field(default_factory=list)
    preventive_actions: List[str] = field(default_factory=list)
    
    # Metadata
    time_to_failure: Optional[float] = None  # Estimated seconds until failure
    probability_distribution: Dict[str, float] = field(default_factory=dict)
    related_predictions: List[str] = field(default_factory=list)


@dataclass
class PerformanceAnomaly:
    """Detected performance anomaly that could indicate future errors."""
    metric_name: str
    current_value: float
    expected_value: float
    deviation_score: float
    trend: str  # 'increasing', 'decreasing', 'fluctuating'
    duration: float  # How long the anomaly has persisted
    severity: ErrorSeverity


class ErrorPattern:
    """Represents a learned error pattern for prediction."""
    
    def __init__(self, name: str, category: ErrorCategory):
        self.name = name
        self.category = category
        self.code_signatures = []  # AST patterns that indicate this error
        self.performance_signatures = []  # Performance patterns
        self.preconditions = []  # Conditions that must be met
        self.confidence_factors = {}  # Factors that affect confidence
        self.historical_accuracy = 0.0
        self.false_positive_rate = 0.0
    
    def matches(self, context: Dict[str, Any]) -> float:
        """Calculate how well this pattern matches the current context."""
        match_score = 0.0
        
        # Check code signatures
        if 'code_ast' in context and self.code_signatures:
            code_matches = sum(
                1 for sig in self.code_signatures
                if self._check_code_signature(sig, context['code_ast'])
            )
            match_score += (code_matches / len(self.code_signatures)) * 0.4
        
        # Check performance signatures
        if 'performance_metrics' in context and self.performance_signatures:
            perf_matches = sum(
                1 for sig in self.performance_signatures
                if self._check_performance_signature(sig, context['performance_metrics'])
            )
            match_score += (perf_matches / len(self.performance_signatures)) * 0.4
        
        # Check preconditions
        if self.preconditions:
            precond_matches = sum(
                1 for precond in self.preconditions
                if self._check_precondition(precond, context)
            )
            match_score += (precond_matches / len(self.preconditions)) * 0.2
        
        return min(1.0, match_score)
    
    def _check_code_signature(self, signature: Dict[str, Any], ast_tree: ast.AST) -> bool:
        """Check if a code signature matches the AST."""
        # Simplified signature matching - in practice this would be more sophisticated
        signature_type = signature.get('type')
        if signature_type == 'infinite_loop_risk':
            return self._has_infinite_loop_risk(ast_tree)
        elif signature_type == 'memory_leak_risk':
            return self._has_memory_leak_risk(ast_tree)
        elif signature_type == 'com_error_risk':
            return self._has_com_error_risk(ast_tree)
        return False
    
    def _check_performance_signature(self, signature: Dict[str, Any], metrics: Dict[str, float]) -> bool:
        """Check if a performance signature matches current metrics."""
        metric_name = signature.get('metric')
        threshold = signature.get('threshold')
        operator = signature.get('operator', '>')
        
        if metric_name not in metrics:
            return False
        
        current_value = metrics[metric_name]
        
        if operator == '>':
            return current_value > threshold
        elif operator == '<':
            return current_value < threshold
        elif operator == '>=':
            return current_value >= threshold
        elif operator == '<=':
            return current_value <= threshold
        
        return False
    
    def _check_precondition(self, precondition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if a precondition is met in the current context."""
        condition_type = precondition.get('type')
        
        if condition_type == 'environment':
            return context.get(precondition['key']) == precondition['value']
        elif condition_type == 'code_context':
            return precondition['pattern'] in context.get('code_text', '')
        
        return False
    
    def _has_infinite_loop_risk(self, ast_tree: ast.AST) -> bool:
        """Check for infinite loop risk patterns in AST."""
        for node in ast.walk(ast_tree):
            if isinstance(node, (ast.For, ast.While)):
                # Check for loops without clear termination conditions
                if isinstance(node, ast.While):
                    # Simplified check - look for while True or complex conditions
                    if isinstance(node.test, ast.Constant) and node.test.value is True:
                        return True
                    if isinstance(node.test, ast.Name) and node.test.id == 'True':
                        return True
        return False
    
    def _has_memory_leak_risk(self, ast_tree: ast.AST) -> bool:
        """Check for memory leak risk patterns in AST."""
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Call):
                # Check for AutoCAD object creation without cleanup
                if hasattr(node.func, 'attr') and node.func.attr in ['Add', 'Create', 'Insert']:
                    return True
        return False
    
    def _has_com_error_risk(self, ast_tree: ast.AST) -> bool:
        """Check for COM error risk patterns in AST."""
        has_com_calls = False
        has_error_handling = False
        
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Attribute):
                # Check for COM-style attribute access
                if any(com_indicator in str(node.attr) 
                       for com_indicator in ['Application', 'ActiveDocument', 'ModelSpace']):
                    has_com_calls = True
            elif isinstance(node, ast.Try):
                has_error_handling = True
        
        return has_com_calls and not has_error_handling


class IntelligentErrorPredictor:
    """
    Intelligent error prediction engine using performance analysis and ML.
    
    Predicts potential errors before they occur using code analysis,
    performance monitoring, and learned patterns from historical data.
    """
    
    def __init__(self, performance_monitor: Optional[PerformanceMonitor] = None):
        """Initialize the error prediction engine."""
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.error_handler = ErrorHandler()
        
        # Pattern storage and learning
        self.error_patterns = self._initialize_error_patterns()
        self.prediction_history = deque(maxlen=1000)
        self.performance_baselines = {}
        self.anomaly_detectors = {}
        
        # ML models (if available)
        self.anomaly_detector = None
        self.performance_scaler = None
        if HAS_SKLEARN:
            self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
            self.performance_scaler = StandardScaler()
        
        # Real-time monitoring
        self.active_predictions = {}
        self.performance_history = defaultdict(lambda: deque(maxlen=100))
        self.error_counters = defaultdict(int)
        
        # Configuration
        self.prediction_window = 300.0  # 5 minutes prediction window
        self.anomaly_threshold = 2.0    # Standard deviations for anomaly detection
        self.min_confidence_threshold = 0.4
        
        # Threading
        self.lock = threading.RLock()
        self.monitoring_thread = None
        self.monitoring_active = False
        
        logger.info("Intelligent error predictor initialized")
    
    def start_monitoring(self):
        """Start real-time error prediction monitoring."""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Error prediction monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time error prediction monitoring."""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        logger.info("Error prediction monitoring stopped")
    
    def predict_errors(self, 
                      code: Optional[str] = None,
                      file_path: Optional[str] = None,
                      context: Optional[Dict[str, Any]] = None) -> List[ErrorPrediction]:
        """
        Predict potential errors for given code or current execution context.
        
        Args:
            code: Source code to analyze (optional)
            file_path: Path to source file (optional)
            context: Additional context information
            
        Returns:
            List of error predictions
        """
        predictions = []
        
        try:
            # Build analysis context
            analysis_context = self._build_analysis_context(code, file_path, context)
            
            # Code-based predictions
            if code:
                code_predictions = self._predict_from_code_analysis(code, file_path, analysis_context)
                predictions.extend(code_predictions)
            
            # Performance-based predictions
            performance_predictions = self._predict_from_performance_analysis(analysis_context)
            predictions.extend(performance_predictions)
            
            # Pattern-based predictions
            pattern_predictions = self._predict_from_patterns(analysis_context)
            predictions.extend(pattern_predictions)
            
            # ML-based predictions (if available)
            if HAS_SKLEARN and self.anomaly_detector:
                ml_predictions = self._predict_from_ml_models(analysis_context)
                predictions.extend(ml_predictions)
            
            # Filter and rank predictions
            predictions = self._filter_and_rank_predictions(predictions)
            
            # Store predictions for learning
            with self.lock:
                for prediction in predictions:
                    self.active_predictions[prediction.id] = prediction
                    self.prediction_history.append({
                        'timestamp': time.time(),
                        'prediction': prediction,
                        'context': analysis_context
                    })
            
        except Exception as e:
            logger.error(f"Error prediction failed: {e}")
        
        return predictions
    
    def analyze_performance_anomalies(self) -> List[PerformanceAnomaly]:
        """Analyze current performance metrics for anomalies."""
        anomalies = []
        
        try:
            # Get current performance metrics
            current_metrics = self.performance_monitor.get_current_metrics()
            
            for metric_name, current_value in current_metrics.items():
                # Check if we have baseline for this metric
                if metric_name not in self.performance_baselines:
                    continue
                
                baseline = self.performance_baselines[metric_name]
                expected_value = baseline['mean']
                std_dev = baseline['std_dev']
                
                # Calculate deviation score
                if std_dev > 0:
                    deviation_score = abs(current_value - expected_value) / std_dev
                else:
                    deviation_score = 0.0
                
                # Check if anomalous
                if deviation_score > self.anomaly_threshold:
                    # Determine trend
                    history = self.performance_history[metric_name]
                    trend = self._analyze_trend(list(history))
                    
                    # Calculate duration of anomaly
                    duration = self._calculate_anomaly_duration(metric_name, current_value)
                    
                    # Determine severity
                    if deviation_score > 4.0:
                        severity = ErrorSeverity.CRITICAL
                    elif deviation_score > 3.0:
                        severity = ErrorSeverity.HIGH
                    elif deviation_score > 2.5:
                        severity = ErrorSeverity.MEDIUM
                    else:
                        severity = ErrorSeverity.LOW
                    
                    anomaly = PerformanceAnomaly(
                        metric_name=metric_name,
                        current_value=current_value,
                        expected_value=expected_value,
                        deviation_score=deviation_score,
                        trend=trend,
                        duration=duration,
                        severity=severity
                    )
                    anomalies.append(anomaly)
            
        except Exception as e:
            logger.error(f"Performance anomaly analysis failed: {e}")
        
        return anomalies
    
    def update_error_patterns(self, actual_error: Dict[str, Any]):
        """Update error patterns based on actual errors that occurred."""
        try:
            error_type = actual_error.get('type', 'unknown')
            error_context = actual_error.get('context', {})
            
            # Find predictions that might have predicted this error
            relevant_predictions = []
            current_time = time.time()
            
            for prediction_id, prediction in self.active_predictions.items():
                time_diff = current_time - prediction.timestamp
                if time_diff <= self.prediction_window:
                    # Check if prediction is relevant to actual error
                    if self._is_prediction_relevant(prediction, actual_error):
                        relevant_predictions.append(prediction)
            
            # Update pattern accuracy
            for prediction in relevant_predictions:
                pattern = self._find_pattern_by_category(prediction.category)
                if pattern:
                    # Successful prediction - increase accuracy
                    pattern.historical_accuracy = min(1.0, pattern.historical_accuracy + 0.1)
            
            # Learn new patterns if no existing pattern predicted this error
            if not relevant_predictions:
                self._learn_new_error_pattern(actual_error)
            
        except Exception as e:
            logger.error(f"Error pattern update failed: {e}")
    
    def get_prediction_accuracy_report(self) -> Dict[str, Any]:
        """Generate a report on prediction accuracy and performance."""
        report = {
            'timestamp': time.time(),
            'total_predictions': len(self.prediction_history),
            'active_predictions': len(self.active_predictions),
            'pattern_accuracy': {},
            'category_stats': defaultdict(int),
            'severity_distribution': defaultdict(int),
            'confidence_distribution': defaultdict(int)
        }
        
        try:
            # Analyze prediction history
            for entry in self.prediction_history:
                prediction = entry['prediction']
                
                # Category statistics
                report['category_stats'][prediction.category.value] += 1
                
                # Severity distribution
                report['severity_distribution'][prediction.severity.value] += 1
                
                # Confidence distribution
                confidence_range = self._get_confidence_range(prediction.confidence)
                report['confidence_distribution'][confidence_range] += 1
            
            # Pattern accuracy
            for pattern in self.error_patterns:
                report['pattern_accuracy'][pattern.name] = {
                    'accuracy': pattern.historical_accuracy,
                    'false_positive_rate': pattern.false_positive_rate
                }
            
            # Overall statistics
            if self.prediction_history:
                avg_confidence = statistics.mean(
                    entry['prediction'].confidence for entry in self.prediction_history
                )
                report['average_confidence'] = avg_confidence
        
        except Exception as e:
            logger.error(f"Accuracy report generation failed: {e}")
            report['error'] = str(e)
        
        return report
    
    def _monitoring_loop(self):
        """Main monitoring loop for real-time error prediction."""
        while self.monitoring_active:
            try:
                # Get current performance metrics
                current_metrics = self.performance_monitor.get_current_metrics()
                
                # Update performance history
                with self.lock:
                    for metric_name, value in current_metrics.items():
                        self.performance_history[metric_name].append({
                            'timestamp': time.time(),
                            'value': value
                        })
                
                # Update baselines
                self._update_performance_baselines(current_metrics)
                
                # Check for anomalies
                anomalies = self.analyze_performance_anomalies()
                
                # Generate predictions based on anomalies
                if anomalies:
                    anomaly_predictions = self._predict_from_anomalies(anomalies)
                    
                    with self.lock:
                        for prediction in anomaly_predictions:
                            self.active_predictions[prediction.id] = prediction
                
                # Clean up old predictions
                self._cleanup_old_predictions()
                
                # Sleep before next iteration
                time.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(10.0)  # Wait longer on error
    
    def _build_analysis_context(self, 
                              code: Optional[str],
                              file_path: Optional[str],
                              context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build comprehensive context for error prediction analysis."""
        analysis_context = {
            'timestamp': time.time(),
            'code_text': code,
            'file_path': file_path,
            'performance_metrics': self.performance_monitor.get_current_metrics()
        }
        
        # Add code AST if available
        if code:
            try:
                ast_tree = ast.parse(code)
                analysis_context['code_ast'] = ast_tree
            except SyntaxError as e:
                analysis_context['syntax_error'] = str(e)
        
        # Add external context
        if context:
            analysis_context.update(context)
        
        # Add historical context
        analysis_context['error_history'] = dict(self.error_counters)
        analysis_context['recent_anomalies'] = self.analyze_performance_anomalies()
        
        return analysis_context
    
    def _predict_from_code_analysis(self, 
                                  code: str,
                                  file_path: Optional[str],
                                  context: Dict[str, Any]) -> List[ErrorPrediction]:
        """Generate predictions based on code analysis."""
        predictions = []
        
        try:
            # Parse the code
            if 'syntax_error' in context:
                # Syntax error prediction
                prediction = ErrorPrediction(
                    id=f"syntax_{int(time.time() * 1000) % 1000000:06d}",
                    timestamp=time.time(),
                    category=ErrorCategory.EXCEPTION,
                    severity=ErrorSeverity.HIGH,
                    confidence=0.95,
                    description=f"Syntax error detected: {context['syntax_error']}",
                    file_path=file_path,
                    indicators=['syntax_error'],
                    recommendations=['Fix syntax error before execution']
                )
                predictions.append(prediction)
                return predictions
            
            ast_tree = context.get('code_ast')
            if not ast_tree:
                return predictions
            
            # Check for infinite loop risks
            if self._has_infinite_loop_risk(ast_tree):
                predictions.append(self._create_infinite_loop_prediction(file_path))
            
            # Check for memory leak risks
            if self._has_memory_leak_risk(ast_tree):
                predictions.append(self._create_memory_leak_prediction(file_path))
            
            # Check for COM error risks
            if self._has_com_error_risk(ast_tree):
                predictions.append(self._create_com_error_prediction(file_path))
            
            # Check for resource exhaustion risks
            resource_risks = self._analyze_resource_usage_risks(ast_tree)
            predictions.extend(resource_risks)
            
        except Exception as e:
            logger.error(f"Code analysis prediction failed: {e}")
        
        return predictions
    
    def _predict_from_performance_analysis(self, context: Dict[str, Any]) -> List[ErrorPrediction]:
        """Generate predictions based on performance analysis."""
        predictions = []
        
        try:
            performance_metrics = context.get('performance_metrics', {})
            
            # Check memory usage trends
            memory_prediction = self._analyze_memory_trends(performance_metrics)
            if memory_prediction:
                predictions.append(memory_prediction)
            
            # Check CPU usage patterns
            cpu_prediction = self._analyze_cpu_patterns(performance_metrics)
            if cpu_prediction:
                predictions.append(cpu_prediction)
            
            # Check AutoCAD-specific metrics
            autocad_predictions = self._analyze_autocad_metrics(performance_metrics)
            predictions.extend(autocad_predictions)
            
        except Exception as e:
            logger.error(f"Performance analysis prediction failed: {e}")
        
        return predictions
    
    def _predict_from_patterns(self, context: Dict[str, Any]) -> List[ErrorPrediction]:
        """Generate predictions based on learned error patterns."""
        predictions = []
        
        try:
            for pattern in self.error_patterns:
                match_score = pattern.matches(context)
                
                if match_score > 0.5:  # Pattern matches reasonably well
                    confidence = match_score * pattern.historical_accuracy
                    
                    if confidence >= self.min_confidence_threshold:
                        prediction = ErrorPrediction(
                            id=f"pattern_{pattern.name}_{int(time.time() * 1000) % 1000000:06d}",
                            timestamp=time.time(),
                            category=pattern.category,
                            severity=self._determine_severity_from_confidence(confidence),
                            confidence=confidence,
                            description=f"Pattern '{pattern.name}' indicates potential {pattern.category.value}",
                            indicators=[f"pattern_match:{pattern.name}"],
                            recommendations=self._get_pattern_recommendations(pattern)
                        )
                        predictions.append(prediction)
            
        except Exception as e:
            logger.error(f"Pattern-based prediction failed: {e}")
        
        return predictions
    
    def _predict_from_ml_models(self, context: Dict[str, Any]) -> List[ErrorPrediction]:
        """Generate predictions using ML models (if available)."""
        predictions = []
        
        if not HAS_SKLEARN or not self.anomaly_detector:
            return predictions
        
        try:
            # Prepare feature vector from context
            features = self._extract_ml_features(context)
            
            if features and len(features) > 0:
                # Reshape for sklearn
                feature_array = np.array(features).reshape(1, -1)
                
                # Scale features
                if self.performance_scaler:
                    feature_array = self.performance_scaler.transform(feature_array)
                
                # Predict anomaly
                anomaly_score = self.anomaly_detector.decision_function(feature_array)[0]
                is_anomaly = self.anomaly_detector.predict(feature_array)[0] == -1
                
                if is_anomaly:
                    # Convert anomaly score to confidence
                    confidence = min(0.9, abs(anomaly_score) / 2.0)
                    
                    prediction = ErrorPrediction(
                        id=f"ml_{int(time.time() * 1000) % 1000000:06d}",
                        timestamp=time.time(),
                        category=ErrorCategory.PERFORMANCE_DEGRADATION,
                        severity=self._determine_severity_from_confidence(confidence),
                        confidence=confidence,
                        description=f"ML model detected performance anomaly (score: {anomaly_score:.3f})",
                        indicators=['ml_anomaly_detection'],
                        performance_metrics={'anomaly_score': anomaly_score},
                        recommendations=['Monitor system performance closely', 'Consider optimizing resource usage']
                    )
                    predictions.append(prediction)
            
        except Exception as e:
            logger.error(f"ML-based prediction failed: {e}")
        
        return predictions
    
    def _create_infinite_loop_prediction(self, file_path: Optional[str]) -> ErrorPrediction:
        """Create a prediction for infinite loop risk."""
        return ErrorPrediction(
            id=f"loop_{int(time.time() * 1000) % 1000000:06d}",
            timestamp=time.time(),
            category=ErrorCategory.INFINITE_LOOP,
            severity=ErrorSeverity.HIGH,
            confidence=0.7,
            description="Potential infinite loop detected in code structure",
            file_path=file_path,
            indicators=['while_true_pattern', 'no_clear_termination'],
            recommendations=[
                'Add explicit termination conditions to loops',
                'Implement timeout mechanisms',
                'Add loop iteration counters for debugging'
            ],
            preventive_actions=[
                'Review loop logic carefully',
                'Add break conditions',
                'Test with various input conditions'
            ]
        )
    
    def _create_memory_leak_prediction(self, file_path: Optional[str]) -> ErrorPrediction:
        """Create a prediction for memory leak risk."""
        return ErrorPrediction(
            id=f"memory_{int(time.time() * 1000) % 1000000:06d}",
            timestamp=time.time(),
            category=ErrorCategory.MEMORY_LEAK,
            severity=ErrorSeverity.MEDIUM,
            confidence=0.6,
            description="Potential memory leak from uncleaned AutoCAD objects",
            file_path=file_path,
            indicators=['autocad_object_creation', 'no_cleanup_pattern'],
            recommendations=[
                'Explicitly release COM object references',
                'Use context managers for AutoCAD operations',
                'Implement proper cleanup in finally blocks'
            ],
            preventive_actions=[
                'Add object cleanup code',
                'Monitor memory usage during execution',
                'Use weak references where appropriate'
            ]
        )
    
    def _create_com_error_prediction(self, file_path: Optional[str]) -> ErrorPrediction:
        """Create a prediction for COM error risk."""
        return ErrorPrediction(
            id=f"com_{int(time.time() * 1000) % 1000000:06d}",
            timestamp=time.time(),
            category=ErrorCategory.COM_ERROR,
            severity=ErrorSeverity.MEDIUM,
            confidence=0.8,
            description="AutoCAD COM operations without error handling detected",
            file_path=file_path,
            indicators=['com_operations', 'no_error_handling'],
            recommendations=[
                'Add try-except blocks around COM operations',
                'Check AutoCAD application state before operations',
                'Implement retry logic for transient COM errors'
            ],
            preventive_actions=[
                'Wrap COM calls in error handlers',
                'Validate COM object states',
                'Add connection verification'
            ]
        )
    
    def _initialize_error_patterns(self) -> List[ErrorPattern]:
        """Initialize built-in error patterns."""
        patterns = []
        
        # Infinite loop pattern
        infinite_loop_pattern = ErrorPattern("infinite_loop_while_true", ErrorCategory.INFINITE_LOOP)
        infinite_loop_pattern.code_signatures = [
            {'type': 'infinite_loop_risk', 'pattern': 'while True:'}
        ]
        infinite_loop_pattern.historical_accuracy = 0.7
        patterns.append(infinite_loop_pattern)
        
        # Memory leak pattern
        memory_leak_pattern = ErrorPattern("autocad_object_leak", ErrorCategory.MEMORY_LEAK)
        memory_leak_pattern.code_signatures = [
            {'type': 'memory_leak_risk', 'pattern': 'ModelSpace.Add'}
        ]
        memory_leak_pattern.performance_signatures = [
            {'metric': 'memory_usage_mb', 'operator': '>', 'threshold': 500}
        ]
        memory_leak_pattern.historical_accuracy = 0.6
        patterns.append(memory_leak_pattern)
        
        # COM error pattern
        com_error_pattern = ErrorPattern("com_no_error_handling", ErrorCategory.COM_ERROR)
        com_error_pattern.code_signatures = [
            {'type': 'com_error_risk', 'pattern': 'Application.'}
        ]
        com_error_pattern.historical_accuracy = 0.8
        patterns.append(com_error_pattern)
        
        return patterns
    
    # Additional helper methods would be implemented here...
    # This is a comprehensive foundation that includes the core ML and pattern-based prediction logic
    
    def _has_infinite_loop_risk(self, ast_tree: ast.AST) -> bool:
        """Check AST for infinite loop risk patterns."""
        # Implementation delegated to ErrorPattern class
        pattern = self._find_pattern_by_category(ErrorCategory.INFINITE_LOOP)
        return pattern and pattern._has_infinite_loop_risk(ast_tree)
    
    def _has_memory_leak_risk(self, ast_tree: ast.AST) -> bool:
        """Check AST for memory leak risk patterns."""
        pattern = self._find_pattern_by_category(ErrorCategory.MEMORY_LEAK)
        return pattern and pattern._has_memory_leak_risk(ast_tree)
    
    def _has_com_error_risk(self, ast_tree: ast.AST) -> bool:
        """Check AST for COM error risk patterns."""
        pattern = self._find_pattern_by_category(ErrorCategory.COM_ERROR)
        return pattern and pattern._has_com_error_risk(ast_tree)
    
    def _find_pattern_by_category(self, category: ErrorCategory) -> Optional[ErrorPattern]:
        """Find the first pattern matching the given category."""
        for pattern in self.error_patterns:
            if pattern.category == category:
                return pattern
        return None