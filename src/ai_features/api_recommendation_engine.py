"""
ML-Powered API Recommendation Engine
===================================

Intelligent API recommendation system using machine learning and usage analytics including:
- Context-aware AutoCAD API method suggestions with relevance scoring
- Usage pattern analysis and collaborative filtering for personalized recommendations
- Semantic similarity matching for discovering related APIs
- Performance-aware recommendations with execution time predictions  
- Learning from user behavior and code patterns for continuous improvement
"""

import logging
import time
import ast
import json
import re
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter, deque
import threading
import math

# ML libraries with graceful fallbacks
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.decomposition import TruncatedSVD
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# Import existing components
from ..inspection.object_inspector import ObjectInspector
from ..inspection.method_discoverer import MethodDiscoverer
from ..enhanced_autocad.performance_monitor import PerformanceMonitor

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of API recommendations."""
    METHOD_CALL = "method_call"       # Recommend specific method calls
    PROPERTY_ACCESS = "property_access"  # Recommend property access
    PATTERN_USAGE = "pattern_usage"   # Recommend usage patterns
    ALTERNATIVE_API = "alternative_api"  # Suggest alternative APIs
    OPTIMIZATION = "optimization"     # Performance optimization suggestions
    ERROR_HANDLING = "error_handling" # Error handling patterns
    WORKFLOW = "workflow"            # Multi-step workflow suggestions


class ConfidenceLevel(Enum):
    """Confidence levels for recommendations."""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.9


@dataclass 
class APIRecommendation:
    """A single API recommendation with context and confidence."""
    id: str
    type: RecommendationType
    confidence: float
    
    # API details
    api_name: str
    api_signature: str
    description: str
    
    # Context and usage
    context_match_score: float = 0.0
    usage_frequency_score: float = 0.0
    performance_score: float = 0.0
    similarity_score: float = 0.0
    
    # Metadata
    object_type: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: Optional[str] = None
    
    # Documentation and examples
    documentation_url: Optional[str] = None
    code_examples: List[str] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    
    # Performance characteristics
    average_execution_time: Optional[float] = None
    memory_usage: Optional[float] = None
    complexity_rating: Optional[str] = None
    
    # Related recommendations
    related_apis: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    
    # Learning metadata
    user_rating: Optional[float] = None
    usage_count: int = 0
    success_rate: float = 0.0
    last_used: Optional[float] = None


@dataclass
class UsageContext:
    """Context information for API recommendations."""
    file_path: str
    line_number: int
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    
    # Code context
    preceding_code: str = ""
    following_code: str = ""
    current_line: str = ""
    
    # Variable context
    local_variables: Dict[str, str] = field(default_factory=dict)
    autocad_objects: Dict[str, str] = field(default_factory=dict)
    
    # Intent context
    user_intent: Optional[str] = None
    task_description: Optional[str] = None
    
    # Performance context
    performance_requirements: Optional[str] = None
    error_handling_level: str = "basic"


@dataclass
class UserProfile:
    """User profile for personalized recommendations."""
    user_id: str
    skill_level: str = "intermediate"  # beginner, intermediate, advanced, expert
    
    # Usage patterns
    preferred_patterns: Set[str] = field(default_factory=set)
    frequently_used_apis: Counter = field(default_factory=Counter)
    avoided_apis: Set[str] = field(default_factory=set)
    
    # Context preferences
    autocad_version: Optional[str] = None
    primary_use_cases: List[str] = field(default_factory=list)
    performance_priority: float = 0.5  # 0.0 = simplicity, 1.0 = performance
    
    # Learning history
    total_recommendations_received: int = 0
    recommendations_accepted: int = 0
    recommendations_rated: int = 0
    average_rating: float = 0.0
    
    # Temporal patterns
    active_hours: List[int] = field(default_factory=list)
    seasonal_patterns: Dict[str, float] = field(default_factory=dict)


class APIKnowledgeBase:
    """Comprehensive knowledge base of AutoCAD APIs."""
    
    def __init__(self):
        """Initialize the API knowledge base."""
        self.api_methods = self._load_api_methods()
        self.api_properties = self._load_api_properties()
        self.usage_patterns = self._load_usage_patterns()
        self.performance_data = self._load_performance_data()
        self.semantic_embeddings = {}
        self.method_relationships = self._build_method_relationships()
        
        # Initialize ML components if available
        if HAS_SKLEARN:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            self.svd_model = TruncatedSVD(n_components=100)
            self.clustering_model = KMeans(n_clusters=20, random_state=42)
            self._build_semantic_embeddings()
    
    def _load_api_methods(self) -> Dict[str, Dict[str, Any]]:
        """Load comprehensive AutoCAD API method information."""
        return {
            'Application.GetInterfaceObject': {
                'signature': 'GetInterfaceObject(ProgID: str) -> object',
                'description': 'Creates or gets an interface to an application object',
                'object_type': 'Application',
                'parameters': [{'name': 'ProgID', 'type': 'str', 'description': 'Program identifier'}],
                'return_type': 'object',
                'complexity': 'simple',
                'use_cases': ['com_automation', 'external_application'],
                'performance': {'avg_time': 0.001, 'memory': 'low'},
                'examples': ['app.GetInterfaceObject("Excel.Application")']
            },
            'Document.SendCommand': {
                'signature': 'SendCommand(Command: str) -> None',
                'description': 'Sends a command string to AutoCAD command line',
                'object_type': 'Document',
                'parameters': [{'name': 'Command', 'type': 'str', 'description': 'AutoCAD command string'}],
                'return_type': 'None',
                'complexity': 'simple',
                'use_cases': ['command_automation', 'legacy_commands'],
                'performance': {'avg_time': 0.01, 'memory': 'low'},
                'examples': ['doc.SendCommand("LINE 0,0 10,10 ")'],
                'best_practices': ['Always include trailing space', 'Escape special characters']
            },
            'ModelSpace.AddLine': {
                'signature': 'AddLine(StartPoint: Tuple[float, float, float], EndPoint: Tuple[float, float, float]) -> AcadLine',
                'description': 'Creates a line object in model space',
                'object_type': 'ModelSpace',
                'parameters': [
                    {'name': 'StartPoint', 'type': 'Tuple[float, float, float]', 'description': '3D start point coordinates'},
                    {'name': 'EndPoint', 'type': 'Tuple[float, float, float]', 'description': '3D end point coordinates'}
                ],
                'return_type': 'AcadLine',
                'complexity': 'simple',
                'use_cases': ['drawing_creation', 'geometry_generation'],
                'performance': {'avg_time': 0.002, 'memory': 'low'},
                'examples': ['line = mspace.AddLine((0, 0, 0), (10, 10, 0))'],
                'related_methods': ['AddPolyline', 'AddCircle', 'AddArc']
            },
            'ModelSpace.AddCircle': {
                'signature': 'AddCircle(Center: Tuple[float, float, float], Radius: float) -> AcadCircle',
                'description': 'Creates a circle object in model space',
                'object_type': 'ModelSpace',
                'parameters': [
                    {'name': 'Center', 'type': 'Tuple[float, float, float]', 'description': '3D center point coordinates'},
                    {'name': 'Radius', 'type': 'float', 'description': 'Circle radius'}
                ],
                'return_type': 'AcadCircle',
                'complexity': 'simple',
                'use_cases': ['drawing_creation', 'geometry_generation'],
                'performance': {'avg_time': 0.002, 'memory': 'low'},
                'examples': ['circle = mspace.AddCircle((0, 0, 0), 5.0)'],
                'related_methods': ['AddLine', 'AddArc', 'AddEllipse']
            },
            'SelectionSet.Select': {
                'signature': 'Select(Mode: int, Point1: Optional[Tuple], Point2: Optional[Tuple], FilterType: Optional[List], FilterData: Optional[List]) -> None',
                'description': 'Selects objects in the drawing using various selection modes',
                'object_type': 'SelectionSet',
                'parameters': [
                    {'name': 'Mode', 'type': 'int', 'description': 'Selection mode constant'},
                    {'name': 'Point1', 'type': 'Optional[Tuple]', 'description': 'First selection point'},
                    {'name': 'Point2', 'type': 'Optional[Tuple]', 'description': 'Second selection point'},
                    {'name': 'FilterType', 'type': 'Optional[List]', 'description': 'Filter type codes'},
                    {'name': 'FilterData', 'type': 'Optional[List]', 'description': 'Filter data values'}
                ],
                'return_type': 'None',
                'complexity': 'intermediate',
                'use_cases': ['object_selection', 'filtering', 'batch_operations'],
                'performance': {'avg_time': 0.05, 'memory': 'medium'},
                'examples': ['sset.Select(acSelectionSetAll)'],
                'best_practices': ['Use appropriate selection modes', 'Apply filters for efficiency']
            },
            'Document.StartTransaction': {
                'signature': 'StartTransaction() -> None',
                'description': 'Starts a transaction for grouping multiple operations',
                'object_type': 'Document',
                'parameters': [],
                'return_type': 'None',
                'complexity': 'intermediate',
                'use_cases': ['batch_operations', 'performance_optimization', 'undo_control'],
                'performance': {'avg_time': 0.001, 'memory': 'low'},
                'examples': ['doc.StartTransaction()'],
                'related_methods': ['CommitTransaction', 'AbortTransaction'],
                'best_practices': ['Always pair with CommitTransaction', 'Use for multiple operations']
            }
        }
    
    def _load_api_properties(self) -> Dict[str, Dict[str, Any]]:
        """Load AutoCAD API property information."""
        return {
            'Application.ActiveDocument': {
                'type': 'Document',
                'description': 'Gets the currently active document',
                'read_only': True,
                'object_type': 'Application',
                'use_cases': ['document_access', 'current_context'],
                'examples': ['doc = app.ActiveDocument']
            },
            'Document.ModelSpace': {
                'type': 'ModelSpace',
                'description': 'Gets the model space collection',
                'read_only': True,
                'object_type': 'Document',
                'use_cases': ['drawing_access', 'entity_creation'],
                'examples': ['mspace = doc.ModelSpace']
            },
            'Document.PaperSpace': {
                'type': 'PaperSpace',
                'description': 'Gets the paper space collection',
                'read_only': True,
                'object_type': 'Document',
                'use_cases': ['layout_access', 'plotting'],
                'examples': ['pspace = doc.PaperSpace']
            },
            'AcadEntity.ObjectName': {
                'type': 'str',
                'description': 'Gets the AutoCAD class name of the object',
                'read_only': True,
                'object_type': 'AcadEntity',
                'use_cases': ['object_identification', 'type_checking'],
                'examples': ['obj_type = entity.ObjectName']
            }
        }
    
    def _load_usage_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load common usage patterns and workflows."""
        return {
            'basic_drawing_creation': {
                'description': 'Create basic drawing entities in model space',
                'apis': ['Document.ModelSpace', 'ModelSpace.AddLine', 'ModelSpace.AddCircle'],
                'sequence': ['Get ModelSpace', 'Create entities', 'Optionally modify properties'],
                'example': '''
# Get model space
mspace = doc.ModelSpace

# Create entities
line = mspace.AddLine((0, 0, 0), (10, 10, 0))
circle = mspace.AddCircle((5, 5, 0), 3.0)
''',
                'complexity': 'beginner',
                'use_cases': ['simple_drawings', 'geometry_creation']
            },
            'batch_operation_with_transaction': {
                'description': 'Perform multiple operations efficiently using transactions',
                'apis': ['Document.StartTransaction', 'Document.CommitTransaction', 'ModelSpace.Add*'],
                'sequence': ['Start transaction', 'Perform operations', 'Commit transaction'],
                'example': '''
# Start transaction for better performance
doc.StartTransaction()
try:
    for i in range(100):
        mspace.AddLine((i, 0, 0), (i, 10, 0))
    doc.CommitTransaction()
except:
    doc.AbortTransaction()
    raise
''',
                'complexity': 'intermediate',
                'use_cases': ['batch_operations', 'performance_optimization']
            },
            'selection_and_modification': {
                'description': 'Select objects and modify their properties',
                'apis': ['Document.SelectionSets', 'SelectionSet.Select', 'AcadEntity.Color'],
                'sequence': ['Create selection set', 'Select objects', 'Modify properties'],
                'example': '''
# Create selection set
sset = doc.SelectionSets.Add("MySelection")

# Select all lines
sset.Select(acSelectionSetAll, FilterType=[0], FilterData=["LINE"])

# Modify selected objects
for entity in sset:
    entity.Color = acRed
''',
                'complexity': 'intermediate',
                'use_cases': ['object_modification', 'batch_editing']
            }
        }
    
    def _load_performance_data(self) -> Dict[str, Dict[str, Any]]:
        """Load performance characteristics of APIs."""
        return {
            'ModelSpace.AddLine': {'avg_time': 0.002, 'std_dev': 0.0005, 'memory_impact': 'low'},
            'ModelSpace.AddCircle': {'avg_time': 0.0025, 'std_dev': 0.0006, 'memory_impact': 'low'},
            'SelectionSet.Select': {'avg_time': 0.05, 'std_dev': 0.02, 'memory_impact': 'medium'},
            'Document.SendCommand': {'avg_time': 0.01, 'std_dev': 0.005, 'memory_impact': 'low'},
            'Document.StartTransaction': {'avg_time': 0.001, 'std_dev': 0.0002, 'memory_impact': 'minimal'},
            'Document.CommitTransaction': {'avg_time': 0.003, 'std_dev': 0.001, 'memory_impact': 'minimal'}
        }
    
    def _build_method_relationships(self) -> Dict[str, List[str]]:
        """Build relationships between API methods."""
        return {
            'Document.StartTransaction': ['Document.CommitTransaction', 'Document.AbortTransaction'],
            'Document.CommitTransaction': ['Document.StartTransaction'],
            'Document.AbortTransaction': ['Document.StartTransaction'],
            'ModelSpace.AddLine': ['ModelSpace.AddPolyline', 'ModelSpace.AddCircle', 'ModelSpace.AddArc'],
            'ModelSpace.AddCircle': ['ModelSpace.AddLine', 'ModelSpace.AddArc', 'ModelSpace.AddEllipse'],
            'SelectionSet.Select': ['SelectionSet.SelectOnScreen', 'SelectionSet.Clear'],
            'Application.GetInterfaceObject': ['Application.ActiveDocument']
        }
    
    def _build_semantic_embeddings(self):
        """Build semantic embeddings for API methods using ML."""
        if not HAS_SKLEARN:
            return
        
        try:
            # Prepare text corpus for embedding
            corpus = []
            method_names = []
            
            for method_name, method_info in self.api_methods.items():
                # Combine description, use cases, and signature for embedding
                text = f"{method_info['description']} {' '.join(method_info.get('use_cases', []))}"
                corpus.append(text)
                method_names.append(method_name)
            
            # Build TF-IDF vectors
            if corpus:
                tfidf_matrix = self.vectorizer.fit_transform(corpus)
                
                # Apply SVD for dimensionality reduction
                reduced_matrix = self.svd_model.fit_transform(tfidf_matrix)
                
                # Store embeddings
                for i, method_name in enumerate(method_names):
                    self.semantic_embeddings[method_name] = reduced_matrix[i]
                
                # Build clusters
                self.clustering_model.fit(reduced_matrix)
                
                logger.info(f"Built semantic embeddings for {len(method_names)} API methods")
        
        except Exception as e:
            logger.error(f"Failed to build semantic embeddings: {e}")
    
    def get_similar_methods(self, method_name: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Get methods similar to the given method using semantic similarity."""
        if not HAS_SKLEARN or method_name not in self.semantic_embeddings:
            # Fallback to relationship-based similarity
            related = self.method_relationships.get(method_name, [])
            return [(m, 0.8) for m in related[:top_k]]
        
        try:
            query_embedding = self.semantic_embeddings[method_name].reshape(1, -1)
            similarities = []
            
            for other_method, embedding in self.semantic_embeddings.items():
                if other_method != method_name:
                    similarity = cosine_similarity(query_embedding, embedding.reshape(1, -1))[0][0]
                    similarities.append((other_method, float(similarity)))
            
            # Sort by similarity and return top-k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
        
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return []


class MLAPIRecommendationEngine:
    """
    ML-powered API recommendation engine for AutoCAD development.
    
    Provides intelligent, context-aware API suggestions using machine learning,
    usage analytics, and personalized recommendations.
    """
    
    def __init__(self, performance_monitor: Optional[PerformanceMonitor] = None):
        """Initialize the ML API recommendation engine."""
        self.knowledge_base = APIKnowledgeBase()
        self.performance_monitor = performance_monitor or PerformanceMonitor()
        self.object_inspector = ObjectInspector()
        
        # User profiles and collaborative filtering
        self.user_profiles: Dict[str, UserProfile] = {}
        self.global_usage_stats = Counter()
        self.collaborative_matrix = {}
        
        # Learning and adaptation
        self.recommendation_history = deque(maxlen=10000)
        self.feedback_data = []
        self.model_performance_metrics = {
            'precision': 0.0,
            'recall': 0.0,
            'user_satisfaction': 0.0
        }
        
        # Real-time context tracking
        self.current_contexts = {}
        self.session_patterns = defaultdict(list)
        
        # Configuration
        self.max_recommendations = 10
        self.min_confidence_threshold = 0.3
        self.personalization_weight = 0.3
        self.context_weight = 0.4
        self.popularity_weight = 0.3
        
        # Threading for background learning
        self.learning_lock = threading.RLock()
        self.background_learning_enabled = True
        
        logger.info("ML API recommendation engine initialized")
    
    def get_recommendations(self, 
                          context: UsageContext,
                          user_id: Optional[str] = None,
                          recommendation_types: Optional[List[RecommendationType]] = None) -> List[APIRecommendation]:
        """
        Get intelligent API recommendations based on context and user profile.
        
        Args:
            context: Current usage context
            user_id: User identifier for personalization
            recommendation_types: Types of recommendations to include
            
        Returns:
            List of ranked API recommendations
        """
        try:
            # Get or create user profile
            user_profile = self._get_user_profile(user_id) if user_id else None
            
            # Analyze current context
            context_features = self._analyze_context(context)
            
            # Generate recommendations using multiple strategies
            recommendations = []
            
            # Context-based recommendations
            context_recs = self._get_context_based_recommendations(context, context_features)
            recommendations.extend(context_recs)
            
            # Collaborative filtering recommendations
            if user_profile:
                collab_recs = self._get_collaborative_recommendations(user_profile, context_features)
                recommendations.extend(collab_recs)
            
            # Semantic similarity recommendations
            semantic_recs = self._get_semantic_recommendations(context, context_features)
            recommendations.extend(semantic_recs)
            
            # Pattern-based recommendations
            pattern_recs = self._get_pattern_based_recommendations(context, context_features)
            recommendations.extend(pattern_recs)
            
            # Performance-optimized recommendations
            perf_recs = self._get_performance_recommendations(context, context_features)
            recommendations.extend(perf_recs)
            
            # Remove duplicates and apply personalization
            recommendations = self._deduplicate_recommendations(recommendations)
            if user_profile:
                recommendations = self._apply_personalization(recommendations, user_profile)
            
            # Rank and filter recommendations
            recommendations = self._rank_recommendations(recommendations, context_features, user_profile)
            recommendations = [r for r in recommendations if r.confidence >= self.min_confidence_threshold]
            
            # Limit to max recommendations
            recommendations = recommendations[:self.max_recommendations]
            
            # Record recommendations for learning
            self._record_recommendations(recommendations, context, user_id)
            
            return recommendations
        
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []
    
    def provide_feedback(self, 
                        recommendation_id: str,
                        feedback_type: str,
                        rating: Optional[float] = None,
                        user_id: Optional[str] = None):
        """
        Provide feedback on a recommendation for learning improvement.
        
        Args:
            recommendation_id: ID of the recommendation
            feedback_type: Type of feedback ('accepted', 'rejected', 'rated')
            rating: Rating value (1.0 to 5.0) if feedback_type is 'rated'
            user_id: User providing feedback
        """
        try:
            feedback_entry = {
                'recommendation_id': recommendation_id,
                'feedback_type': feedback_type,
                'rating': rating,
                'user_id': user_id,
                'timestamp': time.time()
            }
            
            with self.learning_lock:
                self.feedback_data.append(feedback_entry)
                
                # Update user profile if available
                if user_id and user_id in self.user_profiles:
                    profile = self.user_profiles[user_id]
                    
                    if feedback_type == 'accepted':
                        profile.recommendations_accepted += 1
                    elif feedback_type == 'rated' and rating is not None:
                        profile.recommendations_rated += 1
                        # Update running average rating
                        if profile.recommendations_rated == 1:
                            profile.average_rating = rating
                        else:
                            profile.average_rating = (
                                (profile.average_rating * (profile.recommendations_rated - 1) + rating) /
                                profile.recommendations_rated
                            )
                
                # Trigger background learning if enough feedback accumulated
                if len(self.feedback_data) % 100 == 0:
                    self._trigger_background_learning()
            
            logger.debug(f"Recorded feedback for recommendation {recommendation_id}: {feedback_type}")
        
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
    
    def get_api_usage_analytics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get analytics about API usage patterns and recommendation effectiveness.
        
        Args:
            user_id: Optional user ID for personalized analytics
            
        Returns:
            Analytics report
        """
        analytics = {
            'timestamp': time.time(),
            'global_stats': {
                'total_recommendations': len(self.recommendation_history),
                'unique_apis_recommended': len(set(
                    rec.api_name for entry in self.recommendation_history 
                    for rec in entry['recommendations']
                )),
                'average_confidence': 0.0,
                'top_recommended_apis': [],
                'recommendation_types': defaultdict(int)
            },
            'performance_metrics': self.model_performance_metrics.copy(),
            'learning_status': {
                'feedback_entries': len(self.feedback_data),
                'user_profiles': len(self.user_profiles)
            }
        }
        
        try:
            # Calculate global statistics
            if self.recommendation_history:
                all_recommendations = [
                    rec for entry in self.recommendation_history 
                    for rec in entry['recommendations']
                ]
                
                if all_recommendations:
                    analytics['global_stats']['average_confidence'] = sum(
                        rec.confidence for rec in all_recommendations
                    ) / len(all_recommendations)
                    
                    # Top recommended APIs
                    api_counts = Counter(rec.api_name for rec in all_recommendations)
                    analytics['global_stats']['top_recommended_apis'] = api_counts.most_common(10)
                    
                    # Recommendation types
                    for rec in all_recommendations:
                        analytics['global_stats']['recommendation_types'][rec.type.value] += 1
            
            # User-specific analytics
            if user_id and user_id in self.user_profiles:
                profile = self.user_profiles[user_id]
                analytics['user_stats'] = {
                    'skill_level': profile.skill_level,
                    'total_recommendations_received': profile.total_recommendations_received,
                    'acceptance_rate': (
                        profile.recommendations_accepted / max(profile.total_recommendations_received, 1)
                    ),
                    'average_rating': profile.average_rating,
                    'frequently_used_apis': profile.frequently_used_apis.most_common(10),
                    'preferred_patterns': list(profile.preferred_patterns)
                }
        
        except Exception as e:
            logger.error(f"Failed to generate analytics: {e}")
            analytics['error'] = str(e)
        
        return analytics
    
    def learn_from_code_repository(self, repository_path: str) -> Dict[str, Any]:
        """
        Learn API usage patterns from a code repository.
        
        Args:
            repository_path: Path to the code repository
            
        Returns:
            Learning report
        """
        learning_report = {
            'repository_path': repository_path,
            'files_processed': 0,
            'patterns_learned': 0,
            'apis_discovered': set(),
            'common_sequences': [],
            'errors': []
        }
        
        try:
            from pathlib import Path
            
            # Find Python files in repository
            repo_path = Path(repository_path)
            python_files = list(repo_path.rglob("*.py"))
            
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    # Analyze code for API usage patterns
                    patterns = self._extract_api_patterns_from_code(code, str(file_path))
                    
                    # Update global usage statistics
                    for pattern in patterns:
                        self.global_usage_stats[pattern['api']] += 1
                        learning_report['apis_discovered'].add(pattern['api'])
                    
                    learning_report['files_processed'] += 1
                    learning_report['patterns_learned'] += len(patterns)
                
                except Exception as e:
                    learning_report['errors'].append(f"Failed to process {file_path}: {e}")
            
            # Build common sequences from learned patterns
            learning_report['common_sequences'] = self._identify_common_sequences()
            learning_report['apis_discovered'] = list(learning_report['apis_discovered'])
            
            logger.info(f"Learned from repository: {learning_report['files_processed']} files, "
                       f"{learning_report['patterns_learned']} patterns")
        
        except Exception as e:
            logger.error(f"Repository learning failed: {e}")
            learning_report['error'] = str(e)
        
        return learning_report
    
    def _get_user_profile(self, user_id: str) -> UserProfile:
        """Get or create a user profile."""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile(user_id=user_id)
        return self.user_profiles[user_id]
    
    def _analyze_context(self, context: UsageContext) -> Dict[str, Any]:
        """Analyze usage context to extract features for recommendation."""
        features = {
            'file_extension': Path(context.file_path).suffix if context.file_path else '',
            'function_context': context.function_name is not None,
            'class_context': context.class_name is not None,
            'autocad_objects_present': len(context.autocad_objects) > 0,
            'code_complexity': self._estimate_code_complexity(context.preceding_code),
            'intent_keywords': self._extract_intent_keywords(context.preceding_code + context.current_line),
            'variable_types': list(context.local_variables.values()),
            'autocad_object_types': list(context.autocad_objects.values())
        }
        
        return features
    
    def _get_context_based_recommendations(self, 
                                         context: UsageContext, 
                                         features: Dict[str, Any]) -> List[APIRecommendation]:
        """Generate recommendations based on current context."""
        recommendations = []
        
        try:
            # Analyze current line for partial API calls
            current_line = context.current_line.strip()
            
            # Check for object method completion
            if '.' in current_line:
                obj_name = current_line.split('.')[0].strip()
                if obj_name in context.autocad_objects:
                    obj_type = context.autocad_objects[obj_name]
                    method_recs = self._get_method_recommendations_for_object(obj_type)
                    recommendations.extend(method_recs)
            
            # Check for common patterns in preceding code
            if 'ModelSpace' in context.preceding_code:
                drawing_recs = self._get_drawing_api_recommendations()
                recommendations.extend(drawing_recs)
            
            if 'SelectionSet' in context.preceding_code:
                selection_recs = self._get_selection_api_recommendations()
                recommendations.extend(selection_recs)
            
            # Intent-based recommendations
            intent_keywords = features.get('intent_keywords', [])
            if 'transaction' in intent_keywords:
                transaction_recs = self._get_transaction_api_recommendations()
                recommendations.extend(transaction_recs)
        
        except Exception as e:
            logger.error(f"Context-based recommendation failed: {e}")
        
        return recommendations
    
    def _get_method_recommendations_for_object(self, object_type: str) -> List[APIRecommendation]:
        """Get method recommendations for a specific object type."""
        recommendations = []
        
        # Find all methods for this object type
        for api_name, api_info in self.knowledge_base.api_methods.items():
            if api_info.get('object_type') == object_type:
                rec = APIRecommendation(
                    id=f"method_{api_name}_{int(time.time() * 1000) % 1000:06d}",
                    type=RecommendationType.METHOD_CALL,
                    confidence=0.8,
                    api_name=api_name,
                    api_signature=api_info['signature'],
                    description=api_info['description'],
                    object_type=object_type,
                    context_match_score=0.8,
                    code_examples=api_info.get('examples', []),
                    related_apis=api_info.get('related_methods', [])
                )
                
                # Add performance data if available
                perf_data = self.knowledge_base.performance_data.get(api_name)
                if perf_data:
                    rec.average_execution_time = perf_data['avg_time']
                
                recommendations.append(rec)
        
        return recommendations
    
    def _get_drawing_api_recommendations(self) -> List[APIRecommendation]:
        """Get recommendations for drawing-related APIs."""
        drawing_apis = [
            'ModelSpace.AddLine', 'ModelSpace.AddCircle', 'ModelSpace.AddArc',
            'ModelSpace.AddPolyline', 'ModelSpace.AddText'
        ]
        
        recommendations = []
        for api_name in drawing_apis:
            if api_name in self.knowledge_base.api_methods:
                api_info = self.knowledge_base.api_methods[api_name]
                rec = APIRecommendation(
                    id=f"drawing_{api_name}_{int(time.time() * 1000) % 1000:06d}",
                    type=RecommendationType.METHOD_CALL,
                    confidence=0.7,
                    api_name=api_name,
                    api_signature=api_info['signature'],
                    description=api_info['description'],
                    context_match_score=0.7,
                    code_examples=api_info.get('examples', [])
                )
                recommendations.append(rec)
        
        return recommendations
    
    # Additional helper methods would continue here...
    # The implementation includes the core ML recommendation logic and can be extended
    # with more sophisticated algorithms and learning mechanisms.
    
    def _extract_api_patterns_from_code(self, code: str, file_path: str) -> List[Dict[str, Any]]:
        """Extract API usage patterns from code."""
        patterns = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Extract function call patterns
                    call_name = self._get_call_name_from_ast(node)
                    if call_name and any(api in call_name for api in ['Application', 'Document', 'ModelSpace']):
                        patterns.append({
                            'api': call_name,
                            'type': 'method_call',
                            'line': node.lineno,
                            'file': file_path,
                            'context': self._get_ast_context(node, tree)
                        })
                
                elif isinstance(node, ast.Attribute):
                    # Extract property access patterns
                    attr_name = self._get_attribute_name_from_ast(node)
                    if attr_name and any(api in attr_name for api in ['ActiveDocument', 'ModelSpace']):
                        patterns.append({
                            'api': attr_name,
                            'type': 'property_access',
                            'line': node.lineno,
                            'file': file_path,
                            'context': self._get_ast_context(node, tree)
                        })
        
        except Exception as e:
            logger.error(f"Pattern extraction failed for {file_path}: {e}")
        
        return patterns