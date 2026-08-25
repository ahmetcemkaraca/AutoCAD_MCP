"""
Language Coordinator for Master AutoCAD Coder.

Determines optimal programming language for AutoCAD automation tasks
and coordinates multi-language solutions.
"""

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re


class LanguageType(Enum):
    """Supported automation languages."""
    PYTHON = "python"
    AUTOLISP = "autolisp"
    VBA = "vba"


@dataclass
class TaskRequirement:
    """Structured representation of a task requirement."""
    description: str
    complexity: str  # basic, intermediate, advanced
    operations: List[str]  # drawing, data, ui, batch, etc.
    performance_critical: bool
    integration_needs: List[str]  # excel, database, file_system, etc.
    user_interaction: bool
    automation_level: str  # manual, semi_auto, full_auto


@dataclass
class LanguageRecommendation:
    """Language recommendation with reasoning."""
    language: LanguageType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    advantages: List[str]
    limitations: List[str]
    estimated_development_time: str


class LanguageCoordinator:
    """Coordinates multi-language code generation and optimal language selection."""
    
    def __init__(self):
        self.language_capabilities = self._initialize_capabilities()
        self.task_patterns = self._initialize_patterns()
    
    def _initialize_capabilities(self) -> Dict[LanguageType, Dict[str, Any]]:
        """Initialize language capabilities matrix."""
        return {
            LanguageType.PYTHON: {
                "strengths": [
                    "Complex data processing",
                    "External API integration", 
                    "Advanced algorithms",
                    "File system operations",
                    "Database connectivity",
                    "Web services",
                    "Scientific computing",
                    "Error handling"
                ],
                "limitations": [
                    "AutoCAD-specific functions require COM",
                    "Slightly slower for simple drawing operations",
                    "More setup for basic tasks"
                ],
                "best_for": [
                    "batch_processing",
                    "data_analysis", 
                    "integration",
                    "complex_logic",
                    "automation_workflows"
                ],
                "performance": "high",
                "learning_curve": "moderate",
                "maintenance": "excellent"
            },
            
            LanguageType.AUTOLISP: {
                "strengths": [
                    "Native AutoCAD integration",
                    "Fast drawing operations", 
                    "Direct entity manipulation",
                    "Custom command creation",
                    "Minimal setup required",
                    "AutoCAD-optimized functions"
                ],
                "limitations": [
                    "Limited external integration",
                    "Basic data structures",
                    "No modern debugging tools",
                    "Limited error handling"
                ],
                "best_for": [
                    "drawing_automation",
                    "entity_manipulation",
                    "custom_commands",
                    "geometric_calculations",
                    "simple_workflows"
                ],
                "performance": "very_high",
                "learning_curve": "low",
                "maintenance": "moderate"
            },
            
            LanguageType.VBA: {
                "strengths": [
                    "Excel integration",
                    "User interface creation",
                    "Legacy system support",
                    "Microsoft Office integration",
                    "Form-based applications"
                ],
                "limitations": [
                    "Being phased out",
                    "Limited modern features",
                    "Security restrictions",
                    "Platform dependency"
                ],
                "best_for": [
                    "excel_integration",
                    "user_interfaces",
                    "legacy_support",
                    "office_automation",
                    "form_applications"
                ],
                "performance": "moderate",
                "learning_curve": "moderate", 
                "maintenance": "declining"
            }
        }
    
    def _initialize_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize task pattern recognition rules."""
        return {
            "drawing_operations": {
                "keywords": ["draw", "create", "line", "circle", "polyline", "arc", "entity"],
                "preferred_language": LanguageType.AUTOLISP,
                "confidence_boost": 0.3
            },
            "batch_processing": {
                "keywords": ["batch", "multiple", "process", "iterate", "loop", "files"],
                "preferred_language": LanguageType.PYTHON,
                "confidence_boost": 0.4
            },
            "data_integration": {
                "keywords": ["excel", "database", "csv", "import", "export", "data"],
                "preferred_language": LanguageType.PYTHON,
                "confidence_boost": 0.3
            },
            "user_interface": {
                "keywords": ["dialog", "form", "user", "input", "interface", "gui"],
                "preferred_language": LanguageType.VBA,
                "confidence_boost": 0.2
            },
            "complex_algorithms": {
                "keywords": ["algorithm", "calculation", "optimization", "analysis"],
                "preferred_language": LanguageType.PYTHON,
                "confidence_boost": 0.4
            },
            "custom_commands": {
                "keywords": ["command", "function", "tool", "utility", "shortcut"],
                "preferred_language": LanguageType.AUTOLISP,
                "confidence_boost": 0.3
            }
        }
    
    def parse_requirements(self, description: str) -> TaskRequirement:
        """Parse natural language description into structured requirements."""
        description_lower = description.lower()
        
        # Analyze complexity
        complexity = "basic"
        if any(word in description_lower for word in ["complex", "advanced", "sophisticated"]):
            complexity = "advanced"
        elif any(word in description_lower for word in ["multiple", "various", "different"]):
            complexity = "intermediate"
        
        # Identify operations
        operations = []
        operation_keywords = {
            "drawing": ["draw", "create", "line", "circle", "polyline", "entity"],
            "data": ["data", "import", "export", "csv", "excel", "database"],
            "ui": ["dialog", "form", "interface", "user", "input"],
            "batch": ["batch", "multiple", "process", "iterate", "loop"],
            "analysis": ["analyze", "calculate", "measure", "compute"],
            "file": ["file", "folder", "directory", "save", "load"]
        }
        
        for operation, keywords in operation_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                operations.append(operation)
        
        # Determine performance criticality
        performance_critical = any(word in description_lower for word in [
            "fast", "quick", "performance", "speed", "efficient", "optimize"
        ])
        
        # Identify integration needs
        integration_needs = []
        if "excel" in description_lower:
            integration_needs.append("excel")
        if any(word in description_lower for word in ["database", "sql"]):
            integration_needs.append("database")
        if any(word in description_lower for word in ["file", "folder"]):
            integration_needs.append("file_system")
        
        # Determine user interaction requirement
        user_interaction = any(word in description_lower for word in [
            "user", "input", "dialog", "form", "interface", "ask", "prompt"
        ])
        
        # Determine automation level
        automation_level = "full_auto"
        if any(word in description_lower for word in ["manual", "step", "confirm"]):
            automation_level = "semi_auto"
        elif any(word in description_lower for word in ["interactive", "user"]):
            automation_level = "manual"
        
        return TaskRequirement(
            description=description,
            complexity=complexity,
            operations=operations,
            performance_critical=performance_critical,
            integration_needs=integration_needs,
            user_interaction=user_interaction,
            automation_level=automation_level
        )
    
    def recommend_language(self, requirements: TaskRequirement) -> List[LanguageRecommendation]:
        """Recommend optimal language(s) for the given requirements."""
        recommendations = []
        
        for language in LanguageType:
            confidence = self._calculate_confidence(language, requirements)
            if confidence > 0.1:  # Only include viable options
                recommendation = self._create_recommendation(language, requirements, confidence)
                recommendations.append(recommendation)
        
        # Sort by confidence
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        return recommendations
    
    def _calculate_confidence(self, language: LanguageType, req: TaskRequirement) -> float:
        """Calculate confidence score for language choice."""
        base_confidence = 0.3
        capabilities = self.language_capabilities[language]
        
        # Pattern matching boost
        for pattern_name, pattern_info in self.task_patterns.items():
            if any(keyword in req.description.lower() for keyword in pattern_info["keywords"]):
                if pattern_info["preferred_language"] == language:
                    base_confidence += pattern_info["confidence_boost"]
        
        # Operation alignment
        operation_matches = 0
        for operation in req.operations:
            if operation in capabilities["best_for"]:
                operation_matches += 1
        
        if req.operations:
            operation_score = operation_matches / len(req.operations) * 0.3
            base_confidence += operation_score
        
        # Integration requirements
        integration_penalty = 0
        if "excel" in req.integration_needs and language != LanguageType.VBA:
            if language == LanguageType.PYTHON:
                integration_penalty = 0.1  # Python can handle Excel but not as natively
            else:
                integration_penalty = 0.3  # AutoLISP struggles with Excel
        
        if "database" in req.integration_needs and language != LanguageType.PYTHON:
            integration_penalty += 0.2
        
        # Performance considerations
        if req.performance_critical:
            if language == LanguageType.AUTOLISP:
                base_confidence += 0.2
            elif language == LanguageType.PYTHON:
                base_confidence -= 0.1
        
        # Complexity considerations
        if req.complexity == "advanced":
            if language == LanguageType.PYTHON:
                base_confidence += 0.2
            elif language == LanguageType.AUTOLISP:
                base_confidence -= 0.1
        
        # User interaction requirements
        if req.user_interaction:
            if language == LanguageType.VBA:
                base_confidence += 0.2
            elif language == LanguageType.AUTOLISP:
                base_confidence -= 0.1
        
        return max(0.0, min(1.0, base_confidence - integration_penalty))
    
    def _create_recommendation(self, language: LanguageType, req: TaskRequirement, confidence: float) -> LanguageRecommendation:
        """Create detailed language recommendation."""
        capabilities = self.language_capabilities[language]
        
        # Generate reasoning
        reasons = []
        if confidence > 0.7:
            reasons.append(f"Excellent match for {', '.join(req.operations)} operations")
        elif confidence > 0.5:
            reasons.append(f"Good fit for this type of task")
        else:
            reasons.append(f"Viable option with some limitations")
        
        # Add specific reasoning
        if language == LanguageType.PYTHON and "data" in req.operations:
            reasons.append("Python excels at data processing and integration")
        elif language == LanguageType.AUTOLISP and "drawing" in req.operations:
            reasons.append("AutoLISP provides native AutoCAD integration")
        elif language == LanguageType.VBA and req.user_interaction:
            reasons.append("VBA offers excellent UI capabilities")
        
        # Estimate development time
        time_estimates = {
            "basic": {"python": "2-4 hours", "autolisp": "1-2 hours", "vba": "3-5 hours"},
            "intermediate": {"python": "1-2 days", "autolisp": "4-8 hours", "vba": "1-3 days"},
            "advanced": {"python": "3-5 days", "autolisp": "2-4 days", "vba": "1-2 weeks"}
        }
        
        estimated_time = time_estimates[req.complexity][language.value]
        
        return LanguageRecommendation(
            language=language,
            confidence=confidence,
            reasoning=". ".join(reasons),
            advantages=capabilities["strengths"][:3],  # Top 3 advantages
            limitations=capabilities["limitations"][:2],  # Top 2 limitations
            estimated_development_time=estimated_time
        )
    
    def create_hybrid_solution(self, requirements: TaskRequirement) -> Dict[str, Any]:
        """Create a hybrid solution using multiple languages optimally."""
        recommendations = self.recommend_language(requirements)
        
        if len(recommendations) < 2:
            return {
                "hybrid_recommended": False,
                "reason": "Single language solution is optimal",
                "primary_language": recommendations[0].language.value if recommendations else "python"
            }
        
        # Analyze if hybrid makes sense
        primary = recommendations[0]
        secondary = recommendations[1]
        
        # Hybrid scenarios
        hybrid_scenarios = [
            {
                "condition": "excel" in requirements.integration_needs and "drawing" in requirements.operations,
                "solution": {
                    "primary": LanguageType.AUTOLISP,
                    "secondary": LanguageType.PYTHON,
                    "workflow": "AutoLISP for drawing operations, Python for Excel integration"
                }
            },
            {
                "condition": requirements.user_interaction and "batch" in requirements.operations,
                "solution": {
                    "primary": LanguageType.PYTHON,
                    "secondary": LanguageType.VBA,
                    "workflow": "Python for batch processing, VBA for user interface"
                }
            },
            {
                "condition": "data" in requirements.operations and "drawing" in requirements.operations,
                "solution": {
                    "primary": LanguageType.PYTHON,
                    "secondary": LanguageType.AUTOLISP,
                    "workflow": "Python for data processing, AutoLISP for drawing operations"
                }
            }
        ]
        
        for scenario in hybrid_scenarios:
            condition_met = False
            
            # Evaluate condition safely
            if scenario["condition"] == "\"excel\" in requirements.integration_needs and \"drawing\" in requirements.operations":
                condition_met = "excel" in requirements.integration_needs and "drawing" in requirements.operations
            elif scenario["condition"] == "requirements.user_interaction and \"batch\" in requirements.operations":
                condition_met = requirements.user_interaction and "batch" in requirements.operations
            elif scenario["condition"] == "\"data\" in requirements.operations and \"drawing\" in requirements.operations":
                condition_met = "data" in requirements.operations and "drawing" in requirements.operations
            
            if condition_met:
                return {
                    "hybrid_recommended": True,
                    "primary_language": scenario["solution"]["primary"].value,
                    "secondary_language": scenario["solution"]["secondary"].value,
                    "workflow_description": scenario["solution"]["workflow"],
                    "implementation_approach": "Modular design with clear interfaces between components"
                }
        
        return {
            "hybrid_recommended": False,
            "reason": f"Single language ({primary.language.value}) handles all requirements effectively",
            "primary_language": primary.language.value
        }
    
    def get_language_capabilities(self, language: str) -> Dict[str, Any]:
        """Get detailed capabilities for a specific language."""
        try:
            lang_type = LanguageType(language.lower())
            return self.language_capabilities[lang_type]
        except ValueError:
            return {"error": f"Unsupported language: {language}"}
    
    def suggest_optimal_approach(self, description: str) -> Dict[str, Any]:
        """Complete analysis and recommendation for a task description."""
        requirements = self.parse_requirements(description)
        recommendations = self.recommend_language(requirements)
        hybrid_solution = self.create_hybrid_solution(requirements)
        
        return {
            "task_analysis": {
                "complexity": requirements.complexity,
                "operations": requirements.operations,
                "integration_needs": requirements.integration_needs,
                "performance_critical": requirements.performance_critical,
                "user_interaction": requirements.user_interaction
            },
            "language_recommendations": [
                {
                    "language": rec.language.value,
                    "confidence": rec.confidence,
                    "reasoning": rec.reasoning,
                    "advantages": rec.advantages,
                    "limitations": rec.limitations,
                    "estimated_time": rec.estimated_development_time
                }
                for rec in recommendations[:3]  # Top 3 recommendations
            ],
            "hybrid_solution": hybrid_solution,
            "final_recommendation": {
                "approach": "hybrid" if hybrid_solution["hybrid_recommended"] else "single_language",
                "primary_language": hybrid_solution.get("primary_language", recommendations[0].language.value if recommendations else "python"),
                "confidence": recommendations[0].confidence if recommendations else 0.5
            }
        }