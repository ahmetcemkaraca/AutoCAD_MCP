# AutoCAD MCP API Specification

## Overview
This document defines the complete API specification for the AutoCAD Model Context Protocol server, designed for integration with VS Code and Roo Code extension.

## Base Configuration
- **Protocol**: HTTP/1.1
- **Host**: localhost
- **Port**: 5000 (configurable via environment)
- **Content-Type**: application/json
- **Authentication**: None (localhost only)

## Core Endpoints

### Health and Status

#### GET /health
Returns server health status.

**Response**:
```json
{
    "status": "ok"
}
```

#### GET /acad-status
Returns AutoCAD connection status.

**Response (Connected)**:
```json
{
    "status": "connected",
    "version": "2025.0"
}
```

**Response (Not Connected)**:
```json
{
    "status": "not_connected"
}
```
**Status Code**: 503 when not connected

### Basic CAD Operations

#### POST /draw/line
Create a line in AutoCAD.

**Request**:
```json
{
    "start_point": [0, 0, 0],
    "end_point": [100, 100, 0],
    "layer": "0"  // optional
}
```

**Response**:
```json
{
    "entity_id": 123,
    "entity_type": "AcDbLine",
    "success": true
}
```

#### POST /draw/circle
Create a circle in AutoCAD.

**Request**:
```json
{
    "center_point": [0, 0, 0],
    "radius": 50.0,
    "layer": "0"  // optional
}
```

**Response**:
```json
{
    "entity_id": 124,
    "entity_type": "AcDbCircle",
    "success": true
}
```

#### POST /draw/extrude
Create an extruded solid from a profile.

**Request**:
```json
{
    "profile_id": 124,
    "height": 100.0,
    "taper_angle": 0.0  // optional, degrees
}
```

**Response**:
```json
{
    "entity_id": 125,
    "entity_type": "AcDb3dSolid",
    "volume": 785398.16,  // calculated volume
    "success": true
}
```

### Advanced 3D Operations

#### POST /3d/revolve
Create a revolved solid.

**Request**:
```json
{
    "profile_id": 124,
    "axis_start": [0, 0, 0],
    "axis_end": [0, 0, 100],
    "angle": 360.0  // degrees
}
```

**Response**:
```json
{
    "entity_id": 126,
    "entity_type": "AcDb3dSolid",
    "success": true
}
```

#### POST /3d/boolean/union
Perform boolean union operation.

**Request**:
```json
{
    "primary_id": 125,
    "secondary_ids": [126, 127]
}
```

**Response**:
```json
{
    "entity_id": 128,
    "entity_type": "AcDb3dSolid",
    "operation": "union",
    "success": true
}
```

#### POST /3d/boolean/subtract
Perform boolean subtraction operation.

**Request**:
```json
{
    "primary_id": 125,
    "secondary_ids": [126]
}
```

**Response**:
```json
{
    "entity_id": 129,
    "entity_type": "AcDb3dSolid",
    "operation": "subtract",
    "success": true
}
```

### Surface Unfolding Utility

#### POST /unfold_surface
Unfold a 3D surface to 2D pattern using LSCM algorithm.

**Request**:
```json
{
    "entity_id": 130,
    "tolerance": 0.01,
    "method": "triangulation",  // "triangulation" or "conformal"
    "include_markings": true,   // add fold/cut lines
    "output_layer": "UNFOLD_PATTERN"  // optional
}
```

**Response**:
```json
{
    "pattern_id": 131,
    "entity_type": "AcDbPolyline",
    "deviation": 0.0045,  // area deviation percentage
    "original_area": 1000.5,
    "unfolded_area": 1004.5,
    "fold_lines": [132, 133],  // entity IDs of fold lines
    "cut_lines": [134, 135],   // entity IDs of cut lines
    "success": true,
    "warnings": []
}
```

**Error Response**:
```json
{
    "success": false,
    "error": "Entity is not a surface or mesh",
    "error_code": "INVALID_ENTITY_TYPE"
}
```

### Layout and Dimensioning Utility

#### POST /create_layout
Create layout with 3D entity and auto-dimensioning.

**Request**:
```json
{
    "entity_id": 125,
    "layout_name": "PRODUCTION_DRAWING",
    "scale": 1.0,
    "view_type": "isometric",  // "isometric", "front", "top", "right"
    "dimension_style": "STANDARD",  // optional
    "title_block": true  // optional
}
```

**Response**:
```json
{
    "layout_name": "PRODUCTION_DRAWING",
    "viewport_id": 136,
    "dimensions_added": 12,
    "dimension_ids": [137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148],
    "title_block_id": 149,  // if requested
    "success": true
}
```

### Entity Management

#### GET /entities
List all entities in current drawing.

**Response**:
```json
{
    "entities": [
        {
            "id": 123,
            "type": "AcDbLine",
            "layer": "0",
            "color": 256,  // ByLayer
            "length": 141.42  // for lines
        },
        {
            "id": 124,
            "type": "AcDbCircle",
            "layer": "0", 
            "color": 256,
            "radius": 50.0,
            "area": 7853.98
        }
    ],
    "total_count": 2
}
```

#### GET /entities/{entity_id}
Get detailed information about specific entity.

**Response**:
```json
{
    "id": 125,
    "type": "AcDb3dSolid",
    "layer": "0",
    "color": 256,
    "volume": 785398.16,
    "surface_area": 3141.59,
    "bounding_box": {
        "min_point": [-50, -50, 0],
        "max_point": [50, 50, 100]
    },
    "center_of_mass": [0, 0, 50],
    "material": "Steel",  // if assigned
    "success": true
}
```

#### DELETE /entities/{entity_id}
Delete an entity from the drawing.

**Response**:
```json
{
    "success": true,
    "message": "Entity 125 deleted successfully"
}
```

## Plugin Framework Endpoints

#### GET /plugins
List available plugins.

**Response**:
```json
{
    "plugins": [
        {
            "name": "stair_generator",
            "description": "Generate parametric stairs",
            "version": "1.0.0",
            "parameters": [
                {
                    "name": "height",
                    "type": "float",
                    "required": true,
                    "description": "Total height of stairs"
                },
                {
                    "name": "steps",
                    "type": "int",
                    "required": true,
                    "description": "Number of steps"
                }
            ]
        }
    ]
}
```

#### POST /plugins/{plugin_name}/execute
Execute a plugin with parameters.

**Request**:
```json
{
    "parameters": {
        "height": 300.0,
        "steps": 12,
        "width": 120.0
    }
}
```

**Response**:
```json
{
    "plugin_name": "stair_generator",
    "entity_ids": [150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161],
    "execution_time": 2.34,  // seconds
    "success": true,
    "warnings": []
}
```

## Error Handling

### Standard Error Response Format
```json
{
    "success": false,
    "error": "Human readable error message",
    "error_code": "MACHINE_READABLE_CODE",
    "details": {
        "parameter": "Invalid value",
        "suggestion": "Try using a positive number"
    }
}
```

### Common Error Codes
- `AUTOCAD_NOT_CONNECTED`: AutoCAD is not running or accessible
- `INVALID_ENTITY_ID`: Entity ID does not exist
- `INVALID_ENTITY_TYPE`: Operation not supported for entity type
- `INVALID_PARAMETERS`: Request parameters are invalid
- `COMPUTATION_ERROR`: Error during mathematical computation
- `COM_ERROR`: Windows COM interface error
- `TIMEOUT_ERROR`: Operation timed out
- `INSUFFICIENT_MEMORY`: Not enough memory for operation

## Rate Limiting and Performance

### Limits
- **Concurrent Requests**: 5 maximum
- **Request Timeout**: 30 seconds default
- **Large Operations**: 300 seconds for complex unfolding
- **Entity Limit**: 10,000 entities per drawing recommended

### Performance Monitoring
Each response includes timing information:
```json
{
    "execution_time": 1.25,
    "memory_usage": 45.6,  // MB
    "autocad_operations": 15
}
```

## Logging and Debugging

### Log Levels
- `DEBUG`: Detailed operation traces
- `INFO`: General operation info  
- `WARNING`: Non-critical issues
- `ERROR`: Operation failures
- `CRITICAL`: Server failures

### Log Format
```
2025-07-22 10:30:45 INFO [server.py:45] Entity 125 created successfully (type: AcDb3dSolid)
2025-07-22 10:30:46 DEBUG [unfold.py:120] Triangulation completed: 1847 triangles, 924 vertices
2025-07-22 10:30:47 ERROR [server.py:78] AutoCAD COM error: 0x80020009 - Exception occurred
```

## Environment Variables

### Configuration
- `MCP_HOST`: Server host (default: localhost)
- `MCP_PORT`: Server port (default: 5000)
- `MCP_DEBUG`: Enable debug mode (default: false)
- `MCP_LOG_LEVEL`: Logging level (default: INFO)
- `MCP_LOG_FILE`: Log file path (default: logs/mcp.log)
- `AUTOCAD_TIMEOUT`: AutoCAD operation timeout (default: 30)
- `UNFOLD_MAX_FACES`: Maximum faces for unfolding (default: 10000)