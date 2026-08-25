# Roo Code Extension Compatibility Guide

## Overview
This document specifies the compatibility requirements and integration patterns for the AutoCAD MCP server with the Roo Code VS Code extension.

## Roo Code Extension Details
- **Extension ID**: roo-cline.roo-cline  
- **Primary Function**: AI-assisted code generation and completion
- **Language Support**: Python (primary), JavaScript, TypeScript, others
- **AI Models**: Supports multiple models including Claude, GPT-4, local models

## Compatibility Requirements

### Python Environment
- **Python Version**: 3.12+ (matches project requirement)
- **Virtual Environment**: Poetry-managed (isolation required)
- **Package Management**: Poetry for dependency management
- **Interpreter Path**: Must be configurable in VS Code settings

### VS Code Integration Points

#### 1. IntelliSense and Autocompletion
Roo Code enhances Python IntelliSense with:
- AutoCAD API method suggestions
- MCP client library completions
- Context-aware parameter recommendations
- Type hint integration

#### 2. Code Generation Patterns
Roo Code generates scripts following these patterns:

**Basic AutoCAD Operation**:
```python
from mcp_client import McpClient

def create_box(length: float, width: float, height: float):
    \"\"\"Create a 3D box using AutoCAD MCP server\"\"\"
    client = McpClient()
    
    # Create base rectangle
    response = client.draw_rectangle(
        corner1=[0, 0, 0],
        corner2=[length, width, 0]
    )
    
    # Extrude to create box
    box = client.draw_extrude(
        profile_id=response['entity_id'],
        height=height
    )
    
    return box['entity_id']
```

**Surface Unfolding Workflow**:
```python
from mcp_client import McpClient
import pyautocad

def unfold_selected_surface(tolerance: float = 0.01):
    \"\"\"Unfold currently selected surface in AutoCAD\"\"\"
    # Direct AutoCAD access for selection
    acad = pyautocad.Autocad()
    selection = acad.doc.SelectionSets.Add("temp")
    selection.SelectOnScreen()
    
    if selection.Count == 0:
        print("No entities selected")
        return None
        
    entity = selection.Item(0)
    entity_id = entity.ObjectID
    
    # Use MCP for unfolding operation
    client = McpClient()
    result = client.unfold_surface(
        entity_id=entity_id,
        tolerance=tolerance,
        method="triangulation"
    )
    
    # Clean up selection
    selection.Delete()
    
    print(f"Surface unfolded with {result['deviation']}% deviation")
    return result['pattern_id']
```

#### 3. Error Handling Integration
Roo Code generates robust error handling:

```python
from mcp_client import McpClient, McpConnectionError, McpOperationError

def safe_autocad_operation():
    try:
        client = McpClient()
        result = client.some_operation()
        return result
    except McpConnectionError:
        print("Error: MCP server not running. Start with: poetry run python src/server.py")
        return None
    except McpOperationError as e:
        print(f"AutoCAD operation failed: {e.message}")
        if e.error_code == "AUTOCAD_NOT_CONNECTED":
            print("Ensure AutoCAD 2025 is running and visible")
        return None
```

## Natural Language to Code Translation

### Supported Commands
Roo Code can translate these natural language requests:

#### Basic Operations
- "Create a circle at origin with radius 50" → `client.draw_circle([0,0,0], 50)`
- "Extrude the selected profile by 100 units" → `client.draw_extrude(profile_id, 100)`
- "Make a box 100x50x25" → Multi-step rectangle + extrude operation

#### Advanced Operations  
- "Unfold this curved surface for laser cutting" → Complete unfolding workflow
- "Create a production drawing with dimensions" → Layout creation with auto-dimensioning
- "Generate a parametric stair with 12 steps" → Plugin execution call

#### Complex Workflows
- "Create a bent sheet metal part and unfold it" → Multi-operation sequence
- "Model a helical spring and show orthographic views" → 3D modeling + layout creation

### Context Understanding
Roo Code maintains context between operations:

```python
# User: "Create a cylinder"
cylinder_id = client.draw_cylinder([0, 0, 0], radius=25, height=100)

# User: "Now hollow it out with a 20mm radius"
inner_cylinder = client.draw_cylinder([0, 0, 0], radius=20, height=100)
hollow_part = client.boolean_subtract(cylinder_id, [inner_cylinder])

# User: "Unfold the outer surface" 
unfolded = client.unfold_surface(hollow_part, tolerance=0.005)
```

## Configuration Files

### VS Code Settings
File: `.vscode/settings.json` (project-specific)
```json
{
    "rooCline.pythonPath": "C:/Users/barrya/AppData/Local/pypoetry/Cache/virtualenvs/autocad-mcp-lupfEvC3-py3.12/Scripts/python.exe",
    "rooCline.autoCompleteEnabled": true,
    "rooCline.contextWindow": 8000,
    "rooCline.modelProvider": "ai_provider",
    "rooCline.model": "claude-3-sonnet-20240229",
    "rooCline.customInstructions": "This is an AutoCAD automation project using MCP server. Always import McpClient from mcp_client. Prefer using MCP API calls over direct pyautocad calls for complex operations. Include error handling for server connection issues.",
    "python.defaultInterpreterPath": "C:/Users/barrya/AppData/Local/pypoetry/Cache/virtualenvs/autocad-mcp-lupfEvC3-py3.12/Scripts/python.exe"
}
```

### Roo Code Project Context
File: `.roo/context.md`
```markdown
# AutoCAD MCP Project Context

## Project Type
AutoCAD automation and 3D modeling scripts using Model Context Protocol server.

## Key Libraries
- `mcp_client`: Custom client for AutoCAD MCP server
- `pyautocad`: Direct AutoCAD COM interface (use sparingly)
- `numpy`, `scipy`: Mathematical operations for 3D algorithms

## Common Patterns
1. Always start with `McpClient()` connection
2. Use server API for complex operations (unfolding, boolean ops)
3. Use pyautocad only for entity selection and basic queries
4. Include comprehensive error handling
5. Validate AutoCAD connection before operations

## Server Endpoints
- `/draw/line`, `/draw/circle`, `/draw/extrude`: Basic geometry
- `/unfold_surface`: Surface unfolding (key feature)
- `/create_layout`: Layout with auto-dimensioning
- `/3d/boolean/*`: Boolean operations
- `/plugins/*/execute`: Custom plugin execution

## Error Codes
- `AUTOCAD_NOT_CONNECTED`: Start AutoCAD 2025
- `INVALID_ENTITY_ID`: Check entity exists
- `COMPUTATION_ERROR`: Review input parameters
```

## Best Practices for Roo Code Integration

### 1. Code Structure
- Use type hints for better IntelliSense
- Create reusable functions for common operations
- Separate AutoCAD operations from business logic
- Include docstrings for Roo Code context understanding

### 2. Error Messaging
- Provide actionable error messages
- Include troubleshooting steps
- Reference documentation links
- Suggest alternative approaches

### 3. Performance Considerations
- Batch multiple operations when possible
- Use appropriate tolerance values for unfolding
- Monitor memory usage for large operations
- Implement progress indicators for long operations

### 4. Testing Integration
```python
def test_with_mock_server():
    \"\"\"Test script without requiring running AutoCAD\"\"\"
    from unittest.mock import Mock
    
    # Mock the MCP client for testing
    client = Mock()
    client.draw_circle.return_value = {'entity_id': 123, 'success': True}
    
    result = create_circle_script(client)
    assert result is not None
```

## Debugging and Development

### Debugging Configuration
Roo Code supports step-through debugging with proper launch configuration:

```json
{
    "name": "Debug AutoCAD Script",
    "type": "python", 
    "request": "launch",
    "program": "${file}",
    "console": "integratedTerminal",
    "python": "C:/Users/barrya/AppData/Local/pypoetry/Cache/virtualenvs/autocad-mcp-lupfEvC3-py3.12/Scripts/python.exe",
    "env": {
        "MCP_HOST": "localhost",
        "MCP_PORT": "5000",
        "MCP_DEBUG": "true"
    }
}
```

### Live Reload Support
For iterative development, Roo Code can generate scripts with live reload:

```python
import importlib
import sys

def reload_and_run():
    if 'mcp_client' in sys.modules:
        importlib.reload(sys.modules['mcp_client'])
    
    from mcp_client import McpClient
    # Your code here
```

## Limitations and Workarounds

### Current Limitations
1. **AutoCAD Visibility**: Must be visible for COM operations
2. **Windows Only**: COM API restriction
3. **Single Instance**: One AutoCAD session supported
4. **Memory Usage**: Large unfolding operations are memory intensive

### Workarounds
1. **Headless Testing**: Use mock objects for CI/CD
2. **Cross-Platform Dev**: Develop logic separately from AutoCAD calls
3. **Multi-Session**: Use different ports for multiple servers
4. **Memory Management**: Implement operation chunking for large surfaces

## Future Enhancements

### Planned Improvements
1. **Smart Caching**: Cache expensive operations
2. **Batch Processing**: Multiple operations in single API call
3. **Real-time Feedback**: Progress updates for long operations
4. **Plugin Marketplace**: Shared plugin repository
5. **Visual Debugging**: 3D preview in VS Code