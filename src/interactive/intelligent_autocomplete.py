"""
Advanced IntelliSense System with ML-Powered Suggestions
======================================================

Intelligent code completion system with specialized AutoCAD support including:
- Context-aware code completion with semantic analysis
- ML-powered suggestion ranking based on usage patterns
- AutoCAD API method prediction and parameter hints
- Smart import suggestions with dependency analysis
- Code pattern recognition and template suggestions
"""

import logging
import time
import ast
import inspect
import re
import json
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter, deque
import threading
from pathlib import Path
import pickle

# ML and statistical imports (with graceful fallbacks)
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# Import core components
from ..inspection.object_inspector import ObjectInspector
from ..inspection.method_discoverer import MethodDiscoverer
from .secure_evaluator import safe_eval, SecureEvaluationError

logger = logging.getLogger(__name__)


class SuggestionType(Enum):
    """Types of code completion suggestions."""
    METHOD = "method"
    PROPERTY = "property" 
    PARAMETER = "parameter"
    VARIABLE = "variable"
    IMPORT = "import"
    KEYWORD = "keyword"
    TEMPLATE = "template"
    AUTOCAD_API = "autocad_api"
    SNIPPET = "snippet"


class ContextType(Enum):
    """Types of code contexts for intelligent suggestions."""
    FUNCTION_CALL = "function_call"
    ATTRIBUTE_ACCESS = "attribute_access"
    IMPORT_STATEMENT = "import_statement"
    ASSIGNMENT = "assignment"
    FUNCTION_DEF = "function_def"
    CLASS_DEF = "class_def"
    AUTOCAD_CONTEXT = "autocad_context"
    UNKNOWN = "unknown"


@dataclass
class CodeSuggestion:
    """A code completion suggestion with metadata."""
    text: str
    type: SuggestionType
    confidence: float
    description: str = ""
    
    # Completion details
    insert_text: str = ""
    replace_range: Optional[Tuple[int, int]] = None
    trigger_characters: List[str] = field(default_factory=list)
    
    # Context information
    context_type: ContextType = ContextType.UNKNOWN
    required_imports: List[str] = field(default_factory=list)
    
    # AutoCAD-specific metadata
    autocad_object_type: Optional[str] = None
    autocad_method_category: Optional[str] = None
    parameter_hints: List[str] = field(default_factory=list)
    
    # ML-powered scoring
    usage_frequency: float = 0.0
    pattern_match_score: float = 0.0
    semantic_similarity: float = 0.0
    
    # Documentation
    documentation: str = ""
    example_code: str = ""


@dataclass
class CodeContext:
    """Context information for intelligent code completion."""
    file_path: str
    line_number: int
    column_number: int
    
    # Code content
    current_line: str
    preceding_lines: List[str]
    following_lines: List[str]
    
    # AST context
    current_scope: str
    enclosing_function: Optional[str] = None
    enclosing_class: Optional[str] = None
    
    # Variable context
    local_variables: Dict[str, str] = field(default_factory=dict)
    imported_modules: Set[str] = field(default_factory=set)
    
    # AutoCAD context
    autocad_objects: Dict[str, str] = field(default_factory=dict)
    active_document: bool = False
    in_transaction: bool = False


class UsagePattern:
    """Tracks usage patterns for ML-powered suggestions."""
    
    def __init__(self):
        self.method_frequencies = Counter()
        self.method_sequences = deque(maxlen=1000)
        self.context_patterns = defaultdict(Counter)
        self.autocad_patterns = defaultdict(Counter)
        self.user_preferences = defaultdict(float)
    
    def record_usage(self, 
                    method_name: str,
                    context: CodeContext,
                    suggestion_type: SuggestionType):
        """Record usage of a method or suggestion."""
        self.method_frequencies[method_name] += 1
        self.method_sequences.append((method_name, time.time()))
        
        # Record context patterns
        context_key = f"{context.enclosing_function or 'global'}:{context.current_scope}"
        self.context_patterns[context_key][method_name] += 1
        
        # Record AutoCAD-specific patterns
        if suggestion_type == SuggestionType.AUTOCAD_API:
            for obj_name, obj_type in context.autocad_objects.items():
                self.autocad_patterns[obj_type][method_name] += 1
    
    def get_frequency_score(self, method_name: str) -> float:
        """Get normalized frequency score for a method."""
        if not self.method_frequencies:
            return 0.0
        
        frequency = self.method_frequencies.get(method_name, 0)
        max_frequency = max(self.method_frequencies.values())
        return frequency / max_frequency if max_frequency > 0 else 0.0
    
    def get_sequence_score(self, method_name: str) -> float:
        """Get score based on recent usage sequence."""
        recent_methods = [m for m, t in self.method_sequences 
                         if time.time() - t < 300]  # Last 5 minutes
        
        if not recent_methods:
            return 0.0
        
        # Score based on recent usage and position
        score = 0.0
        for i, method in enumerate(reversed(recent_methods)):
            if method == method_name:
                # More recent usage gets higher score
                position_weight = (i + 1) / len(recent_methods)
                score = max(score, position_weight)
        
        return score


class AutoCADAPIDatabase:
    """Database of AutoCAD API methods and properties."""
    
    def __init__(self):
        self.api_methods = self._initialize_api_database()
        self.object_hierarchy = self._build_object_hierarchy()
        self.method_categories = self._categorize_methods()
    
    def _initialize_api_database(self) -> Dict[str, Dict[str, Any]]:
        """Initialize the AutoCAD API database."""
        return {
            'Application': {
                'methods': {
                    'GetInterfaceObject': {
                        'params': ['ProgID'],
                        'returns': 'object',
                        'description': 'Creates or gets an interface to an application object'
                    },
                    'LoadDVB': {
                        'params': ['FileName'],
                        'returns': 'void',
                        'description': 'Loads a DVB project file'
                    },
                    'Quit': {
                        'params': [],
                        'returns': 'void',
                        'description': 'Closes the AutoCAD application'
                    }
                },
                'properties': {
                    'ActiveDocument': 'Document',
                    'Documents': 'Documents',
                    'Preferences': 'Preferences',
                    'Version': 'str',
                    'Visible': 'bool'
                }
            },
            'Document': {
                'methods': {
                    'Close': {
                        'params': ['SaveChanges', 'FileName'],
                        'returns': 'void',
                        'description': 'Closes the document'
                    },
                    'Save': {
                        'params': [],
                        'returns': 'void',
                        'description': 'Saves the document'
                    },
                    'SaveAs': {
                        'params': ['FileName', 'FileType'],
                        'returns': 'void',
                        'description': 'Saves the document with a new name'
                    },
                    'SendCommand': {
                        'params': ['Command'],
                        'returns': 'void',
                        'description': 'Sends a command string to AutoCAD'
                    }
                },
                'properties': {
                    'ModelSpace': 'ModelSpace',
                    'PaperSpace': 'PaperSpace',
                    'Blocks': 'Blocks',
                    'Layers': 'Layers',
                    'Name': 'str',
                    'Path': 'str'
                }
            },
            'ModelSpace': {
                'methods': {
                    'AddLine': {
                        'params': ['StartPoint', 'EndPoint'],
                        'returns': 'AcadLine',
                        'description': 'Creates a line object'
                    },
                    'AddCircle': {
                        'params': ['Center', 'Radius'],
                        'returns': 'AcadCircle',
                        'description': 'Creates a circle object'
                    },
                    'AddText': {
                        'params': ['TextString', 'InsertionPoint', 'Height'],
                        'returns': 'AcadText',
                        'description': 'Creates a text object'
                    },
                    'AddPolyline': {
                        'params': ['VertexList'],
                        'returns': 'AcadLWPolyline',
                        'description': 'Creates a polyline object'
                    }
                },
                'properties': {
                    'Count': 'int',
                    'Name': 'str'
                }
            },
            'SelectionSet': {
                'methods': {
                    'Select': {
                        'params': ['Mode', 'Point1', 'Point2', 'FilterType', 'FilterData'],
                        'returns': 'void',
                        'description': 'Selects objects in the drawing'
                    },
                    'SelectOnScreen': {
                        'params': ['FilterType', 'FilterData'],
                        'returns': 'void',
                        'description': 'Prompts user to select objects'
                    },
                    'Clear': {
                        'params': [],
                        'returns': 'void',
                        'description': 'Clears the selection set'
                    }
                },
                'properties': {
                    'Count': 'int',
                    'Name': 'str'
                }
            }
        }
    
    def _build_object_hierarchy(self) -> Dict[str, List[str]]:
        """Build AutoCAD object hierarchy."""
        return {
            'Application': ['Document', 'Documents', 'Preferences'],
            'Document': ['ModelSpace', 'PaperSpace', 'Blocks', 'Layers', 'SelectionSets'],
            'ModelSpace': ['AcadLine', 'AcadCircle', 'AcadText', 'AcadPolyline'],
            'SelectionSet': ['AcadEntity']
        }
    
    def _categorize_methods(self) -> Dict[str, List[str]]:
        """Categorize AutoCAD methods by functionality."""
        return {
            'Creation': ['Add', 'Create', 'Insert'],
            'Modification': ['Modify', 'Update', 'Set', 'Move', 'Rotate', 'Scale'],
            'Query': ['Get', 'Find', 'Select', 'Count'],
            'Document': ['Open', 'Close', 'Save', 'New'],
            'Transaction': ['Start', 'Commit', 'Abort']
        }
    
    def get_methods_for_object(self, object_type: str) -> List[Dict[str, Any]]:
        """Get available methods for an AutoCAD object type."""
        if object_type in self.api_methods:
            methods = []
            for method_name, method_info in self.api_methods[object_type]['methods'].items():
                methods.append({
                    'name': method_name,
                    'type': SuggestionType.AUTOCAD_API,
                    'params': method_info['params'],
                    'returns': method_info['returns'],
                    'description': method_info['description']
                })
            return methods
        return []
    
    def get_properties_for_object(self, object_type: str) -> List[Dict[str, Any]]:
        """Get available properties for an AutoCAD object type."""
        if object_type in self.api_methods:
            properties = []
            for prop_name, prop_type in self.api_methods[object_type]['properties'].items():
                properties.append({
                    'name': prop_name,
                    'type': SuggestionType.PROPERTY,
                    'data_type': prop_type,
                    'description': f'{prop_name} property of type {prop_type}'
                })
            return properties
        return []


class MLSuggestionEngine:
    """Machine learning-powered suggestion engine."""
    
    def __init__(self):
        self.vectorizer = None
        self.suggestion_vectors = None
        self.suggestion_names = []
        self.model_trained = False
        
        if HAS_SKLEARN and HAS_NUMPY:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            logger.info("ML suggestion engine initialized with sklearn support")
        else:
            logger.warning("ML libraries not available, using fallback suggestion engine")
    
    def train_model(self, training_data: List[Dict[str, Any]]):
        """Train the ML model with code completion data."""
        if not HAS_SKLEARN or not HAS_NUMPY:
            logger.warning("Cannot train ML model without sklearn and numpy")
            return
        
        try:
            # Extract text features from training data
            texts = []
            names = []
            
            for item in training_data:
                context_text = f"{item.get('context', '')} {item.get('description', '')}"
                texts.append(context_text)
                names.append(item.get('name', ''))
            
            if texts:
                self.suggestion_vectors = self.vectorizer.fit_transform(texts)
                self.suggestion_names = names
                self.model_trained = True
                logger.info(f"ML model trained with {len(training_data)} samples")
        
        except Exception as e:
            logger.error(f"Failed to train ML model: {e}")
    
    def get_similarity_scores(self, query_context: str) -> Dict[str, float]:
        """Get similarity scores for suggestions based on context."""
        if not self.model_trained or not HAS_SKLEARN:
            return {}
        
        try:
            query_vector = self.vectorizer.transform([query_context])
            similarities = cosine_similarity(query_vector, self.suggestion_vectors)[0]
            
            scores = {}
            for i, name in enumerate(self.suggestion_names):
                scores[name] = float(similarities[i])
            
            return scores
        
        except Exception as e:
            logger.error(f"Failed to compute similarity scores: {e}")
            return {}


class IntelligentAutoComplete:
    """
    Advanced IntelliSense system with ML-powered suggestions.
    
    Provides context-aware code completion with specialized AutoCAD support,
    usage pattern learning, and intelligent suggestion ranking.
    """
    
    def __init__(self):
        """Initialize the intelligent autocomplete system."""
        self.object_inspector = ObjectInspector()
        self.method_discoverer = MethodDiscoverer()
        self.autocad_db = AutoCADAPIDatabase()
        self.usage_patterns = UsagePattern()
        self.ml_engine = MLSuggestionEngine()
        
        # Caching
        self.suggestion_cache = {}
        self.context_cache = {}
        self.cache_timeout = 30  # seconds
        
        # Configuration
        self.max_suggestions = 20
        self.min_confidence = 0.1
        self.enable_ml_ranking = HAS_SKLEARN and HAS_NUMPY
        
        # Threading
        self.lock = threading.RLock()
        
        # Initialize with basic training data
        self._initialize_training_data()
        
        logger.info("Intelligent autocomplete system initialized")
    
    def get_completions(self, 
                       context: CodeContext,
                       trigger_character: Optional[str] = None) -> List[CodeSuggestion]:
        """
        Get intelligent code completion suggestions.
        
        Args:
            context: Current code context
            trigger_character: Character that triggered completion
            
        Returns:
            List of ranked code suggestions
        """
        cache_key = self._get_cache_key(context, trigger_character)
        
        # Check cache first
        if cache_key in self.suggestion_cache:
            cached_result = self.suggestion_cache[cache_key]
            if time.time() - cached_result['timestamp'] < self.cache_timeout:
                return cached_result['suggestions']
        
        suggestions = []
        
        try:
            # Determine context type
            context_type = self._analyze_context_type(context, trigger_character)
            
            # Generate suggestions based on context type
            if trigger_character == '.':
                suggestions.extend(self._get_attribute_suggestions(context))
            elif trigger_character == '(':
                suggestions.extend(self._get_parameter_suggestions(context))
            elif context_type == ContextType.IMPORT_STATEMENT:
                suggestions.extend(self._get_import_suggestions(context))
            elif context_type == ContextType.AUTOCAD_CONTEXT:
                suggestions.extend(self._get_autocad_suggestions(context))
            else:
                suggestions.extend(self._get_general_suggestions(context))
            
            # Apply ML-powered ranking if available
            if self.enable_ml_ranking:
                suggestions = self._apply_ml_ranking(suggestions, context)
            
            # Apply usage pattern scoring
            suggestions = self._apply_usage_patterns(suggestions, context)
            
            # Sort by confidence and limit results
            suggestions.sort(key=lambda s: s.confidence, reverse=True)
            suggestions = suggestions[:self.max_suggestions]
            
            # Filter by minimum confidence
            suggestions = [s for s in suggestions if s.confidence >= self.min_confidence]
            
            # Cache results
            with self.lock:
                self.suggestion_cache[cache_key] = {
                    'suggestions': suggestions,
                    'timestamp': time.time()
                }
            
            return suggestions
        
        except Exception as e:
            logger.error(f"Failed to get completions: {e}")
            return []
    
    def record_completion_usage(self, 
                              suggestion: CodeSuggestion,
                              context: CodeContext):
        """Record usage of a completion suggestion for learning."""
        try:
            self.usage_patterns.record_usage(
                suggestion.text,
                context,
                suggestion.type
            )
            
            # Update user preferences
            self.usage_patterns.user_preferences[suggestion.text] += 0.1
            
            logger.debug(f"Recorded usage of suggestion: {suggestion.text}")
        
        except Exception as e:
            logger.error(f"Failed to record completion usage: {e}")
    
    def get_signature_help(self, 
                          context: CodeContext,
                          function_name: str) -> Optional[Dict[str, Any]]:
        """
        Get signature help for a function call.
        
        Args:
            context: Current code context
            function_name: Name of the function
            
        Returns:
            Signature help information
        """
        try:
            # Check AutoCAD API database first
            for obj_type, api_info in self.autocad_db.api_methods.items():
                if function_name in api_info['methods']:
                    method_info = api_info['methods'][function_name]
                    return {
                        'function_name': function_name,
                        'parameters': method_info['params'],
                        'return_type': method_info['returns'],
                        'description': method_info['description'],
                        'is_autocad_api': True
                    }
            
            # Try to get signature from inspection
            for var_name, var_type in context.local_variables.items():
                if hasattr(var_type, function_name):
                    try:
                        method = getattr(var_type, function_name)
                        if callable(method):
                            sig = inspect.signature(method)
                            return {
                                'function_name': function_name,
                                'parameters': list(sig.parameters.keys()),
                                'signature': str(sig),
                                'is_autocad_api': False
                            }
                    except Exception:
                        pass
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get signature help: {e}")
            return None
    
    def get_hover_information(self, 
                            context: CodeContext,
                            symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get hover information for a symbol.
        
        Args:
            context: Current code context
            symbol: Symbol to get information for
            
        Returns:
            Hover information
        """
        try:
            # Check if it's an AutoCAD API symbol
            for obj_type, api_info in self.autocad_db.api_methods.items():
                if symbol in api_info['methods']:
                    method_info = api_info['methods'][symbol]
                    return {
                        'symbol': symbol,
                        'type': 'AutoCAD API Method',
                        'description': method_info['description'],
                        'parameters': method_info['params'],
                        'returns': method_info['returns']
                    }
                elif symbol in api_info['properties']:
                    prop_type = api_info['properties'][symbol]
                    return {
                        'symbol': symbol,
                        'type': 'AutoCAD API Property',
                        'data_type': prop_type,
                        'description': f'{symbol} property of type {prop_type}'
                    }
            
            # Check local variables
            if symbol in context.local_variables:
                var_type = context.local_variables[symbol]
                return {
                    'symbol': symbol,
                    'type': 'Local Variable',
                    'data_type': var_type,
                    'description': f'Local variable of type {var_type}'
                }
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get hover information: {e}")
            return None
    
    def _analyze_context_type(self, 
                            context: CodeContext,
                            trigger_character: Optional[str]) -> ContextType:
        """Analyze the type of code context."""
        current_line = context.current_line.strip()
        
        if trigger_character == '.':
            return ContextType.ATTRIBUTE_ACCESS
        elif trigger_character == '(':
            return ContextType.FUNCTION_CALL
        elif current_line.startswith('import ') or current_line.startswith('from '):
            return ContextType.IMPORT_STATEMENT
        elif current_line.startswith('def '):
            return ContextType.FUNCTION_DEF
        elif current_line.startswith('class '):
            return ContextType.CLASS_DEF
        elif any(obj in current_line for obj in context.autocad_objects.keys()):
            return ContextType.AUTOCAD_CONTEXT
        elif '=' in current_line:
            return ContextType.ASSIGNMENT
        else:
            return ContextType.UNKNOWN
    
    def _get_attribute_suggestions(self, context: CodeContext) -> List[CodeSuggestion]:
        """Get suggestions for attribute access (after '.')."""
        suggestions = []
        
        # Parse the object before the dot
        line_before_cursor = context.current_line[:context.column_number]
        match = re.search(r'(\w+)\.$', line_before_cursor)
        
        if match:
            object_name = match.group(1)
            
            # Check if it's an AutoCAD object
            if object_name in context.autocad_objects:
                object_type = context.autocad_objects[object_name]
                
                # Get AutoCAD API suggestions
                methods = self.autocad_db.get_methods_for_object(object_type)
                properties = self.autocad_db.get_properties_for_object(object_type)
                
                for method in methods:
                    suggestions.append(CodeSuggestion(
                        text=method['name'],
                        type=SuggestionType.AUTOCAD_API,
                        confidence=0.9,
                        description=method['description'],
                        insert_text=f"{method['name']}()",
                        autocad_object_type=object_type,
                        autocad_method_category=self._get_method_category(method['name']),
                        parameter_hints=method['params']
                    ))
                
                for prop in properties:
                    suggestions.append(CodeSuggestion(
                        text=prop['name'],
                        type=SuggestionType.PROPERTY,
                        confidence=0.8,
                        description=prop['description'],
                        autocad_object_type=object_type
                    ))
            
            # Try to get suggestions from local variables
            elif object_name in context.local_variables:
                var_type = context.local_variables[object_name]
                # This would require more sophisticated type analysis
                # For now, provide generic suggestions
                suggestions.append(CodeSuggestion(
                    text="__dict__",
                    type=SuggestionType.PROPERTY,
                    confidence=0.3,
                    description="Object's namespace as a dictionary"
                ))
        
        return suggestions
    
    def _get_parameter_suggestions(self, context: CodeContext) -> List[CodeSuggestion]:
        """Get parameter suggestions for function calls."""
        suggestions = []
        
        # Extract function name from context
        line_before_cursor = context.current_line[:context.column_number]
        match = re.search(r'(\w+)\($', line_before_cursor)
        
        if match:
            function_name = match.group(1)
            
            # Get signature help and convert to parameter suggestions
            sig_help = self.get_signature_help(context, function_name)
            if sig_help:
                for param in sig_help['parameters']:
                    suggestions.append(CodeSuggestion(
                        text=param,
                        type=SuggestionType.PARAMETER,
                        confidence=0.8,
                        description=f"Parameter for {function_name}",
                        insert_text=f"{param}=",
                        parameter_hints=[param]
                    ))
        
        return suggestions
    
    def _get_import_suggestions(self, context: CodeContext) -> List[CodeSuggestion]:
        """Get import suggestions."""
        suggestions = []
        
        # Common AutoCAD-related imports
        autocad_imports = [
            "win32com.client",
            "pyautocad",
            "comtypes.client",
            "pythoncom"
        ]
        
        for imp in autocad_imports:
            suggestions.append(CodeSuggestion(
                text=imp,
                type=SuggestionType.IMPORT,
                confidence=0.7,
                description=f"Import {imp} for AutoCAD integration",
                required_imports=[imp]
            ))
        
        return suggestions
    
    def _get_autocad_suggestions(self, context: CodeContext) -> List[CodeSuggestion]:
        """Get AutoCAD-specific suggestions."""
        suggestions = []
        
        # Common AutoCAD patterns
        autocad_snippets = [
            {
                'name': 'AutoCAD Application',
                'code': 'acad = win32com.client.Dispatch("AutoCAD.Application")',
                'description': 'Connect to AutoCAD application'
            },
            {
                'name': 'Active Document',
                'code': 'doc = acad.ActiveDocument',
                'description': 'Get the active document'
            },
            {
                'name': 'Model Space',
                'code': 'mspace = doc.ModelSpace',
                'description': 'Get model space for drawing'
            },
            {
                'name': 'Start Transaction',
                'code': 'doc.StartTransaction()',
                'description': 'Start a transaction for batch operations'
            }
        ]
        
        for snippet in autocad_snippets:
            suggestions.append(CodeSuggestion(
                text=snippet['name'],
                type=SuggestionType.SNIPPET,
                confidence=0.8,
                description=snippet['description'],
                insert_text=snippet['code'],
                autocad_method_category='Common Patterns'
            ))
        
        return suggestions
    
    def _get_general_suggestions(self, context: CodeContext) -> List[CodeSuggestion]:
        """Get general code suggestions."""
        suggestions = []
        
        # Python keywords
        python_keywords = [
            'def', 'class', 'if', 'elif', 'else', 'for', 'while',
            'try', 'except', 'finally', 'with', 'import', 'from',
            'return', 'yield', 'break', 'continue', 'pass'
        ]
        
        for keyword in python_keywords:
            suggestions.append(CodeSuggestion(
                text=keyword,
                type=SuggestionType.KEYWORD,
                confidence=0.4,
                description=f"Python keyword: {keyword}"
            ))
        
        # Local variables
        for var_name, var_type in context.local_variables.items():
            suggestions.append(CodeSuggestion(
                text=var_name,
                type=SuggestionType.VARIABLE,
                confidence=0.6,
                description=f"Local variable of type {var_type}"
            ))
        
        return suggestions
    
    def _apply_ml_ranking(self, 
                         suggestions: List[CodeSuggestion],
                         context: CodeContext) -> List[CodeSuggestion]:
        """Apply ML-powered ranking to suggestions."""
        if not self.ml_engine.model_trained:
            return suggestions
        
        try:
            # Create context string for similarity matching
            context_text = f"{context.current_line} {context.enclosing_function or ''} {context.enclosing_class or ''}"
            
            similarity_scores = self.ml_engine.get_similarity_scores(context_text)
            
            # Update suggestion confidences based on ML scores
            for suggestion in suggestions:
                ml_score = similarity_scores.get(suggestion.text, 0.0)
                suggestion.semantic_similarity = ml_score
                # Boost confidence for high similarity scores
                suggestion.confidence = min(1.0, suggestion.confidence + ml_score * 0.3)
        
        except Exception as e:
            logger.error(f"Failed to apply ML ranking: {e}")
        
        return suggestions
    
    def _apply_usage_patterns(self, 
                            suggestions: List[CodeSuggestion],
                            context: CodeContext) -> List[CodeSuggestion]:
        """Apply usage pattern scoring to suggestions."""
        for suggestion in suggestions:
            # Frequency-based scoring
            frequency_score = self.usage_patterns.get_frequency_score(suggestion.text)
            suggestion.usage_frequency = frequency_score
            
            # Recent usage scoring
            sequence_score = self.usage_patterns.get_sequence_score(suggestion.text)
            
            # User preference scoring
            preference_score = self.usage_patterns.user_preferences.get(suggestion.text, 0.0)
            preference_score = min(1.0, preference_score)  # Cap at 1.0
            
            # Combine scores
            pattern_bonus = (frequency_score * 0.3 + sequence_score * 0.4 + preference_score * 0.3)
            suggestion.pattern_match_score = pattern_bonus
            suggestion.confidence = min(1.0, suggestion.confidence + pattern_bonus * 0.2)
        
        return suggestions
    
    def _get_method_category(self, method_name: str) -> str:
        """Get the category of an AutoCAD method."""
        for category, prefixes in self.autocad_db.method_categories.items():
            if any(method_name.startswith(prefix) for prefix in prefixes):
                return category
        return "Other"
    
    def _get_cache_key(self, context: CodeContext, trigger_character: Optional[str]) -> str:
        """Generate a cache key for the context."""
        return f"{context.file_path}:{context.line_number}:{context.column_number}:{trigger_character}"
    
    def _initialize_training_data(self):
        """Initialize the ML engine with basic training data."""
        if not self.enable_ml_ranking:
            return
        
        training_data = []
        
        # AutoCAD API training data
        for obj_type, api_info in self.autocad_db.api_methods.items():
            for method_name, method_info in api_info['methods'].items():
                training_data.append({
                    'name': method_name,
                    'context': f'autocad {obj_type.lower()}',
                    'description': method_info['description']
                })
        
        # Common Python patterns
        python_patterns = [
            {'name': 'def', 'context': 'function definition', 'description': 'Define a function'},
            {'name': 'class', 'context': 'class definition', 'description': 'Define a class'},
            {'name': 'if', 'context': 'conditional', 'description': 'Conditional statement'},
            {'name': 'for', 'context': 'loop iteration', 'description': 'For loop'},
            {'name': 'while', 'context': 'loop condition', 'description': 'While loop'}
        ]
        
        training_data.extend(python_patterns)
        
        # Train the model
        self.ml_engine.train_model(training_data)
        logger.info(f"Initialized ML engine with {len(training_data)} training samples")