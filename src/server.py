#!/usr/bin/env python3
"""
AutoCAD MCP Server - Claude Desktop Compatible Entry Point.

This is the main entry point for the AutoCAD MCP server when used with Claude Desktop.
It provides stdio transport compatibility and proper error handling for desktop integration.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Sequence

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

# Configure logging for Claude Desktop
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr)  # Claude Desktop reads from stderr
    ]
)
logger = logging.getLogger("autocad-mcp")

# Import our MCP tools and utilities
try:
    from src.utils import get_autocad_instance, validate_point3d, extract_entity_properties
except ImportError as e:
    logger.error(f"Failed to import AutoCAD modules: {e}")
    # Continue with basic functionality if advanced modules aren't available


# Initialize the MCP server
server = Server("autocad-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available AutoCAD MCP tools."""
    return [
        types.Tool(
            name="draw_line",
            description="Draw a line in AutoCAD between two 3D points",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_point": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Starting point [x, y, z]"
                    },
                    "end_point": {
                        "type": "array", 
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Ending point [x, y, z]"
                    }
                },
                "required": ["start_point", "end_point"]
            }
        ),
        types.Tool(
            name="draw_circle",
            description="Draw a circle in AutoCAD with center and radius",
            inputSchema={
                "type": "object",
                "properties": {
                    "center": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Center point [x, y, z]"
                    },
                    "radius": {
                        "type": "number",
                        "minimum": 0,
                        "description": "Circle radius"
                    }
                },
                "required": ["center", "radius"]
            }
        ),
        types.Tool(
            name="extrude_profile",
            description="Create a 3D solid by extruding a 2D profile",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_points": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 3
                        },
                        "description": "List of 2D/3D points defining the profile"
                    },
                    "extrude_height": {
                        "type": "number",
                        "description": "Height to extrude the profile"
                    }
                },
                "required": ["profile_points", "extrude_height"]
            }
        ),
        types.Tool(
            name="revolve_profile",
            description="Create a 3D solid by revolving a profile around an axis",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_points": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"}
                        },
                        "description": "List of points defining the profile"
                    },
                    "axis_start": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Start point of revolution axis"
                    },
                    "axis_end": {
                        "type": "array",
                        "items": {"type": "number"}, 
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "End point of revolution axis"
                    },
                    "angle": {
                        "type": "number",
                        "description": "Revolution angle in degrees"
                    }
                },
                "required": ["profile_points", "axis_start", "axis_end", "angle"]
            }
        ),
        types.Tool(
            name="list_entities",
            description="List all entities in the current AutoCAD drawing",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        types.Tool(
            name="get_entity_info", 
            description="Get detailed information about a specific entity",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "integer",
                        "description": "Entity ID to query"
                    }
                },
                "required": ["entity_id"]
            }
        ),
        types.Tool(
            name="server_status",
            description="Get MCP server and AutoCAD connection status",
            inputSchema={
                "type": "object", 
                "properties": {},
                "additionalProperties": False
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """Handle tool calls from Claude Desktop."""
    if arguments is None:
        arguments = {}
        
    try:
        if name == "draw_line":
            result = await _draw_line(arguments["start_point"], arguments["end_point"])
        elif name == "draw_circle":
            result = await _draw_circle(arguments["center"], arguments["radius"])
        elif name == "extrude_profile":
            result = await _extrude_profile(arguments["profile_points"], arguments["extrude_height"])
        elif name == "revolve_profile":
            result = await _revolve_profile(
                arguments["profile_points"], 
                arguments["axis_start"],
                arguments["axis_end"], 
                arguments["angle"]
            )
        elif name == "list_entities":
            result = await _list_entities()
        elif name == "get_entity_info":
            result = await _get_entity_info(arguments["entity_id"])
        elif name == "server_status":
            result = await _server_status()
        else:
            result = json.dumps({
                "success": False,
                "error": f"Unknown tool: {name}",
                "message": "Tool not found"
            })
            
        return [types.TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        error_result = json.dumps({
            "success": False,
            "error": str(e),
            "message": f"Failed to execute {name}"
        })
        return [types.TextContent(type="text", text=error_result)]


async def _draw_line(start_point: list[float], end_point: list[float]) -> str:
    """Draw a line in AutoCAD."""
    try:
        acad = get_autocad_instance()
        start = validate_point3d(start_point)
        end = validate_point3d(end_point)

        line = acad.model.AddLine(start, end)
        return json.dumps({
            "success": True,
            "message": "Line created successfully",
            "entity_id": line.ObjectID,
            "start_point": start_point,
            "end_point": end_point,
        })
    except Exception as e:
        logger.error(f"Error drawing line: {e}")
        return json.dumps({
            "success": False, 
            "error": str(e),
            "message": "Failed to draw line"
        })


async def _draw_circle(center: list[float], radius: float) -> str:
    """Draw a circle in AutoCAD."""
    try:
        acad = get_autocad_instance()
        center_point = validate_point3d(center)

        circle = acad.model.AddCircle(center_point, radius)
        return json.dumps({
            "success": True,
            "message": "Circle created successfully",
            "entity_id": circle.ObjectID,
            "center": center,
            "radius": radius,
        })
    except Exception as e:
        logger.error(f"Error drawing circle: {e}")
        return json.dumps({
            "success": False,
            "error": str(e), 
            "message": "Failed to draw circle"
        })


async def _extrude_profile(profile_points: list[list[float]], extrude_height: float) -> str:
    """Create a 3D solid by extruding a 2D profile."""
    try:
        acad = get_autocad_instance()

        # Create polyline from profile points
        polyline = acad.model.AddPolyline(profile_points)

        # Create extruded solid
        solid = acad.model.AddExtrudedSolid(polyline, extrude_height)
        return json.dumps({
            "success": True,
            "message": "Extruded solid created successfully",
            "entity_id": solid.ObjectID,
            "profile_points": profile_points,
            "extrude_height": extrude_height,
        })
    except Exception as e:
        logger.error(f"Error creating extrusion: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to create extrusion"
        })


async def _revolve_profile(
    profile_points: list[list[float]], 
    axis_start: list[float], 
    axis_end: list[float], 
    angle: float
) -> str:
    """Create a 3D solid by revolving a profile around an axis."""
    try:
        acad = get_autocad_instance()

        # Create polyline from profile points
        polyline = acad.model.AddPolyline(profile_points)

        # Create revolved solid
        axis_vector = [
            axis_end[0] - axis_start[0],
            axis_end[1] - axis_start[1], 
            axis_end[2] - axis_start[2],
        ]
        solid = acad.model.AddRevolvedSolid(polyline, axis_start, axis_vector, angle)
        return json.dumps({
            "success": True,
            "message": "Revolved solid created successfully",
            "entity_id": solid.ObjectID,
            "profile_points": profile_points,
            "axis_start": axis_start,
            "axis_end": axis_end,
            "angle": angle,
        })
    except Exception as e:
        logger.error(f"Error creating revolution: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to create revolution"
        })


async def _list_entities() -> str:
    """List all entities in the current AutoCAD drawing."""
    try:
        acad = get_autocad_instance()

        entities = []
        for entity in acad.model.modelspace:
            entity_info = {
                "id": entity.ObjectID, 
                "type": entity.ObjectName, 
                "layer": entity.Layer
            }

            # Add additional properties if available
            if hasattr(entity, "Length"):
                entity_info["length"] = entity.Length
            if hasattr(entity, "Area"):
                entity_info["area"] = entity.Area
            if hasattr(entity, "Volume"):
                entity_info["volume"] = entity.Volume

            entities.append(entity_info)

        return json.dumps({
            "success": True, 
            "count": len(entities), 
            "entities": entities
        })
    except Exception as e:
        logger.error(f"Error listing entities: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to list entities"
        })


async def _get_entity_info(entity_id: int) -> str:
    """Get detailed information about a specific entity."""
    try:
        acad = get_autocad_instance()

        # Get entity by iterating through modelspace
        entity = None
        for ent in acad.model.modelspace:
            if ent.ObjectID == entity_id:
                entity = ent
                break

        if not entity:
            return json.dumps({
                "success": False,
                "error": "Entity not found",
                "message": f"No entity found with ID {entity_id}",
            })

        properties = extract_entity_properties(entity)
        return json.dumps({
            "success": True, 
            "entity": properties
        })
    except Exception as e:
        logger.error(f"Error getting entity info: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to get entity info"
        })


async def _server_status() -> str:
    """Get MCP server and AutoCAD connection status."""
    try:
        acad = get_autocad_instance()
        doc_name = acad.ActiveDocument.Name

        return json.dumps({
            "success": True,
            "mcp_server": "running",
            "autocad_connected": True,
            "active_document": doc_name,
            "tools_available": 7,
            "transport": "stdio",
            "message": "MCP server is operational and connected to AutoCAD via Claude Desktop",
        })
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "mcp_server": "running", 
            "autocad_connected": False,
            "transport": "stdio",
            "message": "MCP server running but AutoCAD connection failed"
        })


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available resources."""
    return [
        types.Resource(
            uri="autocad://server-status",
            name="AutoCAD MCP Server Status",
            description="Current status of the MCP server and AutoCAD connection",
            mimeType="application/json",
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read resource content."""
    if uri == "autocad://server-status":
        return await _server_status()
    else:
        raise ValueError(f"Unknown resource: {uri}")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """List available prompts."""
    return [
        types.Prompt(
            name="autocad-help",
            description="Get help with AutoCAD MCP tools and usage examples",
            arguments=[
                types.PromptArgument(
                    name="topic",
                    description="Specific topic to get help with (optional)",
                    required=False
                )
            ]
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """Handle prompt requests."""
    if name == "autocad-help":
        topic = arguments.get("topic", "general") if arguments else "general"
        
        help_content = f"""
# AutoCAD MCP Server Help

## Available Tools:
1. **draw_line** - Draw a line between two 3D points
2. **draw_circle** - Draw a circle with center and radius  
3. **extrude_profile** - Create 3D solid by extruding 2D profile
4. **revolve_profile** - Create 3D solid by revolving profile around axis
5. **list_entities** - List all entities in current drawing
6. **get_entity_info** - Get detailed info about specific entity
7. **server_status** - Check server and AutoCAD connection

## Usage Examples:
- Draw line: `draw_line(start_point=[0,0,0], end_point=[10,10,0])`
- Draw circle: `draw_circle(center=[5,5,0], radius=2.5)`
- Extrude: `extrude_profile(profile_points=[[0,0],[10,0],[10,10],[0,10]], extrude_height=5)`

## Requirements:
- AutoCAD 2025 must be running
- A drawing document must be open
- Proper COM permissions for AutoCAD automation

## Topic: {topic}
{"This is general help. You can ask for specific topics." if topic == "general" else f"Help for {topic} topic."}
        """
        
        return types.GetPromptResult(
            description="AutoCAD MCP Server help information",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=help_content)
                )
            ]
        )
    else:
        raise ValueError(f"Unknown prompt: {name}")


async def main():
    """Main entry point for Claude Desktop integration."""
    # Configure initialization options for Claude Desktop
    options = InitializationOptions(
        server_name="autocad-mcp",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
    
    logger.info("Starting AutoCAD MCP Server for Claude Desktop...")
    logger.info("Server capabilities: tools, resources, prompts")
    logger.info("Transport: stdio")
    
    try:
        # Run the server with stdio transport for Claude Desktop
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                options,
            )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())