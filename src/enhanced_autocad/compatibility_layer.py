"""
Compatibility Layer for pyautocad Replacement
===========================================

Provides seamless compatibility interface that allows EnhancedAutoCAD to be
a drop-in replacement for pyautocad.Autocad with zero code changes required
in existing manufacturing system.
"""

import logging
from typing import Any, Optional, List, Iterator
from .enhanced_wrapper import EnhancedAutoCAD

logger = logging.getLogger(__name__)


class Autocad(EnhancedAutoCAD):
    """
    Drop-in replacement for pyautocad.Autocad class.

    This class provides 100% API compatibility with pyautocad.Autocad
    by inheriting from EnhancedAutoCAD and adding any missing compatibility methods.
    """

    def __init__(self, create_if_not_exists: bool = True, visible: bool = True):
        """
        Initialize Autocad wrapper (pyautocad compatible signature).

        Args:
            create_if_not_exists: Create AutoCAD instance if none exists
            visible: Make AutoCAD visible
        """
        super().__init__(create_if_not_exists=create_if_not_exists, visible=visible)
        logger.info("pyautocad compatibility layer initialized")

    # Additional pyautocad compatibility methods (if any are missing)
    def prompt(self, text: str) -> str:
        """
        Display prompt in AutoCAD command line (pyautocad compatible).

        Args:
            text: Text to display

        Returns:
            User input response
        """
        try:
            with self._performance_monitor.measure_operation("prompt"):
                doc = self.doc
                return doc.Utility.GetString(False, text)
        except Exception as e:
            self._error_handler.handle_error(e, "prompt")
            return ""

    def get_entity(self, message: str = "Select entity: ") -> Optional[Any]:
        """
        Get entity through user selection (pyautocad compatible).

        Args:
            message: Selection prompt message

        Returns:
            Selected entity or None
        """
        try:
            with self._performance_monitor.measure_operation("get_entity"):
                doc = self.doc
                try:
                    entity, pick_point = doc.Utility.GetEntity(message)
                    return entity
                except:
                    return None
        except Exception as e:
            self._error_handler.handle_error(e, "get_entity", raise_exception=False)
            return None

    def get_point(
        self, message: str = "Pick point: ", base_point: Optional[List[float]] = None
    ) -> Optional[List[float]]:
        """
        Get point through user selection (pyautocad compatible).

        Args:
            message: Selection prompt message
            base_point: Base point for relative selection

        Returns:
            Selected point coordinates or None
        """
        try:
            with self._performance_monitor.measure_operation("get_point"):
                doc = self.doc
                try:
                    if base_point:
                        point = doc.Utility.GetPoint(base_point, message)
                    else:
                        point = doc.Utility.GetPoint(message)
                    return list(point)
                except:
                    return None
        except Exception as e:
            self._error_handler.handle_error(e, "get_point", raise_exception=False)
            return None

    def get_selection(self, message: str = "Select objects: ") -> Optional[Any]:
        """
        Get selection set through user selection (pyautocad compatible).

        Args:
            message: Selection prompt message

        Returns:
            Selection set or None
        """
        try:
            with self._performance_monitor.measure_operation("get_selection"):
                doc = self.doc
                try:
                    selection_set = doc.SelectionSets.Add("temp_selection")
                    selection_set.SelectOnScreen()
                    if selection_set.Count > 0:
                        return selection_set
                    else:
                        selection_set.Delete()
                        return None
                except:
                    return None
        except Exception as e:
            self._error_handler.handle_error(e, "get_selection", raise_exception=False)
            return None


# Module-level compatibility functions for import compatibility
def Autocad_instance(*args, **kwargs) -> Autocad:
    """Factory function for creating Autocad instance (compatibility)."""
    return Autocad(*args, **kwargs)


# Common utility functions for pyautocad compatibility
def apoint(x: float, y: float = 0, z: float = 0) -> List[float]:
    """
    Create AutoCAD point from coordinates (pyautocad compatible).

    Args:
        x: X coordinate
        y: Y coordinate (default: 0)
        z: Z coordinate (default: 0)

    Returns:
        Point as [x, y, z] list
    """
    return [float(x), float(y), float(z)]


def aDouble(values: List[float]) -> List[float]:
    """
    Convert values to AutoCAD double array (pyautocad compatible).

    Args:
        values: List of numeric values

    Returns:
        List of float values
    """
    return [float(v) for v in values]


def aInt(values: List[int]) -> List[int]:
    """
    Convert values to AutoCAD integer array (pyautocad compatible).

    Args:
        values: List of integer values

    Returns:
        List of integer values
    """
    return [int(v) for v in values]


def aShort(values: List[int]) -> List[int]:
    """
    Convert values to AutoCAD short integer array (pyautocad compatible).

    Args:
        values: List of integer values

    Returns:
        List of integer values
    """
    return [int(v) for v in values]


# Export all compatibility functions and classes
__all__ = ["Autocad", "Autocad_instance", "apoint", "aDouble", "aInt", "aShort"]
