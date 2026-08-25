"""
Decorators for AutoCAD MCP Server error handling and validation.
"""

import functools
import logging
import time
from typing import Any, Callable, Dict

from flask import jsonify, request
import pyautocad
from pyautocad import Autocad
from .utils import get_autocad_instance

logger = logging.getLogger(__name__)


def handle_autocad_errors(func: Callable) -> Callable:
    """
    Decorator to handle AutoCAD COM errors and provide consistent error responses.
    
    This decorator wraps Flask route handlers to catch and properly format
    AutoCAD COM exceptions, connection errors, and other common failures.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        
        try:
            # Execute the wrapped function
            result = func(*args, **kwargs)
            
            # Add execution time to successful responses
            if isinstance(result, tuple) and len(result) == 2:
                response_data, status_code = result
                if isinstance(response_data.json, dict):
                    response_data.json['execution_time'] = time.time() - start_time
            elif hasattr(result, 'json') and isinstance(result.json, dict):
                result.json['execution_time'] = time.time() - start_time
                
            return result
            
        except pyautocad.api.COMError as e:
            logger.error(f"AutoCAD COM error in {func.__name__}: {e}")
            return jsonify({
                'success': False,
                'error': 'AutoCAD operation failed',
                'error_code': 'AUTOCAD_COM_ERROR',
                'details': {
                    'com_error_code': getattr(e, 'hresult', None),
                    'description': str(e),
                    'suggestion': 'Ensure AutoCAD is running and the drawing is not corrupted'
                },
                'execution_time': time.time() - start_time
            }), 500
            
        except ConnectionError as e:
            logger.error(f"AutoCAD connection error in {func.__name__}: {e}")
            return jsonify({
                'success': False,
                'error': 'Cannot connect to AutoCAD',
                'error_code': 'AUTOCAD_NOT_CONNECTED',
                'details': {
                    'description': str(e),
                    'suggestion': 'Start AutoCAD 2025 and ensure it is visible'
                },
                'execution_time': time.time() - start_time
            }), 503
            
        except ValueError as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            return jsonify({
                'success': False,
                'error': 'Invalid input parameters',
                'error_code': 'INVALID_PARAMETERS',
                'details': {
                    'validation_error': str(e),
                    'suggestion': 'Check input parameters match API specification'
                },
                'execution_time': time.time() - start_time
            }), 400
            
        except TimeoutError as e:
            logger.error(f"Timeout error in {func.__name__}: {e}")
            return jsonify({
                'success': False,
                'error': 'Operation timed out',
                'error_code': 'TIMEOUT_ERROR',
                'details': {
                    'description': str(e),
                    'suggestion': 'Try reducing complexity or increasing timeout'
                },
                'execution_time': time.time() - start_time
            }), 408
            
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'error_code': 'INTERNAL_SERVER_ERROR',
                'details': {
                    'description': 'An unexpected error occurred',
                    'suggestion': 'Contact support if the problem persists'
                },
                'execution_time': time.time() - start_time
            }), 500
            
    return wrapper


def validate_json_request(required_fields: list = None) -> Callable:
    """
    Decorator to validate JSON request data and required fields.
    
    Args:
        required_fields: List of required field names in request JSON
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Request must be JSON',
                    'error_code': 'INVALID_CONTENT_TYPE',
                    'details': {
                        'suggestion': 'Set Content-Type header to application/json'
                    }
                }), 400
                
            data = request.get_json()
            if data is None:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data',
                    'error_code': 'INVALID_JSON',
                    'details': {
                        'suggestion': 'Ensure request body contains valid JSON'
                    }
                }), 400
                
            # Check required fields
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required fields: {", ".join(missing_fields)}',
                        'error_code': 'MISSING_REQUIRED_FIELDS',
                        'details': {
                            'missing_fields': missing_fields,
                            'required_fields': required_fields,
                            'suggestion': 'Include all required fields in request'
                        }
                    }), 400
                    
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_api_call(func: Callable) -> Callable:
    """
    Decorator to log API calls with request parameters and response status.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        
        # Log incoming request
        logger.info(f"API Call: {request.method} {request.path}")
        if request.is_json:
            logger.debug(f"Request data: {request.get_json()}")
            
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Determine status code
            status_code = 200
            if isinstance(result, tuple) and len(result) == 2:
                _, status_code = result
                
            logger.info(f"API Response: {request.method} {request.path} - "
                       f"Status: {status_code}, Time: {execution_time:.3f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"API Error: {request.method} {request.path} - "
                        f"Error: {str(e)}, Time: {execution_time:.3f}s")
            raise
            
    return wrapper


def require_autocad_connection(func: Callable) -> Callable:
    """
    Decorator to ensure AutoCAD connection exists before executing function.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            # Try to get AutoCAD instance using our updated connection method
            acad = get_autocad_instance()
            if acad is None:
                raise ConnectionError("AutoCAD not running")
                
            # Verify connection with a simple operation
            try:
                _ = acad.doc.Name  # This will fail if connection is broken
            except:
                # Fallback: try to access app directly
                _ = acad.app.Name
            
            return func(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"AutoCAD connection check failed: {e}")
            return jsonify({
                'success': False,
                'error': 'AutoCAD not connected',
                'error_code': 'AUTOCAD_NOT_CONNECTED',
                'details': {
                    'description': str(e),
                    'suggestion': 'Start AutoCAD 2025 and ensure it is visible'
                }
            }), 503
            
    return wrapper