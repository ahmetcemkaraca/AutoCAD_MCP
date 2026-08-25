"""
Advanced Monitoring Dashboard with Analytics
==========================================

Enterprise-grade monitoring and analytics dashboard providing comprehensive insights including:
- Real-time system performance monitoring with interactive dashboards
- Advanced metrics collection and aggregation from all system components
- Predictive analytics and anomaly detection for proactive issue resolution
- Custom alerting system with intelligent notification routing
- Historical trend analysis with machine learning-powered forecasting
"""

import logging
import time
import json
import uuid
import threading
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import math
import statistics
from datetime import datetime, timedelta

# ML libraries with graceful fallbacks
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import IsolationForest
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_squared_error
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# Import existing components
from ..enhanced_autocad.performance_monitor import PerformanceMonitor
from ..enhanced_autocad.error_handler import ErrorHandler
from .security_monitoring import SecurityMonitor, AuditLogger
from .collaboration_architecture import CollaborationServer
from .deployment_automation import DeploymentAutomationEngine

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected by the monitoring system."""
    COUNTER = "counter"         # Monotonically increasing values
    GAUGE = "gauge"             # Current value at a point in time
    HISTOGRAM = "histogram"     # Distribution of values
    TIMER = "timer"             # Time-based measurements
    RATE = "rate"              # Rate of change over time


class AlertSeverity(Enum):
    """Severity levels for monitoring alerts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Status of monitoring alerts."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class MetricDataPoint:
    """A single metric data point with timestamp and metadata."""
    metric_name: str
    value: Union[float, int]
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Metric-specific data
    unit: Optional[str] = None
    source: Optional[str] = None
    
    # Quality indicators
    confidence: float = 1.0
    interpolated: bool = False


@dataclass
class MetricSeries:
    """A time series of metric data points."""
    name: str
    metric_type: MetricType
    data_points: deque = field(default_factory=lambda: deque(maxlen=10000))
    
    # Metadata
    unit: Optional[str] = None
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Statistical summary
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: Optional[float] = None
    last_value: Optional[float] = None
    
    # Configuration
    retention_period: int = 86400  # 24 hours in seconds
    aggregation_interval: int = 60  # 1 minute
    
    def add_data_point(self, value: Union[float, int], timestamp: Optional[float] = None, **kwargs):
        """Add a new data point to the series."""
        if timestamp is None:
            timestamp = time.time()
        
        data_point = MetricDataPoint(
            metric_name=self.name,
            value=value,
            timestamp=timestamp,
            **kwargs
        )
        
        self.data_points.append(data_point)
        self._update_statistics()
        self._cleanup_old_data()
    
    def _update_statistics(self):
        """Update statistical summary of the series."""
        if not self.data_points:
            return
        
        values = [dp.value for dp in self.data_points]
        self.min_value = min(values)
        self.max_value = max(values)
        self.avg_value = sum(values) / len(values)
        self.last_value = values[-1]
    
    def _cleanup_old_data(self):
        """Remove data points older than retention period."""
        cutoff_time = time.time() - self.retention_period
        while self.data_points and self.data_points[0].timestamp < cutoff_time:
            self.data_points.popleft()


@dataclass
class MonitoringAlert:
    """A monitoring alert with conditions and actions."""
    id: str
    name: str
    condition: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    
    # Alert details
    description: str = ""
    metric_name: str = ""
    threshold_value: Optional[float] = None
    current_value: Optional[float] = None
    
    # Timing
    created_at: float = field(default_factory=time.time)
    triggered_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    
    # Notification
    notification_channels: List[str] = field(default_factory=list)
    notification_sent: bool = False
    escalation_level: int = 0
    
    # Context
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # History
    trigger_count: int = 0
    last_trigger_time: Optional[float] = None


@dataclass
class DashboardWidget:
    """A widget on the monitoring dashboard."""
    id: str
    type: str  # chart, gauge, table, text, etc.
    title: str
    
    # Data source
    metric_names: List[str] = field(default_factory=list)
    query: Optional[str] = None
    refresh_interval: int = 30  # seconds
    
    # Display configuration
    width: int = 6  # Bootstrap column width (1-12)
    height: int = 300  # pixels
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Position
    row: int = 0
    column: int = 0
    
    # Access control
    required_permissions: Set[str] = field(default_factory=set)


@dataclass
class Dashboard:
    """A monitoring dashboard containing multiple widgets."""
    id: str
    name: str
    description: str = ""
    
    # Content
    widgets: List[DashboardWidget] = field(default_factory=list)
    
    # Configuration
    auto_refresh: bool = True
    refresh_interval: int = 30  # seconds
    time_range: str = "1h"  # Default time range
    
    # Access control
    owner: Optional[str] = None
    shared: bool = False
    permissions: Dict[str, Set[str]] = field(default_factory=dict)
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)
    view_count: int = 0


class AnomalyDetector:
    """Machine learning-based anomaly detection for metrics."""
    
    def __init__(self):
        """Initialize the anomaly detector."""
        self.models = {}  # metric_name -> model
        self.scalers = {}  # metric_name -> scaler
        self.training_data = defaultdict(list)
        self.anomaly_threshold = 0.1  # Threshold for anomaly detection
        self.min_training_samples = 100
        
        # Configuration
        self.enable_ml_detection = HAS_SKLEARN
        self.detection_window_size = 50
        self.retraining_interval = 3600  # 1 hour
        self.last_training_times = {}
    
    def add_training_data(self, metric_name: str, values: List[float]):
        """Add training data for a metric."""
        self.training_data[metric_name].extend(values)
        
        # Limit training data size to prevent memory issues
        if len(self.training_data[metric_name]) > 10000:
            self.training_data[metric_name] = self.training_data[metric_name][-5000:]
    
    def train_model(self, metric_name: str) -> bool:
        """Train anomaly detection model for a specific metric."""
        if not self.enable_ml_detection:
            return False
        
        training_data = self.training_data.get(metric_name, [])
        if len(training_data) < self.min_training_samples:
            logger.debug(f"Insufficient training data for {metric_name}: {len(training_data)}")
            return False
        
        try:
            # Prepare training data
            X = np.array(training_data).reshape(-1, 1)
            
            # Create and fit scaler
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train isolation forest model
            model = IsolationForest(contamination=self.anomaly_threshold, random_state=42)
            model.fit(X_scaled)
            
            # Store model and scaler
            self.models[metric_name] = model
            self.scalers[metric_name] = scaler
            self.last_training_times[metric_name] = time.time()
            
            logger.info(f"Trained anomaly detection model for {metric_name}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to train anomaly detection model for {metric_name}: {e}")
            return False
    
    def detect_anomaly(self, metric_name: str, value: float) -> Tuple[bool, float]:
        """
        Detect if a value is anomalous for a given metric.
        
        Returns:
            Tuple of (is_anomaly, anomaly_score)
        """
        if not self.enable_ml_detection or metric_name not in self.models:
            # Fallback to statistical detection
            return self._statistical_anomaly_detection(metric_name, value)
        
        try:
            model = self.models[metric_name]
            scaler = self.scalers[metric_name]
            
            # Scale the value
            X = np.array([[value]])
            X_scaled = scaler.transform(X)
            
            # Get anomaly score
            anomaly_score = model.decision_function(X_scaled)[0]
            is_anomaly = model.predict(X_scaled)[0] == -1
            
            return is_anomaly, float(anomaly_score)
        
        except Exception as e:
            logger.error(f"Anomaly detection failed for {metric_name}: {e}")
            return False, 0.0
    
    def _statistical_anomaly_detection(self, metric_name: str, value: float) -> Tuple[bool, float]:
        """Fallback statistical anomaly detection."""
        training_data = self.training_data.get(metric_name, [])
        
        if len(training_data) < 10:
            return False, 0.0
        
        # Use simple z-score based detection
        mean_val = statistics.mean(training_data)
        std_val = statistics.stdev(training_data) if len(training_data) > 1 else 0
        
        if std_val == 0:
            return False, 0.0
        
        z_score = abs(value - mean_val) / std_val
        is_anomaly = z_score > 3.0  # 3-sigma rule
        
        return is_anomaly, min(z_score / 3.0, 1.0)
    
    def should_retrain(self, metric_name: str) -> bool:
        """Check if a model should be retrained."""
        last_training = self.last_training_times.get(metric_name, 0)
        return (time.time() - last_training) > self.retraining_interval


class ForecastingEngine:
    """Predictive analytics and forecasting for metrics."""
    
    def __init__(self):
        """Initialize the forecasting engine."""
        self.models = {}  # metric_name -> model
        self.enable_forecasting = HAS_SKLEARN and HAS_NUMPY
        self.forecast_horizon = 3600  # 1 hour ahead
        self.min_data_points = 50
    
    def generate_forecast(self, metric_name: str, historical_data: List[MetricDataPoint]) -> Dict[str, Any]:
        """
        Generate forecast for a metric based on historical data.
        
        Args:
            metric_name: Name of the metric to forecast
            historical_data: Historical data points
            
        Returns:
            Forecast results with predictions and confidence intervals
        """
        if not self.enable_forecasting or len(historical_data) < self.min_data_points:
            return self._simple_forecast(historical_data)
        
        try:
            # Prepare data
            timestamps = np.array([dp.timestamp for dp in historical_data])
            values = np.array([dp.value for dp in historical_data])
            
            # Use time since first data point as feature
            X = (timestamps - timestamps[0]).reshape(-1, 1)
            y = values
            
            # Train linear regression model
            model = LinearRegression()
            model.fit(X, y)
            
            # Generate predictions
            last_timestamp = timestamps[-1]
            future_timestamps = np.arange(
                last_timestamp,
                last_timestamp + self.forecast_horizon,
                60  # 1-minute intervals
            )
            
            future_X = (future_timestamps - timestamps[0]).reshape(-1, 1)
            predictions = model.predict(future_X)
            
            # Calculate confidence intervals (simplified)
            train_predictions = model.predict(X)
            mse = mean_squared_error(y, train_predictions)
            std_error = math.sqrt(mse)
            
            forecast_results = {
                'metric_name': metric_name,
                'forecast_horizon_seconds': self.forecast_horizon,
                'predictions': [
                    {
                        'timestamp': float(ts),
                        'predicted_value': float(pred),
                        'confidence_interval_lower': float(pred - 2 * std_error),
                        'confidence_interval_upper': float(pred + 2 * std_error)
                    }
                    for ts, pred in zip(future_timestamps, predictions)
                ],
                'model_accuracy': {
                    'mse': float(mse),
                    'r_squared': float(model.score(X, y))
                },
                'trend_direction': 'increasing' if model.coef_[0] > 0 else 'decreasing',
                'trend_strength': float(abs(model.coef_[0]))
            }
            
            return forecast_results
        
        except Exception as e:
            logger.error(f"Forecasting failed for {metric_name}: {e}")
            return self._simple_forecast(historical_data)
    
    def _simple_forecast(self, historical_data: List[MetricDataPoint]) -> Dict[str, Any]:
        """Simple fallback forecasting using moving averages."""
        if len(historical_data) < 5:
            return {'error': 'Insufficient data for forecasting'}
        
        # Calculate simple moving average
        recent_values = [dp.value for dp in historical_data[-10:]]
        avg_value = sum(recent_values) / len(recent_values)
        
        # Generate simple flat forecast
        last_timestamp = historical_data[-1].timestamp
        predictions = []
        
        for i in range(60):  # 60 minutes ahead
            predictions.append({
                'timestamp': last_timestamp + (i * 60),
                'predicted_value': avg_value,
                'confidence_interval_lower': avg_value * 0.9,
                'confidence_interval_upper': avg_value * 1.1
            })
        
        return {
            'metric_name': historical_data[0].metric_name if historical_data else 'unknown',
            'forecast_horizon_seconds': 3600,
            'predictions': predictions,
            'model_type': 'simple_average',
            'trend_direction': 'stable'
        }


class AlertManager:
    """Manages monitoring alerts and notifications."""
    
    def __init__(self):
        """Initialize the alert manager."""
        self.active_alerts = {}  # alert_id -> MonitoringAlert
        self.alert_rules = {}  # rule_name -> alert configuration
        self.notification_channels = {}  # channel_name -> channel config
        self.escalation_policies = {}  # policy_name -> escalation config
        
        # Alert processing
        self.alert_queue = deque()
        self.processing_alerts = False
        
        # Statistics
        self.alert_stats = {
            'total_alerts_created': 0,
            'total_alerts_resolved': 0,
            'average_resolution_time': 0.0,
            'alerts_by_severity': defaultdict(int)
        }
    
    def create_alert_rule(self, 
                         rule_name: str,
                         metric_name: str,
                         condition: str,
                         threshold: float,
                         severity: AlertSeverity,
                         **kwargs) -> str:
        """Create a new alert rule."""
        rule_id = str(uuid.uuid4())
        
        self.alert_rules[rule_name] = {
            'id': rule_id,
            'name': rule_name,
            'metric_name': metric_name,
            'condition': condition,  # 'greater_than', 'less_than', 'equals', etc.
            'threshold': threshold,
            'severity': severity,
            'enabled': kwargs.get('enabled', True),
            'notification_channels': kwargs.get('notification_channels', []),
            'cooldown_period': kwargs.get('cooldown_period', 300),  # 5 minutes
            'evaluation_window': kwargs.get('evaluation_window', 60),  # 1 minute
            'created_at': time.time()
        }
        
        logger.info(f"Created alert rule '{rule_name}' for metric '{metric_name}'")
        return rule_id
    
    def evaluate_alert_rules(self, metric_name: str, current_value: float):
        """Evaluate alert rules for a given metric."""
        for rule_name, rule_config in self.alert_rules.items():
            if rule_config['metric_name'] != metric_name or not rule_config['enabled']:
                continue
            
            should_trigger = self._evaluate_condition(
                rule_config['condition'],
                current_value,
                rule_config['threshold']
            )
            
            if should_trigger:
                self._trigger_alert(rule_name, rule_config, current_value)
    
    def _evaluate_condition(self, condition: str, value: float, threshold: float) -> bool:
        """Evaluate alert condition."""
        if condition == 'greater_than':
            return value > threshold
        elif condition == 'less_than':
            return value < threshold
        elif condition == 'equals':
            return abs(value - threshold) < 0.001
        elif condition == 'greater_than_or_equal':
            return value >= threshold
        elif condition == 'less_than_or_equal':
            return value <= threshold
        else:
            logger.warning(f"Unknown alert condition: {condition}")
            return False
    
    def _trigger_alert(self, rule_name: str, rule_config: Dict[str, Any], current_value: float):
        """Trigger an alert based on rule evaluation."""
        # Check cooldown period
        existing_alerts = [
            alert for alert in self.active_alerts.values()
            if alert.name == rule_name and alert.status == AlertStatus.ACTIVE
        ]
        
        if existing_alerts:
            last_alert = max(existing_alerts, key=lambda a: a.triggered_at or 0)
            cooldown_remaining = (last_alert.triggered_at or 0) + rule_config['cooldown_period'] - time.time()
            if cooldown_remaining > 0:
                return  # Still in cooldown period
        
        # Create new alert
        alert_id = str(uuid.uuid4())
        alert = MonitoringAlert(
            id=alert_id,
            name=rule_name,
            condition=rule_config['condition'],
            severity=rule_config['severity'],
            description=f"Metric '{rule_config['metric_name']}' {rule_config['condition']} {rule_config['threshold']}",
            metric_name=rule_config['metric_name'],
            threshold_value=rule_config['threshold'],
            current_value=current_value,
            triggered_at=time.time(),
            notification_channels=rule_config.get('notification_channels', [])
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_queue.append(alert)
        
        # Update statistics
        self.alert_stats['total_alerts_created'] += 1
        self.alert_stats['alerts_by_severity'][alert.severity.value] += 1
        
        logger.warning(f"Alert triggered: {rule_name} - {alert.description}")
    
    def acknowledge_alert(self, alert_id: str, user_id: Optional[str] = None) -> bool:
        """Acknowledge an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = time.time()
        
        if user_id:
            alert.metadata['acknowledged_by'] = user_id
        
        logger.info(f"Alert {alert_id} acknowledged")
        return True
    
    def resolve_alert(self, alert_id: str, user_id: Optional[str] = None) -> bool:
        """Resolve an alert."""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = time.time()
        
        if user_id:
            alert.metadata['resolved_by'] = user_id
        
        # Calculate resolution time
        if alert.triggered_at:
            resolution_time = alert.resolved_at - alert.triggered_at
            
            # Update average resolution time
            total_resolved = self.alert_stats['total_alerts_resolved']
            current_avg = self.alert_stats['average_resolution_time']
            new_avg = (current_avg * total_resolved + resolution_time) / (total_resolved + 1)
            self.alert_stats['average_resolution_time'] = new_avg
        
        self.alert_stats['total_alerts_resolved'] += 1
        
        # Remove from active alerts
        del self.active_alerts[alert_id]
        
        logger.info(f"Alert {alert_id} resolved")
        return True


class AdvancedMonitoringDashboard:
    """
    Advanced monitoring dashboard with comprehensive analytics.
    
    Provides real-time monitoring, alerting, anomaly detection, and predictive
    analytics for enterprise AutoCAD development environments.
    """
    
    def __init__(self, 
                 performance_monitor: Optional[PerformanceMonitor] = None,
                 security_monitor: Optional[SecurityMonitor] = None,
                 collaboration_server: Optional[CollaborationServer] = None):
        """Initialize the advanced monitoring dashboard."""
        
        # Core components
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.security_monitor = security_monitor
        self.collaboration_server = collaboration_server
        self.error_handler = ErrorHandler()
        
        # Monitoring components
        self.metric_series = {}  # metric_name -> MetricSeries
        self.anomaly_detector = AnomalyDetector()
        self.forecasting_engine = ForecastingEngine()
        self.alert_manager = AlertManager()
        
        # Dashboard management
        self.dashboards = {}  # dashboard_id -> Dashboard
        self.default_dashboard_id = None
        
        # Data collection
        self.collectors = {}  # collector_name -> collector function
        self.collection_intervals = {}  # collector_name -> interval in seconds
        self.last_collection_times = {}  # collector_name -> timestamp
        
        # Real-time data streaming
        self.websocket_connections = set()
        self.streaming_enabled = True
        self.stream_buffer = deque(maxlen=1000)
        
        # Background processing
        self.processing_thread = None
        self.processing_active = False
        
        # Configuration
        self.default_retention_period = 86400  # 24 hours
        self.default_collection_interval = 30  # 30 seconds
        self.max_concurrent_connections = 100
        
        # System health tracking
        self.system_health_metrics = {
            'dashboard_uptime': time.time(),
            'total_metrics_collected': 0,
            'active_alerts': 0,
            'anomalies_detected': 0,
            'forecasts_generated': 0
        }
        
        # Initialize built-in collectors and dashboards
        self._initialize_collectors()
        self._create_default_dashboards()
        
        logger.info("Advanced monitoring dashboard initialized")
    
    def start_monitoring(self):
        """Start the monitoring system."""
        if self.processing_active:
            logger.warning("Monitoring already active")
            return
        
        self.processing_active = True
        self.processing_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.processing_thread.start()
        
        # Initialize alert rules
        self._setup_default_alert_rules()
        
        logger.info("Monitoring system started")
    
    def stop_monitoring(self):
        """Stop the monitoring system."""
        self.processing_active = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)
        
        logger.info("Monitoring system stopped")
    
    def collect_metric(self, 
                      metric_name: str, 
                      value: Union[float, int],
                      metric_type: MetricType = MetricType.GAUGE,
                      tags: Optional[Dict[str, str]] = None,
                      timestamp: Optional[float] = None):
        """Collect a metric data point."""
        
        # Get or create metric series
        if metric_name not in self.metric_series:
            self.metric_series[metric_name] = MetricSeries(
                name=metric_name,
                metric_type=metric_type,
                retention_period=self.default_retention_period
            )
        
        series = self.metric_series[metric_name]
        series.add_data_point(
            value=value,
            timestamp=timestamp,
            tags=tags or {}
        )
        
        # Update system health
        self.system_health_metrics['total_metrics_collected'] += 1
        
        # Evaluate alert rules
        self.alert_manager.evaluate_alert_rules(metric_name, float(value))
        
        # Anomaly detection
        is_anomaly, anomaly_score = self.anomaly_detector.detect_anomaly(metric_name, float(value))
        if is_anomaly:
            self.system_health_metrics['anomalies_detected'] += 1
            self._handle_anomaly(metric_name, value, anomaly_score)
        
        # Add to anomaly detector training data
        self.anomaly_detector.add_training_data(metric_name, [float(value)])
        
        # Stream to connected clients
        if self.streaming_enabled:
            self._stream_metric_update(metric_name, value, timestamp or time.time())
    
    def get_metric_data(self, 
                       metric_name: str,
                       start_time: Optional[float] = None,
                       end_time: Optional[float] = None,
                       aggregation: Optional[str] = None) -> Dict[str, Any]:
        """Get metric data for a specific time range."""
        
        if metric_name not in self.metric_series:
            return {'error': f'Metric {metric_name} not found'}
        
        series = self.metric_series[metric_name]
        data_points = list(series.data_points)
        
        # Apply time filtering
        if start_time or end_time:
            filtered_points = []
            for dp in data_points:
                if start_time and dp.timestamp < start_time:
                    continue
                if end_time and dp.timestamp > end_time:
                    continue
                filtered_points.append(dp)
            data_points = filtered_points
        
        if not data_points:
            return {'error': 'No data points in specified time range'}
        
        result = {
            'metric_name': metric_name,
            'metric_type': series.metric_type.value,
            'data_points': [
                {
                    'timestamp': dp.timestamp,
                    'value': dp.value,
                    'tags': dp.tags
                }
                for dp in data_points
            ],
            'statistics': {
                'min': min(dp.value for dp in data_points),
                'max': max(dp.value for dp in data_points),
                'avg': sum(dp.value for dp in data_points) / len(data_points),
                'count': len(data_points)
            }
        }
        
        # Apply aggregation if requested
        if aggregation:
            result['aggregated_data'] = self._aggregate_data(data_points, aggregation)
        
        return result
    
    def create_dashboard(self, name: str, description: str = "") -> str:
        """Create a new monitoring dashboard."""
        dashboard_id = str(uuid.uuid4())
        
        dashboard = Dashboard(
            id=dashboard_id,
            name=name,
            description=description
        )
        
        self.dashboards[dashboard_id] = dashboard
        
        # Set as default if this is the first dashboard
        if self.default_dashboard_id is None:
            self.default_dashboard_id = dashboard_id
        
        logger.info(f"Created dashboard '{name}' with ID {dashboard_id}")
        return dashboard_id
    
    def add_dashboard_widget(self,
                           dashboard_id: str,
                           widget_type: str,
                           title: str,
                           metric_names: List[str],
                           **kwargs) -> str:
        """Add a widget to a dashboard."""
        
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        widget_id = str(uuid.uuid4())
        widget = DashboardWidget(
            id=widget_id,
            type=widget_type,
            title=title,
            metric_names=metric_names,
            **kwargs
        )
        
        self.dashboards[dashboard_id].widgets.append(widget)
        self.dashboards[dashboard_id].last_modified = time.time()
        
        logger.info(f"Added widget '{title}' to dashboard {dashboard_id}")
        return widget_id
    
    def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get data for rendering a dashboard."""
        
        if dashboard_id not in self.dashboards:
            return {'error': f'Dashboard {dashboard_id} not found'}
        
        dashboard = self.dashboards[dashboard_id]
        dashboard.view_count += 1
        
        # Collect data for all widgets
        widget_data = []
        for widget in dashboard.widgets:
            widget_info = {
                'id': widget.id,
                'type': widget.type,
                'title': widget.title,
                'config': widget.config,
                'width': widget.width,
                'height': widget.height,
                'data': {}
            }
            
            # Get metric data for widget
            for metric_name in widget.metric_names:
                metric_data = self.get_metric_data(metric_name)
                if 'error' not in metric_data:
                    widget_info['data'][metric_name] = metric_data
            
            widget_data.append(widget_info)
        
        return {
            'dashboard': {
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description,
                'auto_refresh': dashboard.auto_refresh,
                'refresh_interval': dashboard.refresh_interval,
                'time_range': dashboard.time_range
            },
            'widgets': widget_data,
            'timestamp': time.time()
        }
    
    def generate_analytics_report(self, 
                                time_range: str = "24h",
                                include_forecasts: bool = True) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        
        # Calculate time boundaries
        now = time.time()
        if time_range == "1h":
            start_time = now - 3600
        elif time_range == "24h":
            start_time = now - 86400
        elif time_range == "7d":
            start_time = now - 604800
        else:
            start_time = now - 86400  # Default to 24h
        
        report = {
            'report_id': str(uuid.uuid4()),
            'generated_at': now,
            'time_range': time_range,
            'time_period': {
                'start': start_time,
                'end': now,
                'duration_seconds': now - start_time
            },
            'system_health': self._get_system_health_summary(),
            'metric_summary': {},
            'alert_summary': self._get_alert_summary(),
            'anomaly_summary': self._get_anomaly_summary(),
            'performance_insights': {},
            'recommendations': []
        }
        
        # Analyze all metrics
        for metric_name, series in self.metric_series.items():
            metric_data = self.get_metric_data(metric_name, start_time, now)
            
            if 'error' not in metric_data and metric_data['data_points']:
                values = [dp['value'] for dp in metric_data['data_points']]
                
                metric_analysis = {
                    'name': metric_name,
                    'type': series.metric_type.value,
                    'data_points_count': len(values),
                    'statistics': metric_data['statistics'],
                    'trend_analysis': self._analyze_trend(values),
                    'quality_score': self._calculate_metric_quality(metric_data['data_points'])
                }
                
                # Add forecasts if requested
                if include_forecasts and len(metric_data['data_points']) >= 20:
                    try:
                        forecast = self.forecasting_engine.generate_forecast(
                            metric_name,
                            [MetricDataPoint(
                                metric_name=metric_name,
                                value=dp['value'],
                                timestamp=dp['timestamp']
                            ) for dp in metric_data['data_points']]
                        )
                        metric_analysis['forecast'] = forecast
                        self.system_health_metrics['forecasts_generated'] += 1
                    except Exception as e:
                        logger.error(f"Forecast generation failed for {metric_name}: {e}")
                
                report['metric_summary'][metric_name] = metric_analysis
        
        # Generate performance insights
        report['performance_insights'] = self._generate_performance_insights(report['metric_summary'])
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics snapshot."""
        
        current_metrics = {}
        
        for metric_name, series in self.metric_series.items():
            if series.data_points:
                latest_point = series.data_points[-1]
                current_metrics[metric_name] = {
                    'current_value': latest_point.value,
                    'timestamp': latest_point.timestamp,
                    'unit': series.unit,
                    'tags': latest_point.tags
                }
        
        return {
            'timestamp': time.time(),
            'metrics': current_metrics,
            'system_status': self._get_system_status(),
            'active_alerts': len(self.alert_manager.active_alerts),
            'total_metrics': len(self.metric_series)
        }
    
    def _initialize_collectors(self):
        """Initialize built-in metric collectors."""
        
        # System performance collector
        def collect_system_performance():
            try:
                # CPU and memory metrics
                import psutil
                
                self.collect_metric('system.cpu.usage_percent', psutil.cpu_percent())
                self.collect_metric('system.memory.usage_percent', psutil.virtual_memory().percent)
                self.collect_metric('system.disk.usage_percent', psutil.disk_usage('/').percent)
                
                # Network metrics
                net_io = psutil.net_io_counters()
                self.collect_metric('system.network.bytes_sent', net_io.bytes_sent, MetricType.COUNTER)
                self.collect_metric('system.network.bytes_recv', net_io.bytes_recv, MetricType.COUNTER)
                
            except ImportError:
                # Fallback metrics without psutil
                self.collect_metric('system.uptime', time.time() - self.system_health_metrics['dashboard_uptime'])
        
        # AutoCAD performance collector
        def collect_autocad_performance():
            if self.performance_monitor:
                try:
                    metrics = self.performance_monitor.get_current_metrics()
                    
                    for metric_name, value in metrics.items():
                        if isinstance(value, (int, float)):
                            self.collect_metric(f'autocad.{metric_name}', value)
                            
                except Exception as e:
                    logger.error(f"AutoCAD performance collection failed: {e}")
        
        # Collaboration metrics collector
        def collect_collaboration_metrics():
            if self.collaboration_server:
                try:
                    stats = self.collaboration_server.get_server_statistics()
                    
                    self.collect_metric('collaboration.active_users', stats.get('active_users', 0))
                    self.collect_metric('collaboration.active_workspaces', stats.get('active_workspaces', 0))
                    self.collect_metric('collaboration.total_edits', stats.get('total_edits', 0), MetricType.COUNTER)
                    self.collect_metric('collaboration.pending_events', stats.get('pending_events', 0))
                    
                except Exception as e:
                    logger.error(f"Collaboration metrics collection failed: {e}")
        
        # Security metrics collector
        def collect_security_metrics():
            if self.security_monitor:
                try:
                    # This would integrate with the security monitoring system
                    # to collect security-related metrics
                    self.collect_metric('security.audit_events', 0, MetricType.COUNTER)
                    self.collect_metric('security.threat_level', 0)
                    
                except Exception as e:
                    logger.error(f"Security metrics collection failed: {e}")
        
        # Register collectors
        self.collectors = {
            'system_performance': collect_system_performance,
            'autocad_performance': collect_autocad_performance,
            'collaboration_metrics': collect_collaboration_metrics,
            'security_metrics': collect_security_metrics
        }
        
        # Set collection intervals
        self.collection_intervals = {
            'system_performance': 30,     # 30 seconds
            'autocad_performance': 60,    # 1 minute
            'collaboration_metrics': 30,  # 30 seconds
            'security_metrics': 60        # 1 minute
        }
    
    def _create_default_dashboards(self):
        """Create default monitoring dashboards."""
        
        # System Overview Dashboard
        system_dashboard_id = self.create_dashboard(
            "System Overview",
            "System-wide performance and health metrics"
        )
        
        self.add_dashboard_widget(
            system_dashboard_id,
            "line_chart",
            "CPU Usage",
            ["system.cpu.usage_percent"],
            width=6,
            config={"unit": "%", "threshold": 80}
        )
        
        self.add_dashboard_widget(
            system_dashboard_id,
            "line_chart",
            "Memory Usage",
            ["system.memory.usage_percent"],
            width=6,
            config={"unit": "%", "threshold": 90}
        )
        
        self.add_dashboard_widget(
            system_dashboard_id,
            "gauge",
            "Disk Usage",
            ["system.disk.usage_percent"],
            width=4,
            config={"unit": "%", "max": 100}
        )
        
        # AutoCAD Performance Dashboard
        autocad_dashboard_id = self.create_dashboard(
            "AutoCAD Performance",
            "AutoCAD-specific performance metrics and insights"
        )
        
        self.add_dashboard_widget(
            autocad_dashboard_id,
            "line_chart",
            "AutoCAD CPU Usage",
            ["autocad.cpu_usage"],
            width=12,
            config={"unit": "%"}
        )
        
        # Set system overview as default
        self.default_dashboard_id = system_dashboard_id
    
    def _setup_default_alert_rules(self):
        """Setup default monitoring alert rules."""
        
        # System alerts
        self.alert_manager.create_alert_rule(
            "High CPU Usage",
            "system.cpu.usage_percent",
            "greater_than",
            85.0,
            AlertSeverity.HIGH,
            cooldown_period=300
        )
        
        self.alert_manager.create_alert_rule(
            "High Memory Usage",
            "system.memory.usage_percent",
            "greater_than",
            90.0,
            AlertSeverity.CRITICAL,
            cooldown_period=300
        )
        
        self.alert_manager.create_alert_rule(
            "Low Disk Space",
            "system.disk.usage_percent",
            "greater_than",
            95.0,
            AlertSeverity.CRITICAL,
            cooldown_period=600
        )
    
    def _monitoring_loop(self):
        """Main monitoring loop running in background thread."""
        
        while self.processing_active:
            try:
                current_time = time.time()
                
                # Run metric collectors
                for collector_name, collector_func in self.collectors.items():
                    interval = self.collection_intervals.get(collector_name, self.default_collection_interval)
                    last_collection = self.last_collection_times.get(collector_name, 0)
                    
                    if current_time - last_collection >= interval:
                        try:
                            collector_func()
                            self.last_collection_times[collector_name] = current_time
                        except Exception as e:
                            logger.error(f"Collector {collector_name} failed: {e}")
                
                # Retrain anomaly detection models if needed
                for metric_name in list(self.metric_series.keys()):
                    if self.anomaly_detector.should_retrain(metric_name):
                        self.anomaly_detector.train_model(metric_name)
                
                # Update system health metrics
                self.system_health_metrics['active_alerts'] = len(self.alert_manager.active_alerts)
                
                # Sleep for a short interval
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(5.0)  # Longer sleep on error
    
    def _handle_anomaly(self, metric_name: str, value: float, anomaly_score: float):
        """Handle detected anomaly."""
        logger.warning(f"Anomaly detected in {metric_name}: value={value}, score={anomaly_score}")
        
        # Create anomaly alert if score is high enough
        if anomaly_score > 0.5:
            alert_id = str(uuid.uuid4())
            alert = MonitoringAlert(
                id=alert_id,
                name=f"Anomaly in {metric_name}",
                condition="anomaly_detected",
                severity=AlertSeverity.MEDIUM if anomaly_score < 0.8 else AlertSeverity.HIGH,
                description=f"Anomalous value detected: {value} (score: {anomaly_score:.3f})",
                metric_name=metric_name,
                current_value=value,
                triggered_at=time.time()
            )
            
            self.alert_manager.active_alerts[alert_id] = alert
            self.alert_manager.alert_queue.append(alert)
    
    def _stream_metric_update(self, metric_name: str, value: float, timestamp: float):
        """Stream metric update to connected WebSocket clients."""
        update = {
            'type': 'metric_update',
            'metric_name': metric_name,
            'value': value,
            'timestamp': timestamp
        }
        
        self.stream_buffer.append(update)
        
        # This would send to actual WebSocket connections in a real implementation
        logger.debug(f"Streaming metric update: {metric_name}={value}")
    
    def _get_system_health_summary(self) -> Dict[str, Any]:
        """Get system health summary."""
        uptime = time.time() - self.system_health_metrics['dashboard_uptime']
        
        return {
            'uptime_seconds': uptime,
            'uptime_hours': uptime / 3600,
            'total_metrics_collected': self.system_health_metrics['total_metrics_collected'],
            'active_metrics': len(self.metric_series),
            'active_alerts': self.system_health_metrics['active_alerts'],
            'anomalies_detected': self.system_health_metrics['anomalies_detected'],
            'forecasts_generated': self.system_health_metrics['forecasts_generated'],
            'system_status': self._get_system_status()
        }
    
    def _get_system_status(self) -> str:
        """Get overall system status."""
        active_alerts = len(self.alert_manager.active_alerts)
        
        if active_alerts == 0:
            return "healthy"
        elif active_alerts < 5:
            return "warning"
        else:
            return "critical"
    
    def _get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics."""
        return {
            'total_active_alerts': len(self.alert_manager.active_alerts),
            'alerts_by_severity': dict(self.alert_manager.alert_stats['alerts_by_severity']),
            'total_alerts_created': self.alert_manager.alert_stats['total_alerts_created'],
            'total_alerts_resolved': self.alert_manager.alert_stats['total_alerts_resolved'],
            'average_resolution_time_seconds': self.alert_manager.alert_stats['average_resolution_time']
        }
    
    def _get_anomaly_summary(self) -> Dict[str, Any]:
        """Get anomaly detection summary."""
        return {
            'total_anomalies_detected': self.system_health_metrics['anomalies_detected'],
            'models_trained': len(self.anomaly_detector.models),
            'ml_detection_enabled': self.anomaly_detector.enable_ml_detection
        }
    
    def _analyze_trend(self, values: List[float]) -> Dict[str, Any]:
        """Analyze trend in a series of values."""
        if len(values) < 2:
            return {'direction': 'stable', 'strength': 0.0}
        
        # Simple linear trend analysis
        x = list(range(len(values)))
        y = values
        
        if HAS_NUMPY:
            correlation = np.corrcoef(x, y)[0, 1]
            direction = 'increasing' if correlation > 0.1 else 'decreasing' if correlation < -0.1 else 'stable'
            strength = abs(correlation)
        else:
            # Fallback: compare first and last values
            change = (values[-1] - values[0]) / abs(values[0]) if values[0] != 0 else 0
            direction = 'increasing' if change > 0.1 else 'decreasing' if change < -0.1 else 'stable'
            strength = min(abs(change), 1.0)
        
        return {
            'direction': direction,
            'strength': strength,
            'change_percent': ((values[-1] - values[0]) / abs(values[0]) * 100) if values[0] != 0 else 0
        }
    
    def _calculate_metric_quality(self, data_points: List[Dict[str, Any]]) -> float:
        """Calculate quality score for metric data."""
        if not data_points:
            return 0.0
        
        # Check data completeness and consistency
        quality_factors = []
        
        # Completeness: how much data we have vs expected
        expected_points = len(data_points)  # Simplified
        actual_points = len(data_points)
        completeness = min(actual_points / max(expected_points, 1), 1.0)
        quality_factors.append(completeness)
        
        # Consistency: check for reasonable values (no extreme outliers)
        values = [dp['value'] for dp in data_points]
        if len(values) > 1:
            mean_val = sum(values) / len(values)
            outliers = sum(1 for v in values if abs(v - mean_val) > 3 * statistics.stdev(values))
            consistency = 1.0 - (outliers / len(values))
            quality_factors.append(consistency)
        
        # Freshness: how recent is the latest data
        latest_timestamp = max(dp['timestamp'] for dp in data_points)
        age_seconds = time.time() - latest_timestamp
        freshness = max(0.0, 1.0 - (age_seconds / 3600))  # Decrease over 1 hour
        quality_factors.append(freshness)
        
        return sum(quality_factors) / len(quality_factors)
    
    def _generate_performance_insights(self, metric_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance insights from metric analysis."""
        insights = {
            'high_cpu_metrics': [],
            'memory_pressure_indicators': [],
            'performance_bottlenecks': [],
            'optimization_opportunities': []
        }
        
        for metric_name, analysis in metric_summary.items():
            stats = analysis.get('statistics', {})
            trend = analysis.get('trend_analysis', {})
            
            # CPU-related insights
            if 'cpu' in metric_name.lower():
                if stats.get('avg', 0) > 70:
                    insights['high_cpu_metrics'].append({
                        'metric': metric_name,
                        'average': stats['avg'],
                        'trend': trend['direction']
                    })
            
            # Memory-related insights
            if 'memory' in metric_name.lower():
                if stats.get('avg', 0) > 80:
                    insights['memory_pressure_indicators'].append({
                        'metric': metric_name,
                        'average': stats['avg'],
                        'max': stats['max']
                    })
            
            # Performance bottlenecks
            if trend.get('direction') == 'increasing' and trend.get('strength', 0) > 0.7:
                insights['performance_bottlenecks'].append({
                    'metric': metric_name,
                    'trend_strength': trend['strength'],
                    'change_percent': trend.get('change_percent', 0)
                })
        
        return insights
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on report data."""
        recommendations = []
        
        insights = report.get('performance_insights', {})
        alert_summary = report.get('alert_summary', {})
        
        # CPU recommendations
        if insights.get('high_cpu_metrics'):
            recommendations.append(
                "High CPU usage detected. Consider optimizing AutoCAD operations or scaling resources."
            )
        
        # Memory recommendations
        if insights.get('memory_pressure_indicators'):
            recommendations.append(
                "Memory pressure detected. Monitor for memory leaks and consider increasing available memory."
            )
        
        # Alert recommendations
        active_alerts = alert_summary.get('total_active_alerts', 0)
        if active_alerts > 10:
            recommendations.append(
                f"High number of active alerts ({active_alerts}). Review alert thresholds and resolve critical issues."
            )
        
        # Anomaly recommendations
        anomalies = report.get('anomaly_summary', {}).get('total_anomalies_detected', 0)
        if anomalies > 5:
            recommendations.append(
                "Multiple anomalies detected. Investigate unusual patterns in system behavior."
            )
        
        if not recommendations:
            recommendations.append("System is operating within normal parameters. Continue monitoring.")
        
        return recommendations
    
    def _aggregate_data(self, data_points: List[MetricDataPoint], aggregation: str) -> List[Dict[str, Any]]:
        """Aggregate data points using specified method."""
        if not data_points:
            return []
        
        # Group data points by time intervals (simplified to 1-minute buckets)
        buckets = defaultdict(list)
        
        for dp in data_points:
            bucket_time = int(dp.timestamp // 60) * 60  # Round to minute
            buckets[bucket_time].append(dp.value)
        
        aggregated = []
        for bucket_time, values in sorted(buckets.items()):
            if aggregation == 'avg':
                agg_value = sum(values) / len(values)
            elif aggregation == 'min':
                agg_value = min(values)
            elif aggregation == 'max':
                agg_value = max(values)
            elif aggregation == 'sum':
                agg_value = sum(values)
            else:
                agg_value = sum(values) / len(values)  # Default to average
            
            aggregated.append({
                'timestamp': bucket_time,
                'value': agg_value,
                'data_points_count': len(values)
            })
        
        return aggregated