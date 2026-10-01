# Enhanced Development Workflow Guide

**Version**: 1.0  
**Date**: 2025-07-28  
**Target Audience**: Development Team

## Overview

This guide provides step-by-step instructions for implementing the AutoCAD MCP enhancements, ensuring consistent development practices and successful project completion.

## Prerequisites Setup

### Development Environment Requirements

#### Software Installation
1. **AutoCAD 2025** (full version)
   - Must be licensed and activated
   - Required for COM interface testing
   - Minimum: Professional version

2. **Python 3.12+**
   ```bash
   # Verify Python version
   python --version  # Should be 3.12 or higher
   
   # Install Poetry if not present
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **VS Code with Extensions**
   ```bash
   # Required extensions
   code --install-extension ms-python.python
   code --install-extension ms-python.debugpy
   code --install-extension rooveterinaryinc.roo-cline
   ```

4. **Git Configuration**
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your.email@domain.com"
   ```

#### Project Setup
```bash
# Clone and setup project
git clone https://github.com/BarryMcAdams/AutoCAD_MCP.git
cd AutoCAD_MCP

# Install dependencies
poetry install

# Install additional enhancement dependencies
poetry add win32com.client pytest-asyncio mypy black ruff sphinx

# Setup pre-commit hooks
poetry run pre-commit install
```

#### AutoCAD Configuration
1. **Enable COM Interface**
   - Launch AutoCAD 2025
   - Type `SECURELOAD` → Set to 0 (allows loading external applications)
   - Type `COMMANDLINE` → Ensure command line is visible

2. **Create Test Drawing**
   ```autocad
   NEW
   SAVE "C:\temp\test_drawing.dwg"
   ```

3. **Verify COM Access**
   ```python
   # Test script: test_com_access.py
   import win32com.client
   
   try:
       app = win32com.client.GetActiveObject("AutoCAD.Application")
       print(f"Connected to AutoCAD {app.Version}")
       print(f"Active document: {app.ActiveDocument.Name}")
   except Exception as e:
       print(f"COM connection failed: {e}")
   ```

## Phase 1: Enhanced COM Wrapper Development

### Step 1.1: Create Enhanced AutoCAD Module

#### File Structure Setup
```bash
# Create new module structure
mkdir -p src/enhanced_autocad
touch src/enhanced_autocad/__init__.py
touch src/enhanced_autocad/wrapper.py
touch src/enhanced_autocad/connection.py
touch src/enhanced_autocad/errors.py
```

#### Implementation Steps

**1. Base Wrapper Class** (`src/enhanced_autocad/wrapper.py`)
```python
"""
Enhanced AutoCAD COM wrapper implementation
"""
import win32com.client
import logging
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class EnhancedAutoCAD:
    """Enhanced AutoCAD COM wrapper with improved reliability"""
    
    def __init__(self, visible: bool = True, timeout: int = 30):
        self._app = None
        self._doc = None
        self._model = None
        self._visible = visible
        self._timeout = timeout
        self._connected = False
        
    def connect(self) -> bool:
        """Establish connection to AutoCAD"""
        try:
            # Implementation details from technical architecture
            self._app = win32com.client.GetActiveObject("AutoCAD.Application")
            self._doc = self._app.ActiveDocument
            self._model = self._doc.ModelSpace
            self._connected = True
            logger.info(f"Connected to AutoCAD {self._app.Version}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to AutoCAD: {e}")
            return False
    
    # Additional methods as specified in technical architecture...
```

**2. Connection Manager** (`src/enhanced_autocad/connection.py`)
```python
"""
AutoCAD connection management with resilience
"""
import asyncio
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class ConnectionStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

@dataclass
class ConnectionHealth:
    status: ConnectionStatus
    last_check: float
    error_message: Optional[str] = None
    retry_count: int = 0

class ConnectionManager:
    """Manage AutoCAD connections with health monitoring"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 5.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._health = ConnectionHealth(ConnectionStatus.DISCONNECTED, time.time())
    
    async def ensure_connection(self) -> bool:
        """Ensure AutoCAD connection is healthy"""
        # Implementation details...
```

**3. Error Handling** (`src/enhanced_autocad/errors.py`)
```python
"""
Comprehensive error handling for AutoCAD operations
"""
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class AutoCADError(Exception):
    """Base exception for AutoCAD operations"""
    
    def __init__(self, message: str, error_code: Optional[int] = None, 
                 suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.suggestions = suggestions or []

class AutoCADErrorHandler:
    """Handle and translate AutoCAD COM errors"""
    
    ERROR_TRANSLATIONS = {
        0x80040E37: "Entity not found in drawing database",
        0x80040E14: "Invalid entity type for operation", 
        0x80040E10: "AutoCAD is not responding",
        # Add more translations as needed
    }
    
    def translate_com_error(self, com_error: Exception) -> AutoCADError:
        """Convert COM error to actionable AutoCAD error"""
        # Implementation details...
```

#### Testing Implementation
```python
# tests/test_enhanced_wrapper.py
import pytest
from src.enhanced_autocad import EnhancedAutoCAD

@pytest.fixture
def autocad():
    """Fixture providing AutoCAD connection"""
    acad = EnhancedAutoCAD()
    if acad.connect():
        yield acad
    else:
        pytest.skip("AutoCAD not available")

def test_connection(autocad):
    """Test basic AutoCAD connection"""
    assert autocad.connected
    assert autocad.app is not None
    assert autocad.doc is not None

def test_line_creation(autocad):
    """Test line creation functionality"""
    start_point = [0, 0, 0]
    end_point = [100, 100, 0]
    
    line = autocad.create_line(start_point, end_point)
    assert line is not None
    
    # Verify line properties
    assert autocad.get_entity_property(line, "StartPoint") == start_point
    assert autocad.get_entity_property(line, "EndPoint") == end_point
```

#### Implementation Validation
```bash
# Run tests
poetry run pytest tests/test_enhanced_wrapper.py -v

# Check code quality
poetry run black src/enhanced_autocad/
poetry run ruff check src/enhanced_autocad/
poetry run mypy src/enhanced_autocad/

# Performance benchmark
poetry run python scripts/benchmark_wrapper.py
```

### Step 1.2: Replace pyautocad Dependencies

#### Migration Script
```python
# scripts/migrate_from_pyautocad.py
"""
Script to migrate from pyautocad to EnhancedAutoCAD
"""
import os
import re
from pathlib import Path

def migrate_file(file_path: Path) -> bool:
    """Migrate a single Python file"""
    content = file_path.read_text()
    
    # Replace imports
    content = re.sub(
        r'from pyautocad import Autocad',
        'from enhanced_autocad import EnhancedAutoCAD',
        content
    )
    
    # Replace instantiation
    content = re.sub(
        r'acad = Autocad\(\)',
        'acad = EnhancedAutoCAD()\nacad.connect()',
        content
    )
    
    # Write back if changes made
    if content != file_path.read_text():
        file_path.write_text(content)
        return True
    return False

def migrate_project():
    """Migrate entire project from pyautocad"""
    src_dir = Path("src")
    migrated_files = []
    
    for py_file in src_dir.rglob("*.py"):
        if migrate_file(py_file):
            migrated_files.append(py_file)
    
    print(f"Migrated {len(migrated_files)} files:")
    for file in migrated_files:
        print(f"  - {file}")

if __name__ == "__main__":
    migrate_project()
```

#### Validation Process
```bash
# Run migration script
poetry run python scripts/migrate_from_pyautocad.py

# Test existing functionality
poetry run pytest tests/ -v

# Check for any remaining pyautocad references
grep -r "pyautocad" src/ || echo "Migration complete"
```

## Phase 2: VS Code Integration Tools

### Step 2.1: Real-time Script Execution Tool

#### Implementation Structure
```python
# src/development_tools/executor.py
"""
Real-time Python script execution with AutoCAD context
"""
import asyncio
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, Optional

class ScriptExecutor:
    """Execute Python scripts with AutoCAD context"""
    
    def __init__(self, autocad_wrapper: EnhancedAutoCAD):
        self.autocad = autocad_wrapper
        self.global_context = {
            'acad': autocad_wrapper,
            'app': autocad_wrapper.app,
            'doc': autocad_wrapper.doc,
            'model': autocad_wrapper.model
        }
    
    async def execute_script(self, script_code: str, capture_output: bool = True) -> Dict[str, Any]:
        """Execute Python script with full context capture"""
        # Implementation details...
```

#### MCP Tool Implementation
```python
# Add to src/mcp_server.py
@mcp.tool()
def execute_python_in_autocad(
    script_code: str,
    execution_mode: str = "interactive",
    capture_output: bool = True
) -> str:
    """
    Execute Python code directly in AutoCAD context with real-time feedback
    """
    try:
        from development_tools.executor import ScriptExecutor
        
        # Get AutoCAD connection
        acad = get_autocad_instance()
        executor = ScriptExecutor(acad)
        
        # Execute script
        result = asyncio.run(executor.execute_script(
            script_code, 
            capture_output=capture_output
        ))
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        raise McpError("EXECUTION_ERROR", f"Failed to execute script: {str(e)}")
```

#### Testing Script Execution
```python
# tests/test_script_executor.py
import pytest
from development_tools.executor import ScriptExecutor

def test_simple_script_execution(autocad):
    """Test executing simple Python script"""
    executor = ScriptExecutor(autocad)
    
    script = """
line = acad.create_line([0, 0, 0], [100, 100, 0])
result = f"Created line with ID: {line.ObjectID}"
"""
    
    result = asyncio.run(executor.execute_script(script))
    
    assert result['success'] is True
    assert 'Created line with ID:' in result['output']
    assert result['error'] is None
```

### Step 2.2: Object Inspector Tool

#### Implementation
```python
# src/development_tools/inspector.py
"""
AutoCAD object inspection and introspection
"""
import win32com.client
from typing import Dict, List, Any, Optional

class ObjectInspector:
    """Inspect AutoCAD objects and their properties"""
    
    def __init__(self, autocad_wrapper: EnhancedAutoCAD):
        self.autocad = autocad_wrapper
    
    def inspect_entity(self, entity_id: int, depth: str = "basic") -> Dict[str, Any]:
        """Inspect AutoCAD entity properties and methods"""
        try:
            entity = self.autocad.get_entity_by_id(entity_id)
            
            inspection_result = {
                'entity_id': entity_id,
                'entity_type': entity.ObjectName,
                'properties': self._get_properties(entity, depth),
                'methods': self._get_methods(entity) if depth != "basic" else [],
                'relationships': self._get_relationships(entity) if depth == "complete" else []
            }
            
            return inspection_result
            
        except Exception as e:
            return {
                'error': f"Failed to inspect entity {entity_id}: {str(e)}",
                'suggestions': [
                    "Verify entity exists in current drawing",
                    "Check entity ID is valid integer",
                    "Ensure AutoCAD connection is active"
                ]
            }
    
    def _get_properties(self, entity: Any, depth: str) -> Dict[str, Any]:
        """Extract entity properties based on inspection depth"""
        # Implementation details...
    
    def _get_methods(self, entity: Any) -> List[Dict[str, str]]:
        """Get available methods for entity"""
        # Implementation details...
    
    def _get_relationships(self, entity: Any) -> List[Dict[str, Any]]:
        """Get entity relationships and dependencies"""
        # Implementation details...
```

### Step 2.3: Interactive REPL Environment

#### Implementation
```python
# src/development_tools/repl.py
"""
Interactive Python REPL with AutoCAD context
"""
import code
import sys
from typing import Dict, Any, Optional
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

class AutoCADREPL:
    """Interactive Python REPL with AutoCAD integration"""
    
    def __init__(self, autocad_wrapper: EnhancedAutoCAD):
        self.autocad = autocad_wrapper
        self.sessions = {}
    
    def start_session(self, session_id: str, initial_imports: List[str] = None) -> Dict[str, Any]:
        """Start new REPL session"""
        # Implementation details...
    
    def execute_command(self, session_id: str, command: str) -> Dict[str, Any]:
        """Execute command in REPL session"""
        # Implementation details...
    
    def get_completions(self, session_id: str, text: str) -> List[str]:
        """Get auto-completion suggestions"""
        # Implementation details...
```

## Phase 3: Code Generation Tools

### Step 3.1: AutoLISP Generator

#### Template System
```python
# src/code_generation/templates/autolisp/basic_commands.lisp
;; Basic AutoLISP command template
(defun C:{{COMMAND_NAME}} (/ {{LOCAL_VARS}})
  (princ "\nStarting {{COMMAND_NAME}}...")
  
  {{COMMAND_LOGIC}}
  
  (princ "\n{{COMMAND_NAME}} completed.")
  (princ)
)
```

#### Generator Implementation
```python
# src/code_generation/autolisp_generator.py
"""
AI-assisted AutoLISP code generation
"""
from typing import Dict, List, Optional
from pathlib import Path
import re

class AutoLISPGenerator:
    """Generate AutoLISP code from task descriptions"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent / "templates" / "autolisp"
        self.load_templates()
    
    def generate_script(self, task_description: str, complexity: str = "simple") -> Dict[str, str]:
        """Generate AutoLISP script from task description"""
        # Implementation using AI assistance and templates
        
    def load_templates(self):
        """Load AutoLISP templates from files"""
        # Implementation details...
    
    def validate_syntax(self, lisp_code: str) -> Dict[str, Any]:
        """Validate AutoLISP syntax"""
        # Implementation details...
```

#### Template Examples
```lisp
;; templates/autolisp/entity_creation.lisp
;; Entity creation template
(defun C:CREATE{{ENTITY_TYPE}} (/ pt1 pt2 ent)
  (setq pt1 (getpoint "\nSpecify first point: "))
  (setq pt2 (getpoint pt1 "\nSpecify second point: "))
  
  (setq ent (entmake
    (list
      (cons 0 "{{ENTITY_TYPE}}")
      (cons 10 pt1)
      (cons 11 pt2)
      {{ADDITIONAL_PROPERTIES}}
    )
  ))
  
  (if ent
    (princ (strcat "\n{{ENTITY_TYPE}} created successfully."))
    (princ "\nFailed to create {{ENTITY_TYPE}}.")
  )
  (princ)
)
```

### Step 3.2: Testing Framework Implementation

#### Test Base Classes
```python
# src/testing_framework/autocad_test_base.py
"""
Base classes for AutoCAD testing
"""
import pytest
import unittest
from typing import Any, Dict, List, Optional
from enhanced_autocad import EnhancedAutoCAD

class AutoCADTestBase(unittest.TestCase):
    """Base test class for AutoCAD operations"""
    
    @classmethod
    def setUpClass(cls):
        """Setup AutoCAD connection for test class"""
        cls.acad = EnhancedAutoCAD()
        if not cls.acad.connect():
            pytest.skip("AutoCAD not available for testing")
    
    def setUp(self):
        """Setup for individual test"""
        # Create clean test environment
        self.test_entities = []
    
    def tearDown(self):
        """Cleanup after individual test"""
        # Remove test entities
        for entity_id in self.test_entities:
            try:
                self.acad.delete_entity(entity_id)
            except:
                pass
    
    def create_test_line(self) -> int:
        """Helper to create test line"""
        line_id = self.acad.create_line([0, 0, 0], [100, 100, 0])
        self.test_entities.append(line_id)
        return line_id
```

#### Mock AutoCAD for Testing
```python
# src/testing_framework/mock_autocad.py
"""
Mock AutoCAD implementation for offline testing
"""
from typing import Dict, List, Any, Optional
import uuid

class MockEntity:
    """Mock AutoCAD entity"""
    
    def __init__(self, entity_type: str, properties: Dict[str, Any]):
        self.ObjectID = str(uuid.uuid4())
        self.ObjectName = entity_type
        self.properties = properties
    
    def __getattr__(self, name: str) -> Any:
        return self.properties.get(name)

class MockAutoCAD:
    """Mock AutoCAD for offline testing"""
    
    def __init__(self):
        self.entities = {}
        self.entity_counter = 1000
        self.connected = True
    
    def create_line(self, start_point: List[float], end_point: List[float]) -> int:
        """Mock line creation"""
        entity_id = self.entity_counter
        self.entity_counter += 1
        
        self.entities[entity_id] = MockEntity("LINE", {
            "StartPoint": start_point,
            "EndPoint": end_point,
            "Layer": "0"
        })
        
        return entity_id
    
    def get_entity_by_id(self, entity_id: int) -> MockEntity:
        """Get mock entity by ID"""
        if entity_id not in self.entities:
            raise ValueError(f"Entity {entity_id} not found")
        return self.entities[entity_id]
```

## Development Best Practices

### Code Quality Standards

#### Type Hints and Documentation
```python
# Example of proper type hints and documentation
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

@dataclass
class EntityInfo:
    """Information about an AutoCAD entity"""
    entity_id: int
    entity_type: str
    properties: Dict[str, Any]
    created_at: float

def create_entity_with_validation(
    entity_type: str,
    properties: Dict[str, Any],
    validate: bool = True
) -> Optional[EntityInfo]:
    """
    Create AutoCAD entity with validation.
    
    Args:
        entity_type: Type of entity to create (LINE, CIRCLE, etc.)
        properties: Entity properties dictionary
        validate: Whether to validate properties before creation
    
    Returns:
        EntityInfo object if successful, None if failed
    
    Raises:
        ValueError: If entity_type is invalid
        AutoCADError: If entity creation fails
    
    Example:
        >>> info = create_entity_with_validation(
        ...     "LINE", 
        ...     {"StartPoint": [0, 0, 0], "EndPoint": [100, 100, 0]}
        ... )
        >>> print(f"Created entity: {info.entity_id}")
    """
    # Implementation...
```

#### Error Handling Patterns
```python
# Consistent error handling pattern
def safe_autocad_operation(operation_func, *args, **kwargs):
    """Wrapper for safe AutoCAD operations"""
    try:
        return operation_func(*args, **kwargs)
    except win32com.client.pywintypes.com_error as e:
        error_handler = AutoCADErrorHandler()
        autocad_error = error_handler.translate_com_error(e)
        logger.error(f"AutoCAD operation failed: {autocad_error}")
        raise autocad_error
    except Exception as e:
        logger.error(f"Unexpected error in AutoCAD operation: {e}")
        raise AutoCADError(f"Unexpected error: {str(e)}")
```

### Testing Strategies

#### Unit Testing
```python
# Example unit test structure
class TestEnhancedAutoCAD(AutoCADTestBase):
    """Unit tests for EnhancedAutoCAD wrapper"""
    
    def test_connection_establishment(self):
        """Test AutoCAD connection establishment"""
        self.assertTrue(self.acad.connected)
        self.assertIsNotNone(self.acad.app)
    
    def test_line_creation_and_properties(self):
        """Test line creation and property retrieval"""
        start_point = [0, 0, 0]
        end_point = [100, 100, 0]
        
        line_id = self.create_test_line()
        
        # Verify properties
        start_prop = self.acad.get_entity_property(line_id, "StartPoint")
        end_prop = self.acad.get_entity_property(line_id, "EndPoint")
        
        self.assertEqual(start_prop, start_point)
        self.assertEqual(end_prop, end_point)
    
    def test_error_handling(self):
        """Test error handling for invalid operations"""
        with self.assertRaises(AutoCADError):
            self.acad.get_entity_by_id(999999)  # Non-existent entity
```

#### Integration Testing
```python
# Example integration test
class TestMCPToolIntegration(AutoCADTestBase):
    """Integration tests for MCP tools"""
    
    def test_script_execution_tool(self):
        """Test script execution MCP tool"""
        script_code = '''
line_id = acad.create_line([0, 0, 0], [50, 50, 0])
result = f"Line created: {line_id}"
'''
        
        # Execute via MCP tool
        result = execute_python_in_autocad(script_code, "interactive", True)
        result_data = json.loads(result)
        
        self.assertTrue(result_data['success'])
        self.assertIn('Line created:', result_data['output'])
```

### Performance Optimization

#### Profiling Code
```python
# Performance profiling decorator
import time
import functools
from typing import Callable, Any

def profile_operation(func: Callable) -> Callable:
    """Decorator to profile AutoCAD operations"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
            raise
        finally:
            duration = time.time() - start_time
            logger.info(f"Operation {func.__name__} took {duration:.3f}s (success: {success})")
            
            # Record metrics
            metrics_collector.record_operation(
                operation=func.__name__,
                duration=duration,
                success=success,
                error=error
            )
        
        return result
    return wrapper

# Usage
@profile_operation
def create_multiple_lines(count: int) -> List[int]:
    """Create multiple lines for performance testing"""
    line_ids = []
    for i in range(count):
        line_id = acad.create_line([i*10, 0, 0], [i*10+10, 10, 0])
        line_ids.append(line_id)
    return line_ids
```

### Debugging Workflow

#### VS Code Debug Configuration
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug AutoCAD MCP Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/server.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src",
                "AUTOCAD_MCP_DEBUG": "true"
            },
            "args": ["--debug"]
        },
        {
            "name": "Debug MCP Tool",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/debug_tool.py",
            "console": "integratedTerminal",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src"
            }
        }
    ]
}
```

#### Debug Helper Script
```python
# debug_tool.py
"""Debug helper for testing individual MCP tools"""
import asyncio
import json
from src.mcp_server import execute_python_in_autocad

async def debug_script_execution():
    """Debug script execution tool"""
    test_script = '''
# Test script for debugging
import time
print("Starting test script...")

# Create a simple line
line = acad.create_line([0, 0, 0], [100, 100, 0])
print(f"Created line: {line}")

# Get line properties
start_point = acad.get_entity_property(line, "StartPoint")
print(f"Start point: {start_point}")

time.sleep(1)
print("Test script completed successfully")
'''
    
    try:
        result = execute_python_in_autocad(test_script, "debug", True)
        print("Tool result:")
        print(json.dumps(json.loads(result), indent=2))
    except Exception as e:
        print(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_script_execution())
```

## Quality Assurance Process

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.5.5
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Continuous Integration
```yaml
# .github/workflows/test.yml
name: Test AutoCAD MCP Enhancements

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install Poetry
      uses: snok/install-poetry@v1
    
    - name: Install dependencies
      run: poetry install
    
    - name: Run linting
      run: |
        poetry run black --check .
        poetry run ruff check .
        poetry run mypy src/
    
    - name: Run tests
      run: poetry run pytest tests/ -v --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Documentation Standards

### API Documentation
```python
# Example of comprehensive API documentation
class EnhancedAutoCAD:
    """
    Enhanced AutoCAD COM wrapper with improved reliability and features.
    
    This class provides a robust interface to AutoCAD 2025 via COM,
    with automatic error handling, connection recovery, and performance monitoring.
    
    Examples:
        Basic usage:
        >>> acad = EnhancedAutoCAD()
        >>> acad.connect()
        True
        >>> line_id = acad.create_line([0, 0, 0], [100, 100, 0])
        >>> print(f"Created line: {line_id}")
        
        With error handling:
        >>> try:
        ...     entity = acad.get_entity_by_id(invalid_id)
        ... except AutoCADError as e:
        ...     print(f"Error: {e}")
        ...     print(f"Suggestions: {e.suggestions}")
    
    Attributes:
        app: AutoCAD Application object
        doc: Active Document object
        model: Model Space object
        connected: Connection status boolean
    """
    
    def create_line(self, start_point: List[float], end_point: List[float]) -> int:
        """
        Create a line entity in AutoCAD.
        
        Args:
            start_point: [x, y, z] coordinates for line start
            end_point: [x, y, z] coordinates for line end
        
        Returns:
            Entity ID of created line
        
        Raises:
            AutoCADError: If line creation fails
            ValueError: If point coordinates are invalid
        
        Example:
            >>> line_id = acad.create_line([0, 0, 0], [100, 100, 0])
            >>> print(f"Line created with ID: {line_id}")
        """
        # Implementation...
```

This comprehensive development workflow guide provides detailed, step-by-step instructions for implementing all enhancements while maintaining code quality and ensuring project success.