"""
MCP Client implementation for AutoCAD MCP Server communication.
"""

import requests
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

from .exceptions import (
    McpConnectionError,
    McpOperationError,
    McpTimeoutError,
    McpValidationError
)
from .types import Point3D, EntityInfo, UnfoldResult, LayoutResult, EntityId


logger = logging.getLogger(__name__)


class McpClient:
    """Client for communicating with AutoCAD MCP Server."""
    
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
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        if debug:
            logging.basicConfig(level=logging.DEBUG)
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def close(self) -> None:
        """Close client session and cleanup resources."""
        self.session.close()
        
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to MCP server with error handling.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            data: Request data for POST requests
            timeout: Override default timeout
            
        Returns:
            Response data as dictionary
            
        Raises:
            McpConnectionError: Server not reachable
            McpOperationError: Server returned error
            McpTimeoutError: Request timed out
        """
        url = urljoin(self.base_url, endpoint)
        request_timeout = timeout or self.timeout
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=request_timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=request_timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=request_timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            result = response.json()
            
            # Check for application-level errors
            if isinstance(result, dict) and result.get('success') is False:
                raise McpOperationError(
                    result.get('error', 'Unknown error'),
                    error_code=result.get('error_code'),
                    details=result.get('details', {})
                )
                
            return result
            
        except requests.exceptions.ConnectionError as e:
            raise McpConnectionError(
                "Cannot connect to MCP server. Ensure server is running.",
                error_code="CONNECTION_FAILED",
                details={'url': url, 'original_error': str(e)}
            )
        except requests.exceptions.Timeout as e:
            raise McpTimeoutError(
                f"Request timed out after {request_timeout} seconds",
                error_code="REQUEST_TIMEOUT",
                details={'timeout': request_timeout, 'url': url}
            )
        except requests.exceptions.RequestException as e:
            raise McpOperationError(
                f"HTTP request failed: {str(e)}",
                error_code="HTTP_ERROR",
                details={'url': url, 'original_error': str(e)}
            )
            
    # Connection Management
    
    def is_connected(self) -> bool:
        """Check if server is reachable and healthy."""
        try:
            response = self._make_request('GET', '/health')
            return response.get('status') == 'ok'
        except Exception:
            return False
            
    def get_server_status(self) -> Dict[str, Any]:
        """Get server health and version information."""
        return self._make_request('GET', '/health')
        
    def get_autocad_status(self) -> Dict[str, Any]:
        """Get AutoCAD connection status and version."""
        return self._make_request('GET', '/acad-status')
        
    # Basic CAD Operations
    
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
        """
        data = {
            'start_point': start_point,
            'end_point': end_point,
            'layer': layer
        }
        response = self._make_request('POST', '/draw/line', data)
        return EntityInfo(
            id=response['entity_id'],
            type=response['entity_type'],
            layer=layer
        )
        
    def draw_circle(
        self,
        center_point: Point3D,
        radius: float,
        layer: str = "0"
    ) -> EntityInfo:
        """Create a circle in AutoCAD."""
        data = {
            'center_point': center_point,
            'radius': radius,
            'layer': layer
        }
        response = self._make_request('POST', '/draw/circle', data)
        return EntityInfo(
            id=response['entity_id'],
            type=response['entity_type'],
            layer=layer,
            radius=radius
        )
        
    # 3D Operations
    
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
        data = {
            'profile_id': profile_id,
            'height': height,
            'taper_angle': taper_angle
        }
        response = self._make_request('POST', '/draw/extrude', data)
        return EntityInfo(
            id=response['entity_id'],
            type=response['entity_type'],
            layer="0",  # Default layer for solids
            volume=response.get('volume')
        )
        
    # Surface Unfolding
    
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
        """
        data = {
            'entity_id': entity_id,
            'tolerance': tolerance,
            'method': method,
            'include_markings': include_markings,
            'output_layer': output_layer
        }
        response = self._make_request('POST', '/unfold_surface', data, timeout=60.0)
        
        return UnfoldResult(
            pattern_id=response['pattern_id'],
            entity_type=response['entity_type'],
            deviation=response['deviation'],
            original_area=response['original_area'],
            unfolded_area=response['unfolded_area'],
            fold_lines=response.get('fold_lines', []),
            cut_lines=response.get('cut_lines', []),
            method_used=response.get('method_used', method),
            success=response['success'],
            warnings=response.get('warnings', []),
            execution_time=response.get('execution_time', 0.0)
        )
        
    # Entity Management
    
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
        params = {}
        if entity_type:
            params['entity_type'] = entity_type
        if layer:
            params['layer'] = layer
            
        # Add query parameters to URL
        endpoint = '/entities'
        if params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            endpoint = f"{endpoint}?{query_string}"
            
        response = self._make_request('GET', endpoint)
        entities = []
        
        for entity_data in response.get('entities', []):
            entities.append(EntityInfo(
                id=entity_data['id'],
                type=entity_data['type'],
                layer=entity_data['layer'],
                color=entity_data['color'],
                length=entity_data.get('length'),
                radius=entity_data.get('radius'),
                area=entity_data.get('area'),
                volume=entity_data.get('volume')
            ))
            
        return entities
        
    def delete_entity(self, entity_id: int) -> bool:
        """Delete entity from drawing."""
        response = self._make_request('DELETE', f'/entities/{entity_id}')
        return response.get('success', False)