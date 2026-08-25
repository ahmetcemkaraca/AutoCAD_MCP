"""
Project Template System for AutoCAD Automation.

Provides tools for creating new AutoCAD automation projects from templates,
including project scaffolding, dependency management, and documentation generation.
"""

from .template_engine import TemplateEngine
from .project_scaffolder import ProjectScaffolder
from .dependency_manager import DependencyManager
from .documentation_generator import DocumentationGenerator

__all__ = [
    'TemplateEngine',
    'ProjectScaffolder', 
    'DependencyManager',
    'DocumentationGenerator',
]