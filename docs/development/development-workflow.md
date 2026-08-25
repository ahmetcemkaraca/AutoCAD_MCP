# Development Workflow Guide

## Overview
This document outlines the complete development workflow for the AutoCAD MCP project, from environment setup through testing and deployment.

## Environment Setup

### Prerequisites
1. **Windows 10/11** (required for AutoCAD COM API)
2. **AutoCAD 2025** (full version, must be installed and licensed)
3. **Python 3.12+** 
4. **Poetry** (dependency management)
5. **VS Code 1.92+** with extensions:
   - Roo Code (roo-cline.roo-cline)
   - Python (ms-python.python)
   - Optional: AI coding assistants

### Initial Setup
```bash
# Clone repository
git clone <repository-url>
cd autocad_mcp

# Install dependencies
poetry install

# Verify installation
poetry run python -c "import flask; import pyautocad; import numpy; import scipy; print('Dependencies OK')"
```

### VS Code Configuration
1. Copy `.vscode/` configuration files (settings.json, launch.json, tasks.json)
2. Set Python interpreter to Poetry virtual environment
3. Configure Roo Code extension with project context
4. Test debugging configuration

## Development Phases

### Phase 1: Core MCP Server (Current)
**Duration**: 1-2 weeks
**Status**: In Progress

#### Completed Tasks
- [x] Basic Flask server structure
- [x] Health and AutoCAD status endpoints
- [x] pyautocad integration
- [x] Basic testing framework
- [x] Project documentation

#### Remaining Tasks
- [ ] Basic 2D drawing operations (line, circle, polyline)
- [ ] Basic 3D operations (extrude, revolve)
- [ ] Entity management endpoints
- [ ] Error handling and logging
- [ ] Unit tests for core functionality

#### Success Criteria
- Server starts without errors
- AutoCAD connection established
- Basic drawing operations work
- >80% test coverage for implemented features

### Phase 2: Advanced 3D Features
**Duration**: 2-3 weeks
**Status**: Planned

#### Tasks
- [ ] Boolean operations (union, subtract, intersect)
- [ ] Surface and mesh operations
- [ ] Surface unfolding utility implementation
- [ ] Layout creation and auto-dimensioning
- [ ] Performance optimization for complex operations

#### Success Criteria
- Surface unfolding with <0.1% area deviation
- Layout auto-dimensioning works correctly
- Performance targets met (<5s for moderate surfaces)
- Comprehensive error handling

### Phase 3: Plugin Framework and VS Code Integration
**Duration**: 1-2 weeks  
**Status**: Planned

#### Tasks
- [ ] Plugin registration system
- [ ] MCP client library for VS Code
- [ ] Roo Code integration testing
- [ ] Script templates and examples
- [ ] VS Code debugging configuration

#### Success Criteria
- Plugin system functional with sample plugins
- Roo Code can generate working scripts
- VS Code debugging works end-to-end
- Documentation complete

### Phase 4: Optimization and Polish
**Duration**: 1 week
**Status**: Planned

#### Tasks
- [ ] Performance profiling and optimization
- [ ] Memory usage optimization
- [ ] Enhanced error messages
- [ ] Complete documentation
- [ ] Example gallery

## Daily Development Workflow

### 1. Start Development Session
```bash
# Ensure AutoCAD is running
# Start MCP server
poetry run python src/server.py

# In another terminal, run tests
poetry run pytest -v --watch
```

### 2. Code Development
- Use VS Code with Roo Code for AI-assisted development
- Follow TDD: write tests first, then implementation
- Run tests frequently during development
- Use debugger for complex issues

### 3. Code Quality Checks
```bash
# Format code
poetry run black .

# Check style
poetry run ruff check .

# Type checking (when mypy is added)
# poetry run mypy .
```

### 4. Testing Workflow
```bash
# Run all tests
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_server.py -v

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Integration testing with AutoCAD
poetry run pytest tests/integration/ -v -s
```

### 5. End of Session
- Commit changes with descriptive messages
- Update documentation if needed
- Update CLAUDE.md if architecture changes
- Push to feature branch

## Testing Strategy

### Unit Tests
**Location**: `tests/unit/`
**Coverage**: All business logic, API endpoints
**Mocking**: AutoCAD operations mocked

```python
# Example unit test
import pytest
from unittest.mock import Mock, patch
from src.server import app

@patch('src.server.get_autocad_instance')
def test_draw_circle(mock_autocad, client):
    mock_acad = Mock()
    mock_acad.model.AddCircle.return_value.ObjectID = 123
    mock_autocad.return_value = mock_acad
    
    response = client.post('/draw/circle', json={
        'center_point': [0, 0, 0],
        'radius': 50.0
    })
    
    assert response.status_code == 200
    assert response.json['entity_id'] == 123
```

### Integration Tests
**Location**: `tests/integration/`
**Coverage**: End-to-end workflows
**Requirements**: AutoCAD running

```python
# Example integration test
import pytest
from pyautocad import Autocad
from mcp_client import McpClient

@pytest.mark.integration
def test_unfold_workflow():
    # Requires AutoCAD running
    acad = Autocad()
    client = McpClient()
    
    # Create test surface
    circle = acad.model.AddCircle([0, 0, 0], 50)
    solid = acad.model.AddExtrudedSolid(circle, 100, 0)
    
    # Test unfolding
    result = client.unfold_surface(solid.ObjectID, tolerance=0.01)
    
    assert result['success'] == True
    assert result['deviation'] < 0.1
```

### Performance Tests
**Location**: `tests/performance/`
**Coverage**: Resource usage, timing benchmarks

```python
import time
import psutil
from mcp_client import McpClient

def test_unfold_performance():
    client = McpClient()
    
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss
    
    result = client.unfold_surface(entity_id=123, tolerance=0.01)
    
    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss
    
    assert (end_time - start_time) < 5.0  # 5 second limit
    assert (end_memory - start_memory) < 100 * 1024 * 1024  # 100MB limit
```

## Code Style and Standards

### Python Style
- **Formatter**: Black (line length 88)
- **Linter**: Ruff 
- **Type Hints**: Required for all functions
- **Docstrings**: Required for public functions
- **Naming**: snake_case for functions/variables, CamelCase for classes

### Example Function
```python
def unfold_surface(
    entity_id: int, 
    tolerance: float = 0.01,
    method: str = "triangulation"
) -> dict:
    """
    Unfold a 3D surface to 2D pattern.
    
    Args:
        entity_id: AutoCAD entity ID of surface to unfold
        tolerance: Maximum allowable deviation (default 0.01)
        method: Unfolding algorithm ("triangulation" or "conformal")
        
    Returns:
        Dictionary with pattern_id, deviation, and success status
        
    Raises:
        ValueError: If entity_id is invalid
        ComputationError: If unfolding fails
    """
    # Implementation here
    pass
```

### API Design Standards
- RESTful endpoints where appropriate
- Consistent JSON response format
- Comprehensive error codes
- Input validation on all endpoints
- Proper HTTP status codes

## Error Handling Strategy

### Error Categories
1. **Connection Errors**: AutoCAD not running, MCP server unreachable
2. **Validation Errors**: Invalid parameters, missing required fields
3. **Operation Errors**: AutoCAD COM errors, computation failures
4. **Resource Errors**: Memory, timeout, entity limits

### Error Response Format
```json
{
    "success": false,
    "error": "Human readable message",
    "error_code": "MACHINE_READABLE_CODE",
    "details": {
        "parameter": "problematic_value",
        "suggestion": "Try using a positive number"
    },
    "timestamp": "2025-07-22T10:30:45Z",
    "request_id": "req_12345"
}
```

### Logging Standards
```python
import logging

logger = logging.getLogger(__name__)

def some_operation():
    logger.info("Starting surface unfolding", extra={
        "entity_id": 123,
        "tolerance": 0.01
    })
    
    try:
        result = complex_operation()
        logger.info("Operation completed successfully", extra={
            "execution_time": 2.5,
            "result_entities": 3
        })
        return result
    except Exception as e:
        logger.error("Operation failed", extra={
            "error": str(e),
            "entity_id": 123
        }, exc_info=True)
        raise
```

## Documentation Standards

### Code Documentation
- Docstrings for all public functions and classes
- Inline comments for complex algorithms
- Type hints for all parameters and returns
- Examples in docstrings where helpful

### API Documentation
- Complete endpoint documentation with examples
- Error response documentation
- Performance characteristics noted
- Version compatibility information

### User Documentation
- Step-by-step setup guides
- Common use cases and examples
- Troubleshooting guides
- FAQ section

## Deployment and Distribution

### Local Development
- Poetry for dependency management
- VS Code for development environment
- pytest for testing
- Black/Ruff for code quality

### Production Considerations
- Logging configuration for production
- Environment variable configuration
- Error reporting and monitoring
- Performance monitoring hooks

### Future Distribution
- Python package (setuptools/poetry)
- VS Code extension marketplace
- Docker container for isolated deployment
- Documentation website