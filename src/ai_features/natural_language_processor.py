"""
Natural Language Processing Engine for AutoCAD Commands
=====================================================

Advanced NLP system for translating natural language descriptions into AutoCAD commands including:
- Intent recognition and parameter extraction from natural language
- Command mapping with context-aware interpretation  
- Multi-step operation planning from complex descriptions
- AutoCAD-specific entity and action recognition
- Code generation from natural language specifications
"""

import logging
import re
import json
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import time
import ast
from collections import defaultdict, Counter

# NLP libraries with graceful fallbacks
try:
    import spacy
    HAS_SPACY = True
    # Try to load English model
    try:
        nlp_model = spacy.load("en_core_web_sm")
    except OSError:
        nlp_model = None
        logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
except ImportError:
    HAS_SPACY = False
    spacy = None
    nlp_model = None

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False
    TextBlob = None

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of intents for AutoCAD commands."""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    QUERY = "query"
    SELECT = "select"
    MOVE = "move"
    COPY = "copy"
    ROTATE = "rotate"
    SCALE = "scale"
    MEASURE = "measure"
    LAYER = "layer"
    BLOCK = "block"
    DIMENSION = "dimension"
    TEXT = "text"
    HATCH = "hatch"
    PLOT = "plot"
    SAVE = "save"
    OPEN = "open"
    UNKNOWN = "unknown"


class EntityType(Enum):
    """Types of AutoCAD entities."""
    LINE = "line"
    CIRCLE = "circle"
    ARC = "arc"
    RECTANGLE = "rectangle"
    POLYGON = "polygon"
    POLYLINE = "polyline"
    SPLINE = "spline"
    TEXT = "text"
    DIMENSION = "dimension"
    BLOCK = "block"
    HATCH = "hatch"
    POINT = "point"
    ELLIPSE = "ellipse"
    REGION = "region"
    SOLID = "solid"
    UNKNOWN = "unknown"


@dataclass
class GeometricParameter:
    """Geometric parameter extracted from natural language."""
    name: str
    value: Union[float, Tuple[float, ...], str]
    unit: Optional[str] = None
    type: str = "numeric"  # numeric, coordinate, text, boolean


@dataclass
class NLCommand:
    """A natural language command parsed into structured data."""
    original_text: str
    intent: IntentType
    entity_type: EntityType
    confidence: float
    
    # Parameters
    parameters: Dict[str, GeometricParameter] = field(default_factory=dict)
    coordinates: List[Tuple[float, float]] = field(default_factory=list)
    
    # Context
    layer_name: Optional[str] = None
    block_name: Optional[str] = None
    selection_criteria: Optional[str] = None
    
    # Generated code
    autocad_commands: List[str] = field(default_factory=list)
    python_code: Optional[str] = None
    
    # Metadata
    processing_time: float = 0.0
    requires_interaction: bool = False
    error_message: Optional[str] = None


@dataclass
class CommandTemplate:
    """Template for generating AutoCAD commands from intents."""
    intent: IntentType
    entity_type: EntityType
    template: str
    required_params: List[str]
    optional_params: List[str] = field(default_factory=list)
    python_template: Optional[str] = None
    examples: List[str] = field(default_factory=list)


class AutoCADNLPEngine:
    """
    Natural Language Processing engine for AutoCAD commands.
    
    Translates natural language descriptions into executable AutoCAD commands
    with intelligent parameter extraction and context awareness.
    """
    
    def __init__(self):
        """Initialize the NLP engine."""
        self.command_templates = self._load_command_templates()
        self.entity_patterns = self._load_entity_patterns()
        self.intent_patterns = self._load_intent_patterns()
        self.parameter_extractors = self._load_parameter_extractors()
        
        # Vocabulary and synonyms
        self.entity_synonyms = self._load_entity_synonyms()
        self.action_synonyms = self._load_action_synonyms()
        self.measurement_units = self._load_measurement_units()
        
        # Processing cache
        self.command_cache = {}
        self.cache_timeout = 300  # 5 minutes
        
        # Statistics
        self.processing_stats = {
            'total_commands': 0,
            'successful_parses': 0,
            'failed_parses': 0,
            'average_confidence': 0.0
        }
        
        logger.info(f"AutoCAD NLP engine initialized (spaCy: {HAS_SPACY}, TextBlob: {HAS_TEXTBLOB})")
    
    def process_natural_language(self, text: str, context: Optional[Dict[str, Any]] = None) -> NLCommand:
        """
        Process natural language text into AutoCAD commands.
        
        Args:
            text: Natural language description
            context: Optional context information
            
        Returns:
            Structured command with AutoCAD code
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{text.lower().strip()}_{hash(str(context))}"
        if cache_key in self.command_cache:
            cached_result = self.command_cache[cache_key]
            if time.time() - cached_result['timestamp'] < self.cache_timeout:
                return cached_result['command']
        
        try:
            # Clean and normalize input
            cleaned_text = self._clean_text(text)
            
            # Extract intent and entity type
            intent = self._extract_intent(cleaned_text)
            entity_type = self._extract_entity_type(cleaned_text)
            
            # Create base command structure
            command = NLCommand(
                original_text=text,
                intent=intent,
                entity_type=entity_type,
                confidence=0.0
            )
            
            # Extract parameters
            parameters = self._extract_parameters(cleaned_text, intent, entity_type)
            command.parameters = parameters
            
            # Extract coordinates if present
            coordinates = self._extract_coordinates(cleaned_text)
            command.coordinates = coordinates
            
            # Extract context information
            self._extract_context(command, cleaned_text, context)
            
            # Calculate confidence score
            command.confidence = self._calculate_confidence(command, cleaned_text)
            
            # Generate AutoCAD commands
            if command.confidence > 0.5:
                self._generate_autocad_commands(command)
                self._generate_python_code(command)
            else:
                command.error_message = f"Low confidence ({command.confidence:.2f}) - unable to generate reliable commands"
            
            # Record processing time
            command.processing_time = time.time() - start_time
            
            # Update statistics
            self._update_statistics(command)
            
            # Cache result
            self.command_cache[cache_key] = {
                'command': command,
                'timestamp': time.time()
            }
            
            return command
        
        except Exception as e:
            logger.error(f"Failed to process natural language: {e}")
            error_command = NLCommand(
                original_text=text,
                intent=IntentType.UNKNOWN,
                entity_type=EntityType.UNKNOWN,
                confidence=0.0,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
            return error_command
    
    def get_command_suggestions(self, partial_text: str, limit: int = 5) -> List[str]:
        """
        Get command suggestions for partial natural language input.
        
        Args:
            partial_text: Partial natural language input
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested complete commands
        """
        suggestions = []
        
        try:
            # Extract partial intent and entity
            intent = self._extract_intent(partial_text)
            entity_type = self._extract_entity_type(partial_text)
            
            # Get matching templates
            matching_templates = [
                template for template in self.command_templates
                if template.intent == intent or template.entity_type == entity_type
            ]
            
            # Generate suggestions from templates
            for template in matching_templates[:limit]:
                for example in template.examples:
                    if len(suggestions) < limit:
                        suggestions.append(example)
            
            # Add common variations
            if intent != IntentType.UNKNOWN:
                common_phrases = self._get_common_phrases_for_intent(intent)
                suggestions.extend(common_phrases[:limit - len(suggestions)])
        
        except Exception as e:
            logger.error(f"Failed to get command suggestions: {e}")
        
        return suggestions[:limit]
    
    def explain_command(self, command: NLCommand) -> Dict[str, Any]:
        """
        Provide detailed explanation of how a command was interpreted.
        
        Args:
            command: Parsed natural language command
            
        Returns:
            Detailed explanation
        """
        explanation = {
            'original_text': command.original_text,
            'interpretation': {
                'intent': command.intent.value,
                'entity_type': command.entity_type.value,
                'confidence': command.confidence
            },
            'extracted_parameters': {},
            'generated_commands': command.autocad_commands,
            'reasoning': []
        }
        
        # Explain parameters
        for param_name, param in command.parameters.items():
            explanation['extracted_parameters'][param_name] = {
                'value': param.value,
                'type': param.type,
                'unit': param.unit
            }
        
        # Add reasoning steps
        explanation['reasoning'].extend([
            f"Identified intent as '{command.intent.value}' based on action words in the text",
            f"Recognized entity type as '{command.entity_type.value}' from object references",
            f"Extracted {len(command.parameters)} parameters from the description",
            f"Generated {len(command.autocad_commands)} AutoCAD commands"
        ])
        
        if command.error_message:
            explanation['error'] = command.error_message
        
        return explanation
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text."""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Expand common contractions
        contractions = {
            "can't": "cannot",
            "won't": "will not",
            "n't": " not",
            "'ll": " will",
            "'re": " are",
            "'ve": " have",
            "'d": " would"
        }
        
        for contraction, expansion in contractions.items():
            text = text.replace(contraction, expansion)
        
        return text
    
    def _extract_intent(self, text: str) -> IntentType:
        """Extract the intent from natural language text."""
        # Check explicit intent patterns
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return IntentType(intent)
        
        # Check action synonyms
        words = text.split()
        for word in words:
            for intent, synonyms in self.action_synonyms.items():
                if word in synonyms:
                    return IntentType(intent)
        
        # Use spaCy for more sophisticated analysis if available
        if nlp_model:
            try:
                doc = nlp_model(text)
                for token in doc:
                    if token.pos_ == "VERB":
                        verb_lemma = token.lemma_
                        for intent, synonyms in self.action_synonyms.items():
                            if verb_lemma in synonyms:
                                return IntentType(intent)
            except Exception:
                pass
        
        return IntentType.UNKNOWN
    
    def _extract_entity_type(self, text: str) -> EntityType:
        """Extract the entity type from natural language text."""
        # Check explicit entity patterns
        for entity, patterns in self.entity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return EntityType(entity)
        
        # Check entity synonyms
        words = text.split()
        for word in words:
            for entity, synonyms in self.entity_synonyms.items():
                if word in synonyms:
                    return EntityType(entity)
        
        # Use spaCy for named entity recognition if available
        if nlp_model:
            try:
                doc = nlp_model(text)
                for ent in doc.ents:
                    if ent.label_ in ["ORG", "PRODUCT"]:  # Might indicate CAD objects
                        entity_text = ent.text.lower()
                        for entity, synonyms in self.entity_synonyms.items():
                            if entity_text in synonyms:
                                return EntityType(entity)
            except Exception:
                pass
        
        return EntityType.UNKNOWN
    
    def _extract_parameters(self, text: str, intent: IntentType, entity_type: EntityType) -> Dict[str, GeometricParameter]:
        """Extract parameters from natural language text."""
        parameters = {}
        
        # Extract numeric parameters
        numeric_matches = re.finditer(r'(\d+(?:\.\d+)?)\s*(\w+)?', text)
        numeric_values = []
        
        for match in numeric_matches:
            value = float(match.group(1))
            unit = match.group(2) if match.group(2) else None
            
            # Check if unit is a measurement unit
            if unit and unit.lower() in self.measurement_units:
                unit = self.measurement_units[unit.lower()]
            
            numeric_values.append((value, unit))
        
        # Assign parameters based on entity type and intent
        if entity_type == EntityType.CIRCLE:
            if numeric_values:
                parameters['radius'] = GeometricParameter(
                    name='radius',
                    value=numeric_values[0][0],
                    unit=numeric_values[0][1],
                    type='numeric'
                )
        
        elif entity_type == EntityType.RECTANGLE:
            if len(numeric_values) >= 2:
                parameters['width'] = GeometricParameter(
                    name='width',
                    value=numeric_values[0][0],
                    unit=numeric_values[0][1],
                    type='numeric'
                )
                parameters['height'] = GeometricParameter(
                    name='height',
                    value=numeric_values[1][0],
                    unit=numeric_values[1][1],
                    type='numeric'
                )
        
        elif entity_type == EntityType.LINE:
            if len(numeric_values) >= 1:
                parameters['length'] = GeometricParameter(
                    name='length',
                    value=numeric_values[0][0],
                    unit=numeric_values[0][1],
                    type='numeric'
                )
        
        # Extract text parameters (for text entities)
        if entity_type == EntityType.TEXT:
            text_match = re.search(r'["\']([^"\']+)["\']', text)
            if text_match:
                parameters['text_content'] = GeometricParameter(
                    name='text_content',
                    value=text_match.group(1),
                    type='text'
                )
            
            # Extract text height
            height_match = re.search(r'height\s+(\d+(?:\.\d+)?)', text)
            if height_match:
                parameters['height'] = GeometricParameter(
                    name='height',
                    value=float(height_match.group(1)),
                    type='numeric'
                )
        
        # Extract color parameters
        color_match = re.search(r'color\s+(\w+)', text)
        if color_match:
            parameters['color'] = GeometricParameter(
                name='color',
                value=color_match.group(1),
                type='text'
            )
        
        # Extract layer parameters
        layer_match = re.search(r'layer\s+(\w+)', text)
        if layer_match:
            parameters['layer'] = GeometricParameter(
                name='layer',
                value=layer_match.group(1),
                type='text'
            )
        
        return parameters
    
    def _extract_coordinates(self, text: str) -> List[Tuple[float, float]]:
        """Extract coordinate pairs from natural language text."""
        coordinates = []
        
        # Pattern for coordinate pairs like (10, 20) or "at 10,20"
        coord_patterns = [
            r'\((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\)',
            r'at\s+(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)',
            r'from\s+(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)',
            r'to\s+(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)'
        ]
        
        for pattern in coord_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                x = float(match.group(1))
                y = float(match.group(2))
                coordinates.append((x, y))
        
        return coordinates
    
    def _extract_context(self, command: NLCommand, text: str, context: Optional[Dict[str, Any]]):
        """Extract context information like layer names, block references, etc."""
        # Extract layer name
        layer_match = re.search(r'on\s+layer\s+(\w+)', text)
        if layer_match:
            command.layer_name = layer_match.group(1)
        
        # Extract block reference
        block_match = re.search(r'block\s+(\w+)', text)
        if block_match:
            command.block_name = block_match.group(1)
        
        # Extract selection criteria
        selection_patterns = [
            r'select\s+(.+?)(?:\s+(?:and|or|then)|\s*$)',
            r'all\s+(\w+)',
            r'(\w+)s?\s+that\s+(.+)'
        ]
        
        for pattern in selection_patterns:
            match = re.search(pattern, text)
            if match:
                command.selection_criteria = match.group(1)
                break
        
        # Apply external context if provided
        if context:
            if 'current_layer' in context and not command.layer_name:
                command.layer_name = context['current_layer']
            
            if 'active_block' in context and not command.block_name:
                command.block_name = context['active_block']
    
    def _calculate_confidence(self, command: NLCommand, text: str) -> float:
        """Calculate confidence score for the parsed command."""
        confidence = 0.0
        
        # Base confidence from intent and entity recognition
        if command.intent != IntentType.UNKNOWN:
            confidence += 0.3
        if command.entity_type != EntityType.UNKNOWN:
            confidence += 0.3
        
        # Boost confidence for extracted parameters
        if command.parameters:
            confidence += min(0.2, len(command.parameters) * 0.05)
        
        # Boost confidence for coordinates
        if command.coordinates:
            confidence += min(0.1, len(command.coordinates) * 0.05)
        
        # Penalize for ambiguous language
        ambiguous_words = ['maybe', 'might', 'could', 'perhaps', 'possibly']
        for word in ambiguous_words:
            if word in text:
                confidence -= 0.1
        
        # Boost confidence for specific measurements
        if re.search(r'\d+(?:\.\d+)?\s*(?:mm|cm|m|in|ft)', text):
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_autocad_commands(self, command: NLCommand):
        """Generate AutoCAD command strings from the parsed command."""
        # Find matching template
        template = self._find_command_template(command.intent, command.entity_type)
        
        if not template:
            command.error_message = f"No template found for {command.intent.value} {command.entity_type.value}"
            return
        
        try:
            # Prepare parameter values for template substitution
            param_values = {}
            for param_name, param in command.parameters.items():
                param_values[param_name] = param.value
            
            # Add coordinates if available
            if command.coordinates:
                param_values['start_point'] = command.coordinates[0] if command.coordinates else (0, 0)
                if len(command.coordinates) > 1:
                    param_values['end_point'] = command.coordinates[1]
            
            # Add context values
            if command.layer_name:
                param_values['layer'] = command.layer_name
            
            # Generate command using template
            autocad_command = template.template.format(**param_values)
            command.autocad_commands.append(autocad_command)
            
            # Add layer change command if needed
            if command.layer_name:
                command.autocad_commands.insert(0, f"LAYER S {command.layer_name}")
        
        except KeyError as e:
            command.error_message = f"Missing required parameter: {e}"
        except Exception as e:
            command.error_message = f"Template generation failed: {e}"
    
    def _generate_python_code(self, command: NLCommand):
        """Generate Python code for the AutoCAD command."""
        template = self._find_command_template(command.intent, command.entity_type)
        
        if not template or not template.python_template:
            return
        
        try:
            # Prepare parameter values
            param_values = {}
            for param_name, param in command.parameters.items():
                if param.type == 'text':
                    param_values[param_name] = f'"{param.value}"'
                else:
                    param_values[param_name] = param.value
            
            # Add coordinates
            if command.coordinates:
                param_values['start_point'] = command.coordinates[0]
                if len(command.coordinates) > 1:
                    param_values['end_point'] = command.coordinates[1]
            
            # Generate Python code
            python_code = template.python_template.format(**param_values)
            command.python_code = python_code
        
        except Exception as e:
            logger.error(f"Failed to generate Python code: {e}")
    
    def _find_command_template(self, intent: IntentType, entity_type: EntityType) -> Optional[CommandTemplate]:
        """Find the best matching command template."""
        # First try exact match
        for template in self.command_templates:
            if template.intent == intent and template.entity_type == entity_type:
                return template
        
        # Try intent match only
        for template in self.command_templates:
            if template.intent == intent:
                return template
        
        # Try entity match only
        for template in self.command_templates:
            if template.entity_type == entity_type:
                return template
        
        return None
    
    def _update_statistics(self, command: NLCommand):
        """Update processing statistics."""
        self.processing_stats['total_commands'] += 1
        
        if command.confidence > 0.5:
            self.processing_stats['successful_parses'] += 1
        else:
            self.processing_stats['failed_parses'] += 1
        
        # Update running average confidence
        total = self.processing_stats['total_commands']
        current_avg = self.processing_stats['average_confidence']
        self.processing_stats['average_confidence'] = (
            (current_avg * (total - 1) + command.confidence) / total
        )
    
    def _get_common_phrases_for_intent(self, intent: IntentType) -> List[str]:
        """Get common phrases for a given intent."""
        phrases = {
            IntentType.CREATE: [
                "create a circle with radius 10",
                "draw a line from (0,0) to (10,10)",
                "add a rectangle 20 by 30"
            ],
            IntentType.MODIFY: [
                "move the selected objects 10 units right",
                "rotate the circle by 45 degrees",
                "scale the text to height 5"
            ],
            IntentType.DELETE: [
                "delete all circles",
                "erase the selected lines",
                "remove objects on layer temp"
            ]
        }
        return phrases.get(intent, [])
    
    def _load_command_templates(self) -> List[CommandTemplate]:
        """Load command templates for different intent/entity combinations."""
        return [
            # Line creation
            CommandTemplate(
                intent=IntentType.CREATE,
                entity_type=EntityType.LINE,
                template="LINE {start_point[0]},{start_point[1]} {end_point[0]},{end_point[1]}",
                required_params=['start_point', 'end_point'],
                python_template="mspace.AddLine({start_point}, {end_point})",
                examples=[
                    "draw a line from (0,0) to (10,10)",
                    "create a line 20 units long",
                    "add a line from origin to point 15,5"
                ]
            ),
            
            # Circle creation
            CommandTemplate(
                intent=IntentType.CREATE,
                entity_type=EntityType.CIRCLE,
                template="CIRCLE {start_point[0]},{start_point[1]} {radius}",
                required_params=['start_point', 'radius'],
                python_template="mspace.AddCircle({start_point}, {radius})",
                examples=[
                    "create a circle with radius 10",
                    "draw a circle at (5,5) radius 15",
                    "add a circle centered at origin with diameter 20"
                ]
            ),
            
            # Rectangle creation
            CommandTemplate(
                intent=IntentType.CREATE,
                entity_type=EntityType.RECTANGLE,
                template="RECTANG {start_point[0]},{start_point[1]} {width},{height}",
                required_params=['start_point', 'width', 'height'],
                python_template="mspace.AddRectangle({start_point}, {width}, {height})",
                examples=[
                    "create a rectangle 20 by 30",
                    "draw a square with side 15",
                    "add a rectangle from (10,10) size 25x40"
                ]
            ),
            
            # Text creation
            CommandTemplate(
                intent=IntentType.CREATE,
                entity_type=EntityType.TEXT,
                template="TEXT {start_point[0]},{start_point[1]} {height} 0 {text_content}",
                required_params=['start_point', 'text_content'],
                optional_params=['height'],
                python_template="mspace.AddText({text_content}, {start_point}, {height})",
                examples=[
                    'add text "Hello World" at (10,10)',
                    'create text "Drawing Title" height 5',
                    'insert text "Note: Check dimensions" at origin'
                ]
            ),
            
            # Object deletion
            CommandTemplate(
                intent=IntentType.DELETE,
                entity_type=EntityType.UNKNOWN,
                template="ERASE {selection_criteria}",
                required_params=['selection_criteria'],
                examples=[
                    "delete all circles",
                    "erase the selected objects",
                    "remove everything on layer temp"
                ]
            ),
            
            # Object selection
            CommandTemplate(
                intent=IntentType.SELECT,
                entity_type=EntityType.UNKNOWN,
                template="SELECT {selection_criteria}",
                required_params=['selection_criteria'],
                examples=[
                    "select all lines",
                    "choose circles with radius greater than 10",
                    "pick objects on current layer"
                ]
            )
        ]
    
    def _load_entity_patterns(self) -> Dict[str, List[str]]:
        """Load regex patterns for entity recognition."""
        return {
            'line': [r'\blines?\b', r'\bstraight\s+lines?\b'],
            'circle': [r'\bcircles?\b', r'\bround\s+shapes?\b'],
            'rectangle': [r'\brect(?:angle)?s?\b', r'\bsquares?\b', r'\bbox(?:es)?\b'],
            'text': [r'\btexts?\b', r'\blabels?\b', r'\bannotations?\b'],
            'arc': [r'\barcs?\b', r'\bcurved?\s+lines?\b'],
            'polyline': [r'\bpolylines?\b', r'\bplines?\b'],
            'point': [r'\bpoints?\b', r'\bdots?\b'],
            'dimension': [r'\bdimensions?\b', r'\bmeasurements?\b']
        }
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """Load regex patterns for intent recognition."""
        return {
            'create': [r'\b(?:create|draw|add|make|insert)\b'],
            'modify': [r'\b(?:modify|change|edit|update|alter)\b'],
            'delete': [r'\b(?:delete|remove|erase|clear)\b'],
            'move': [r'\b(?:move|translate|shift)\b'],
            'copy': [r'\b(?:copy|duplicate|clone)\b'],
            'rotate': [r'\b(?:rotate|turn|spin)\b'],
            'scale': [r'\b(?:scale|resize|size)\b'],
            'select': [r'\b(?:select|choose|pick|find)\b'],
            'query': [r'\b(?:what|where|how|list|show|get)\b']
        }
    
    def _load_parameter_extractors(self) -> Dict[str, str]:
        """Load parameter extraction patterns."""
        return {
            'radius': r'radius\s+(\d+(?:\.\d+)?)',
            'diameter': r'diameter\s+(\d+(?:\.\d+)?)',
            'width': r'width\s+(\d+(?:\.\d+)?)',
            'height': r'height\s+(\d+(?:\.\d+)?)',
            'length': r'length\s+(\d+(?:\.\d+)?)',
            'angle': r'angle\s+(\d+(?:\.\d+)?)',
            'color': r'color\s+(\w+)',
            'layer': r'layer\s+(\w+)'
        }
    
    def _load_entity_synonyms(self) -> Dict[str, Set[str]]:
        """Load entity synonyms for better recognition."""
        return {
            'line': {'line', 'lines', 'segment', 'segments', 'edge', 'edges'},
            'circle': {'circle', 'circles', 'round', 'circular', 'ring', 'rings'},
            'rectangle': {'rectangle', 'rectangles', 'rect', 'rects', 'box', 'boxes', 'square', 'squares'},
            'text': {'text', 'texts', 'label', 'labels', 'annotation', 'annotations', 'note', 'notes'},
            'arc': {'arc', 'arcs', 'curve', 'curves', 'curved'},
            'polyline': {'polyline', 'polylines', 'pline', 'plines', 'path', 'paths'},
            'point': {'point', 'points', 'dot', 'dots', 'marker', 'markers'},
            'dimension': {'dimension', 'dimensions', 'dim', 'dims', 'measurement', 'measurements'}
        }
    
    def _load_action_synonyms(self) -> Dict[str, Set[str]]:
        """Load action synonyms for better intent recognition."""
        return {
            'create': {'create', 'draw', 'add', 'make', 'insert', 'place', 'put', 'build'},
            'modify': {'modify', 'change', 'edit', 'update', 'alter', 'adjust', 'fix'},
            'delete': {'delete', 'remove', 'erase', 'clear', 'eliminate', 'destroy'},
            'move': {'move', 'translate', 'shift', 'relocate', 'position'},
            'copy': {'copy', 'duplicate', 'clone', 'replicate', 'mirror'},
            'rotate': {'rotate', 'turn', 'spin', 'revolve', 'pivot'},
            'scale': {'scale', 'resize', 'size', 'stretch', 'shrink', 'enlarge'},
            'select': {'select', 'choose', 'pick', 'find', 'get', 'grab'},
            'query': {'what', 'where', 'how', 'list', 'show', 'display', 'tell'}
        }
    
    def _load_measurement_units(self) -> Dict[str, str]:
        """Load measurement unit mappings."""
        return {
            'mm': 'millimeters',
            'cm': 'centimeters', 
            'm': 'meters',
            'in': 'inches',
            'ft': 'feet',
            'yd': 'yards',
            'units': 'drawing_units',
            'pixels': 'pixels',
            'pt': 'points'
        }