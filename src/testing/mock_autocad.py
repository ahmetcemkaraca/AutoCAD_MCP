"""
Mock AutoCAD Implementation for Testing.

Provides a mock AutoCAD interface that simulates AutoCAD COM behavior
for offline testing and development.
"""

import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from unittest.mock import MagicMock
import math

logger = logging.getLogger(__name__)


@dataclass
class MockEntity:
    """Mock AutoCAD entity."""
    object_id: int
    entity_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    handle: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def __post_init__(self):
        # Set default properties
        self.properties.setdefault('Layer', '0')
        self.properties.setdefault('Color', 256)  # ByLayer
        self.properties.setdefault('Linetype', 'ByLayer')


@dataclass
class MockLine(MockEntity):
    """Mock AutoCAD line entity."""
    start_point: List[float] = field(default_factory=lambda: [0, 0, 0])
    end_point: List[float] = field(default_factory=lambda: [0, 0, 0])
    
    def __post_init__(self):
        super().__post_init__()
        self.entity_type = 'AcDbLine'
        self.properties['StartPoint'] = self.start_point
        self.properties['EndPoint'] = self.end_point
        self.properties['Length'] = self._calculate_length()
    
    def _calculate_length(self) -> float:
        """Calculate line length."""
        dx = self.end_point[0] - self.start_point[0]
        dy = self.end_point[1] - self.start_point[1]
        dz = self.end_point[2] - self.start_point[2]
        return math.sqrt(dx*dx + dy*dy + dz*dz)


@dataclass
class MockCircle(MockEntity):
    """Mock AutoCAD circle entity."""
    center: List[float] = field(default_factory=lambda: [0, 0, 0])
    radius: float = 1.0
    
    def __post_init__(self):
        super().__post_init__()
        self.entity_type = 'AcDbCircle'
        self.properties['Center'] = self.center
        self.properties['Radius'] = self.radius
        self.properties['Area'] = math.pi * self.radius * self.radius
        self.properties['Circumference'] = 2 * math.pi * self.radius


@dataclass
class MockSolid(MockEntity):
    """Mock AutoCAD 3D solid entity."""
    volume: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.entity_type = 'AcDb3dSolid'
        self.properties['Volume'] = self.volume


class MockModelSpace:
    """Mock AutoCAD ModelSpace."""
    
    def __init__(self, parent: 'MockAutoCAD'):
        self.parent = parent
        self.entities: Dict[int, MockEntity] = {}
        self._next_object_id = 1
    
    def _get_next_object_id(self) -> int:
        """Get next available object ID."""
        object_id = self._next_object_id
        self._next_object_id += 1
        return object_id
    
    def AddLine(self, start_point: List[float], end_point: List[float]) -> MockLine:
        """Add line to model space."""
        object_id = self._get_next_object_id()
        line = MockLine(
            object_id=object_id,
            start_point=start_point.copy(),
            end_point=end_point.copy()
        )
        self.entities[object_id] = line
        
        # Log the operation
        self.parent.log_operation('AddLine', {
            'start_point': start_point,
            'end_point': end_point,
            'object_id': object_id
        })
        
        return line
    
    def AddCircle(self, center: List[float], radius: float) -> MockCircle:
        """Add circle to model space."""
        object_id = self._get_next_object_id()
        circle = MockCircle(
            object_id=object_id,
            center=center.copy(),
            radius=radius
        )
        self.entities[object_id] = circle
        
        # Log the operation
        self.parent.log_operation('AddCircle', {
            'center': center,
            'radius': radius,
            'object_id': object_id
        })
        
        return circle
    
    def AddPolyline(self, points: List[List[float]]) -> MockEntity:
        """Add polyline to model space."""
        object_id = self._get_next_object_id()
        polyline = MockEntity(
            object_id=object_id,
            entity_type='AcDbPolyline'
        )
        polyline.properties['Vertices'] = [p.copy() for p in points]
        self.entities[object_id] = polyline
        
        # Log the operation
        self.parent.log_operation('AddPolyline', {
            'points': points,
            'object_id': object_id
        })
        
        return polyline
    
    def AddExtrudedSolid(self, profile: MockEntity, height: float, taper_angle: float = 0.0) -> MockSolid:
        """Add extruded solid to model space."""
        object_id = self._get_next_object_id()
        
        # Calculate approximate volume based on profile type
        volume = 0.0
        if hasattr(profile, 'properties'):
            if 'Area' in profile.properties:
                volume = profile.properties['Area'] * height
            elif profile.entity_type == 'AcDbPolyline':
                # Approximate area for polyline (simple rectangular approximation)
                vertices = profile.properties.get('Vertices', [])
                if len(vertices) >= 3:
                    # Simple area calculation
                    volume = 100.0 * height  # Placeholder
        
        solid = MockSolid(
            object_id=object_id,
            volume=volume
        )
        solid.properties['Height'] = height
        solid.properties['TaperAngle'] = taper_angle
        solid.properties['Profile'] = profile.object_id
        
        self.entities[object_id] = solid
        
        # Log the operation
        self.parent.log_operation('AddExtrudedSolid', {
            'profile_id': profile.object_id,
            'height': height,
            'taper_angle': taper_angle,
            'object_id': object_id,
            'volume': volume
        })
        
        return solid
    
    def AddRevolvedSolid(self, profile: MockEntity, axis_point: List[float], 
                        axis_vector: List[float], angle: float) -> MockSolid:
        """Add revolved solid to model space."""
        object_id = self._get_next_object_id()
        
        # Calculate approximate volume (placeholder calculation)
        volume = 150.0  # Placeholder volume
        
        solid = MockSolid(
            object_id=object_id,
            volume=volume
        )
        solid.properties['Profile'] = profile.object_id
        solid.properties['AxisPoint'] = axis_point.copy()
        solid.properties['AxisVector'] = axis_vector.copy()
        solid.properties['Angle'] = angle
        
        self.entities[object_id] = solid
        
        # Log the operation
        self.parent.log_operation('AddRevolvedSolid', {
            'profile_id': profile.object_id,
            'axis_point': axis_point,
            'axis_vector': axis_vector,
            'angle': angle,
            'object_id': object_id,
            'volume': volume
        })
        
        return solid
    
    def Union(self, entities: List[MockEntity]) -> MockSolid:
        """Perform boolean union operation."""
        if len(entities) < 2:
            raise ValueError("Union requires at least 2 entities")
        
        object_id = self._get_next_object_id()
        
        # Calculate combined volume
        total_volume = sum(
            getattr(entity, 'volume', entity.properties.get('Volume', 0))
            for entity in entities
            if hasattr(entity, 'volume') or 'Volume' in entity.properties
        )
        
        solid = MockSolid(
            object_id=object_id,
            volume=total_volume
        )
        solid.properties['Operation'] = 'Union'
        solid.properties['SourceEntities'] = [e.object_id for e in entities]
        
        self.entities[object_id] = solid
        
        # Remove source entities
        for entity in entities:
            if entity.object_id in self.entities:
                del self.entities[entity.object_id]
        
        # Log the operation
        self.parent.log_operation('Union', {
            'entity_ids': [e.object_id for e in entities],
            'result_id': object_id,
            'volume': total_volume
        })
        
        return solid
    
    def Subtract(self, base_entity: MockEntity, subtract_entities: List[MockEntity]) -> MockSolid:
        """Perform boolean subtraction operation."""
        object_id = self._get_next_object_id()
        
        # Calculate result volume
        base_volume = getattr(base_entity, 'volume', base_entity.properties.get('Volume', 0))
        subtract_volume = sum(
            getattr(entity, 'volume', entity.properties.get('Volume', 0))
            for entity in subtract_entities
            if hasattr(entity, 'volume') or 'Volume' in entity.properties
        )
        result_volume = max(0, base_volume - subtract_volume)
        
        solid = MockSolid(
            object_id=object_id,
            volume=result_volume
        )
        solid.properties['Operation'] = 'Subtract'
        solid.properties['BaseEntity'] = base_entity.object_id
        solid.properties['SubtractEntities'] = [e.object_id for e in subtract_entities]
        
        self.entities[object_id] = solid
        
        # Remove source entities
        if base_entity.object_id in self.entities:
            del self.entities[base_entity.object_id]
        for entity in subtract_entities:
            if entity.object_id in self.entities:
                del self.entities[entity.object_id]
        
        # Log the operation
        self.parent.log_operation('Subtract', {
            'base_entity_id': base_entity.object_id,
            'subtract_entity_ids': [e.object_id for e in subtract_entities],
            'result_id': object_id,
            'volume': result_volume
        })
        
        return solid
    
    def GetEntity(self, object_id: int) -> Optional[MockEntity]:
        """Get entity by object ID."""
        return self.entities.get(object_id)
    
    def DeleteEntity(self, object_id: int) -> bool:
        """Delete entity by object ID."""
        if object_id in self.entities:
            del self.entities[object_id]
            self.parent.log_operation('DeleteEntity', {'object_id': object_id})
            return True
        return False
    
    def GetAllEntities(self) -> List[MockEntity]:
        """Get all entities in model space."""
        return list(self.entities.values())
    
    def Clear(self):
        """Clear all entities from model space."""
        count = len(self.entities)
        self.entities.clear()
        self._next_object_id = 1
        self.parent.log_operation('ClearModelSpace', {'entities_cleared': count})


class MockApplication:
    """Mock AutoCAD Application."""
    
    def __init__(self, parent: 'MockAutoCAD'):
        self.parent = parent
        self.visible = True
        self.version = "AutoCAD 2025 Mock"
    
    @property
    def Visible(self) -> bool:
        return self.visible
    
    @Visible.setter
    def Visible(self, value: bool):
        self.visible = value
        self.parent.log_operation('SetVisibility', {'visible': value})


class MockAutoCAD:
    """Mock AutoCAD COM interface for testing."""
    
    def __init__(self):
        self.model = MockModelSpace(self)
        self.app = MockApplication(self)
        self.connected = True
        self.call_log: List[Dict[str, Any]] = []
        
        # Mock additional properties
        self.ActiveDocument = MagicMock()
        self.Documents = MagicMock()
        
        logger.info("Mock AutoCAD initialized")
    
    def log_operation(self, operation: str, parameters: Dict[str, Any]):
        """Log an operation for testing verification."""
        self.call_log.append({
            'operation': operation,
            'parameters': parameters,
            'timestamp': __import__('time').time()
        })
        
        logger.debug(f"Mock AutoCAD operation: {operation} with {parameters}")
    
    def get_call_log(self) -> List[str]:
        """Get formatted call log for test results."""
        return [
            f"{entry['operation']}({entry['parameters']})"
            for entry in self.call_log
        ]
    
    def clear_call_log(self):
        """Clear the operation call log."""
        self.call_log.clear()
    
    def is_connected(self) -> bool:
        """Check if mock AutoCAD is connected."""
        return self.connected
    
    def disconnect(self):
        """Simulate disconnection."""
        self.connected = False
        self.log_operation('Disconnect', {})
    
    def reconnect(self):
        """Simulate reconnection."""
        self.connected = True
        self.log_operation('Reconnect', {})
    
    def get_entity_count(self) -> int:
        """Get total number of entities."""
        return len(self.model.entities)
    
    def get_entities_by_type(self, entity_type: str) -> List[MockEntity]:
        """Get all entities of specific type."""
        return [
            entity for entity in self.model.entities.values()
            if entity.entity_type == entity_type
        ]
    
    def simulate_error(self, error_message: str):
        """Simulate an AutoCAD error for testing error handling."""
        self.log_operation('SimulateError', {'error_message': error_message})
        raise RuntimeError(f"Mock AutoCAD Error: {error_message}")
    
    def reset(self):
        """Reset mock AutoCAD to initial state."""
        self.model.Clear()
        self.clear_call_log()
        self.connected = True
        self.app.visible = True
        self.log_operation('Reset', {})
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get mock AutoCAD statistics."""
        entity_counts = {}
        for entity in self.model.entities.values():
            entity_type = entity.entity_type
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        return {
            'total_entities': len(self.model.entities),
            'entity_types': entity_counts,
            'operations_performed': len(self.call_log),
            'connected': self.connected
        }
    
    # Additional compatibility methods for different AutoCAD interfaces
    def draw_line(self, start_point: List[float], end_point: List[float]) -> int:
        """Legacy method for drawing lines."""
        line = self.model.AddLine(start_point, end_point)
        return line.object_id
    
    def draw_circle(self, center: List[float], radius: float) -> int:
        """Legacy method for drawing circles."""
        circle = self.model.AddCircle(center, radius)
        return circle.object_id
    
    def extrude_profile(self, profile_points: List[List[float]], height: float) -> int:
        """Legacy method for extrusion."""
        # Create profile polyline first
        polyline = self.model.AddPolyline(profile_points)
        # Create extruded solid
        solid = self.model.AddExtrudedSolid(polyline, height)
        return solid.object_id
    
    # Implement common AutoCAD COM interface methods
    def __getattr__(self, name):
        """Handle unknown attribute access with mock behavior."""
        mock_obj = MagicMock()
        mock_obj._mock_name = name
        self.log_operation('AttributeAccess', {'attribute': name})
        return mock_obj


def create_test_scenario(scenario_name: str) -> MockAutoCAD:
    """Create pre-configured test scenarios."""
    mock_acad = MockAutoCAD()
    
    if scenario_name == "empty_drawing":
        # Already empty by default
        pass
    
    elif scenario_name == "basic_shapes":
        # Add some basic shapes for testing
        mock_acad.model.AddLine([0, 0, 0], [100, 100, 0])
        mock_acad.model.AddCircle([50, 50, 0], 25)
        
    elif scenario_name == "3d_solids":
        # Add 3D solids for testing
        profile = mock_acad.model.AddPolyline([[0, 0, 0], [50, 0, 0], [50, 50, 0], [0, 50, 0]])
        mock_acad.model.AddExtrudedSolid(profile, 25)
        
    elif scenario_name == "complex_drawing":
        # Complex drawing with multiple entity types
        for i in range(5):
            mock_acad.model.AddLine([i*10, 0, 0], [i*10, 50, 0])
            mock_acad.model.AddCircle([i*10, 75, 0], 5)
        
        # Add some 3D elements
        profile = mock_acad.model.AddPolyline([[100, 0, 0], [150, 0, 0], [150, 50, 0], [100, 50, 0]])
        mock_acad.model.AddExtrudedSolid(profile, 30)
    
    else:
        logger.warning(f"Unknown test scenario: {scenario_name}")
    
    mock_acad.log_operation('CreateTestScenario', {'scenario': scenario_name})
    return mock_acad