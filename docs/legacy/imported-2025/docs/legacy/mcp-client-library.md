# MCP Client Library Interface Specification

## Overview
The MCP Client Library provides a Python interface for VS Code scripts and Roo Code generated code to interact with the AutoCAD MCP Server. This library abstracts HTTP communication and provides type-safe, well-documented methods for all server endpoints.

## Installation and Setup

### Import Structure
```python
from mcp_client import (
    McpClient,           # Main client class
    McpConnectionError,  # Connection exceptions
    McpOperationError,   # Operation exceptions
    Point3D,            # Type alias for 3D points
    EntityInfo,         # Entity information container
    UnfoldResult,       # Surface unfolding result
    LayoutResult,       # Layout creation result
)
```

### Client Initialization
```python
class McpClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5000,
        timeout: float = 30.0,
        retry_attempts: int = 3,
        debug: bool = False
    ):
        """
        Initialize MCP client connection.
        
        Args:
            host: Server hostname (default: localhost)
            port: Server port (default: 5000) 
            timeout: Request timeout in seconds (default: 30.0)
            retry_attempts: Number of retry attempts for failed requests (default: 3)
            debug: Enable debug logging (default: False)
        """
```

## Core Client Interface

### Connection Management
```python
def is_connected(self) -> bool:
    """Check if server is reachable and healthy."""
    
def get_server_status(self) -> dict:
    """Get server health and version information."""
    
def get_autocad_status(self) -> dict:
    """Get AutoCAD connection status and version."""
    
async def wait_for_server(self, max_wait: float = 60.0) -> bool:
    """Wait for server to become available (async)."""
    
def close(self) -> None:
    """Close client session and cleanup resources."""
```

### Context Manager Support
```python
# Usage as context manager
with McpClient() as client:
    result = client.draw_circle([0, 0, 0], 50.0)
    print(f"Created circle with ID: {result.entity_id}")
```

## Basic CAD Operations

### Drawing Operations
```python
def draw_line(
    self,
    start_point: Point3D,
    end_point: Point3D,
    layer: str = "0"
) -> EntityInfo:
    """
    Create a line in AutoCAD.
    
    Args:
        start_point: Starting point [x, y, z]
        end_point: Ending point [x, y, z]
        layer: Target layer name (default: "0")
        
    Returns:
        EntityInfo: Created entity information
        
    Raises:
        McpConnectionError: Server not reachable
        McpOperationError: AutoCAD operation failed
    """

def draw_circle(
    self,
    center_point: Point3D,
    radius: float,
    layer: str = "0"
) -> EntityInfo:
    """Create a circle in AutoCAD."""

def draw_polyline(
    self,
    points: List[Point3D],
    closed: bool = False,
    layer: str = "0"
) -> EntityInfo:
    """Create a polyline from multiple points."""

def draw_rectangle(
    self,
    corner1: Point3D,
    corner2: Point3D, 
    layer: str = "0"
) -> EntityInfo:
    """Create a rectangle from two corner points."""
```

### 3D Operations
```python
def draw_extrude(
    self,
    profile_id: int,
    height: float,
    taper_angle: float = 0.0
) -> EntityInfo:
    """
    Extrude a 2D profile to create a 3D solid.
    
    Args:
        profile_id: Entity ID of profile to extrude
        height: Extrusion height
        taper_angle: Taper angle in degrees (default: 0.0)
        
    Returns:
        EntityInfo: Created solid with volume information
    """

def draw_revolve(
    self,
    profile_id: int,
    axis_start: Point3D,
    axis_end: Point3D,
    angle: float = 360.0
) -> EntityInfo:
    """Revolve a profile around an axis to create a solid."""

def draw_loft(
    self,
    profile_ids: List[int],
    guide_curves: Optional[List[int]] = None,
    closed: bool = False
) -> EntityInfo:
    """Create a lofted solid from multiple profiles."""
```

## Advanced 3D Operations

### Boolean Operations
```python
def boolean_union(
    self,
    primary_id: int,
    secondary_ids: List[int]
) -> EntityInfo:
    """
    Perform Boolean union operation.
    
    Args:
        primary_id: Primary solid entity ID
        secondary_ids: List of secondary solid IDs to union with
        
    Returns:
        EntityInfo: Resulting unified solid
    """

def boolean_subtract(
    self,
    primary_id: int,
    secondary_ids: List[int]
) -> EntityInfo:
    """Subtract secondary solids from primary solid."""

def boolean_intersect(
    self,
    primary_id: int,
    secondary_ids: List[int]
) -> EntityInfo:
    """Create intersection of solids."""
```

## Surface Unfolding Operations

### Main Unfolding Method
```python
def unfold_surface(
    self,
    entity_id: int,
    tolerance: float = 0.01,
    method: str = "triangulation",
    include_markings: bool = True,
    output_layer: str = "UNFOLD_PATTERN"
) -> UnfoldResult:
    """
    Unfold a 3D surface to 2D pattern for manufacturing.
    
    Args:
        entity_id: Entity ID of surface/solid to unfold
        tolerance: Unfolding tolerance (default: 0.01)
        method: Algorithm method ("triangulation", "conformal", "adaptive")
        include_markings: Add fold and cut line markings (default: True)
        output_layer: Layer for unfolded pattern (default: "UNFOLD_PATTERN")
        
    Returns:
        UnfoldResult: Complete unfolding results with pattern info
        
    Raises:
        McpOperationError: Surface cannot be unfolded or operation failed
        ValueError: Invalid parameters
    """

def analyze_surface(
    self,
    entity_id: int,
    tolerance: float = 0.01
) -> dict:
    """
    Analyze surface properties for unfolding feasibility.
    
    Returns detailed curvature analysis and recommended method.
    """
```

### UnfoldResult Data Class
```python
@dataclass
class UnfoldResult:
    pattern_id: int                    # Entity ID of 2D pattern
    entity_type: str                   # Type of created pattern entity
    deviation: float                   # Area deviation percentage
    original_area: float               # Original 3D surface area
    unfolded_area: float              # Unfolded 2D pattern area
    fold_lines: List[int]             # Entity IDs of fold line markings
    cut_lines: List[int]              # Entity IDs of cut line markings
    method_used: str                  # Actual algorithm method used
    success: bool                     # Operation success flag
    warnings: List[str]               # Non-critical warnings
    execution_time: float             # Processing time in seconds
    
    @property
    def area_accuracy(self) -> float:
        """Calculate area accuracy percentage (100% - deviation)."""
        return 100.0 - self.deviation
    
    def is_manufacturing_ready(self, max_deviation: float = 0.1) -> bool:
        """Check if pattern meets manufacturing tolerances."""
        return self.deviation <= max_deviation and self.success
```

## Layout and Dimensioning

### Layout Creation
```python
def create_layout(
    self,
    entity_id: int,
    layout_name: str,
    scale: float = 1.0,
    view_type: str = "isometric",
    dimension_style: str = "STANDARD",
    title_block: bool = False
) -> LayoutResult:
    """
    Create a layout with 3D entity and automatic dimensioning.
    
    Args:
        entity_id: Entity to place in layout
        layout_name: Name for new layout tab
        scale: Viewport scale (default: 1.0)
        view_type: View orientation ("isometric", "front", "top", "right")
        dimension_style: AutoCAD dimension style name
        title_block: Include title block (default: False)
        
    Returns:
        LayoutResult: Layout creation results with dimension info
    """

@dataclass
class LayoutResult:
    layout_name: str                  # Created layout name
    viewport_id: int                  # Viewport entity ID
    dimensions_added: int             # Number of dimensions created
    dimension_ids: List[int]          # List of dimension entity IDs
    title_block_id: Optional[int]     # Title block entity ID (if created)
    success: bool                     # Operation success
    execution_time: float             # Processing time
```

## Entity Management

### Entity Operations
```python
def get_entities(
    self,
    entity_type: Optional[str] = None,
    layer: Optional[str] = None
) -> List[EntityInfo]:
    """
    Get list of entities in current drawing.
    
    Args:
        entity_type: Filter by entity type (e.g., "AcDbLine")
        layer: Filter by layer name
        
    Returns:
        List[EntityInfo]: Entity information objects
    """

def get_entity_details(self, entity_id: int) -> EntityInfo:
    """Get detailed information about specific entity."""

def delete_entity(self, entity_id: int) -> bool:
    """Delete entity from drawing."""

def entity_exists(self, entity_id: int) -> bool:
    """Check if entity exists in drawing."""
```

### EntityInfo Data Class
```python
@dataclass
class EntityInfo:
    id: int                           # AutoCAD entity ID
    type: str                         # Entity class name
    layer: str                        # Layer name
    color: int                        # Color index
    length: Optional[float] = None    # Length (for lines)
    radius: Optional[float] = None    # Radius (for circles)
    area: Optional[float] = None      # Area (for closed entities)
    volume: Optional[float] = None    # Volume (for solids)
    bounding_box: Optional[dict] = None  # Min/max extents
    center_of_mass: Optional[Point3D] = None  # Center point
    material: Optional[str] = None    # Material assignment
    custom_properties: dict = field(default_factory=dict)
    
    @property
    def is_2d(self) -> bool:
        """Check if entity is 2D (no Z variation)."""
        
    @property
    def is_solid(self) -> bool:
        """Check if entity is a 3D solid."""
```

## Plugin Framework

### Plugin Operations
```python
def get_plugins(self) -> List[dict]:
    """Get list of available plugins with parameters."""

def execute_plugin(
    self,
    plugin_name: str,
    parameters: dict,
    timeout: Optional[float] = None
) -> dict:
    """
    Execute a plugin with specified parameters.
    
    Args:
        plugin_name: Name of plugin to execute
        parameters: Plugin-specific parameters
        timeout: Override default timeout for long operations
        
    Returns:
        dict: Plugin execution results
    """

def plugin_exists(self, plugin_name: str) -> bool:
    """Check if plugin is available."""
```

## Error Handling

### Exception Classes
```python
class McpError(Exception):
    """Base exception for MCP client errors."""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}

class McpConnectionError(McpError):
    """Raised when server connection fails."""

class McpOperationError(McpError):
    """Raised when AutoCAD operation fails."""

class McpTimeoutError(McpError):
    """Raised when operation times out."""

class McpValidationError(McpError):
    """Raised when input validation fails."""
```

### Error Handling Patterns
```python
def robust_autocad_operation(client: McpClient) -> Optional[EntityInfo]:
    """Example of robust error handling."""
    try:
        # Ensure server is connected
        if not client.is_connected():
            raise McpConnectionError("MCP server not reachable")
        
        # Check AutoCAD status
        acad_status = client.get_autocad_status()
        if acad_status.get('status') != 'connected':
            raise McpOperationError(
                "AutoCAD not connected", 
                error_code="AUTOCAD_NOT_CONNECTED",
                details={'suggestion': 'Start AutoCAD 2025 and ensure it is visible'}
            )
        
        # Perform operation with timeout
        result = client.draw_circle([0, 0, 0], 50.0)
        return result
        
    except McpConnectionError as e:
        logging.error(f"Connection error: {e}")
        print("Error: MCP server not running. Start with: poetry run python src/server.py")
        return None
        
    except McpOperationError as e:
        logging.error(f"Operation error: {e}")
        if e.error_code == "AUTOCAD_NOT_CONNECTED":
            print("Error: AutoCAD 2025 must be running and visible")
        elif e.error_code == "INVALID_ENTITY_TYPE":
            print(f"Error: {e.details.get('suggestion', 'Invalid entity type')}")
        return None
        
    except McpTimeoutError as e:
        logging.error(f"Timeout error: {e}")
        print("Error: Operation timed out. Try reducing complexity or increasing timeout")
        return None
        
    except Exception as e:
        logging.exception("Unexpected error")
        print(f"Unexpected error: {e}")
        return None
```

## Utility Functions and Helpers

### Geometric Utilities
```python
def distance_3d(point1: Point3D, point2: Point3D) -> float:
    """Calculate 3D distance between two points."""

def midpoint_3d(point1: Point3D, point2: Point3D) -> Point3D:
    """Calculate midpoint between two 3D points."""

def normalize_vector(vector: Point3D) -> Point3D:
    """Normalize a 3D vector to unit length."""

def cross_product(vector1: Point3D, vector2: Point3D) -> Point3D:
    """Calculate cross product of two 3D vectors."""
```

### Validation Utilities
```python
def validate_point3d(point: Point3D) -> Point3D:
    """Validate and normalize 3D point coordinates."""

def validate_entity_id(entity_id: int) -> int:
    """Validate entity ID is positive integer."""

def validate_tolerance(tolerance: float) -> float:
    """Validate tolerance is within acceptable range."""
```

### Conversion Utilities
```python
def degrees_to_radians(degrees: float) -> float:
    """Convert degrees to radians."""

def radians_to_degrees(radians: float) -> float:
    """Convert radians to degrees."""

def mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""

def inches_to_mm(inches: float) -> float:
    """Convert inches to millimeters."""
```

## Configuration and Settings

### Client Configuration
```python
@dataclass
class McpClientConfig:
    host: str = "localhost"
    port: int = 5000
    timeout: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    debug: bool = False
    log_level: str = "INFO"
    
    @classmethod
    def from_environment(cls) -> 'McpClientConfig':
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv('MCP_HOST', 'localhost'),
            port=int(os.getenv('MCP_PORT', '5000')),
            timeout=float(os.getenv('MCP_TIMEOUT', '30.0')),
            debug=os.getenv('MCP_DEBUG', 'false').lower() == 'true'
        )
```

## Usage Examples

### Basic Drawing Script
```python
from mcp_client import McpClient

def create_simple_box():
    """Create a simple 3D box."""
    with McpClient() as client:
        # Create base rectangle
        rect = client.draw_rectangle([0, 0, 0], [100, 50, 0])
        
        # Extrude to create box
        box = client.draw_extrude(rect.id, height=25.0)
        
        print(f"Created box with volume: {box.volume} cubic units")
        return box.id

if __name__ == "__main__":
    box_id = create_simple_box()
```

### Surface Unfolding Workflow
```python
from mcp_client import McpClient, McpOperationError

def unfold_selected_surface():
    """Unfold a surface selected in AutoCAD."""
    with McpClient() as client:
        # Get all surfaces in drawing
        surfaces = client.get_entities(entity_type="AcDbSurface")
        
        if not surfaces:
            print("No surfaces found in drawing")
            return
        
        # Unfold the first surface
        surface = surfaces[0]
        try:
            result = client.unfold_surface(
                surface.id,
                tolerance=0.005,
                method="triangulation",
                include_markings=True
            )
            
            print(f"Surface unfolded successfully!")
            print(f"Pattern ID: {result.pattern_id}")
            print(f"Area accuracy: {result.area_accuracy:.2f}%")
            print(f"Fold lines: {len(result.fold_lines)}")
            print(f"Cut lines: {len(result.cut_lines)}")
            
            if result.warnings:
                print("Warnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")
                    
        except McpOperationError as e:
            print(f"Unfolding failed: {e}")
            if e.error_code == "SURFACE_TOO_COMPLEX":
                print("Try increasing tolerance or using 'adaptive' method")

if __name__ == "__main__":
    unfold_selected_surface()
```

## Type Definitions

```python
# Type aliases for better code clarity
Point3D = List[float]  # [x, y, z] coordinates
Vector3D = List[float]  # [x, y, z] vector components
EntityId = int         # AutoCAD entity ID
LayerName = str        # AutoCAD layer name
```

## Testing Support

### Mock Client for Testing
```python
class MockMcpClient(McpClient):
    """Mock client for unit testing without server dependency."""
    
    def __init__(self, mock_responses: dict = None):
        self.mock_responses = mock_responses or {}
        self.call_history = []
    
    def draw_circle(self, center_point: Point3D, radius: float, layer: str = "0") -> EntityInfo:
        self.call_history.append(('draw_circle', center_point, radius, layer))
        return EntityInfo(id=123, type="AcDbCircle", layer=layer, radius=radius)
```

This MCP Client Library specification provides a comprehensive, type-safe interface for AutoCAD automation that integrates seamlessly with VS Code and Roo Code workflows.