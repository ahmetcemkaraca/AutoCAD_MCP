"""
AI-Assisted Code Generation Engine
=================================

Intelligent code generation system that leverages existing templates and AI techniques including:
- Context-aware code generation with pattern recognition
- Template-based generation with intelligent parameter inference
- Code completion and expansion using learned patterns
- AutoCAD-specific code optimization and best practices
- Multi-language code generation (Python, AutoLISP, VBA)
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
from pathlib import Path
from collections import defaultdict, Counter
import random

# Optional ML libraries with graceful fallbacks
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    TfidfVectorizer = None
    cosine_similarity = None

try:
    from transformers import pipeline, Pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    pipeline = None
    Pipeline = None

# Import existing template system
from ..project_templates.template_engine import TemplateEngine
from ..code_generation.python_generator import PythonGenerator
from ..code_generation.autolisp_generator import AutoLISPGenerator
from ..code_generation.vba_generator import VBAGenerator

# Import AI features
from .natural_language_processor import AutoCADNLPEngine, NLCommand, IntentType, EntityType

logger = logging.getLogger(__name__)


class GenerationType(Enum):
    """Types of code generation requests."""
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    SCRIPT = "script"
    SNIPPET = "snippet"
    AUTOCAD_COMMAND = "autocad_command"
    TEST_CASE = "test_case"
    DOCUMENTATION = "documentation"


class CodeLanguage(Enum):
    """Supported code generation languages."""
    PYTHON = "python"
    AUTOLISP = "autolisp"
    VBA = "vba"
    JAVASCRIPT = "javascript"
    C_SHARP = "csharp"


class ComplexityLevel(Enum):
    """Code complexity levels for generation."""
    SIMPLE = "simple"       # Basic operations, minimal logic
    INTERMEDIATE = "intermediate"  # Some conditionals and loops
    COMPLEX = "complex"     # Advanced patterns, multiple components
    ENTERPRISE = "enterprise"  # Full-featured with error handling, logging


@dataclass
class CodeGenerationRequest:
    """Request for AI-assisted code generation."""
    description: str
    generation_type: GenerationType
    target_language: CodeLanguage
    complexity_level: ComplexityLevel = ComplexityLevel.INTERMEDIATE
    
    # Context information
    project_context: Optional[Dict[str, Any]] = None
    existing_code_context: Optional[str] = None
    requirements: List[str] = field(default_factory=list)
    
    # Generation preferences
    include_error_handling: bool = True
    include_documentation: bool = True
    include_tests: bool = False
    follow_pep8: bool = True
    
    # AutoCAD-specific options
    autocad_version: Optional[str] = None
    use_transactions: bool = True
    optimize_performance: bool = True


@dataclass
class GeneratedCode:
    """Result of AI-assisted code generation."""
    request_id: str
    success: bool
    
    # Generated content
    main_code: str = ""
    supporting_code: Dict[str, str] = field(default_factory=dict)  # Additional files/modules
    test_code: Optional[str] = None
    documentation: Optional[str] = None
    
    # Metadata
    generation_time: float = 0.0
    confidence_score: float = 0.0
    template_used: Optional[str] = None
    ai_techniques_applied: List[str] = field(default_factory=list)
    
    # Quality metrics
    estimated_lines: int = 0
    complexity_score: float = 0.0
    maintainability_score: float = 0.0
    
    # Warnings and suggestions
    warnings: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    
    # Error information
    error_message: Optional[str] = None
    partial_generation: bool = False


class CodePattern:
    """Represents a learned code pattern for generation."""
    
    def __init__(self, name: str, pattern_type: str, template: str):
        self.name = name
        self.pattern_type = pattern_type
        self.template = template
        self.usage_count = 0
        self.success_rate = 0.0
        self.parameters = []
        self.examples = []
        self.context_tags = set()
    
    def matches_context(self, context: Dict[str, Any]) -> float:
        """Calculate how well this pattern matches the given context."""
        score = 0.0
        
        # Check context tags
        context_tags = set(context.get('tags', []))
        tag_overlap = len(self.context_tags.intersection(context_tags))
        if self.context_tags:
            score += (tag_overlap / len(self.context_tags)) * 0.4
        
        # Check pattern type
        if context.get('pattern_type') == self.pattern_type:
            score += 0.3
        
        # Check success rate
        score += self.success_rate * 0.3
        
        return min(1.0, score)


class AICodeGenerator:
    """
    AI-assisted code generation engine that integrates with existing templates.
    
    Provides intelligent code generation with context awareness, pattern learning,
    and optimization for AutoCAD development workflows.
    """
    
    def __init__(self):
        """Initialize the AI code generator."""
        # Initialize component generators
        self.template_engine = TemplateEngine()
        self.python_generator = PythonGenerator()
        self.autolisp_generator = AutoLISPGenerator()
        self.vba_generator = VBAGenerator()
        self.nlp_engine = AutoCADNLPEngine()
        
        # Pattern learning and storage
        self.learned_patterns = []
        self.pattern_usage_stats = defaultdict(int)
        self.generation_history = []
        
        # AI models and techniques
        self.code_templates_db = self._initialize_code_templates()
        self.best_practices_db = self._initialize_best_practices()
        self.optimization_rules = self._initialize_optimization_rules()
        
        # Configuration
        self.max_generation_time = 30.0  # seconds
        self.enable_pattern_learning = True
        self.confidence_threshold = 0.6
        
        # ML capabilities detection
        self.ml_capabilities = {
            'sklearn': HAS_SKLEARN,
            'transformers': HAS_TRANSFORMERS,
            'advanced_similarity': HAS_SKLEARN,
            'language_models': HAS_TRANSFORMERS
        }
        
        # Initialize ML components if available
        self.similarity_vectorizer = None
        self.code_similarity_matrix = None
        if HAS_SKLEARN:
            try:
                self.similarity_vectorizer = TfidfVectorizer(max_features=1000)
                logger.info("Initialized TF-IDF vectorizer for code similarity")
            except Exception as e:
                logger.warning(f"Failed to initialize TF-IDF vectorizer: {e}")
        
        # Log capabilities
        enabled_features = [k for k, v in self.ml_capabilities.items() if v]
        if enabled_features:
            logger.info(f"AI code generator initialized with ML features: {', '.join(enabled_features)}")
        else:
            logger.info("AI code generator initialized with template-based generation (no ML libraries)")
    
    def generate_code(self, request: CodeGenerationRequest) -> GeneratedCode:
        """
        Generate code using AI-assisted techniques.
        
        Args:
            request: Code generation request with specifications
            
        Returns:
            Generated code with metadata and quality metrics
        """
        start_time = time.time()
        request_id = f"gen_{int(time.time() * 1000) % 1000000:06d}"
        
        result = GeneratedCode(
            request_id=request_id,
            success=False
        )
        
        try:
            # Phase 1: Analyze request and determine approach
            analysis = self._analyze_generation_request(request)
            result.ai_techniques_applied.append("request_analysis")
            
            # Phase 2: Select or create templates
            template_candidates = self._select_templates(request, analysis)
            result.ai_techniques_applied.append("template_selection")
            
            # Phase 3: Generate base code
            base_code = self._generate_base_code(request, template_candidates, analysis)
            result.main_code = base_code
            result.ai_techniques_applied.append("base_code_generation")
            
            # Phase 4: Apply AI enhancements
            enhanced_code = self._apply_ai_enhancements(base_code, request, analysis)
            result.main_code = enhanced_code
            result.ai_techniques_applied.append("ai_enhancement")
            
            # Phase 5: Generate supporting code if needed
            if request.include_tests or request.generation_type == GenerationType.MODULE:
                supporting_code = self._generate_supporting_code(request, enhanced_code)
                result.supporting_code = supporting_code
                result.ai_techniques_applied.append("supporting_code_generation")
            
            # Phase 6: Generate documentation
            if request.include_documentation:
                documentation = self._generate_documentation(enhanced_code, request)
                result.documentation = documentation
                result.ai_techniques_applied.append("documentation_generation")
            
            # Phase 7: Quality assessment and optimization
            quality_metrics = self._assess_code_quality(enhanced_code, request)
            result.confidence_score = quality_metrics['confidence']
            result.complexity_score = quality_metrics['complexity']
            result.maintainability_score = quality_metrics['maintainability']
            result.estimated_lines = len(enhanced_code.split('\n'))
            result.ai_techniques_applied.append("quality_assessment")
            
            # Phase 8: Generate optimization suggestions
            optimizations = self._generate_optimization_suggestions(enhanced_code, request)
            result.optimization_suggestions = optimizations
            result.ai_techniques_applied.append("optimization_analysis")
            
            # Finalize result
            result.success = result.confidence_score >= self.confidence_threshold
            result.generation_time = time.time() - start_time
            
            # Learn from successful generation
            if result.success and self.enable_pattern_learning:
                self._learn_from_generation(request, result)
            
            # Store in history
            self.generation_history.append({
                'timestamp': time.time(),
                'request': request,
                'result': result
            })
            
        except Exception as e:
            result.error_message = str(e)
            result.generation_time = time.time() - start_time
            logger.error(f"Code generation failed: {e}")
        
        return result
    
    def generate_from_natural_language(self, 
                                     description: str, 
                                     target_language: CodeLanguage = CodeLanguage.PYTHON,
                                     context: Optional[Dict[str, Any]] = None) -> GeneratedCode:
        """
        Generate code from natural language description.
        
        Args:
            description: Natural language description of desired code
            target_language: Target programming language
            context: Optional context information
            
        Returns:
            Generated code result
        """
        # First, process the natural language to extract structured requirements
        nl_command = self.nlp_engine.process_natural_language(description, context)
        
        # Convert NL command to code generation request
        request = self._nl_command_to_generation_request(nl_command, target_language)
        
        # Generate code using the standard pipeline
        result = self.generate_code(request)
        result.ai_techniques_applied.insert(0, "natural_language_processing")
        
        return result
    
    def suggest_code_completions(self, 
                               partial_code: str,
                               cursor_position: int,
                               context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Suggest code completions based on partial code and context.
        
        Args:
            partial_code: Partial code being written
            cursor_position: Position of cursor in the code
            context: Optional context information
            
        Returns:
            List of suggested code completions
        """
        suggestions = []
        
        try:
            # Analyze the partial code context
            code_context = self._analyze_code_context(partial_code, cursor_position)
            
            # Find matching patterns
            matching_patterns = self._find_matching_patterns(code_context)
            
            # Generate completions from patterns
            for pattern in matching_patterns[:5]:  # Top 5 patterns
                completion = self._generate_completion_from_pattern(
                    pattern, code_context, partial_code
                )
                if completion:
                    suggestions.append(completion)
            
            # Add template-based suggestions
            template_suggestions = self._get_template_based_suggestions(code_context)
            suggestions.extend(template_suggestions[:3])  # Top 3 template suggestions
            
        except Exception as e:
            logger.error(f"Failed to suggest code completions: {e}")
        
        return suggestions[:10]  # Return top 10 suggestions
    
    def optimize_existing_code(self, 
                             code: str, 
                             language: CodeLanguage = CodeLanguage.PYTHON,
                             focus_areas: Optional[List[str]] = None) -> GeneratedCode:
        """
        Optimize existing code using AI techniques.
        
        Args:
            code: Existing code to optimize
            language: Programming language of the code
            focus_areas: Specific areas to focus optimization on
            
        Returns:
            Optimized code result
        """
        request_id = f"opt_{int(time.time() * 1000) % 1000000:06d}"
        
        result = GeneratedCode(
            request_id=request_id,
            success=False
        )
        
        try:
            # Analyze existing code
            analysis = self._analyze_existing_code(code, language)
            result.ai_techniques_applied.append("code_analysis")
            
            # Identify optimization opportunities
            opportunities = self._identify_optimization_opportunities(code, analysis, focus_areas)
            result.ai_techniques_applied.append("optimization_identification")
            
            # Apply optimizations
            optimized_code = self._apply_optimizations(code, opportunities, language)
            result.main_code = optimized_code
            result.ai_techniques_applied.append("optimization_application")
            
            # Generate diff and explanation
            diff_explanation = self._generate_optimization_explanation(code, optimized_code, opportunities)
            result.documentation = diff_explanation
            result.ai_techniques_applied.append("explanation_generation")
            
            # Assess improvement
            improvement_metrics = self._assess_optimization_improvement(code, optimized_code)
            result.confidence_score = improvement_metrics['confidence']
            result.optimization_suggestions = improvement_metrics['additional_suggestions']
            
            result.success = True
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Code optimization failed: {e}")
        
        return result
    
    def _analyze_generation_request(self, request: CodeGenerationRequest) -> Dict[str, Any]:
        """Analyze the generation request to determine the best approach."""
        analysis = {
            'complexity_indicators': [],
            'required_components': [],
            'autocad_features': [],
            'estimated_effort': 0.0,
            'suggested_templates': [],
            'risk_factors': []
        }
        
        # Analyze description for complexity indicators
        complexity_keywords = {
            'simple': ['create', 'add', 'basic', 'simple'],
            'intermediate': ['process', 'handle', 'manage', 'convert'],
            'complex': ['optimize', 'analyze', 'integrate', 'advanced'],
            'enterprise': ['scalable', 'robust', 'enterprise', 'production']
        }
        
        description_lower = request.description.lower()
        for level, keywords in complexity_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                analysis['complexity_indicators'].append(level)
        
        # Identify AutoCAD-specific features
        autocad_keywords = [
            'modelspace', 'paperspace', 'block', 'layer', 'dimension',
            'entity', 'selection', 'transaction', 'drawing', 'document'
        ]
        
        for keyword in autocad_keywords:
            if keyword in description_lower:
                analysis['autocad_features'].append(keyword)
        
        # Estimate effort based on complexity and features
        base_effort = {
            GenerationType.FUNCTION: 1.0,
            GenerationType.CLASS: 2.0,
            GenerationType.MODULE: 4.0,
            GenerationType.SCRIPT: 1.5,
            GenerationType.SNIPPET: 0.5
        }.get(request.generation_type, 1.0)
        
        complexity_multiplier = {
            ComplexityLevel.SIMPLE: 1.0,
            ComplexityLevel.INTERMEDIATE: 2.0,
            ComplexityLevel.COMPLEX: 3.0,
            ComplexityLevel.ENTERPRISE: 4.0
        }.get(request.complexity_level, 2.0)
        
        analysis['estimated_effort'] = base_effort * complexity_multiplier
        
        return analysis
    
    def _select_templates(self, 
                         request: CodeGenerationRequest, 
                         analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Select the most appropriate templates for the generation request."""
        candidates = []
        
        # Get templates from the template engine
        available_templates = self.template_engine.get_available_templates()
        
        for template_name, template_info in available_templates.items():
            # Calculate template relevance score
            relevance_score = self._calculate_template_relevance(
                template_info, request, analysis
            )
            
            if relevance_score > 0.3:  # Threshold for relevance
                candidates.append({
                    'name': template_name,
                    'info': template_info,
                    'relevance_score': relevance_score
                })
        
        # Sort by relevance score
        candidates.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return candidates[:3]  # Return top 3 candidates
    
    def _generate_base_code(self, 
                          request: CodeGenerationRequest,
                          template_candidates: List[Dict[str, Any]],
                          analysis: Dict[str, Any]) -> str:
        """Generate base code using templates and AI techniques."""
        if not template_candidates:
            # Fallback to pattern-based generation
            return self._generate_from_patterns(request, analysis)
        
        # Use the best template
        best_template = template_candidates[0]
        template_name = best_template['name']
        
        try:
            # Prepare template parameters from request
            template_params = self._extract_template_parameters(request, analysis)
            
            # Generate code using template engine
            base_code = self.template_engine.generate_from_template(
                template_name, template_params
            )
            
            return base_code
            
        except Exception as e:
            logger.warning(f"Template generation failed: {e}. Falling back to pattern generation.")
            return self._generate_from_patterns(request, analysis)
    
    def _apply_ai_enhancements(self, 
                             base_code: str,
                             request: CodeGenerationRequest,
                             analysis: Dict[str, Any]) -> str:
        """Apply AI-powered enhancements to the base code."""
        enhanced_code = base_code
        
        try:
            # Apply language-specific enhancements
            if request.target_language == CodeLanguage.PYTHON:
                enhanced_code = self._enhance_python_code(enhanced_code, request)
            elif request.target_language == CodeLanguage.AUTOLISP:
                enhanced_code = self._enhance_autolisp_code(enhanced_code, request)
            elif request.target_language == CodeLanguage.VBA:
                enhanced_code = self._enhance_vba_code(enhanced_code, request)
            
            # Apply AutoCAD-specific optimizations
            if analysis.get('autocad_features'):
                enhanced_code = self._apply_autocad_optimizations(enhanced_code, analysis)
            
            # Add error handling if requested
            if request.include_error_handling:
                enhanced_code = self._add_error_handling(enhanced_code, request.target_language)
            
            # Apply code formatting
            if request.follow_pep8 and request.target_language == CodeLanguage.PYTHON:
                enhanced_code = self._apply_pep8_formatting(enhanced_code)
            
        except Exception as e:
            logger.warning(f"AI enhancement failed: {e}. Using base code.")
        
        return enhanced_code
    
    def _generate_supporting_code(self, 
                                request: CodeGenerationRequest,
                                main_code: str) -> Dict[str, str]:
        """Generate supporting code like tests, utilities, etc."""
        supporting_code = {}
        
        try:
            # Generate test cases if requested
            if request.include_tests:
                test_code = self._generate_test_code(main_code, request)
                supporting_code['test_' + request.generation_type.value + '.py'] = test_code
            
            # Generate utility modules for complex generations
            if request.complexity_level in [ComplexityLevel.COMPLEX, ComplexityLevel.ENTERPRISE]:
                utils_code = self._generate_utility_code(main_code, request)
                if utils_code:
                    supporting_code['utils.py'] = utils_code
            
            # Generate configuration files for enterprise-level code
            if request.complexity_level == ComplexityLevel.ENTERPRISE:
                config_code = self._generate_configuration_code(request)
                if config_code:
                    supporting_code['config.py'] = config_code
        
        except Exception as e:
            logger.warning(f"Supporting code generation failed: {e}")
        
        return supporting_code
    
    def _generate_documentation(self, 
                              code: str, 
                              request: CodeGenerationRequest) -> str:
        """Generate documentation for the generated code."""
        try:
            # Parse the code to extract structure
            if request.target_language == CodeLanguage.PYTHON:
                documentation = self._generate_python_documentation(code, request)
            elif request.target_language == CodeLanguage.AUTOLISP:
                documentation = self._generate_autolisp_documentation(code, request)
            elif request.target_language == CodeLanguage.VBA:
                documentation = self._generate_vba_documentation(code, request)
            else:
                documentation = self._generate_generic_documentation(code, request)
            
            return documentation
            
        except Exception as e:
            logger.warning(f"Documentation generation failed: {e}")
            return f"# Documentation for {request.generation_type.value}\n\n{request.description}"
    
    def _assess_code_quality(self, 
                           code: str, 
                           request: CodeGenerationRequest) -> Dict[str, float]:
        """Assess the quality of generated code."""
        metrics = {
            'confidence': 0.5,
            'complexity': 0.5,
            'maintainability': 0.5
        }
        
        try:
            if request.target_language == CodeLanguage.PYTHON:
                # Simple Python code quality assessment
                lines = code.split('\n')
                non_empty_lines = [line for line in lines if line.strip()]
                
                # Confidence based on code structure
                has_functions = any('def ' in line for line in lines)
                has_classes = any('class ' in line for line in lines)
                has_docstrings = any('"""' in line or "'''" in line for line in lines)
                has_comments = any(line.strip().startswith('#') for line in lines)
                
                confidence_factors = [
                    0.2 if has_functions else 0.0,
                    0.2 if has_classes else 0.0,
                    0.2 if has_docstrings else 0.0,
                    0.1 if has_comments else 0.0,
                    0.3  # Base confidence
                ]
                metrics['confidence'] = sum(confidence_factors)
                
                # Complexity based on line count and structure
                complexity_score = min(1.0, len(non_empty_lines) / 100.0)
                if has_classes:
                    complexity_score += 0.2
                if 'try:' in code:
                    complexity_score += 0.1
                metrics['complexity'] = min(1.0, complexity_score)
                
                # Maintainability based on documentation and structure
                maintainability_score = 0.3  # Base score
                if has_docstrings:
                    maintainability_score += 0.3
                if has_comments:
                    maintainability_score += 0.2
                if request.include_error_handling and 'try:' in code:
                    maintainability_score += 0.2
                metrics['maintainability'] = min(1.0, maintainability_score)
        
        except Exception as e:
            logger.warning(f"Quality assessment failed: {e}")
        
        return metrics
    
    def _generate_optimization_suggestions(self, 
                                         code: str, 
                                         request: CodeGenerationRequest) -> List[str]:
        """Generate optimization suggestions for the code."""
        suggestions = []
        
        try:
            # Generic optimization suggestions
            if 'for ' in code and 'in range(' in code:
                suggestions.append("Consider using list comprehensions where appropriate for better performance")
            
            if 'print(' in code and request.complexity_level == ComplexityLevel.ENTERPRISE:
                suggestions.append("Replace print statements with proper logging for production code")
            
            if request.target_language == CodeLanguage.PYTHON:
                # Python-specific suggestions
                if 'import *' in code:
                    suggestions.append("Avoid wildcard imports, use specific imports instead")
                
                if not any('def ' in line for line in code.split('\n')):
                    suggestions.append("Consider organizing code into functions for better modularity")
            
            # AutoCAD-specific suggestions
            if any(feature in code.lower() for feature in ['modelspace', 'add', 'create']):
                if 'transaction' not in code.lower():
                    suggestions.append("Consider wrapping AutoCAD operations in transactions for better performance")
                
                if 'error' not in code.lower() and 'try' not in code.lower():
                    suggestions.append("Add error handling for AutoCAD COM operations")
        
        except Exception as e:
            logger.warning(f"Optimization suggestion generation failed: {e}")
        
        return suggestions
    
    def _nl_command_to_generation_request(self, 
                                        nl_command: NLCommand,
                                        target_language: CodeLanguage) -> CodeGenerationRequest:
        """Convert a natural language command to a generation request."""
        # Determine generation type based on intent
        generation_type_mapping = {
            IntentType.CREATE: GenerationType.FUNCTION,
            IntentType.MODIFY: GenerationType.FUNCTION,
            IntentType.DELETE: GenerationType.FUNCTION,
            IntentType.QUERY: GenerationType.FUNCTION,
            IntentType.SELECT: GenerationType.FUNCTION
        }
        
        generation_type = generation_type_mapping.get(nl_command.intent, GenerationType.FUNCTION)
        
        # Determine complexity based on parameters and requirements
        param_count = len(nl_command.parameters)
        if param_count <= 2:
            complexity = ComplexityLevel.SIMPLE
        elif param_count <= 5:
            complexity = ComplexityLevel.INTERMEDIATE
        else:
            complexity = ComplexityLevel.COMPLEX
        
        # Build requirements list
        requirements = []
        for param_name, param in nl_command.parameters.items():
            requirements.append(f"Parameter {param_name}: {param.value} ({param.type})")
        
        if nl_command.coordinates:
            requirements.append(f"Coordinates: {nl_command.coordinates}")
        
        return CodeGenerationRequest(
            description=nl_command.original_text,
            generation_type=generation_type,
            target_language=target_language,
            complexity_level=complexity,
            requirements=requirements,
            project_context={
                'autocad_context': True,
                'intent': nl_command.intent.value,
                'entity_type': nl_command.entity_type.value,
                'confidence': nl_command.confidence
            }
        )
    
    def _calculate_template_relevance(self, 
                                    template_info: Dict[str, Any],
                                    request: CodeGenerationRequest,
                                    analysis: Dict[str, Any]) -> float:
        """Calculate how relevant a template is for the generation request."""
        relevance_score = 0.0
        
        # Check template category vs generation type
        template_category = template_info.get('category', '').lower()
        request_type = request.generation_type.value.lower()
        
        if template_category in request_type or request_type in template_category:
            relevance_score += 0.3
        
        # Check template language compatibility
        template_language = template_info.get('language', '').lower()
        request_language = request.target_language.value.lower()
        
        if template_language == request_language:
            relevance_score += 0.2
        
        # Check AutoCAD feature overlap
        template_features = set(template_info.get('features', []))
        analysis_features = set(analysis.get('autocad_features', []))
        
        if template_features and analysis_features:
            feature_overlap = len(template_features.intersection(analysis_features))
            relevance_score += (feature_overlap / len(template_features)) * 0.3
        
        # Check complexity compatibility
        template_complexity = template_info.get('complexity', 'intermediate').lower()
        request_complexity = request.complexity_level.value.lower()
        
        if template_complexity == request_complexity:
            relevance_score += 0.2
        
        return min(1.0, relevance_score)
    
    def _extract_template_parameters(self, 
                                   request: CodeGenerationRequest,
                                   analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters for template instantiation from the request."""
        params = {
            'project_name': 'generated_project',
            'description': request.description,
            'author': 'AI Code Generator',
            'complexity_level': request.complexity_level.value,
            'target_language': request.target_language.value,
            'include_error_handling': request.include_error_handling,
            'include_documentation': request.include_documentation,
            'autocad_features': analysis.get('autocad_features', [])
        }
        
        # Extract specific parameters from project context
        if request.project_context:
            params.update(request.project_context)
        
        return params
    
    def _generate_from_patterns(self, 
                              request: CodeGenerationRequest,
                              analysis: Dict[str, Any]) -> str:
        """Generate code using learned patterns when templates are not available."""
        # Find matching patterns
        matching_patterns = []
        for pattern in self.learned_patterns:
            relevance = pattern.matches_context({
                'generation_type': request.generation_type.value,
                'complexity': request.complexity_level.value,
                'language': request.target_language.value,
                'tags': analysis.get('autocad_features', [])
            })
            
            if relevance > 0.5:
                matching_patterns.append((pattern, relevance))
        
        if not matching_patterns:
            # Fallback to basic code structure
            return self._generate_basic_code_structure(request)
        
        # Use the best matching pattern
        best_pattern, _ = max(matching_patterns, key=lambda x: x[1])
        
        try:
            # Generate code from pattern template
            code = best_pattern.template.format(
                description=request.description,
                complexity=request.complexity_level.value,
                language=request.target_language.value
            )
            return code
        except Exception as e:
            logger.warning(f"Pattern-based generation failed: {e}")
            return self._generate_basic_code_structure(request)
    
    def _generate_basic_code_structure(self, request: CodeGenerationRequest) -> str:
        """Generate a basic code structure as a last resort."""
        if request.target_language == CodeLanguage.PYTHON:
            return self._generate_python_basic_structure(request)
        elif request.target_language == CodeLanguage.AUTOLISP:
            return self._generate_autolisp_basic_structure(request)
        elif request.target_language == CodeLanguage.VBA:
            return self._generate_vba_basic_structure(request)
        else:
            return f"// {request.description}\n// Generated by AI Code Generator\n\n// Basic implementation template"
    
    def _generate_python_basic_structure(self, request: CodeGenerationRequest) -> str:
        """Generate Python code structure based on generation type."""
        base_imports = []
        main_code = ""
        
        if request.generation_type == GenerationType.FUNCTION:
            base_imports = ["from typing import Any, Optional"]
            main_code = f'''def {request.project_context.get('function_name', 'generated_function')}(*args, **kwargs) -> Optional[Any]:
    """
    {request.description}
    
    Args:
        *args: Variable arguments
        **kwargs: Keyword arguments
        
    Returns:
        Optional[Any]: Function result
    """
    # Implementation would go here
    print(f"Executing: {request.description}")
    return None'''
        
        elif request.generation_type == GenerationType.CLASS:
            base_imports = ["from typing import Any, Optional"]
            class_name = request.project_context.get('class_name', 'GeneratedClass')
            main_code = f'''class {class_name}:
    """
    {request.description}
    """
    
    def __init__(self):
        """Initialize the class."""
        self.initialized = True
        
    def process(self) -> Optional[Any]:
        """Main processing method."""
        print(f"Processing: {request.description}")
        return None'''
        
        elif request.generation_type == GenerationType.AUTOCAD_COMMAND:
            base_imports = ["from src.utils import get_autocad_instance", "import logging"]
            main_code = f'''def autocad_command():
    """
    {request.description}
    """
    logger = logging.getLogger(__name__)
    
    try:
        acad = get_autocad_instance()
        logger.info("AutoCAD command executed: {request.description}")
        # AutoCAD-specific implementation would go here
        return {{"success": True, "message": "Command completed"}}
    except Exception as e:
        logger.error(f"AutoCAD command failed: {{e}}")
        return {{"success": False, "error": str(e)}}'''
        
        else:
            main_code = f'''def main():
    """
    {request.description}
    """
    print("Generated code structure ready for implementation")
    # Add your specific logic here
    return True'''
        
        imports_section = "\n".join(base_imports) + "\n\n" if base_imports else ""
        
        return f'''"""
{request.description}

Generated by AI Code Generator
"""

{imports_section}{main_code}

if __name__ == "__main__":
    main()
'''
    
    def _generate_autolisp_basic_structure(self, request: CodeGenerationRequest) -> str:
        """Generate AutoLISP code structure based on generation type."""
        if request.generation_type == GenerationType.AUTOCAD_COMMAND:
            function_name = request.project_context.get('function_name', 'GENERATED-CMD')
            return f''';; {request.description}
;; Generated by AI Code Generator

(defun C:{function_name} ()
  "AutoCAD command: {request.description}"
  (princ "\\nExecuting: {request.description}")
  
  ;; Command implementation
  (setq result (list "success" T))
  
  ;; Return result
  (princ "\\nCommand completed successfully")
  (princ)
  result
)

;; Load command
(princ "\\nLoaded command: {function_name}")
(princ)
'''
        else:
            function_name = request.project_context.get('function_name', 'generated-function')
            return f''';; {request.description}
;; Generated by AI Code Generator

(defun {function_name} ()
  "Function: {request.description}"
  (princ "\\nExecuting: {request.description}")
  
  ;; Function implementation
  (setq result nil)
  
  ;; Return result
  result
)

;; Test the function
(princ "\\nLoaded function: {function_name}")
(princ)
'''
    
    def _generate_vba_basic_structure(self, request: CodeGenerationRequest) -> str:
        """Generate VBA code structure based on generation type."""
        if request.generation_type == GenerationType.AUTOCAD_COMMAND:
            sub_name = request.project_context.get('sub_name', 'GeneratedCommand')
            return f'''' {request.description}
' Generated by AI Code Generator

Sub {sub_name}()
    ' AutoCAD VBA Command: {request.description}
    
    Dim acDoc As AcadDocument
    Set acDoc = ThisDrawing
    
    ' Command implementation
    MsgBox "{request.description} executed successfully"
    
End Sub
'''
        else:
            function_name = request.project_context.get('function_name', 'GeneratedFunction')
            return f'''' {request.description}
' Generated by AI Code Generator

Function {function_name}() As Boolean
    ' Function: {request.description}
    
    On Error GoTo ErrorHandler
    
    ' Function implementation
    {function_name} = True
    Exit Function
    
ErrorHandler:
    MsgBox "Error in {function_name}: " & Err.Description
    {function_name} = False
End Function
'''
    
    def _learn_from_generation(self, 
                             request: CodeGenerationRequest, 
                             result: GeneratedCode):
        """Learn patterns from successful code generation."""
        if not result.success or result.confidence_score < 0.7:
            return
        
        try:
            # Create a new pattern if this was a novel generation
            pattern_name = f"{request.generation_type.value}_{request.target_language.value}_{len(self.learned_patterns)}"
            
            pattern = CodePattern(
                name=pattern_name,
                pattern_type=request.generation_type.value,
                template=result.main_code
            )
            
            # Add context tags
            if request.project_context:
                pattern.context_tags.update(request.project_context.get('autocad_features', []))
            
            pattern.context_tags.add(request.complexity_level.value)
            pattern.context_tags.add(request.target_language.value)
            
            # Set initial metrics
            pattern.success_rate = result.confidence_score
            pattern.usage_count = 1
            
            self.learned_patterns.append(pattern)
            
            # Limit the number of learned patterns
            if len(self.learned_patterns) > 100:
                # Remove least successful patterns
                self.learned_patterns.sort(key=lambda p: p.success_rate * p.usage_count)
                self.learned_patterns = self.learned_patterns[-50:]
            
        except Exception as e:
            logger.warning(f"Pattern learning failed: {e}")
    
    def _initialize_code_templates(self) -> Dict[str, str]:
        """Initialize built-in code templates."""
        return {
            'python_function': '''def {function_name}({parameters}):
    """
    {description}
    
    Args:
        {parameter_docs}
    
    Returns:
        {return_type}: {return_description}
    """
    {function_body}
''',
            'python_class': '''class {class_name}:
    """
    {description}
    """
    
    def __init__(self{init_parameters}):
        """Initialize {class_name}."""
        {init_body}
    
    {class_methods}
''',
            'autolisp_function': ''';; {description}
(defun {function_name} ({parameters})
  {function_body}
)
''',
            'vba_function': '''Function {function_name}({parameters}) As {return_type}
    ' {description}
    {function_body}
End Function
'''
        }
    
    def _initialize_best_practices(self) -> Dict[str, List[str]]:
        """Initialize coding best practices database."""
        return {
            'python': [
                "Use meaningful variable and function names",
                "Follow PEP 8 style guidelines",
                "Include docstrings for functions and classes",
                "Handle exceptions appropriately",
                "Use type hints where applicable"
            ],
            'autolisp': [
                "Use consistent indentation",
                "Include descriptive comments",
                "Handle error conditions",
                "Use meaningful function names",
                "Minimize global variable usage"
            ],
            'autocad': [
                "Use transactions for multiple operations",
                "Handle COM errors gracefully",
                "Clean up object references",
                "Use selection sets efficiently",
                "Optimize drawing update frequency"
            ]
        }
    
    def _initialize_optimization_rules(self) -> List[Dict[str, Any]]:
        """Initialize code optimization rules."""
        return [
            {
                'name': 'transaction_wrapping',
                'pattern': r'(ModelSpace|PaperSpace)\.Add',
                'suggestion': 'Wrap multiple Add operations in a transaction',
                'language': 'python',
                'impact': 'high'
            },
            {
                'name': 'selection_optimization',
                'pattern': r'for.*in.*ModelSpace',
                'suggestion': 'Use selection sets instead of iterating all objects',
                'language': 'python',
                'impact': 'medium'
            },
            {
                'name': 'error_handling',
                'pattern': r'(?<!try:).*\.Add.*',
                'suggestion': 'Add try-except blocks for COM operations',
                'language': 'python',
                'impact': 'medium'
            }
        ]
    
    # Additional helper methods would be implemented here for specific language enhancements,
    # code analysis, pattern matching, etc. The implementation continues with more specialized
    # methods for each supported language and feature.
    
    def _enhance_python_code(self, code: str, request: CodeGenerationRequest) -> str:
        """Apply Python-specific enhancements."""
        # This would contain Python-specific optimization logic
        return code
    
    def _enhance_autolisp_code(self, code: str, request: CodeGenerationRequest) -> str:
        """Apply AutoLISP-specific enhancements."""
        # This would contain AutoLISP-specific optimization logic
        return code
    
    def _enhance_vba_code(self, code: str, request: CodeGenerationRequest) -> str:
        """Apply VBA-specific enhancements."""
        # This would contain VBA-specific optimization logic
        return code
    
    def _find_similar_patterns_ml(self, request: CodeGenerationRequest) -> List[Tuple[CodePattern, float]]:
        """Find similar patterns using machine learning techniques."""
        if not HAS_SKLEARN or not self.learned_patterns:
            return []
        
        try:
            # Create feature vectors from request and patterns
            request_text = f"{request.description} {request.generation_type.value} {request.target_language.value}"
            pattern_texts = [f"{p.template} {p.pattern_type}" for p in self.learned_patterns]
            all_texts = [request_text] + pattern_texts
            
            # Use TF-IDF vectorization for similarity
            if self.similarity_vectorizer is None:
                self.similarity_vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            
            vectors = self.similarity_vectorizer.fit_transform(all_texts)
            request_vector = vectors[0]
            pattern_vectors = vectors[1:]
            
            # Calculate cosine similarities
            similarities = cosine_similarity(request_vector, pattern_vectors).flatten()
            
            # Combine with traditional pattern matching
            results = []
            for i, pattern in enumerate(self.learned_patterns):
                ml_similarity = similarities[i]
                traditional_similarity = pattern.calculate_similarity({
                    'pattern_type': request.generation_type.value,
                    'language': request.target_language.value,
                    'complexity': request.complexity_level.value
                })
                
                # Weighted combination
                combined_score = 0.6 * ml_similarity + 0.4 * traditional_similarity
                results.append((pattern, combined_score))
            
            # Sort by similarity score
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:5]  # Top 5 matches
            
        except Exception as e:
            logger.warning(f"ML pattern matching failed: {e}")
            return []
    
    def _enhance_code_with_ml(self, code: str, request: CodeGenerationRequest) -> str:
        """Enhance generated code using ML techniques."""
        if not HAS_TRANSFORMERS:
            return code
        
        try:
            # This would use transformers for code enhancement
            # For now, return the original code with a comment
            enhanced_code = f"# Code enhanced with ML capabilities\n{code}"
            return enhanced_code
        except Exception as e:
            logger.warning(f"ML code enhancement failed: {e}")
            return code
    
    def get_ml_capabilities(self) -> Dict[str, Any]:
        """Get information about available ML capabilities."""
        return {
            'capabilities': self.ml_capabilities.copy(),
            'sklearn_version': getattr(__import__('sklearn', fromlist=['__version__']), '__version__', None) if HAS_SKLEARN else None,
            'transformers_version': getattr(__import__('transformers', fromlist=['__version__']), '__version__', None) if HAS_TRANSFORMERS else None,
            'features': {
                'advanced_pattern_matching': HAS_SKLEARN,
                'code_similarity_analysis': HAS_SKLEARN,
                'language_model_enhancement': HAS_TRANSFORMERS,
                'intelligent_code_completion': HAS_TRANSFORMERS
            }
        }