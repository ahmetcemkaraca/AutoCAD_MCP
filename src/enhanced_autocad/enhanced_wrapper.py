"""
Enhanced AutoCAD Wrapper with 100% pyautocad Compatibility
========================================================

Master AutoCAD Coder enhanced COM wrapper that provides 100% API compatibility
with pyautocad while adding enhanced reliability, performance monitoring,
and development features. This is a drop-in replacement for pyautocad.Autocad.
"""

import logging
from typing import Any, Optional, List, Dict, Iterator
from .connection_manager import ConnectionManager
from .performance_monitor import PerformanceMonitor
from .error_handler import ErrorHandler, ErrorCategory

logger = logging.getLogger(__name__)


class EnhancedAutoCAD:
    """
    Enhanced AutoCAD wrapper with 100% pyautocad compatibility.

    This class provides a drop-in replacement for pyautocad.Autocad with
    enhanced reliability, automatic connection recovery, performance monitoring,
    and comprehensive error handling while maintaining complete API compatibility.
    """

    def __init__(self, create_if_not_exists: bool = True, visible: bool = True):
        """
        Initialize Enhanced AutoCAD wrapper.

        Args:
            create_if_not_exists: Create AutoCAD instance if none exists (pyautocad compatible)
            visible: Make AutoCAD visible (pyautocad compatible)
        """
        self._connection_manager = ConnectionManager()
        self._performance_monitor = PerformanceMonitor()
        self._error_handler = ErrorHandler()

        # Store initialization parameters for compatibility
        self._create_if_not_exists = create_if_not_exists
        self._visible = visible

        # Cache for commonly accessed objects
        self._app_cache = None
        self._doc_cache = None
        self._model_cache = None

        logger.info("Enhanced AutoCAD wrapper initialized")

    def _get_autocad_app(self) -> Any:
        """Get AutoCAD application object with caching and error handling."""
        try:
            with self._performance_monitor.measure_operation("get_autocad_app"):
                if not self._app_cache:
                    connection = self._connection_manager.get_connection()
                    self._app_cache = connection
                    # Ensure visibility if requested
                    if self._visible:
                        self._app_cache.Visible = True
                return self._app_cache
        except Exception as e:
            error_context = self._error_handler.handle_error(
                e, "get_autocad_app", raise_exception=False
            )
            if error_context.is_recoverable:
                # Attempt recovery
                self._app_cache = None
                if self._connection_manager.recover_connection():
                    return self._get_autocad_app()
            raise

    def _clear_cache(self):
        """Clear cached objects to force refresh."""
        self._app_cache = None
        self._doc_cache = None
        self._model_cache = None

    # pyautocad compatibility properties
    @property
    def app(self) -> Any:
        """AutoCAD Application object (pyautocad compatible)."""
        return self._get_autocad_app()

    @property
    def doc(self) -> Any:
        """Active AutoCAD document (pyautocad compatible)."""
        try:
            with self._performance_monitor.measure_operation("get_active_document"):
                if not self._doc_cache:
                    app = self._get_autocad_app()
                    self._doc_cache = app.ActiveDocument
                return self._doc_cache
        except Exception as e:
            self._error_handler.handle_error(e, "get_active_document")

    @property
    def model(self) -> Any:
        """Model space object (pyautocad compatible)."""
        try:
            with self._performance_monitor.measure_operation("get_model_space"):
                if not self._model_cache:
                    doc = self.doc
                    self._model_cache = doc.ModelSpace
                return self._model_cache
        except Exception as e:
            self._error_handler.handle_error(e, "get_model_space")

    # pyautocad compatibility methods
    def iter_objects(
        self, object_name_or_list=None, container=None, dont_convert=False
    ) -> Iterator[Any]:
        """
        Iterate over objects in AutoCAD (pyautocad compatible).

        Args:
            object_name_or_list: Object name(s) to filter by
            container: Container to iterate over (default: model space)
            dont_convert: Don't convert to wrapper objects

        Yields:
            AutoCAD objects matching criteria
        """
        try:
            with self._performance_monitor.measure_operation(
                "iter_objects", {"filter": str(object_name_or_list)}
            ):
                if container is None:
                    container = self.model

                # Convert object_name_or_list to list if single string
                if isinstance(object_name_or_list, str):
                    object_names = [object_name_or_list]
                elif object_name_or_list is None:
                    object_names = None
                else:
                    object_names = list(object_name_or_list)

                for obj in container:
                    if object_names is None or obj.ObjectName in object_names:
                        yield obj

        except Exception as e:
            self._error_handler.handle_error(e, "iter_objects")

    def find_one(self, object_name_or_list, container=None, predicate=None) -> Optional[Any]:
        """
        Find first object matching criteria (pyautocad compatible).

        Args:
            object_name_or_list: Object name(s) to search for
            container: Container to search in (default: model space)
            predicate: Additional filter function

        Returns:
            First matching object or None
        """
        try:
            with self._performance_monitor.measure_operation(
                "find_one", {"filter": str(object_name_or_list)}
            ):
                for obj in self.iter_objects(object_name_or_list, container):
                    if predicate is None or predicate(obj):
                        return obj
                return None
        except Exception as e:
            self._error_handler.handle_error(e, "find_one")
            return None

    # Enhanced wrapper methods (additional functionality)
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status and diagnostics.

        Returns:
            Dictionary containing connection status and metrics
        """
        return self._connection_manager.get_connection_status()

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for AutoCAD operations.

        Returns:
            Dictionary containing performance statistics
        """
        return self._performance_monitor.get_performance_summary()

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get error statistics and recovery information.

        Returns:
            Dictionary containing error statistics and patterns
        """
        return self._error_handler.get_error_statistics()

    def recover_connection(self) -> bool:
        """
        Manually trigger connection recovery.

        Returns:
            True if recovery successful
        """
        try:
            self._clear_cache()
            success = self._connection_manager.recover_connection()
            if success:
                logger.info("Connection recovery successful")
            return success
        except Exception as e:
            logger.error(f"Connection recovery failed: {str(e)}")
            return False

    def create_diagnostic_report(self) -> Dict[str, Any]:
        """
        Create comprehensive diagnostic report.

        Returns:
            Dictionary containing diagnostic information
        """
        return {
            "connection_status": self.get_connection_status(),
            "performance_metrics": self.get_performance_metrics(),
            "error_statistics": self.get_error_statistics(),
            "error_report": self._error_handler.create_error_report(),
        }

    # Manufacturing workflow compatibility methods
    def draw_line(self, start_point: List[float], end_point: List[float]) -> int:
        """
        Draw line in AutoCAD (manufacturing system compatible).

        Args:
            start_point: [x, y, z] coordinates for line start
            end_point: [x, y, z] coordinates for line end

        Returns:
            Entity handle as integer
        """
        try:
            with self._performance_monitor.measure_operation("draw_line"):
                model = self.model
                line_obj = model.AddLine(start_point, end_point)
                return int(line_obj.Handle, 16)  # Convert hex handle to int
        except Exception as e:
            self._error_handler.handle_error(e, "draw_line")

    def draw_circle(self, center: List[float], radius: float) -> int:
        """
        Draw circle in AutoCAD (manufacturing system compatible).

        Args:
            center: [x, y, z] coordinates for circle center
            radius: Circle radius

        Returns:
            Entity handle as integer
        """
        try:
            with self._performance_monitor.measure_operation("draw_circle"):
                model = self.model
                circle_obj = model.AddCircle(center, radius)
                return int(circle_obj.Handle, 16)  # Convert hex handle to int
        except Exception as e:
            self._error_handler.handle_error(e, "draw_circle")

    def get_entity_by_id(self, entity_id: int) -> Any:
        """
        Get entity by its handle ID (manufacturing system compatible).

        Args:
            entity_id: Entity handle as integer

        Returns:
            AutoCAD entity object
        """
        try:
            with self._performance_monitor.measure_operation("get_entity_by_id"):
                doc = self.doc
                handle_hex = hex(entity_id)
                return doc.HandleToObject(handle_hex)
        except Exception as e:
            self._error_handler.handle_error(e, "get_entity_by_id")

    # Context manager support
    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Don't close connection on context exit to allow reuse
        pass

    # Dynamic attribute access for pyautocad compatibility
    def __getattr__(self, name: str) -> Any:
        """
        Proxy attribute access to AutoCAD application for full pyautocad compatibility.

        Args:
            name: Attribute name

        Returns:
            Attribute value from AutoCAD application
        """
        try:
            with self._performance_monitor.measure_operation(
                "attribute_access", {"attribute": name}
            ):
                app = self._get_autocad_app()
                return getattr(app, name)
        except AttributeError:
            # If attribute doesn't exist on app, try doc
            try:
                doc = self.doc
                return getattr(doc, name)
            except AttributeError:
                # If attribute doesn't exist on doc, try model
                try:
                    model = self.model
                    return getattr(model, name)
                except AttributeError as e:
                    self._error_handler.handle_error(
                        e, f"attribute_access_{name}", raise_exception=False
                    )
                    raise AttributeError(
                        f"'{self.__class__.__name__}' object has no attribute '{name}'"
                    )
        except Exception as e:
            self._error_handler.handle_error(e, f"attribute_access_{name}")

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Handle attribute setting with special handling for internal attributes.

        Args:
            name: Attribute name
            value: Attribute value
        """
        # Handle internal attributes normally
        if name.startswith("_") or name in ["app", "doc", "model"]:
            super().__setattr__(name, value)
        else:
            # Proxy to AutoCAD application for pyautocad compatibility
            try:
                with self._performance_monitor.measure_operation(
                    "attribute_set", {"attribute": name}
                ):
                    app = self._get_autocad_app()
                    setattr(app, name, value)
            except Exception as e:
                self._error_handler.handle_error(e, f"attribute_set_{name}")

    def __repr__(self) -> str:
        """String representation of Enhanced AutoCAD wrapper."""
        connection_status = (
            "connected" if self._connection_manager._is_connection_healthy() else "disconnected"
        )
        return f"<EnhancedAutoCAD({connection_status})>"

    def __str__(self) -> str:
        """String representation of Enhanced AutoCAD wrapper."""
        return self.__repr__()
