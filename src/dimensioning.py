"""
Automated dimensioning system for manufacturing drawings.
Generates dimensions, annotations, and manufacturing specifications.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pyautocad import Autocad, APoint
import win32com.client

logger = logging.getLogger(__name__)


class DimensioningSystem:
    """
    Automated dimensioning system for AutoCAD manufacturing drawings.
    
    Provides functionality to automatically generate dimensions, annotations,
    and manufacturing specifications for unfolded surfaces and patterns.
    """
    
    def __init__(self, autocad_instance: Autocad):
        """
        Initialize the dimensioning system.
        
        Args:
            autocad_instance: Connected AutoCAD application instance
        """
        self.acad = autocad_instance
        self.doc = self.acad.doc
        self.model_space = self.doc.ModelSpace
        
        # Dimensioning settings with manufacturing focus
        self.dimension_settings = {
            'text_height': 2.5,          # mm for manufacturing drawings
            'arrow_size': 1.25,          # mm for clear visibility  
            'extension_line_extend': 1.0, # mm beyond dimension line
            'extension_line_offset': 0.5, # mm from object
            'text_gap': 0.5,             # mm around dimension text
            'precision': 2,              # decimal places for dimensions
            'units': 'mm',               # manufacturing standard
            
            # Colors and styles for manufacturing
            'dimension_color': 3,        # Green for dimensions
            'annotation_color': 1,       # Red for important notes
            'fold_line_color': 6,        # Magenta for fold lines
            'cut_line_color': 2,         # Yellow for cut lines
            
            # Layers for organization
            'dimension_layer': 'DIMENSIONS',
            'annotation_layer': 'ANNOTATIONS', 
            'manufacturing_layer': 'MANUFACTURING'
        }
        
        logger.info("Dimensioning system initialized with manufacturing settings")
    
    def setup_dimension_layers(self) -> None:
        """Create and configure layers for dimensioning."""
        try:
            layers = self.doc.Layers
            
            # Create dimensioning layers if they don't exist
            for layer_name in [self.dimension_settings['dimension_layer'],
                             self.dimension_settings['annotation_layer'],
                             self.dimension_settings['manufacturing_layer']]:
                try:
                    layer = layers.Add(layer_name)
                    logger.info(f"Created layer: {layer_name}")
                except:
                    # Layer already exists
                    layer = layers.Item(layer_name)
                    logger.debug(f"Using existing layer: {layer_name}")
            
            # Set dimension layer properties
            dim_layer = layers.Item(self.dimension_settings['dimension_layer'])
            dim_layer.Color = self.dimension_settings['dimension_color']
            
            # Set annotation layer properties  
            ann_layer = layers.Item(self.dimension_settings['annotation_layer'])
            ann_layer.Color = self.dimension_settings['annotation_color']
            
            # Set manufacturing layer properties
            mfg_layer = layers.Item(self.dimension_settings['manufacturing_layer'])
            mfg_layer.Color = self.dimension_settings['fold_line_color']
            
        except Exception as e:
            logger.error(f"Failed to setup dimension layers: {e}")
    
    def create_linear_dimension(self, start_point: List[float], end_point: List[float], 
                              dimension_line_point: List[float], text_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a linear dimension between two points.
        
        Args:
            start_point: [x, y, z] coordinates of dimension start
            end_point: [x, y, z] coordinates of dimension end  
            dimension_line_point: [x, y, z] coordinates for dimension line placement
            text_override: Optional custom dimension text
            
        Returns:
            Dictionary containing dimension information
        """
        try:
            logger.info(f"Creating linear dimension from {start_point} to {end_point}")
            
            # Ensure layers exist
            self.setup_dimension_layers()
            
            # Set current layer to dimensions
            self.doc.ActiveLayer = self.doc.Layers.Item(self.dimension_settings['dimension_layer'])
            
            # Convert points to AutoCAD format
            pt1 = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, start_point)
            pt2 = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, end_point)
            dim_pt = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, dimension_line_point)
            
            # Create aligned dimension (works for both horizontal and vertical)
            dimension = self.model_space.AddDimAligned(pt1, pt2, dim_pt)
            
            # Apply dimension settings
            dimension.TextHeight = self.dimension_settings['text_height']
            dimension.ArrowheadSize = self.dimension_settings['arrow_size']
            dimension.ExtensionLineExtend = self.dimension_settings['extension_line_extend']
            dimension.ExtensionLineOffset = self.dimension_settings['extension_line_offset']
            dimension.TextGap = self.dimension_settings['text_gap']
            
            # Set precision for manufacturing
            dimension.PrimaryUnitsPrecision = self.dimension_settings['precision']
            
            # Override text if specified
            if text_override:
                dimension.TextOverride = text_override
            
            # Calculate actual dimension value
            distance = np.linalg.norm(np.array(end_point) - np.array(start_point))
            
            dimension_info = {
                'handle': dimension.Handle,
                'start_point': start_point,
                'end_point': end_point,
                'dimension_line_point': dimension_line_point,
                'measured_distance': round(distance, self.dimension_settings['precision']),
                'text_override': text_override,
                'units': self.dimension_settings['units'],
                'layer': self.dimension_settings['dimension_layer']
            }
            
            logger.info(f"Linear dimension created: {distance:.{self.dimension_settings['precision']}f} {self.dimension_settings['units']}")
            
            return dimension_info
            
        except Exception as e:
            logger.error(f"Failed to create linear dimension: {e}")
            return {'error': str(e)}
    
    def create_angular_dimension(self, vertex_point: List[float], first_point: List[float], 
                               second_point: List[float], text_point: List[float]) -> Dict[str, Any]:
        """
        Create an angular dimension between two lines.
        
        Args:
            vertex_point: [x, y, z] coordinates of angle vertex
            first_point: [x, y, z] coordinates on first line
            second_point: [x, y, z] coordinates on second line
            text_point: [x, y, z] coordinates for angle text placement
            
        Returns:
            Dictionary containing angle dimension information
        """
        try:
            logger.info(f"Creating angular dimension at vertex {vertex_point}")
            
            # Ensure layers exist
            self.setup_dimension_layers()
            
            # Set current layer to dimensions
            self.doc.ActiveLayer = self.doc.Layers.Item(self.dimension_settings['dimension_layer'])
            
            # Convert points to AutoCAD format
            vertex_pt = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, vertex_point)
            first_pt = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, first_point)
            second_pt = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, second_point)
            text_pt = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, text_point)
            
            # Create angular dimension
            ang_dimension = self.model_space.AddDim3PointAngular(vertex_pt, first_pt, second_pt, text_pt)
            
            # Apply dimension settings
            ang_dimension.TextHeight = self.dimension_settings['text_height']
            ang_dimension.ArrowheadSize = self.dimension_settings['arrow_size']
            
            # Calculate actual angle
            vec1 = np.array(first_point) - np.array(vertex_point)
            vec2 = np.array(second_point) - np.array(vertex_point)
            
            # Normalize vectors
            vec1_norm = vec1 / np.linalg.norm(vec1) if np.linalg.norm(vec1) > 1e-12 else vec1
            vec2_norm = vec2 / np.linalg.norm(vec2) if np.linalg.norm(vec2) > 1e-12 else vec2
            
            # Calculate angle in degrees
            cos_angle = np.clip(np.dot(vec1_norm, vec2_norm), -1, 1)
            angle_degrees = np.degrees(np.arccos(cos_angle))
            
            angle_info = {
                'handle': ang_dimension.Handle,
                'vertex_point': vertex_point,
                'first_point': first_point,
                'second_point': second_point,
                'text_point': text_point,
                'measured_angle': round(angle_degrees, 1),
                'units': 'degrees',
                'layer': self.dimension_settings['dimension_layer']
            }
            
            logger.info(f"Angular dimension created: {angle_degrees:.1f}°")
            
            return angle_info
            
        except Exception as e:
            logger.error(f"Failed to create angular dimension: {e}")
            return {'error': str(e)}
    
    def create_text_annotation(self, insertion_point: List[float], text_content: str, 
                             text_height: Optional[float] = None, rotation: float = 0.0) -> Dict[str, Any]:
        """
        Create a text annotation for manufacturing notes.
        
        Args:
            insertion_point: [x, y, z] coordinates for text placement
            text_content: Text content to display
            text_height: Optional text height (uses default if None)
            rotation: Text rotation angle in degrees
            
        Returns:
            Dictionary containing text annotation information
        """
        try:
            logger.info(f"Creating text annotation: '{text_content[:30]}...'")
            
            # Set current layer to annotations
            self.doc.ActiveLayer = self.doc.Layers.Item(self.dimension_settings['annotation_layer'])
            
            # Use default text height if not specified
            if text_height is None:
                text_height = self.dimension_settings['text_height']
            
            # Convert point to AutoCAD format
            insert_pt = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, insertion_point)
            
            # Create text object
            text_obj = self.model_space.AddText(text_content, insert_pt, text_height)
            
            # Set rotation if specified
            if rotation != 0.0:
                text_obj.Rotation = np.radians(rotation)
            
            # Set color for annotations
            text_obj.Color = self.dimension_settings['annotation_color']
            
            annotation_info = {
                'handle': text_obj.Handle,
                'insertion_point': insertion_point,
                'text_content': text_content,
                'text_height': text_height,
                'rotation': rotation,
                'layer': self.dimension_settings['annotation_layer']
            }
            
            logger.info(f"Text annotation created at {insertion_point}")
            
            return annotation_info
            
        except Exception as e:
            logger.error(f"Failed to create text annotation: {e}")
            return {'error': str(e)}
    
    def create_leader_with_text(self, start_point: List[float], end_point: List[float], 
                              text_content: str) -> Dict[str, Any]:
        """
        Create a leader line with text annotation.
        
        Args:
            start_point: [x, y, z] coordinates where leader points to
            end_point: [x, y, z] coordinates where text is placed
            text_content: Text content for the annotation
            
        Returns:
            Dictionary containing leader information
        """
        try:
            logger.info(f"Creating leader with text: '{text_content[:30]}...'")
            
            # Set current layer to annotations
            self.doc.ActiveLayer = self.doc.Layers.Item(self.dimension_settings['annotation_layer'])
            
            # Create leader points array
            leader_points = [start_point[0], start_point[1], start_point[2],
                           end_point[0], end_point[1], end_point[2]]
            
            points_array = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, leader_points)
            
            # Create leader
            leader = self.model_space.AddLeader(points_array, None, 1)  # 1 = Text annotation type
            
            # Set leader properties
            leader.Color = self.dimension_settings['annotation_color']
            leader.ArrowheadSize = self.dimension_settings['arrow_size']
            
            # Add text annotation at end point
            text_info = self.create_text_annotation(end_point, text_content)
            
            leader_info = {
                'leader_handle': leader.Handle,
                'text_info': text_info,
                'start_point': start_point,
                'end_point': end_point,
                'text_content': text_content,
                'layer': self.dimension_settings['annotation_layer']
            }
            
            logger.info(f"Leader with text created from {start_point} to {end_point}")
            
            return leader_info
            
        except Exception as e:
            logger.error(f"Failed to create leader with text: {e}")
            return {'error': str(e)}
    
    def dimension_unfolded_pattern(self, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically dimension an unfolded pattern for manufacturing.
        
        Args:
            pattern_data: Dictionary containing unfolded pattern information
            
        Returns:
            Dictionary containing all created dimensions and annotations
        """
        try:
            logger.info("Auto-dimensioning unfolded pattern...")
            
            dimensions = []
            annotations = []
            
            # Extract pattern bounds and key points
            if 'pattern_bounds' in pattern_data:
                bounds = pattern_data['pattern_bounds']
                min_pt = bounds['min']
                max_pt = bounds['max']
                
                # Create overall pattern dimensions
                # Width dimension (bottom of pattern)
                width_start = [min_pt[0], min_pt[1] - 10, 0]  # Offset below pattern
                width_end = [max_pt[0], min_pt[1] - 10, 0]
                width_dim_line = [min_pt[0] + (max_pt[0] - min_pt[0])/2, min_pt[1] - 15, 0]
                
                width_dim = self.create_linear_dimension(width_start, width_end, width_dim_line)
                if 'error' not in width_dim:
                    dimensions.append(width_dim)
                
                # Height dimension (left side of pattern)
                height_start = [min_pt[0] - 10, min_pt[1], 0]  # Offset left of pattern
                height_end = [min_pt[0] - 10, max_pt[1], 0]
                height_dim_line = [min_pt[0] - 15, min_pt[1] + (max_pt[1] - min_pt[1])/2, 0]
                
                height_dim = self.create_linear_dimension(height_start, height_end, height_dim_line)
                if 'error' not in height_dim:
                    dimensions.append(height_dim)
            
            # Add fold line dimensions if available
            if 'fold_lines' in pattern_data:
                for i, fold_line in enumerate(pattern_data['fold_lines'][:5]):  # Limit to 5 fold lines
                    try:
                        start_coord = fold_line['start_coord']
                        end_coord = fold_line['end_coord']
                        fold_type = fold_line.get('fold_type', 'fold')
                        fold_angle = fold_line.get('fold_angle', 0)
                        
                        # Create dimension for fold line length
                        offset_dist = 5 + i * 3  # Stagger dimensions
                        mid_x = (start_coord[0] + end_coord[0]) / 2
                        mid_y = (start_coord[1] + end_coord[1]) / 2
                        dim_line_pt = [mid_x, mid_y + offset_dist, 0]
                        
                        fold_dim = self.create_linear_dimension(start_coord, end_coord, dim_line_pt, 
                                                              f"{fold_type.upper()}")
                        if 'error' not in fold_dim:
                            dimensions.append(fold_dim)
                        
                        # Add fold angle annotation if significant
                        if fold_angle > 1.0:
                            angle_text = f"{fold_type.replace('_', ' ').title()}: {fold_angle:.1f}°"
                            angle_annotation = self.create_text_annotation(
                                [mid_x + 5, mid_y + offset_dist + 3, 0], 
                                angle_text,
                                text_height=1.5
                            )
                            if 'error' not in angle_annotation:
                                annotations.append(angle_annotation)
                                
                    except Exception as e:
                        logger.warning(f"Failed to dimension fold line {i}: {e}")
            
            # Add manufacturing notes
            manufacturing_notes = self.generate_manufacturing_notes(pattern_data)
            for note in manufacturing_notes:
                note_annotation = self.create_text_annotation(
                    note['position'], 
                    note['text'],
                    text_height=2.0
                )
                if 'error' not in note_annotation:
                    annotations.append(note_annotation)
            
            # Add title block information
            title_info = self.create_title_block(pattern_data)
            annotations.extend(title_info)
            
            result = {
                'success': True,
                'dimensions_created': len(dimensions),
                'annotations_created': len(annotations),
                'dimensions': dimensions,
                'annotations': annotations,
                'layers_used': [
                    self.dimension_settings['dimension_layer'],
                    self.dimension_settings['annotation_layer']
                ]
            }
            
            logger.info(f"Pattern dimensioning completed: {len(dimensions)} dimensions, {len(annotations)} annotations")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to dimension unfolded pattern: {e}")
            return {'error': str(e)}
    
    def generate_manufacturing_notes(self, pattern_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate manufacturing notes based on pattern analysis."""
        notes = []
        
        try:
            # Material specifications
            if 'manufacturing_data' in pattern_data:
                mfg_data = pattern_data['manufacturing_data']
                
                if 'recommended_material_size' in mfg_data:
                    mat_size = mfg_data['recommended_material_size']
                    notes.append({
                        'position': [10, 10, 0],
                        'text': f"MATERIAL: {mat_size[0]:.1f} x {mat_size[1]:.1f} mm min."
                    })
                
                if 'distortion_acceptable' in mfg_data:
                    distortion_ok = mfg_data['distortion_acceptable']
                    status = "ACCEPTABLE" if distortion_ok else "CHECK TOLERANCES"
                    notes.append({
                        'position': [10, 5, 0],
                        'text': f"DISTORTION: {status}"
                    })
            
            # Surface analysis notes
            if 'distortion_metrics' in pattern_data:
                metrics = pattern_data['distortion_metrics']
                max_distortion = metrics.get('max_angle_distortion', 0)
                notes.append({
                    'position': [10, 0, 0],
                    'text': f"MAX DISTORTION: {max_distortion:.2f}°"
                })
            
            # Method identification
            method = pattern_data.get('method', 'Unknown')
            notes.append({
                'position': [10, -5, 0],
                'text': f"UNFOLDING METHOD: {method}"
            })
            
        except Exception as e:
            logger.warning(f"Error generating manufacturing notes: {e}")
        
        return notes
    
    def create_title_block(self, pattern_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create a basic title block for the drawing."""
        title_annotations = []
        
        try:
            # Title block position (bottom right area)
            title_x = 200
            title_y = -50
            
            # Drawing title
            title_annotations.append(self.create_text_annotation(
                [title_x, title_y, 0],
                "UNFOLDED SURFACE PATTERN",
                text_height=4.0
            ))
            
            # Date and method
            import datetime
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            title_annotations.append(self.create_text_annotation(
                [title_x, title_y - 8, 0],
                f"DATE: {date_str}  METHOD: {pattern_data.get('method', 'N/A')}",
                text_height=2.0
            ))
            
            # Scale and units
            title_annotations.append(self.create_text_annotation(
                [title_x, title_y - 16, 0],
                f"SCALE: 1:1  UNITS: {self.dimension_settings['units']}",
                text_height=2.0
            ))
            
        except Exception as e:
            logger.warning(f"Error creating title block: {e}")
        
        return [ann for ann in title_annotations if 'error' not in ann]


def create_manufacturing_drawing(autocad_instance: Autocad, pattern_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    High-level function to create a complete manufacturing drawing with dimensions.
    
    Args:
        autocad_instance: Connected AutoCAD application  
        pattern_data: Unfolded pattern data with coordinates and analysis
        
    Returns:
        Dictionary containing drawing creation results
    """
    try:
        logger.info("Creating complete manufacturing drawing...")
        
        # Initialize dimensioning system
        dim_system = DimensioningSystem(autocad_instance)
        
        # Auto-dimension the pattern
        dimensioning_result = dim_system.dimension_unfolded_pattern(pattern_data)
        
        if 'error' in dimensioning_result:
            return dimensioning_result
        
        # Zoom to show all elements
        autocad_instance.app.ZoomExtents()
        
        result = {
            'success': True,
            'drawing_type': 'manufacturing_drawing',
            'pattern_method': pattern_data.get('method', 'Unknown'),
            'dimensioning_result': dimensioning_result,
            'total_elements': (dimensioning_result.get('dimensions_created', 0) + 
                             dimensioning_result.get('annotations_created', 0))
        }
        
        logger.info(f"Manufacturing drawing created successfully with {result['total_elements']} elements")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create manufacturing drawing: {e}")
        return {'error': str(e)}