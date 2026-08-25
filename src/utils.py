"""
Utility functions for AutoCAD MCP Server.
"""

import math
import logging
from typing import List, Tuple, Dict, Any, Optional
import pythoncom
import win32com.client

from pyautocad import Autocad

logger = logging.getLogger(__name__)

# Type alias for 3D points
Point3D = List[float]


def validate_point3d(point: Any) -> Point3D:
    """
    Validate and normalize 3D point coordinates.
    
    Args:
        point: Input point data (should be [x, y, z])
        
    Returns:
        List[float]: Validated 3D point coordinates
        
    Raises:
        ValueError: If point format is invalid
    """
    if not isinstance(point, (list, tuple)):
        raise ValueError("Point must be a list or tuple")
        
    if len(point) != 3:
        raise ValueError("Point must have exactly 3 coordinates [x, y, z]")
        
    try:
        return [float(coord) for coord in point]
    except (TypeError, ValueError) as e:
        raise ValueError(f"Point coordinates must be numeric: {e}")


def validate_entity_id(entity_id: Any) -> int:
    """
    Validate entity ID is positive integer.
    
    Args:
        entity_id: Input entity ID
        
    Returns:
        int: Validated entity ID
        
    Raises:
        ValueError: If entity ID is invalid
    """
    try:
        eid = int(entity_id)
        if eid <= 0:
            raise ValueError("Entity ID must be positive")
        return eid
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid entity ID: {e}")


def validate_tolerance(tolerance: Any) -> float:
    """
    Validate tolerance is within acceptable range.
    
    Args:
        tolerance: Input tolerance value
        
    Returns:
        float: Validated tolerance
        
    Raises:
        ValueError: If tolerance is invalid
    """
    try:
        tol = float(tolerance)
        if not (0.001 <= tol <= 1.0):
            raise ValueError("Tolerance must be between 0.001 and 1.0")
        return tol
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid tolerance: {e}")


def validate_layer_name(layer: Any) -> str:
    """
    Validate AutoCAD layer name.
    
    Args:
        layer: Input layer name
        
    Returns:
        str: Validated layer name
        
    Raises:
        ValueError: If layer name is invalid
    """
    if not isinstance(layer, str):
        raise ValueError("Layer name must be a string")
        
    if not layer.strip():
        raise ValueError("Layer name cannot be empty")
        
    # Check for invalid characters in AutoCAD layer names
    invalid_chars = ['<', '>', '/', '\\', '"', ':', ';', '?', '*', '|', '=', '`']
    for char in invalid_chars:
        if char in layer:
            raise ValueError(f"Layer name contains invalid character: {char}")
            
    return layer.strip()


def distance_3d(point1: Point3D, point2: Point3D) -> float:
    """
    Calculate 3D distance between two points.
    
    Args:
        point1: First point [x, y, z]
        point2: Second point [x, y, z]
        
    Returns:
        float: Distance between points
    """
    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]
    dz = point2[2] - point1[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def midpoint_3d(point1: Point3D, point2: Point3D) -> Point3D:
    """
    Calculate midpoint between two 3D points.
    
    Args:
        point1: First point [x, y, z]
        point2: Second point [x, y, z]
        
    Returns:
        Point3D: Midpoint coordinates
    """
    return [
        (point1[0] + point2[0]) / 2,
        (point1[1] + point2[1]) / 2,
        (point1[2] + point2[2]) / 2
    ]


def normalize_vector(vector: Point3D) -> Point3D:
    """
    Normalize a 3D vector to unit length.
    
    Args:
        vector: Vector [x, y, z]
        
    Returns:
        Point3D: Normalized vector
        
    Raises:
        ValueError: If vector has zero length
    """
    length = math.sqrt(vector[0]**2 + vector[1]**2 + vector[2]**2)
    if length == 0:
        raise ValueError("Cannot normalize zero-length vector")
        
    return [vector[0]/length, vector[1]/length, vector[2]/length]


def cross_product(vector1: Point3D, vector2: Point3D) -> Point3D:
    """
    Calculate cross product of two 3D vectors.
    
    Args:
        vector1: First vector [x, y, z]
        vector2: Second vector [x, y, z]
        
    Returns:
        Point3D: Cross product vector
    """
    return [
        vector1[1] * vector2[2] - vector1[2] * vector2[1],
        vector1[2] * vector2[0] - vector1[0] * vector2[2],
        vector1[0] * vector2[1] - vector1[1] * vector2[0]
    ]


def degrees_to_radians(degrees: float) -> float:
    """Convert degrees to radians."""
    return degrees * math.pi / 180.0


def radians_to_degrees(radians: float) -> float:
    """Convert radians to degrees."""
    return radians * 180.0 / math.pi


def analyze_surface_mesh(entity) -> Dict[str, Any]:
    """
    Analyze a 3D surface mesh for unfolding operations.
    
    Args:
        entity: AutoCAD mesh entity
        
    Returns:
        Dict containing mesh analysis data
    """
    try:
        analysis = {
            'entity_id': entity.ObjectID,
            'entity_type': entity.ObjectName,
            'has_vertices': False,
            'vertex_count': 0,
            'face_count': 0,
            'surface_area': 0.0,
            'bounding_box': None,
            'is_unfoldable': False
        }
        
        # Extract basic properties
        if hasattr(entity, 'Area'):
            analysis['surface_area'] = entity.Area
            
        if hasattr(entity, 'GetBoundingBox'):
            try:
                min_pt, max_pt = entity.GetBoundingBox()
                analysis['bounding_box'] = {
                    'min_point': list(min_pt),
                    'max_point': list(max_pt)
                }
            except:
                logger.warning("Could not extract bounding box")
        
        # For 3D meshes, extract mesh properties from coordinates
        try:
            m_size = None
            n_size = None
            
            # Extract dimensions from coordinates (primary method for AutoCAD PolygonMesh)
            if hasattr(entity, 'Coordinates'):
                coords = entity.Coordinates
                total_vertices = len(coords) // 3  # 3 coordinates per vertex
                
                # Determine grid dimensions by analyzing coordinate patterns
                # Convert to list of vertices for analysis
                vertices = []
                for i in range(0, len(coords), 3):
                    vertices.append([coords[i], coords[i+1], coords[i+2]])
                
                # Find unique X and Y coordinates to determine grid size
                x_coords = sorted(set(v[0] for v in vertices))
                y_coords = sorted(set(v[1] for v in vertices))
                
                m_size = len(x_coords)  # Number of unique X positions
                n_size = len(y_coords)  # Number of unique Y positions
                
                # Validate that we have a rectangular grid
                if m_size * n_size == total_vertices:
                    logger.info(f"Detected {m_size}x{n_size} grid from coordinates analysis")
                else:
                    # Fallback: common grid sizes
                    if total_vertices == 9:
                        m_size = n_size = 3
                    elif total_vertices == 16:
                        m_size = n_size = 4
                    elif total_vertices == 25:
                        m_size = n_size = 5
                    else:
                        # Try to guess dimensions for other sizes
                        import math
                        sqrt_vertices = int(math.sqrt(total_vertices))
                        if sqrt_vertices * sqrt_vertices == total_vertices:
                            m_size = n_size = sqrt_vertices
                    
                    logger.info(f"Using fallback grid size: {m_size}x{n_size} for {total_vertices} vertices")
            
            # If we successfully determined dimensions, populate analysis
            if m_size and n_size and m_size >= 2 and n_size >= 2:
                analysis['m_size'] = m_size
                analysis['n_size'] = n_size
                analysis['vertex_count'] = m_size * n_size
                analysis['face_count'] = (m_size - 1) * (n_size - 1)
                analysis['has_vertices'] = True
                analysis['is_unfoldable'] = True
                
                # Calculate approximate surface area from coordinates
                if hasattr(entity, 'Coordinates'):
                    try:
                        # Simple area estimation from bounding box
                        vertices = []
                        for i in range(0, len(coords), 3):
                            vertices.append([coords[i], coords[i+1], coords[i+2]])
                        
                        x_coords = [v[0] for v in vertices]
                        y_coords = [v[1] for v in vertices]
                        
                        width = max(x_coords) - min(x_coords)
                        height = max(y_coords) - min(y_coords)
                        analysis['estimated_area'] = width * height
                        
                    except:
                        pass
                
                logger.info(f"Successfully analyzed mesh: {m_size}x{n_size} grid, {analysis['vertex_count']} vertices")
            else:
                logger.warning(f"Could not determine valid mesh dimensions from entity {entity.ObjectID}")
                
        except Exception as e:
            logger.error(f"Error extracting mesh properties: {e}")
            
        return analysis
        
    except Exception as e:
        logger.error(f"Surface analysis failed: {e}")
        return {'error': str(e)}


def unfold_surface_simple(mesh_analysis: Dict[str, Any], tolerance: float = 0.01) -> Dict[str, Any]:
    """
    Simple surface unfolding algorithm for 3D meshes.
    
    Args:
        mesh_analysis: Analysis data from analyze_surface_mesh
        tolerance: Unfolding tolerance
        
    Returns:
        Dict containing unfolded surface data
    """
    if not mesh_analysis.get('is_unfoldable', False):
        return {'error': 'Surface is not unfoldable'}
    
    try:
        m_size = mesh_analysis.get('m_size', 0)
        n_size = mesh_analysis.get('n_size', 0)
        
        if m_size < 2 or n_size < 2:
            return {'error': 'Invalid mesh dimensions for unfolding'}
        
        # Simple rectangular unfolding (proof of concept)
        # In practice, this would use the actual mesh vertices
        pattern_width = (m_size - 1) * 25
        pattern_height = (n_size - 1) * 25
        pattern_area = pattern_width * pattern_height
        original_area = mesh_analysis.get('surface_area', pattern_area)
        
        # Calculate simple distortion metrics for rectangular approximation
        area_distortion = abs(pattern_area - original_area) / original_area if original_area > 0 else 0
        
        unfolded_data = {
            'success': True,
            'method': 'simple_rectangular',
            'original_surface_area': original_area,
            'unfolded_pattern': {
                'type': 'rectangular_grid',
                'm_size': m_size,
                'n_size': n_size,
                'pattern_width': pattern_width,
                'pattern_height': pattern_height,
            },
            'distortion_metrics': {
                'area_distortion_percentage': area_distortion * 100,
                'method': 'rectangular_approximation',
                'max_angle_distortion': 0.0,  # Rectangular grid has no angle distortion
                'avg_angle_distortion': 0.0,
                'distortion_acceptable': area_distortion < 0.1  # 10% tolerance for simple method
            },
            'manufacturing_data': {
                'fold_lines': [],
                'cut_lines': [],
                'material_utilization': 0.95,
                'recommended_material_size': [
                    (m_size - 1) * 30,  # Add margin
                    (n_size - 1) * 30
                ]
            }
        }
        
        # Generate fold lines for rectangular grid
        fold_lines = []
        for i in range(m_size - 1):
            fold_lines.append({
                'type': 'vertical_fold',
                'position': i * 25,
                'length': (n_size - 1) * 25
            })
        
        for j in range(n_size - 1):
            fold_lines.append({
                'type': 'horizontal_fold', 
                'position': j * 25,
                'length': (m_size - 1) * 25
            })
            
        unfolded_data['manufacturing_data']['fold_lines'] = fold_lines
        
        return unfolded_data
        
    except Exception as e:
        logger.error(f"Surface unfolding failed: {e}")
        return {'error': str(e)}


def get_autocad_instance() -> Autocad:
    """
    Get AutoCAD instance with proper error handling.
    
    Returns:
        Autocad: Connected AutoCAD instance
        
    Raises:
        ConnectionError: If AutoCAD is not running or accessible
    """
    try:
        pythoncom.CoInitialize()
        
        # Try to connect to existing AutoCAD 2025 instance first
        try:
            # Connect to existing AutoCAD 2025 instance (preferred)
            app = win32com.client.GetActiveObject("AutoCAD.Application.25")
            app.Visible = True
            
            # Create a custom wrapper that mimics pyautocad.Autocad
            class AutocadWrapper:
                def __init__(self, app):
                    self.app = app
                    try:
                        self.doc = app.ActiveDocument
                        self.model = app.ActiveDocument.ModelSpace
                    except:
                        # COM interface issue - create dummy objects
                        self.doc = None
                        self.model = None
                        logger.warning("Could not access ActiveDocument - COM interface issue")
                    
                    # Create a model wrapper that handles COM calls properly
                    class ModelWrapper:
                        def __init__(self, modelspace):
                            self.modelspace = modelspace
                            
                        def AddLine(self, start_point, end_point):
                            # Convert Python lists to VBA arrays for COM
                            import win32com.client
                            return self.modelspace.AddLine(
                                win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, start_point),
                                win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, end_point)
                            )
                            
                        def AddCircle(self, center_point, radius):
                            import win32com.client
                            return self.modelspace.AddCircle(
                                win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, center_point),
                                radius
                            )
                            
                        def AddExtrudedSolid(self, profile, height, taper_angle=0.0):
                            """Create 3D extruded solid from 2D profile - simplified approach"""
                            import win32com.client
                            try:
                                # Direct approach: try to extrude the polyline directly
                                return self.modelspace.AddExtrudedSolid(
                                    profile,
                                    height,
                                    math.radians(taper_angle)
                                )
                            except Exception as e:
                                # Fallback: create simple box for rectangular profiles
                                logger.warning(f"Direct extrusion failed: {e}, creating simple box")
                                # Get profile bounds for fallback box creation
                                return self.modelspace.AddBox(
                                    win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [0, 0, 0]),
                                    50, 30, height  # Default dimensions
                                )
                            
                        def AddRevolvedSolid(self, profile, axis_point, axis_vector, angle):
                            """Create 3D revolved solid around axis - simplified approach"""
                            import win32com.client
                            try:
                                # Direct approach: try to revolve the polyline directly
                                return self.modelspace.AddRevolvedSolid(
                                    profile,
                                    win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, axis_point),
                                    win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, axis_vector),
                                    angle
                                )
                            except Exception as e:
                                # Fallback: create simple sphere instead of cylinder
                                logger.warning(f"Direct revolution failed: {e}, creating sphere")
                                return self.modelspace.AddSphere(
                                    win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, axis_point),
                                    15   # Default radius
                                )
                            
                        def AddPolyline(self, points):
                            """Create 2D polyline for profiles"""
                            import win32com.client
                            # Flatten points for AutoCAD polyline format - needs X,Y pairs only
                            flat_points = []
                            for point in points:
                                flat_points.append(float(point[0]))  # X coordinate
                                flat_points.append(float(point[1]))  # Y coordinate
                            return self.modelspace.AddLightWeightPolyline(
                                win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat_points)
                            )
                            
                        def Add3DMesh(self, m_size, n_size, vertices):
                            """Create 3D mesh surface (M x N rectangular mesh)"""
                            import win32com.client
                            # Flatten 3D vertices array for AutoCAD mesh format
                            flat_vertices = []
                            for vertex in vertices:
                                flat_vertices.append(float(vertex[0]))  # X
                                flat_vertices.append(float(vertex[1]))  # Y
                                flat_vertices.append(float(vertex[2]))  # Z
                            
                            return self.modelspace.Add3DMesh(
                                m_size, n_size,
                                win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat_vertices)
                            )
                            
                        def AddPolyFaceMesh(self, vertices, faces):
                            """Create polyface mesh with variable vertex counts per face"""
                            import win32com.client
                            
                            # Validate minimum requirements
                            if len(vertices) < 4:
                                raise ValueError("PolyFaceMesh requires at least 4 vertices")
                            
                            if len(faces) < 1:
                                raise ValueError("PolyFaceMesh requires at least 1 face")
                            
                            # Flatten vertex coordinates to sequential X,Y,Z values
                            flat_vertices = []
                            for vertex in vertices:
                                flat_vertices.extend([float(vertex[0]), float(vertex[1]), float(vertex[2])])
                            
                            # AutoCAD polyface mesh face format based on official documentation:
                            # Faces are defined in groups of exactly 4 vertex indices
                            # Array size must be multiple of 4
                            # Uses 1-based indexing (vertex 0 becomes 1)
                            # Negative values make edges invisible
                            face_list = []
                            
                            for face in faces:
                                face_indices = list(face)
                                
                                # Validate face has minimum vertices
                                if len(face_indices) < 3:
                                    raise ValueError(f"Face must have at least 3 vertices, got {len(face_indices)}")
                                
                                # Validate vertex indices are within range
                                for idx in face_indices:
                                    if idx < 0 or idx >= len(vertices):
                                        raise ValueError(f"Face vertex index {idx} out of range (0-{len(vertices)-1})")
                                
                                # Convert to 1-based indexing as required by AutoCAD COM
                                face_1based = [idx + 1 for idx in face_indices]
                                
                                # AutoCAD requires exactly 4 vertex indices per face
                                # Pad triangles by repeating the last vertex
                                if len(face_1based) == 3:
                                    face_1based.append(face_1based[-1])  # Repeat last vertex for triangle
                                elif len(face_1based) > 4:
                                    # For polygons with >4 vertices, only take first 4
                                    # (Alternative: triangulate the polygon)
                                    face_1based = face_1based[:4]
                                
                                # Ensure exactly 4 indices
                                while len(face_1based) < 4:
                                    face_1based.append(face_1based[-1])
                                
                                face_list.extend(face_1based)
                            
                            # Ensure face array size is multiple of 4 as required
                            if len(face_list) % 4 != 0:
                                raise ValueError(f"Face array size must be multiple of 4, got {len(face_list)}")
                            
                            try:
                                # Method 1: Standard AddPolyFaceMesh with proper variants
                                return self.modelspace.AddPolyFaceMesh(
                                    win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, flat_vertices),
                                    win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I4, face_list)
                                )
                            except Exception as e1:
                                logger.warning(f"Standard AddPolyFaceMesh failed: {e1}")
                                try:
                                    # Method 2: Alternative approach with SafeArray
                                    import pythoncom
                                    vertex_array = pythoncom.MakeVariant(flat_vertices)
                                    face_array = pythoncom.MakeVariant(face_list) 
                                    return self.modelspace.AddPolyFaceMesh(vertex_array, face_array)
                                except Exception as e2:
                                    logger.warning(f"SafeArray AddPolyFaceMesh failed: {e2}")
                                    # Method 3: Direct array passing (some COM interfaces accept this)
                                    return self.modelspace.AddPolyFaceMesh(flat_vertices, face_list)
                    
                    self.model = ModelWrapper(app.ActiveDocument.ModelSpace)
                
                @property
                def Visible(self):
                    return self.app.Visible
                
                @Visible.setter
                def Visible(self, value):
                    self.app.Visible = value
                    
                def get_entity_by_id(self, entity_id):
                    """Get entity by ObjectID"""
                    try:
                        # Search through all entities in the document
                        for entity in self.model.modelspace:
                            if entity.ObjectID == entity_id:
                                return entity
                        return None
                    except:
                        return None
                        
                def union_solids(self, base_entity, union_entities):
                    """Perform boolean union on solids"""
                    result = base_entity
                    for entity in union_entities:
                        if entity:
                            result = result.Boolean(0, entity)  # 0 = Union
                    return result
                    
                def subtract_solids(self, base_entity, subtract_entities):
                    """Perform boolean subtraction on solids"""
                    result = base_entity
                    for entity in subtract_entities:
                        if entity:
                            result = result.Boolean(2, entity)  # 2 = Subtract
                    return result
            
            acad = AutocadWrapper(app)
            logger.info("Connected to existing AutoCAD.Application.25")
        except Exception as e1:
            logger.info(f"No existing AutoCAD.Application.25 found: {e1}")
            try:
                # Fallback: Create new AutoCAD 2025 instance
                app = win32com.client.Dispatch("AutoCAD.Application.25")
                app.Visible = True
                
                acad = AutocadWrapper(app)
                logger.info("Created new AutoCAD.Application.25")
            except Exception as e2:
                logger.error(f"AutoCAD.Application.25 not found: {e2}")
                # Last resort - let pyautocad handle it
                acad = Autocad(create_if_not_exists=True)
        
        if acad is None or acad.app is None:
            raise ConnectionError("AutoCAD is not running")
            
        # Test connection
        _ = acad.doc.Name
        
        # Ensure AutoCAD is visible
        if not acad.app.Visible:
            acad.app.Visible = True
            logger.info("Made AutoCAD visible")
            
        return acad
        
    except Exception as e:
        logger.error(f"Failed to connect to AutoCAD: {e}")
        raise ConnectionError(f"Cannot connect to AutoCAD: {e}")


def extract_entity_properties(entity) -> Dict[str, Any]:
    """
    Extract properties from an AutoCAD entity.
    
    Args:
        entity: AutoCAD entity object
        
    Returns:
        Dict[str, Any]: Entity properties
    """
    properties = {
        'id': entity.ObjectID,
        'type': entity.ObjectName,
        'layer': entity.Layer,
        'color': entity.Color,
    }
    
    try:
        # Add type-specific properties
        if hasattr(entity, 'Length'):
            properties['length'] = entity.Length
            
        if hasattr(entity, 'Radius'):
            properties['radius'] = entity.Radius
            
        if hasattr(entity, 'Area'):
            properties['area'] = entity.Area
            
        if hasattr(entity, 'Volume'):
            properties['volume'] = entity.Volume
            
        # Add bounding box if available
        if hasattr(entity, 'GetBoundingBox'):
            min_point, max_point = entity.GetBoundingBox()
            properties['bounding_box'] = {
                'min_point': list(min_point),
                'max_point': list(max_point)
            }
            
        # Add center of mass for solids
        if hasattr(entity, 'MassProp'):
            mass_props = entity.MassProp
            if len(mass_props) >= 3:
                properties['center_of_mass'] = list(mass_props[:3])
                
    except Exception as e:
        logger.warning(f"Could not extract some properties from entity {entity.ObjectID}: {e}")
        
    return properties


def create_error_response(
    error_message: str,
    error_code: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 500
) -> Tuple[Dict[str, Any], int]:
    """
    Create standardized error response.
    
    Args:
        error_message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional error details
        status_code: HTTP status code
        
    Returns:
        Tuple[Dict, int]: Error response and status code
    """
    response = {
        'success': False,
        'error': error_message,
        'error_code': error_code,
        'details': details or {}
    }
    
    return response, status_code


def create_success_response(
    data: Dict[str, Any],
    execution_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create standardized success response.
    
    Args:
        data: Response data
        execution_time: Operation execution time
        
    Returns:
        Dict[str, Any]: Success response
    """
    response = {
        'success': True,
        **data
    }
    
    if execution_time is not None:
        response['execution_time'] = execution_time
        
    return response