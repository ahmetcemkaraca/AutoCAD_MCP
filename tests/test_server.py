
import pytest
from unittest.mock import patch, MagicMock
from src.server import app

@pytest.fixture
def client():
    """A test client for the app."""
    return app.test_client()


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'ok'}


@patch('src.server.get_autocad_instance')
def test_acad_status_connected(mock_get_acad, client):
    """Test the acad-status endpoint when AutoCAD is connected."""
    mock_acad = MagicMock()
    mock_acad.app.Version = "2025.0"
    mock_get_acad.return_value = mock_acad

    response = client.get('/acad-status')
    assert response.status_code == 200
    assert response.json == {'status': 'connected', 'version': '2025.0'}


@patch('src.server.get_autocad_instance')
def test_acad_status_not_connected(mock_get_acad, client):
    """Test the acad-status endpoint when AutoCAD is not connected."""
    mock_get_acad.return_value = None

    response = client.get('/acad-status')
    assert response.status_code == 503
    assert response.json == {'status': 'not_connected'}
