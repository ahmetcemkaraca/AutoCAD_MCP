"""
Documentation Generator for AutoCAD Projects.

Automatically generates comprehensive documentation for AutoCAD automation projects,
including API docs, tutorials, and user guides.
"""

import os
import ast
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FunctionDoc:
    """Documentation for a function."""
    name: str
    signature: str
    docstring: str
    parameters: List[Dict[str, str]] = field(default_factory=list)
    returns: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    source_file: str = ""
    line_number: int = 0


@dataclass
class ClassDoc:
    """Documentation for a class."""
    name: str
    docstring: str
    methods: List[FunctionDoc] = field(default_factory=list)
    attributes: List[Dict[str, str]] = field(default_factory=list)
    inheritance: List[str] = field(default_factory=list)
    source_file: str = ""
    line_number: int = 0


@dataclass
class ModuleDoc:
    """Documentation for a module."""
    name: str
    docstring: str
    functions: List[FunctionDoc] = field(default_factory=list)
    classes: List[ClassDoc] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    file_path: str = ""


class DocumentationGenerator:
    """Generates comprehensive documentation for AutoCAD projects."""
    
    def __init__(self):
        self.project_docs: Dict[str, ModuleDoc] = {}
        
    def generate_project_documentation(self, project_path: str, 
                                     output_dir: str = "docs/generated") -> str:
        """Generate complete project documentation."""
        project_path = Path(project_path)
        output_path = Path(project_path) / output_dir
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating documentation for project at {project_path}")
        
        # Analyze project structure
        self._analyze_project(project_path)
        
        # Generate different types of documentation
        self._generate_api_documentation(output_path)
        self._generate_user_guide(output_path, project_path)
        self._generate_tutorial(output_path, project_path)
        self._generate_readme_updates(project_path)
        
        logger.info(f"Documentation generated at {output_path}")
        return str(output_path)
    
    def _analyze_project(self, project_path: Path):
        """Analyze project structure and extract documentation."""
        python_files = list(project_path.glob("src/**/*.py"))
        
        for py_file in python_files:
            try:
                module_doc = self._analyze_python_file(py_file, project_path)
                if module_doc:
                    self.project_docs[module_doc.name] = module_doc
            except Exception as e:
                logger.warning(f"Failed to analyze {py_file}: {e}")
    
    def _analyze_python_file(self, file_path: Path, project_root: Path) -> Optional[ModuleDoc]:
        """Analyze a Python file and extract documentation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            # Get relative module name
            relative_path = file_path.relative_to(project_root)
            module_name = str(relative_path).replace(os.sep, '.').replace('.py', '')
            
            # Extract module docstring
            module_docstring = ast.get_docstring(tree) or ""
            
            module_doc = ModuleDoc(
                name=module_name,
                docstring=module_docstring,
                file_path=str(file_path)
            )
            
            # Analyze AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):  # Skip private functions
                        func_doc = self._extract_function_doc(node, str(file_path))
                        module_doc.functions.append(func_doc)
                
                elif isinstance(node, ast.ClassDef):
                    class_doc = self._extract_class_doc(node, str(file_path))
                    module_doc.classes.append(class_doc)
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_str = self._extract_import_string(node)
                    if import_str:
                        module_doc.imports.append(import_str)
            
            return module_doc
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return None
    
    def _extract_function_doc(self, node: ast.FunctionDef, source_file: str) -> FunctionDoc:
        """Extract documentation from function AST node."""
        # Get function signature
        args = [arg.arg for arg in node.args.args]
        signature = f"{node.name}({', '.join(args)})"
        
        # Get docstring
        docstring = ast.get_docstring(node) or ""
        
        # Parse parameters and return type from docstring
        parameters, returns, examples = self._parse_docstring(docstring)
        
        return FunctionDoc(
            name=node.name,
            signature=signature,
            docstring=docstring,
            parameters=parameters,
            returns=returns,
            examples=examples,
            source_file=source_file,
            line_number=node.lineno
        )
    
    def _extract_class_doc(self, node: ast.ClassDef, source_file: str) -> ClassDoc:
        """Extract documentation from class AST node."""
        docstring = ast.get_docstring(node) or ""
        
        # Get inheritance
        inheritance = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                inheritance.append(base.id)
            elif isinstance(base, ast.Attribute):
                inheritance.append(f"{base.value.id}.{base.attr}")
        
        class_doc = ClassDoc(
            name=node.name,
            docstring=docstring,
            inheritance=inheritance,
            source_file=source_file,
            line_number=node.lineno
        )
        
        # Extract methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                method_doc = self._extract_function_doc(item, source_file)
                class_doc.methods.append(method_doc)
        
        return class_doc
    
    def _extract_import_string(self, node) -> Optional[str]:
        """Extract import statement as string."""
        if isinstance(node, ast.Import):
            return f"import {', '.join(alias.name for alias in node.names)}"
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ', '.join(alias.name for alias in node.names)
            return f"from {module} import {names}"
        return None
    
    def _parse_docstring(self, docstring: str) -> tuple:
        """Parse docstring to extract parameters, return type, and examples."""
        parameters = []
        returns = None
        examples = []
        
        if not docstring:
            return parameters, returns, examples
        
        lines = docstring.split('\\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('Args:') or line.startswith('Parameters:'):
                current_section = 'params'
                continue
            elif line.startswith('Returns:'):
                current_section = 'returns'
                continue
            elif line.startswith('Examples:'):
                current_section = 'examples'
                continue
            elif line.startswith('Example:'):
                current_section = 'examples'
                continue
            
            if current_section == 'params' and ':' in line:
                param_parts = line.split(':', 1)
                if len(param_parts) == 2:
                    param_name = param_parts[0].strip()
                    param_desc = param_parts[1].strip()
                    parameters.append({
                        'name': param_name,
                        'description': param_desc
                    })
            
            elif current_section == 'returns' and line:
                returns = line
            
            elif current_section == 'examples' and line:
                examples.append(line)
        
        return parameters, returns, examples
    
    def _generate_api_documentation(self, output_path: Path):
        """Generate API documentation."""
        api_doc_path = output_path / "api.md"
        
        with open(api_doc_path, 'w', encoding='utf-8') as f:
            f.write("# API Documentation\\n\\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
            
            for module_name, module_doc in self.project_docs.items():
                f.write(f"## Module: `{module_name}`\\n\\n")
                
                if module_doc.docstring:
                    f.write(f"{module_doc.docstring}\\n\\n")
                
                # Document classes
                if module_doc.classes:
                    f.write("### Classes\\n\\n")
                    for class_doc in module_doc.classes:
                        f.write(f"#### `{class_doc.name}`\\n\\n")
                        
                        if class_doc.inheritance:
                            f.write(f"**Inherits from:** {', '.join(class_doc.inheritance)}\\n\\n")
                        
                        if class_doc.docstring:
                            f.write(f"{class_doc.docstring}\\n\\n")
                        
                        # Document methods
                        if class_doc.methods:
                            f.write("**Methods:**\\n\\n")
                            for method in class_doc.methods:
                                f.write(f"##### `{method.signature}`\\n\\n")
                                if method.docstring:
                                    f.write(f"{method.docstring}\\n\\n")
                                
                                if method.parameters:
                                    f.write("**Parameters:**\\n")
                                    for param in method.parameters:
                                        f.write(f"- `{param['name']}`: {param['description']}\\n")
                                    f.write("\\n")
                                
                                if method.returns:
                                    f.write(f"**Returns:** {method.returns}\\n\\n")
                                
                                if method.examples:
                                    f.write("**Examples:**\\n")
                                    for example in method.examples:
                                        f.write(f"```python\\n{example}\\n```\\n")
                                    f.write("\\n")
                
                # Document functions
                if module_doc.functions:
                    f.write("### Functions\\n\\n")
                    for func_doc in module_doc.functions:
                        f.write(f"#### `{func_doc.signature}`\\n\\n")
                        
                        if func_doc.docstring:
                            f.write(f"{func_doc.docstring}\\n\\n")
                        
                        if func_doc.parameters:
                            f.write("**Parameters:**\\n")
                            for param in func_doc.parameters:
                                f.write(f"- `{param['name']}`: {param['description']}\\n")
                            f.write("\\n")
                        
                        if func_doc.returns:
                            f.write(f"**Returns:** {func_doc.returns}\\n\\n")
                        
                        if func_doc.examples:
                            f.write("**Examples:**\\n")
                            for example in func_doc.examples:
                                f.write(f"```python\\n{example}\\n```\\n")
                            f.write("\\n")
                
                f.write("---\\n\\n")
        
        logger.info(f"API documentation generated: {api_doc_path}")
    
    def _generate_user_guide(self, output_path: Path, project_path: Path):
        """Generate user guide."""
        guide_path = output_path / "user_guide.md"
        
        # Detect project type
        project_type = self._detect_project_type(project_path)
        
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write("# User Guide\\n\\n")
            
            f.write("## Quick Start\\n\\n")
            f.write("This guide helps you get started with your AutoCAD automation project.\\n\\n")
            
            f.write("### Installation\\n\\n")
            f.write("1. Ensure you have AutoCAD 2025 or later installed\\n")
            f.write("2. Install Python 3.12 or later\\n")
            f.write("3. Install project dependencies:\\n")
            f.write("   ```bash\\n")
            f.write("   poetry install\\n")
            f.write("   # or\\n")
            f.write("   pip install -r requirements.txt\\n")
            f.write("   ```\\n\\n")
            
            f.write("### Basic Usage\\n\\n")
            
            if project_type == "basic_autocad":
                f.write(self._get_basic_usage_guide())
            elif project_type == "advanced_mcp":
                f.write(self._get_mcp_usage_guide())
            elif project_type == "manufacturing_cad":
                f.write(self._get_manufacturing_usage_guide())
            
            f.write("\\n## Configuration\\n\\n")
            f.write("Configure your project by editing the `config/settings.json` file:\\n\\n")
            f.write("```json\\n")
            f.write('{\\n')
            f.write('  "autocad": {\\n')
            f.write('    "version": "2025",\\n')
            f.write('    "visibility": true\\n')
            f.write('  }\\n')
            f.write('}\\n')
            f.write("```\\n\\n")
            
            f.write("## Troubleshooting\\n\\n")
            f.write("### Common Issues\\n\\n")
            f.write("1. **AutoCAD connection failed**\\n")
            f.write("   - Ensure AutoCAD is running\\n")
            f.write("   - Check that COM interface is enabled\\n\\n")
            f.write("2. **Import errors**\\n")
            f.write("   - Verify all dependencies are installed\\n")
            f.write("   - Check Python version compatibility\\n\\n")
        
        logger.info(f"User guide generated: {guide_path}")
    
    def _generate_tutorial(self, output_path: Path, project_path: Path):
        """Generate tutorial documentation."""
        tutorial_path = output_path / "tutorial.md"
        
        with open(tutorial_path, 'w', encoding='utf-8') as f:
            f.write("# Tutorial\\n\\n")
            f.write("Step-by-step tutorial for AutoCAD automation.\\n\\n")
            
            f.write("## Lesson 1: Basic Drawing Operations\\n\\n")
            f.write("Learn how to create basic shapes in AutoCAD using Python.\\n\\n")
            
            f.write("```python\\n")
            f.write("from src.autocad_utils import AutoCADConnection\\n\\n")
            f.write("# Connect to AutoCAD\\n")
            f.write("acad = AutoCADConnection()\\n")
            f.write("acad.connect()\\n\\n")
            f.write("# Create a line\\n")
            f.write("acad.create_line([0, 0, 0], [100, 100, 0])\\n\\n")
            f.write("# Create a circle\\n")
            f.write("acad.create_circle([50, 50, 0], 25)\\n")
            f.write("```\\n\\n")
            
            f.write("## Lesson 2: Working with Selections\\n\\n")
            f.write("Learn how to select and modify existing objects.\\n\\n")
            
            f.write("## Lesson 3: Advanced Operations\\n\\n")
            f.write("Explore advanced AutoCAD automation techniques.\\n\\n")
        
        logger.info(f"Tutorial generated: {tutorial_path}")
    
    def _generate_readme_updates(self, project_path: Path):
        """Update project README with generated documentation links."""
        readme_path = project_path / "README.md"
        
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add documentation section if not present
            if "## Documentation" not in content:
                doc_section = """
## Documentation

- [API Documentation](docs/generated/api.md) - Complete API reference
- [User Guide](docs/generated/user_guide.md) - Getting started guide
- [Tutorial](docs/generated/tutorial.md) - Step-by-step tutorial

"""
                # Insert before the last section or at the end
                if "## License" in content:
                    content = content.replace("## License", doc_section + "## License")
                else:
                    content += doc_section
                
                with open(readme_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info("Updated README with documentation links")
    
    def _detect_project_type(self, project_path: Path) -> str:
        """Detect the type of AutoCAD project."""
        if (project_path / "src" / "mcp_tools").exists():
            return "advanced_mcp"
        elif (project_path / "src" / "manufacturing").exists():
            return "manufacturing_cad"
        else:
            return "basic_autocad"
    
    def _get_basic_usage_guide(self) -> str:
        """Get usage guide for basic AutoCAD projects."""
        return """```python
from src.main import AutoCADAutomation

# Create and run automation
automation = AutoCADAutomation()
automation.run()
```

The main automation class handles:
- AutoCAD connection management
- Basic drawing operations
- Error handling and cleanup
"""
    
    def _get_mcp_usage_guide(self) -> str:
        """Get usage guide for MCP projects."""
        return """### Starting the MCP Server

```bash
python src/mcp_tools/server.py
```

### Using with VS Code

1. Install the MCP extension for VS Code
2. Connect to the MCP server
3. Use the command palette to access AutoCAD tools

### Available MCP Tools

The project provides MCP tools for:
- Creating AutoCAD objects
- Analyzing drawings
- Batch processing operations
"""
    
    def _get_manufacturing_usage_guide(self) -> str:
        """Get usage guide for manufacturing projects."""
        return """### Manufacturing Workflow

```python
from src.manufacturing.pattern_optimizer import PatternOptimizer
from src.manufacturing.surface_unfolding import SurfaceUnfolder

# Initialize tools
optimizer = PatternOptimizer()
unfolder = SurfaceUnfolder()

# Optimize material usage
result = optimizer.optimize_nesting(parts_list)

# Unfold 3D surfaces
pattern = unfolder.unfold_surface(surface_data)
```

### Supported Operations

- Pattern nesting optimization
- Surface unfolding with LSCM
- Material usage calculation
- Batch processing for manufacturing
"""
    
    def generate_changelog(self, project_path: str, version: str = "0.1.0") -> str:
        """Generate changelog documentation."""
        changelog_path = Path(project_path) / "CHANGELOG.md"
        
        changelog_content = f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [{version}] - {datetime.now().strftime('%Y-%m-%d')}

### Added
- Initial project structure
- AutoCAD automation framework
- Basic drawing operations
- Documentation generation
- Testing framework

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A
"""
        
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write(changelog_content)
        
        logger.info(f"Changelog generated: {changelog_path}")
        return str(changelog_path)
    
    def generate_contributing_guide(self, project_path: str) -> str:
        """Generate contributing guidelines."""
        contrib_path = Path(project_path) / "CONTRIBUTING.md"
        
        contrib_content = """# Contributing Guidelines

Thank you for your interest in contributing to this AutoCAD automation project!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone <your-fork-url>`
3. Create a new branch: `git checkout -b feature/your-feature-name`
4. Install dependencies: `poetry install`
5. Make your changes
6. Run tests: `python -m pytest`
7. Commit your changes: `git commit -m "Add your feature"`
8. Push to your fork: `git push origin feature/your-feature-name`
9. Create a Pull Request

## Development Setup

### Prerequisites
- Python 3.12+
- AutoCAD 2025+
- Poetry (recommended) or pip

### Code Style
- Use Black for code formatting: `black .`
- Use Ruff for linting: `ruff check .`
- Use MyPy for type checking: `mypy src/`

### Testing
- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for high test coverage

### Documentation
- Update documentation for new features
- Include docstrings for all public functions
- Add examples where appropriate

## Pull Request Guidelines

- Provide clear description of changes
- Include tests for new functionality
- Update documentation as needed
- Follow existing code style
- Keep commits focused and atomic

## Reporting Issues

When reporting issues, please include:
- AutoCAD version
- Python version
- Error messages and stack traces
- Steps to reproduce
- Expected vs actual behavior

## Code of Conduct

This project follows standard open source community guidelines. Be respectful and constructive in all interactions.
"""
        
        with open(contrib_path, 'w', encoding='utf-8') as f:
            f.write(contrib_content)
        
        logger.info(f"Contributing guide generated: {contrib_path}")
        return str(contrib_path)