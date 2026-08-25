"""
Type definitions for MCP Client Library.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

# Type aliases for better code clarity
Point3D = List[float]  # [x, y, z] coordinates
Vector3D = List[float]  # [x, y, z] vector components
EntityId = int         # AutoCAD entity ID
LayerName = str        # AutoCAD layer name


@dataclass
class EntityInfo:
    """Container for AutoCAD entity information."""
    
    id: int                           # AutoCAD entity ID
    type: str                         # Entity class name
    layer: str                        # Layer name
    color: int                        # Color index
    length: Optional[float] = None    # Length (for lines)
    radius: Optional[float] = None    # Radius (for circles)
    area: Optional[float] = None      # Area (for closed entities)
    volume: Optional[float] = None    # Volume (for solids)
    bounding_box: Optional[Dict[str, Point3D]] = None  # Min/max extents
    center_of_mass: Optional[Point3D] = None  # Center point
    material: Optional[str] = None    # Material assignment
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_2d(self) -> bool:
        """Check if entity is 2D (no Z variation)."""
        if self.bounding_box:
            min_z = self.bounding_box['min_point'][2]
            max_z = self.bounding_box['max_point'][2]
            return abs(max_z - min_z) < 1e-6
        return True
        
    @property
    def is_solid(self) -> bool:
        """Check if entity is a 3D solid."""
        return self.type == "AcDb3dSolid"


@dataclass
class UnfoldResult:
    """Result container for surface unfolding operations."""
    
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


@dataclass
class LayoutResult:
    """Result container for layout creation operations."""
    
    layout_name: str                  # Created layout name
    viewport_id: int                  # Viewport entity ID
    dimensions_added: int             # Number of dimensions created
    dimension_ids: List[int]          # List of dimension entity IDs
    title_block_id: Optional[int]     # Title block entity ID (if created)
    success: bool                     # Operation success
    execution_time: float             # Processing time