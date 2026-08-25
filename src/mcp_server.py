"""
AutoCAD MCP Server using FastMCP.

This module provides a Model Context Protocol server for AutoCAD operations,
integrating with the full AutoCAD functionality.
"""

import json
import logging
from typing import List, Optional

from mcp import McpError
from mcp.server import FastMCP

from src.utils import get_autocad_instance, validate_point3d

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("AutoCAD MCP Server")


@mcp.tool()
def draw_line(start_point: List[float], end_point: List[float]) -> str:
    """
    Draw a line in AutoCAD between two 3D points.

    Args:
        start_point: Starting point [x, y, z]
        end_point: Ending point [x, y, z]

    Returns:
        str: Success message with entity ID
    """
    try:
        acad = get_autocad_instance()
        start = validate_point3d(start_point)
        end = validate_point3d(end_point)

        line = acad.model.AddLine(start, end)
        return json.dumps(
            {
                "success": True,
                "message": "Line created successfully",
                "entity_id": line.ObjectID,
                "start_point": start_point,
                "end_point": end_point,
            }
        )
    except Exception as e:
        logger.error(f"Error drawing line: {e}")
        return json.dumps({"success": False, "error": str(e), "message": "Failed to draw line"})


@mcp.tool()
def draw_circle(center: List[float], radius: float) -> str:
    """
    Draw a circle in AutoCAD.

    Args:
        center: Center point [x, y, z]
        radius: Circle radius

    Returns:
        str: Success message with entity ID
    """
    try:
        acad = get_autocad_instance()
        center_point = validate_point3d(center)

        circle = acad.model.AddCircle(center_point, radius)
        return json.dumps(
            {
                "success": True,
                "message": "Circle created successfully",
                "entity_id": circle.ObjectID,
                "center": center,
                "radius": radius,
            }
        )
    except Exception as e:
        logger.error(f"Error drawing circle: {e}")
        return json.dumps({"success": False, "error": str(e), "message": "Failed to draw circle"})


@mcp.tool()
def extrude_profile(profile_points: List[List[float]], extrude_height: float) -> str:
    """
    Create a 3D solid by extruding a 2D profile.

    Args:
        profile_points: List of 2D points defining the profile
        extrude_height: Height to extrude

    Returns:
        str: Success message with entity ID
    """
    try:
        acad = get_autocad_instance()

        # Create polyline from profile points
        polyline = acad.model.AddPolyline(profile_points)

        # Create extruded solid
        solid = acad.model.AddExtrudedSolid(polyline, extrude_height)
        return json.dumps(
            {
                "success": True,
                "message": "Extruded solid created successfully",
                "entity_id": solid.ObjectID,
                "profile_points": profile_points,
                "extrude_height": extrude_height,
            }
        )
    except Exception as e:
        logger.error(f"Error creating extrusion: {e}")
        return json.dumps(
            {"success": False, "error": str(e), "message": "Failed to create extrusion"}
        )


@mcp.tool()
def revolve_profile(
    profile_points: List[List[float]], axis_start: List[float], axis_end: List[float], angle: float
) -> str:
    """
    Create a 3D solid by revolving a 2D profile around an axis.

    Args:
        profile_points: List of 2D points defining the profile
        axis_start: Start point of revolution axis
        axis_end: End point of revolution axis
        angle: Revolution angle in degrees

    Returns:
        str: Success message with entity ID
    """
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
        return json.dumps(
            {
                "success": True,
                "message": "Revolved solid created successfully",
                "entity_id": solid.ObjectID,
                "profile_points": profile_points,
                "axis_start": axis_start,
                "axis_end": axis_end,
                "angle": angle,
            }
        )
    except Exception as e:
        logger.error(f"Error creating revolution: {e}")
        return json.dumps(
            {"success": False, "error": str(e), "message": "Failed to create revolution"}
        )


@mcp.tool()
def list_entities() -> str:
    """
    List all entities in the current AutoCAD drawing.

    Returns:
        str: JSON string with entity information
    """
    try:
        acad = get_autocad_instance()

        entities = []
        for entity in acad.model.modelspace:
            entity_info = {"id": entity.ObjectID, "type": entity.ObjectName, "layer": entity.Layer}

            # Add additional properties if available
            if hasattr(entity, "Length"):
                entity_info["length"] = entity.Length
            if hasattr(entity, "Area"):
                entity_info["area"] = entity.Area
            if hasattr(entity, "Volume"):
                entity_info["volume"] = entity.Volume

            entities.append(entity_info)

        return json.dumps({"success": True, "count": len(entities), "entities": entities})
    except Exception as e:
        logger.error(f"Error listing entities: {e}")
        return json.dumps({"success": False, "error": str(e), "message": "Failed to list entities"})


@mcp.tool()
def get_entity_info(entity_id: int) -> str:
    """
    Get detailed information about a specific entity.

    Args:
        entity_id: Entity ID to query

    Returns:
        str: JSON string with entity details
    """
    try:
        acad = get_autocad_instance()

        # Get entity by iterating through modelspace
        entity = None
        for ent in acad.model.modelspace:
            if ent.ObjectID == entity_id:
                entity = ent
                break

        if not entity:
            return json.dumps(
                {
                    "success": False,
                    "error": "Entity not found",
                    "message": f"No entity found with ID {entity_id}",
                }
            )

        from src.utils import extract_entity_properties

        properties = extract_entity_properties(entity)

        return json.dumps({"success": True, "entity": properties})
    except Exception as e:
        logger.error(f"Error getting entity info: {e}")
        return json.dumps(
            {"success": False, "error": str(e), "message": "Failed to get entity info"}
        )


@mcp.tool()
def server_status() -> str:
    """
    Get MCP server and AutoCAD connection status.

    Returns:
        str: JSON string with status information
    """
    try:
        acad = get_autocad_instance()
        doc_name = acad.ActiveDocument.Name

        return json.dumps(
            {
                "success": True,
                "mcp_server": "running",
                "autocad_connected": True,
                "active_document": doc_name,
                "tools_available": 6,
                "message": "MCP server is operational and connected to AutoCAD",
            }
        )
    except Exception as e:
        return json.dumps(
            {"success": False, "error": str(e), "message": "Failed to get server status"}
        )


@mcp.resource("autocad://server-status")
def get_server_status() -> str:
    """Get current MCP server status."""
    try:
        return json.dumps(
            {
                "mcp_server": "running",
                "tools_available": 6,
                "resources_available": 1,
                "message": "AutoCAD MCP server is operational",
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.prompt("autocad-help")
def autocad_help_prompt() -> str:
    """Get help with AutoCAD MCP tools."""
    return """
    AutoCAD MCP Server Help
    ======================
    
    Available tools:
    1. draw_line - Draw a line between two 3D points
    2. draw_circle - Draw a circle with center and radius
    3. extrude_profile - Create 3D solid by extruding 2D profile
    4. revolve_profile - Create 3D solid by revolving profile around axis
    5. list_entities - List all entities in current drawing
    6. get_entity_info - Get detailed info about specific entity
    7. server_status - Check server and AutoCAD connection
    
    Usage examples:
    - draw_line: start_point=[0,0,0], end_point=[10,10,0]
    - draw_circle: center=[5,5,0], radius=2.5
    - extrude_profile: profile_points=[[0,0],[10,0],[10,10],[0,10]], extrude_height=5
    
    Requirements:
    - AutoCAD 2025 must be running
    - A drawing document must be open
    """


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run the MCP server
    print("Starting AutoCAD MCP Server...")
    mcp.run()
