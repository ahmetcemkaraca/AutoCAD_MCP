"""
Unit tests for basic drawing operations.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.server import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture  
def mock_autocad():
    """Mock AutoCAD instance for testing."""
    with patch('pyautocad.Autocad') as mock_autocad_class, \
         patch('src.utils.get_autocad_instance') as mock_get_acad:
        
        # Mock the AutoCAD instance with all necessary properties
        mock_acad = Mock()
        mock_acad.model = Mock()
        mock_acad.doc = Mock()
        mock_acad.doc.Name = "Test Drawing"
        mock_acad.Visible = True
        mock_acad.app = Mock()
        mock_acad.app.Version = "2025.0"
        
        # Make both the class and get_autocad_instance return our mock
        mock_autocad_class.return_value = mock_acad
        mock_get_acad.return_value = mock_acad
        
        yield mock_acad


class TestDrawLine:
    """Test cases for /draw/line endpoint."""
    
    def test_draw_line_success(self, client, mock_autocad):
        """Test successful line creation."""
        # Setup mock
        mock_line = Mock()
        mock_line.ObjectID = 12345
        mock_line.ObjectName = "AcDbLine"
        mock_line.Layer = "0"
        mock_line.Length = 141.42
        mock_autocad.model.AddLine.return_value = mock_line
        
        # Test data
        data = {
            'start_point': [0, 0, 0],
            'end_point': [100, 100, 0],
            'layer': '0'
        }
        
        response = client.post('/draw/line', 
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        
        assert response_data['success'] is True
        assert response_data['entity_id'] == 12345
        assert response_data['entity_type'] == "AcDbLine"
        assert response_data['layer'] == "0"
        assert response_data['start_point'] == [0, 0, 0]
        assert response_data['end_point'] == [100, 100, 0]
        assert 'execution_time' in response_data
        
        # Verify AutoCAD was called correctly
        mock_autocad.model.AddLine.assert_called_once_with([0, 0, 0], [100, 100, 0])
        assert mock_line.Layer == "0"
    
    def test_draw_line_missing_fields(self, client):
        """Test line creation with missing required fields."""
        data = {'start_point': [0, 0, 0]}  # Missing end_point
        
        response = client.post('/draw/line',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'MISSING_REQUIRED_FIELDS'
        assert 'end_point' in response_data['error']
    
    def test_draw_line_invalid_point(self, client):
        """Test line creation with invalid point format."""
        data = {
            'start_point': [0, 0],  # Missing Z coordinate
            'end_point': [100, 100, 0]
        }
        
        response = client.post('/draw/line',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'INVALID_PARAMETERS'
    
    def test_draw_line_invalid_json(self, client):
        """Test line creation with invalid JSON."""
        response = client.post('/draw/line',
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'INVALID_CONTENT_TYPE'
    
    @patch('src.utils.get_autocad_instance')
    def test_draw_line_autocad_error(self, mock_get_acad, client):
        """Test line creation when AutoCAD connection fails."""
        mock_get_acad.side_effect = ConnectionError("AutoCAD not running")
        
        data = {
            'start_point': [0, 0, 0],
            'end_point': [100, 100, 0]
        }
        
        response = client.post('/draw/line',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 503
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'AUTOCAD_NOT_CONNECTED'


class TestDrawCircle:
    """Test cases for /draw/circle endpoint."""
    
    def test_draw_circle_success(self, client, mock_autocad):
        """Test successful circle creation."""
        # Setup mock
        mock_circle = Mock()
        mock_circle.ObjectID = 12346
        mock_circle.ObjectName = "AcDbCircle"
        mock_circle.Layer = "0"
        mock_circle.Area = 78.54
        mock_autocad.model.AddCircle.return_value = mock_circle
        
        # Test data
        data = {
            'center_point': [50, 50, 0],
            'radius': 25.0,
            'layer': 'CIRCLES'
        }
        
        response = client.post('/draw/circle',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        
        assert response_data['success'] is True
        assert response_data['entity_id'] == 12346
        assert response_data['entity_type'] == "AcDbCircle"
        assert response_data['center_point'] == [50, 50, 0]
        assert response_data['radius'] == 25.0
        assert response_data['circumference'] == pytest.approx(157.08, rel=1e-2)
        
        # Verify AutoCAD was called correctly
        mock_autocad.model.AddCircle.assert_called_once_with([50, 50, 0], 25.0)
        assert mock_circle.Layer == "CIRCLES"
    
    def test_draw_circle_negative_radius(self, client):
        """Test circle creation with negative radius."""
        data = {
            'center_point': [0, 0, 0],
            'radius': -10.0
        }
        
        response = client.post('/draw/circle',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'INVALID_PARAMETERS'
        assert 'positive' in response_data['error']
    
    def test_draw_circle_missing_radius(self, client):
        """Test circle creation without radius."""
        data = {'center_point': [0, 0, 0]}  # Missing radius
        
        response = client.post('/draw/circle',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'MISSING_REQUIRED_FIELDS'


class TestDrawPolyline:
    """Test cases for /draw/polyline endpoint."""
    
    def test_draw_polyline_success(self, client, mock_autocad):
        """Test successful polyline creation."""
        # Setup mock
        mock_polyline = Mock()
        mock_polyline.ObjectID = 12347
        mock_polyline.ObjectName = "AcDbPolyline"
        mock_polyline.Layer = "0"
        mock_polyline.Length = 300.0
        mock_polyline.Closed = False
        mock_autocad.model.AddLightWeightPolyline.return_value = mock_polyline
        
        # Test data
        data = {
            'points': [[0, 0, 0], [100, 0, 0], [100, 100, 0], [0, 100, 0]],
            'closed': False,
            'layer': 'POLYLINES'
        }
        
        response = client.post('/draw/polyline',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        
        assert response_data['success'] is True
        assert response_data['entity_id'] == 12347
        assert response_data['entity_type'] == "AcDbPolyline"
        assert response_data['point_count'] == 4
        assert response_data['closed'] is False
        
        # Verify AutoCAD was called
        mock_autocad.model.AddLightWeightPolyline.assert_called_once()
        assert mock_polyline.Layer == "POLYLINES"
        assert mock_polyline.Closed is False
    
    def test_draw_polyline_closed(self, client, mock_autocad):
        """Test closed polyline creation."""
        # Setup mock
        mock_polyline = Mock()
        mock_polyline.ObjectID = 12348
        mock_polyline.ObjectName = "AcDbPolyline"
        mock_polyline.Layer = "0"
        mock_polyline.Length = 400.0
        mock_polyline.Area = 10000.0
        mock_polyline.Closed = True
        mock_autocad.model.AddLightWeightPolyline.return_value = mock_polyline
        
        # Test data - square polyline
        data = {
            'points': [[0, 0, 0], [100, 0, 0], [100, 100, 0], [0, 100, 0]],
            'closed': True
        }
        
        response = client.post('/draw/polyline',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        
        assert response_data['success'] is True
        assert response_data['closed'] is True
        assert mock_polyline.Closed is True
    
    def test_draw_polyline_insufficient_points(self, client):
        """Test polyline creation with insufficient points."""
        data = {
            'points': [[0, 0, 0]]  # Only one point
        }
        
        response = client.post('/draw/polyline',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'INVALID_PARAMETERS'
        assert 'at least 2 points' in response_data['error']
    
    def test_draw_polyline_invalid_point(self, client):
        """Test polyline creation with invalid point in array."""
        data = {
            'points': [[0, 0, 0], [100, 'invalid', 0]]  # Invalid Y coordinate
        }
        
        response = client.post('/draw/polyline',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'INVALID_PARAMETERS'
        assert 'index 1' in response_data['error']


class TestDrawRectangle:
    """Test cases for /draw/rectangle endpoint."""
    
    def test_draw_rectangle_success(self, client, mock_autocad):
        """Test successful rectangle creation."""
        # Setup mock
        mock_rectangle = Mock()
        mock_rectangle.ObjectID = 12349
        mock_rectangle.ObjectName = "AcDbPolyline"
        mock_rectangle.Layer = "0"
        mock_rectangle.Area = 5000.0
        mock_rectangle.Length = 300.0
        mock_rectangle.Closed = True
        mock_autocad.model.AddLightWeightPolyline.return_value = mock_rectangle
        
        # Test data
        data = {
            'corner1': [0, 0, 0],
            'corner2': [100, 50, 0],
            'layer': 'RECTANGLES'
        }
        
        response = client.post('/draw/rectangle',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        
        assert response_data['success'] is True
        assert response_data['entity_id'] == 12349
        assert response_data['entity_type'] == "AcDbPolyline"
        assert response_data['width'] == 100.0
        assert response_data['height'] == 50.0
        assert response_data['corner1'] == [0, 0, 0]
        assert response_data['corner2'] == [100, 50, 0]
        
        # Verify AutoCAD was called
        mock_autocad.model.AddLightWeightPolyline.assert_called_once()
        assert mock_rectangle.Layer == "RECTANGLES"
        assert mock_rectangle.Closed is True
    
    def test_draw_rectangle_negative_dimensions(self, client, mock_autocad):
        """Test rectangle creation with negative dimensions (should work)."""
        # Setup mock
        mock_rectangle = Mock()
        mock_rectangle.ObjectID = 12350
        mock_rectangle.ObjectName = "AcDbPolyline"
        mock_rectangle.Layer = "0"
        mock_autocad.model.AddLightWeightPolyline.return_value = mock_rectangle
        
        # Test data with corner2 having smaller coordinates than corner1
        data = {
            'corner1': [100, 100, 0],
            'corner2': [0, 0, 0]
        }
        
        response = client.post('/draw/rectangle',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        
        assert response_data['success'] is True
        assert response_data['width'] == 100.0  # abs(0 - 100)
        assert response_data['height'] == 100.0  # abs(0 - 100)
    
    def test_draw_rectangle_missing_corner(self, client):
        """Test rectangle creation with missing corner."""
        data = {'corner1': [0, 0, 0]}  # Missing corner2
        
        response = client.post('/draw/rectangle',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'MISSING_REQUIRED_FIELDS'
        assert 'corner2' in response_data['error']


class TestCommonScenarios:
    """Test common scenarios across all drawing operations."""
    
    def test_invalid_layer_name(self, client):
        """Test drawing operation with invalid layer name."""
        data = {
            'start_point': [0, 0, 0],
            'end_point': [100, 100, 0],
            'layer': 'LAYER<INVALID>'  # Contains invalid character
        }
        
        response = client.post('/draw/line',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'INVALID_PARAMETERS'
        assert 'invalid character' in response_data['error']
    
    def test_no_content_type_header(self, client):
        """Test request without proper Content-Type header."""
        data = {'start_point': [0, 0, 0], 'end_point': [100, 100, 0]}
        
        response = client.post('/draw/line',
                             data=json.dumps(data))  # No content_type specified
        
        assert response.status_code == 400
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'INVALID_CONTENT_TYPE'
    
    @patch('src.decorators.require_autocad_connection')
    def test_autocad_connection_required(self, mock_require_connection, client):
        """Test that AutoCAD connection is required for drawing operations."""
        # Mock the decorator to simulate connection failure
        def mock_decorator(func):
            def wrapper(*args, **kwargs):
                from flask import jsonify
                return jsonify({
                    'success': False,
                    'error': 'AutoCAD not connected',
                    'error_code': 'AUTOCAD_NOT_CONNECTED'
                }), 503
            return wrapper
        
        mock_require_connection.return_value = mock_decorator
        
        data = {
            'start_point': [0, 0, 0],
            'end_point': [100, 100, 0]
        }
        
        response = client.post('/draw/line',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 503
        response_data = response.get_json()
        
        assert response_data['success'] is False
        assert response_data['error_code'] == 'AUTOCAD_NOT_CONNECTED'


# Integration test markers for pytest
@pytest.mark.integration
class TestDrawingIntegration:
    """Integration tests that require actual AutoCAD connection."""
    
    def test_real_autocad_line_creation(self, client):
        """
        Integration test for line creation with real AutoCAD.
        This test will be skipped if AutoCAD is not running.
        """
        # This would only run with actual AutoCAD instance
        pytest.skip("Integration test - requires AutoCAD 2025 running")
    
    def test_real_autocad_circle_creation(self, client):
        """Integration test for circle creation with real AutoCAD."""
        pytest.skip("Integration test - requires AutoCAD 2025 running")