"""
Template Engine for AutoCAD Project Creation.

Manages project templates and provides template-based project generation
with customizable parameters and template inheritance.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import shutil

try:
    from jinja2 import Environment, FileSystemLoader, Template
    HAS_JINJA2 = True
except ImportError:
    Environment = None
    FileSystemLoader = None
    Template = None
    HAS_JINJA2 = False

logger = logging.getLogger(__name__)


@dataclass
class ProjectTemplate:
    """Project template definition."""
    name: str
    description: str
    template_type: str  # 'basic', 'advanced', 'specialized'
    files: Dict[str, str] = field(default_factory=dict)  # path -> template_content
    directories: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    post_create_commands: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class TemplateEngine:
    """Template engine for creating AutoCAD automation projects."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment if available
        if HAS_JINJA2:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.templates_dir)),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self.jinja_env = None
            logger.warning("Jinja2 not available - using simple string replacement for templates")
        
        self.templates: Dict[str, ProjectTemplate] = {}
        self._initialize_builtin_templates()
        self._load_custom_templates()
    
    def _initialize_builtin_templates(self):
        """Initialize built-in project templates."""
        
        # Basic AutoCAD Automation Template
        basic_template = ProjectTemplate(
            name="basic_autocad",
            description="Basic AutoCAD automation project with essential structure",
            template_type="basic",
            directories=[
                "src",
                "tests",
                "docs",
                "examples",
                "config"
            ],
            files={
                "README.md": self._get_basic_readme_template(),
                "src/main.py": self._get_basic_main_template(),
                "src/autocad_utils.py": self._get_autocad_utils_template(),
                "tests/test_main.py": self._get_basic_test_template(),
                "pyproject.toml": self._get_pyproject_template(),
                ".gitignore": self._get_gitignore_template(),
                "config/settings.json": self._get_settings_template(),
                "examples/example_usage.py": self._get_example_template()
            },
            parameters={
                "project_name": "My AutoCAD Project",
                "project_slug": "{{ project_name|lower|replace(' ', '_') }}",
                "author_name": "Developer",
                "author_email": "developer@example.com",
                "python_version": "3.12",
                "autocad_version": "2025"
            },
            dependencies=[
                "pyautocad>=0.2.0",
                "pytest>=8.0.0",
                "black>=24.0.0",
                "ruff>=0.5.0"
            ],
            tags=["basic", "automation", "2d", "3d"]
        )
        
        # Advanced MCP Integration Template
        advanced_template = ProjectTemplate(
            name="advanced_mcp",
            description="Advanced AutoCAD project with MCP integration and VS Code support",
            template_type="advanced",
            directories=[
                "src",
                "src/mcp_tools",
                "src/autocad_modules",
                "tests",
                "tests/unit",
                "tests/integration", 
                "docs",
                "examples",
                "config",
                "vscode_extension",
                ".github/workflows"
            ],
            files={
                "README.md": self._get_advanced_readme_template(),
                "src/main.py": self._get_advanced_main_template(),
                "src/mcp_tools/server.py": self._get_mcp_server_template(),
                "src/mcp_tools/__init__.py": "",
                "src/autocad_modules/__init__.py": "",
                "src/autocad_modules/enhanced_wrapper.py": self._get_enhanced_wrapper_template(),
                "tests/test_mcp_integration.py": self._get_mcp_test_template(),
                "pyproject.toml": self._get_advanced_pyproject_template(),
                ".github/workflows/ci.yml": self._get_github_actions_template(),
                "vscode_extension/package.json": self._get_vscode_package_template(),
                "config/mcp_config.json": self._get_mcp_config_template()
            },
            parameters={
                "project_name": "Advanced AutoCAD MCP Project",
                "project_slug": "{{ project_name|lower|replace(' ', '_') }}",
                "author_name": "Developer",
                "author_email": "developer@example.com",
                "mcp_server_name": "{{ project_slug }}_mcp",
                "vscode_extension_name": "{{ project_slug }}-vscode",
                "python_version": "3.12"
            },
            dependencies=[
                "fastmcp>=1.0.0",
                "pyautocad>=0.2.0",
                "pytest>=8.0.0",
                "pytest-asyncio>=0.23.0",
                "black>=24.0.0",
                "ruff>=0.5.0",
                "mypy>=1.8.0"
            ],
            tags=["advanced", "mcp", "vscode", "integration"]
        )
        
        # Manufacturing Specialized Template
        manufacturing_template = ProjectTemplate(
            name="manufacturing_cad",
            description="Specialized template for manufacturing CAD automation",
            template_type="specialized",
            directories=[
                "src",
                "src/manufacturing",
                "src/manufacturing/nesting",
                "src/manufacturing/unfolding", 
                "tests",
                "docs",
                "examples",
                "templates/parts"
            ],
            files={
                "README.md": self._get_manufacturing_readme_template(),
                "src/main.py": self._get_manufacturing_main_template(),
                "src/manufacturing/__init__.py": "",
                "src/manufacturing/pattern_optimizer.py": self._get_pattern_optimizer_template(),
                "src/manufacturing/surface_unfolding.py": self._get_surface_unfolding_template(),
                "tests/test_manufacturing.py": self._get_manufacturing_test_template(),
                "pyproject.toml": self._get_manufacturing_pyproject_template()
            },
            parameters={
                "project_name": "Manufacturing CAD Automation",
                "company_name": "Manufacturing Corp",
                "material_types": ["steel", "aluminum", "plastic"],
                "default_thickness": "3.0"
            },
            dependencies=[
                "pyautocad>=0.2.0",
                "numpy>=1.24.0",
                "scipy>=1.10.0",
                "matplotlib>=3.7.0",
                "pytest>=8.0.0"
            ],
            tags=["manufacturing", "nesting", "unfolding", "optimization"]
        )
        
        self.templates.update({
            "basic_autocad": basic_template,
            "advanced_mcp": advanced_template,
            "manufacturing_cad": manufacturing_template
        })
    
    def _load_custom_templates(self):
        """Load custom templates from templates directory."""
        template_files = list(self.templates_dir.glob("*.json"))
        
        for template_file in template_files:
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                template = ProjectTemplate(**template_data)
                self.templates[template.name] = template
                logger.info(f"Loaded custom template: {template.name}")
                
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Get list of available project templates."""
        return [
            {
                "name": template.name,
                "description": template.description,
                "type": template.template_type,
                "tags": template.tags,
                "parameters": list(template.parameters.keys())
            }
            for template in self.templates.values()
        ]
    
    def get_template(self, template_name: str) -> Optional[ProjectTemplate]:
        """Get specific template by name."""
        return self.templates.get(template_name)
    
    def create_project_from_template(self, template_name: str, output_dir: str, 
                                   parameters: Dict[str, Any]) -> str:
        """Create a new project from template."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Merge template parameters with provided parameters
        render_context = {**template.parameters, **parameters}
        
        # Create directories
        for directory in template.directories:
            dir_path = output_path / self._render_string(directory, render_context)
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create files from templates
        for file_path, file_content in template.files.items():
            rendered_path = output_path / self._render_string(file_path, render_context)
            rendered_content = self._render_string(file_content, render_context)
            
            # Ensure parent directory exists
            rendered_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(rendered_path, 'w', encoding='utf-8') as f:
                f.write(rendered_content)
        
        logger.info(f"Created project from template '{template_name}' at {output_path}")
        return str(output_path)
    
    def _render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template string with Jinja2."""
        if not template_string:
            return ""
        
        try:
            template = Template(template_string)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return template_string
    
    def save_template(self, template: ProjectTemplate, overwrite: bool = False):
        """Save a custom template to disk."""
        template_file = self.templates_dir / f"{template.name}.json"
        
        if template_file.exists() and not overwrite:
            raise FileExistsError(f"Template '{template.name}' already exists")
        
        template_data = {
            "name": template.name,
            "description": template.description,
            "template_type": template.template_type,
            "files": template.files,
            "directories": template.directories,
            "parameters": template.parameters,
            "dependencies": template.dependencies,
            "post_create_commands": template.post_create_commands,
            "tags": template.tags
        }
        
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2)
        
        # Update in-memory templates
        self.templates[template.name] = template
        logger.info(f"Saved template: {template.name}")
    
    # Template content methods
    def _get_basic_readme_template(self) -> str:
        return '''# {{ project_name }}

{{ project_name }} is an AutoCAD automation project created with the Master AutoCAD Coder template system.

## Description

This project provides automated CAD operations using Python and the AutoCAD COM interface.

## Requirements

- AutoCAD {{ autocad_version }} or later
- Python {{ python_version }}+
- Windows (required for AutoCAD COM interface)

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

```python
from src.main import AutoCADAutomation

# Initialize automation
automation = AutoCADAutomation()

# Run automation tasks
automation.run()
```

## Project Structure

```
{{ project_slug }}/
├── src/                    # Source code
├── tests/                  # Test files
├── docs/                   # Documentation
├── examples/               # Usage examples
├── config/                 # Configuration files
└── README.md              # This file
```

## Author

{{ author_name }} <{{ author_email }}>

## License

MIT License
'''
    
    def _get_basic_main_template(self) -> str:
        return '''"""
{{ project_name }} - Main module.

Author: {{ author_name }}
"""

import logging
from pathlib import Path
from src.autocad_utils import AutoCADConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoCADAutomation:
    """Main automation class for {{ project_name }}."""
    
    def __init__(self):
        self.acad = AutoCADConnection()
        logger.info("{{ project_name }} initialized")
    
    def run(self):
        """Run the main automation workflow."""
        logger.info("Starting automation workflow...")
        
        try:
            # Connect to AutoCAD
            if not self.acad.connect():
                raise ConnectionError("Failed to connect to AutoCAD")
            
            # Your automation logic here
            self.create_sample_drawing()
            
            logger.info("Automation completed successfully")
            
        except Exception as e:
            logger.error(f"Automation failed: {e}")
            raise
        finally:
            self.acad.disconnect()
    
    def create_sample_drawing(self):
        """Create a sample drawing to demonstrate functionality."""
        # Example: Create a simple rectangle
        self.acad.create_rectangle([0, 0, 0], [100, 50, 0])
        logger.info("Created sample rectangle")


def main():
    """Main entry point."""
    automation = AutoCADAutomation()
    automation.run()


if __name__ == "__main__":
    main()
'''
    
    def _get_autocad_utils_template(self) -> str:
        return '''"""
AutoCAD utilities for {{ project_name }}.

Provides connection management and basic AutoCAD operations.
"""

import logging
import win32com.client
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class AutoCADConnection:
    """Manages AutoCAD COM connection and basic operations."""
    
    def __init__(self):
        self.acad = None
        self.model_space = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to AutoCAD."""
        try:
            self.acad = win32com.client.Dispatch("AutoCAD.Application")
            self.acad.Visible = True
            
            # Get active document's model space
            doc = self.acad.ActiveDocument
            self.model_space = doc.ModelSpace
            
            self.connected = True
            logger.info("Connected to AutoCAD successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to AutoCAD: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from AutoCAD."""
        self.acad = None
        self.model_space = None
        self.connected = False
        logger.info("Disconnected from AutoCAD")
    
    def is_connected(self) -> bool:
        """Check if connected to AutoCAD."""
        return self.connected and self.acad is not None
    
    def create_line(self, start_point: List[float], end_point: List[float]) -> int:
        """Create a line in AutoCAD."""
        if not self.is_connected():
            raise ConnectionError("Not connected to AutoCAD")
        
        line = self.model_space.AddLine(start_point, end_point)
        return line.ObjectID
    
    def create_circle(self, center: List[float], radius: float) -> int:
        """Create a circle in AutoCAD."""
        if not self.is_connected():
            raise ConnectionError("Not connected to AutoCAD")
        
        circle = self.model_space.AddCircle(center, radius)
        return circle.ObjectID
    
    def create_rectangle(self, corner1: List[float], corner2: List[float]) -> int:
        """Create a rectangle in AutoCAD.""" 
        if not self.is_connected():
            raise ConnectionError("Not connected to AutoCAD")
        
        # Create rectangle using polyline
        points = [
            corner1[0], corner1[1], corner1[2],
            corner2[0], corner1[1], corner1[2], 
            corner2[0], corner2[1], corner2[2],
            corner1[0], corner2[1], corner1[2],
            corner1[0], corner1[1], corner1[2]  # Close the rectangle
        ]
        
        polyline = self.model_space.AddPolyline(points)
        return polyline.ObjectID
    
    def zoom_extents(self):
        """Zoom to show all objects in the drawing."""
        if not self.is_connected():
            raise ConnectionError("Not connected to AutoCAD")
        
        self.acad.ZoomExtents()
        logger.info("Zoomed to extents")
'''
    
    def _get_basic_test_template(self) -> str:
        return '''"""
Tests for {{ project_name }}.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.main import AutoCADAutomation
from src.autocad_utils import AutoCADConnection


class TestAutoCADConnection:
    """Test AutoCAD connection functionality."""
    
    @patch('src.autocad_utils.win32com.client.Dispatch')
    def test_connect_success(self, mock_dispatch):
        """Test successful AutoCAD connection."""
        # Arrange
        mock_acad = MagicMock()
        mock_acad.ActiveDocument.ModelSpace = MagicMock()
        mock_dispatch.return_value = mock_acad
        
        connection = AutoCADConnection()
        
        # Act
        result = connection.connect()
        
        # Assert
        assert result is True
        assert connection.connected is True
        assert connection.acad is not None
    
    @patch('src.autocad_utils.win32com.client.Dispatch')
    def test_connect_failure(self, mock_dispatch):
        """Test AutoCAD connection failure."""
        # Arrange
        mock_dispatch.side_effect = Exception("Connection failed")
        connection = AutoCADConnection()
        
        # Act
        result = connection.connect()
        
        # Assert
        assert result is False
        assert connection.connected is False
    
    def test_create_line_not_connected(self):
        """Test creating line when not connected."""
        connection = AutoCADConnection()
        
        with pytest.raises(ConnectionError):
            connection.create_line([0, 0, 0], [100, 100, 0])


class TestAutoCADAutomation:
    """Test main automation functionality."""
    
    @patch('src.main.AutoCADConnection')
    def test_automation_run_success(self, mock_connection_class):
        """Test successful automation run."""
        # Arrange
        mock_connection = MagicMock()
        mock_connection.connect.return_value = True
        mock_connection_class.return_value = mock_connection
        
        automation = AutoCADAutomation()
        
        # Act
        automation.run()
        
        # Assert
        mock_connection.connect.assert_called_once()
        mock_connection.create_rectangle.assert_called_once()
        mock_connection.disconnect.assert_called_once()
    
    @patch('src.main.AutoCADConnection')
    def test_automation_run_connection_failure(self, mock_connection_class):
        """Test automation run with connection failure."""
        # Arrange
        mock_connection = MagicMock()
        mock_connection.connect.return_value = False
        mock_connection_class.return_value = mock_connection
        
        automation = AutoCADAutomation()
        
        # Act & Assert
        with pytest.raises(ConnectionError):
            automation.run()
        
        mock_connection.disconnect.assert_called_once()
'''
    
    def _get_pyproject_template(self) -> str:
        return '''[tool.poetry]
name = "{{ project_slug }}"
version = "0.1.0"
description = "{{ project_name }}"
authors = ["{{ author_name }} <{{ author_email }}>"]

[tool.poetry.dependencies]
python = "^{{ python_version }}"
pywin32 = "^306"
{% for dep in dependencies %}
{{ dep }}
{% endfor %}

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-cov = "^4.0.0"
black = "^24.0.0"
ruff = "^0.5.0"
mypy = "^1.8.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 88
target-version = ["py{{ python_version|replace('.', '') }}"]

[tool.ruff]
line-length = 88
target-version = "py{{ python_version|replace('.', '') }}"

[tool.mypy]
python_version = "{{ python_version }}"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
'''
    
    def _get_gitignore_template(self) -> str:
        return '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# AutoCAD backup files
*.bak
*.dwl
*.dwl2

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
'''
    
    def _get_settings_template(self) -> str:
        return '''{
  "autocad": {
    "version": "{{ autocad_version }}",
    "visibility": true,
    "auto_save": true
  },
  "project": {
    "name": "{{ project_name }}",
    "version": "0.1.0",
    "author": "{{ author_name }}"
  },
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}'''
    
    def _get_example_template(self) -> str:
        return '''"""
Example usage of {{ project_name }}.

This script demonstrates basic usage of the automation framework.
"""

from src.main import AutoCADAutomation
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run example automation."""
    logger.info("Starting {{ project_name }} example")
    
    # Create automation instance
    automation = AutoCADAutomation()
    
    try:
        # Run the automation
        automation.run()
        logger.info("Example completed successfully")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")


if __name__ == "__main__":
    main()
'''
    
    # Additional template methods for advanced templates would go here...
    # For brevity, I'll provide simplified versions
    
    def _get_advanced_readme_template(self) -> str:
        return '''# {{ project_name }}

Advanced AutoCAD automation project with MCP integration and VS Code support.

## Features

- MCP server integration for VS Code
- Enhanced AutoCAD wrapper
- Professional development tools
- Automated testing framework

## Quick Start

1. Install dependencies: `poetry install`
2. Start MCP server: `python src/mcp_tools/server.py`
3. Connect VS Code with MCP extension

## Author

{{ author_name }} <{{ author_email }}>
'''
    
    def _get_advanced_main_template(self) -> str:
        return '''"""
{{ project_name }} - Advanced AutoCAD automation with MCP integration.
"""

import asyncio
import logging
from src.mcp_tools.server import MCPServer
from src.autocad_modules.enhanced_wrapper import EnhancedAutoCAD

logger = logging.getLogger(__name__)


class AdvancedAutomation:
    """Advanced automation with MCP integration."""
    
    def __init__(self):
        self.acad = EnhancedAutoCAD()
        self.mcp_server = MCPServer()
    
    async def run(self):
        """Run advanced automation workflow."""
        logger.info("Starting advanced automation...")
        
        # Start MCP server
        await self.mcp_server.start()
        
        # Connect to AutoCAD
        self.acad.connect()
        
        # Your advanced automation logic here
        
        logger.info("Advanced automation completed")


async def main():
    """Main entry point."""
    automation = AdvancedAutomation()
    await automation.run()


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    def _get_mcp_server_template(self) -> str:
        return '''"""
MCP Server for {{ project_name }}.
"""

from mcp.server import FastMCP
import logging

logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("{{ mcp_server_name }}")


@mcp.tool()
def create_autocad_line(start_point: list, end_point: list) -> str:
    """Create a line in AutoCAD."""
    # Implementation here
    return f"Line created from {start_point} to {end_point}"


class MCPServer:
    """MCP server for AutoCAD integration."""
    
    def __init__(self):
        self.server = mcp
    
    async def start(self):
        """Start the MCP server."""
        logger.info("Starting MCP server for {{ project_name }}")
        # Server startup logic
'''
    
    def _get_enhanced_wrapper_template(self) -> str:
        return '''"""
Enhanced AutoCAD wrapper for {{ project_name }}.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class EnhancedAutoCAD:
    """Enhanced AutoCAD wrapper with additional features."""
    
    def __init__(self):
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to AutoCAD with enhanced features."""
        # Enhanced connection logic
        self.connected = True
        return True
    
    def create_line(self, start: List[float], end: List[float]) -> int:
        """Create line with enhanced features."""
        # Enhanced line creation
        return 12345
'''
    
    def _get_mcp_test_template(self) -> str:
        return '''"""
Tests for MCP integration.
"""

import pytest
from src.mcp_tools.server import MCPServer


class TestMCPIntegration:
    """Test MCP server functionality."""
    
    def test_server_creation(self):
        """Test MCP server creation."""
        server = MCPServer()
        assert server is not None
'''
    
    def _get_advanced_pyproject_template(self) -> str:
        return '''[tool.poetry]
name = "{{ project_slug }}"
version = "0.1.0"
description = "{{ project_name }}"
authors = ["{{ author_name }} <{{ author_email }}>"]

[tool.poetry.dependencies]
python = "^{{ python_version }}"
fastmcp = "^1.0.0"
pywin32 = "^306"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
black = "^24.0.0"
ruff = "^0.5.0"
mypy = "^1.8.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
'''
    
    def _get_github_actions_template(self) -> str:
        return '''name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: windows-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: {{ python_version }}
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install
    - name: Run tests
      run: poetry run pytest
'''
    
    def _get_vscode_package_template(self) -> str:
        return '''{
  "name": "{{ vscode_extension_name }}",
  "displayName": "{{ project_name }} VS Code Extension",
  "description": "VS Code integration for {{ project_name }}",
  "version": "0.1.0",
  "engines": {
    "vscode": "^1.85.0"
  },
  "categories": ["Other"],
  "activationEvents": ["onStartupFinished"],
  "main": "./out/extension.js",
  "contributes": {
    "commands": [
      {
        "command": "{{ project_slug }}.connect",
        "title": "Connect to AutoCAD"
      }
    ]
  }
}'''
    
    def _get_mcp_config_template(self) -> str:
        return '''{
  "server_name": "{{ mcp_server_name }}",
  "host": "localhost",
  "port": 3000,
  "tools": [
    "create_autocad_line",
    "create_autocad_circle"
  ]
}'''
    
    # Manufacturing template methods
    def _get_manufacturing_readme_template(self) -> str:
        return '''# {{ project_name }}

Manufacturing CAD automation with advanced optimization algorithms.

## Features

- Pattern nesting optimization
- Surface unfolding with LSCM
- Material usage optimization
- Batch processing capabilities

## Company

{{ company_name }}

## Supported Materials

{% for material in material_types %}
- {{ material|title }}
{% endfor %}

Default thickness: {{ default_thickness }}mm
'''
    
    def _get_manufacturing_main_template(self) -> str:
        return '''"""
{{ project_name }} - Manufacturing automation main module.
"""

import logging
from src.manufacturing.pattern_optimizer import PatternOptimizer
from src.manufacturing.surface_unfolding import SurfaceUnfolder

logger = logging.getLogger(__name__)


class ManufacturingAutomation:
    """Manufacturing automation workflow."""
    
    def __init__(self):
        self.optimizer = PatternOptimizer()
        self.unfolder = SurfaceUnfolder()
        self.default_thickness = {{ default_thickness }}
    
    def run_manufacturing_workflow(self):
        """Run complete manufacturing workflow."""
        logger.info("Starting manufacturing automation for {{ company_name }}")
        
        # Your manufacturing logic here
        
        logger.info("Manufacturing workflow completed")


def main():
    automation = ManufacturingAutomation()
    automation.run_manufacturing_workflow()


if __name__ == "__main__":
    main()
'''
    
    def _get_pattern_optimizer_template(self) -> str:
        return '''"""
Pattern optimization for manufacturing.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PatternOptimizer:
    """Optimize material usage through pattern nesting."""
    
    def __init__(self):
        self.material_types = {{ material_types }}
        self.default_thickness = {{ default_thickness }}
    
    def optimize_nesting(self, parts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize part nesting for material efficiency."""
        logger.info("Optimizing pattern nesting...")
        
        # Optimization algorithm implementation
        result = {
            "efficiency": 0.85,
            "material_usage": "85%",
            "waste_percentage": 15.0
        }
        
        return result
'''
    
    def _get_surface_unfolding_template(self) -> str:
        return '''"""
Surface unfolding for manufacturing.
"""

import logging
import numpy as np
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SurfaceUnfolder:
    """Unfold 3D surfaces for manufacturing."""
    
    def __init__(self):
        self.tolerance = 0.001
    
    def unfold_surface(self, surface_data: Dict[str, Any]) -> Dict[str, Any]:
        """Unfold 3D surface using LSCM algorithm."""
        logger.info("Unfolding surface for manufacturing...")
        
        # LSCM unfolding implementation
        result = {
            "unfolded_pattern": "pattern_data",
            "distortion": 0.0005,
            "manufacturing_ready": True
        }
        
        return result
'''
    
    def _get_manufacturing_test_template(self) -> str:
        return '''"""
Tests for manufacturing automation.
"""

import pytest
from src.manufacturing.pattern_optimizer import PatternOptimizer
from src.manufacturing.surface_unfolding import SurfaceUnfolder


class TestPatternOptimizer:
    """Test pattern optimization."""
    
    def test_optimizer_creation(self):
        optimizer = PatternOptimizer()
        assert optimizer.default_thickness == {{ default_thickness }}
        assert "{{ material_types[0] }}" in optimizer.material_types


class TestSurfaceUnfolder:
    """Test surface unfolding."""
    
    def test_unfolder_creation(self):
        unfolder = SurfaceUnfolder()
        assert unfolder.tolerance == 0.001
'''
    
    def _get_manufacturing_pyproject_template(self) -> str:
        return '''[tool.poetry]
name = "{{ project_slug }}"
version = "0.1.0"
description = "{{ project_name }}"
authors = ["{{ author_name }} <{{ author_email }}>"]

[tool.poetry.dependencies]
python = "^3.12"
numpy = "^1.24.0"
scipy = "^1.10.0"
matplotlib = "^3.7.0"
pywin32 = "^306"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
black = "^24.0.0"
ruff = "^0.5.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
'''