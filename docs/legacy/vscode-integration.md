# VS Code Integration Specification

## Overview
This document specifies how the AutoCAD MCP Server integrates with Visual Studio Code and the Roo Code extension to enable AI-assisted script and plugin creation for AutoCAD 2025.

## Architecture

### MCP Server Role
- **Primary Function**: Provides AutoCAD automation capabilities via HTTP API
- **Target Client**: VS Code with Roo Code extension (not Claude desktop)
- **Communication**: REST API over HTTP (localhost:5001)
- **Data Flow**: VS Code → MCP Server → AutoCAD 2025 COM API

### Integration Points

#### 1. VS Code Extensions
- **Roo Code**: Primary AI coding assistant extension
- **AI Assistant**: Secondary AI assistant (if available)
- **Cline**: Command-line interface integration
- **Python Extension**: For script development and debugging

#### 2. MCP Client Library
Location: `src/mcp_client.py`

```python
class McpClient:
    def __init__(self, host='localhost:5001'):
        self.session = requests.Session()
        self.base_url = f"http://{host}"
    
    def unfold_surface(self, entity_id: int, tolerance: float = 0.01) -> dict:
        """Unfold 3D surface to 2D pattern"""
        
    def create_layout(self, entity_id: int, layout_name: str, scale: float = 1.0) -> dict:
        """Create layout with auto-dimensioning"""
        
    def draw_extrude(self, profile_id: int, height: float) -> dict:
        """Create extruded solid"""
```

#### 3. Script Templates
Location: `templates/scripts/`

Templates for common AutoCAD operations:
- Basic 3D primitives (extrude, revolve, loft)
- Surface unfolding workflows
- Layout creation and dimensioning
- Plugin boilerplate code

## Roo Code Integration

### Requirements
- **VS Code Version**: 1.92+
- **Python Environment**: Use Poetry virtual environment
- **AutoCAD**: Must be running and visible
- **Network**: MCP server accessible on localhost:5001

### Workflow
1. User describes desired AutoCAD operation in natural language
2. Roo Code generates Python script using MCP client library
3. Script executes, calling MCP server endpoints
4. MCP server communicates with AutoCAD via pyautocad
5. Results returned to VS Code for review/iteration

### Script Structure
```python
# Standard template for Roo Code generated scripts
from mcp_client import McpClient
import pyautocad

def main():
    # Connect to MCP server
    client = McpClient()
    
    # Connect to AutoCAD (direct access for verification)
    acad = pyautocad.Autocad()
    
    # Execute operations via MCP
    result = client.operation_name(parameters)
    
    # Verify results
    print(f"Operation completed: {result}")

if __name__ == "__main__":
    main()
```

## Development Environment Setup

### VS Code Configuration
File: `.vscode/settings.json`
```json
{
    "python.defaultInterpreterPath": "C:/Users/barrya/AppData/Local/pypoetry/Cache/virtualenvs/autocad-mcp-lupfEvC3-py3.12/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["-v"],
    "python.linting.enabled": true,
    "python.formatting.provider": "black"
}
```

### Launch Configuration
File: `.vscode/launch.json`
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Start MCP Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/server.py",
            "console": "integratedTerminal",
            "python": "C:/Users/barrya/AppData/Local/pypoetry/Cache/virtualenvs/autocad-mcp-lupfEvC3-py3.12/Scripts/python.exe"
        },
        {
            "name": "Debug AutoCAD Script",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "python": "C:/Users/barrya/AppData/Local/pypoetry/Cache/virtualenvs/autocad-mcp-lupfEvC3-py3.12/Scripts/python.exe"
        }
    ]
}
```

### Tasks Configuration
File: `.vscode/tasks.json`
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Start MCP Server",
            "type": "shell",
            "command": "poetry run python src/server.py",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "new"
            }
        },
        {
            "label": "Run Tests",
            "type": "shell",
            "command": "poetry run pytest -v",
            "group": "test"
        },
        {
            "label": "Format Code",
            "type": "shell",
            "command": "poetry run black . && poetry run ruff check .",
            "group": "build"
        }
    ]
}
```

## Error Handling

### Connection Issues
- MCP server not running: Provide clear startup instructions
- AutoCAD not accessible: Check COM registration and visibility
- Port conflicts: Allow port configuration via environment variables

### Debugging Support
- Comprehensive logging to `logs/mcp.log`
- VS Code debugging configuration for step-through
- Mock AutoCAD support for development without AutoCAD

## Security Considerations

### Local Development
- Server bound to localhost only
- No external network access
- Input validation for all API endpoints
- COM object cleanup to prevent AutoCAD hangs

### Environment Isolation
- Poetry virtual environment isolation
- No global Python package pollution
- Clear dependency boundaries

## Performance Optimization

### Caching
- COM object reuse where safe
- Entity lookup optimization
- Response caching for expensive operations

### Resource Management
- Automatic cleanup of temporary objects
- Memory usage monitoring
- Connection pooling for multiple requests