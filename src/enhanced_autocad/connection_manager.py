"""
Connection Manager for Enhanced AutoCAD Wrapper
============================================

Manages AutoCAD COM connections with automatic recovery, health monitoring,
and intelligent retry logic. Ensures robust connection management for
both manufacturing workflows and interactive development sessions.
"""

import logging
import time
from typing import Optional, Dict, Any
from threading import Lock

# Setup logger first
logger = logging.getLogger(__name__)

# Optional Windows COM imports - graceful degradation if not available
try:
    import pythoncom
    import win32com.client

    COM_AVAILABLE = True
except ImportError:
    COM_AVAILABLE = False
    logger.warning(
        "Windows COM modules not available - enhanced AutoCAD functionality will be limited"
    )


class ConnectionManager:
    """
    Manages AutoCAD COM connections with automatic recovery and health monitoring.
    """

    def __init__(self, max_retry_attempts: int = 3, retry_delay: float = 2.0):
        """
        Initialize connection manager.

        Args:
            max_retry_attempts: Maximum number of connection retry attempts
            retry_delay: Delay between retry attempts in seconds
        """
        self._connection = None
        self._connection_lock = Lock()
        self._max_retry_attempts = max_retry_attempts
        self._retry_delay = retry_delay
        self._connection_attempts = 0
        self._last_connection_time = None
        self._connection_stats = {
            "total_connections": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "recovery_attempts": 0,
            "successful_recoveries": 0,
        }

    def get_connection(self, force_reconnect: bool = False) -> Any:
        """
        Get AutoCAD connection with automatic recovery.

        Args:
            force_reconnect: Force new connection even if current exists

        Returns:
            AutoCAD application object

        Raises:
            ConnectionError: If unable to establish connection after retries
        """
        with self._connection_lock:
            if force_reconnect or not self._is_connection_healthy():
                self._establish_connection()

            return self._connection

    def _establish_connection(self) -> None:
        """
        Establish new AutoCAD connection with retry logic.

        Raises:
            ConnectionError: If unable to establish connection after max retries
        """
        if not COM_AVAILABLE:
            raise ConnectionError("Windows COM modules not available - cannot connect to AutoCAD")

        for attempt in range(self._max_retry_attempts):
            try:
                logger.info(
                    f"Attempting AutoCAD connection (attempt {attempt + 1}/{self._max_retry_attempts})"
                )

                # Initialize COM
                pythoncom.CoInitialize()

                # Try to connect to existing AutoCAD instance
                try:
                    self._connection = win32com.client.GetActiveObject("AutoCAD.Application")
                    logger.info("Connected to existing AutoCAD instance")
                except:
                    # Start new AutoCAD instance if none exists
                    logger.info("No existing AutoCAD instance found, starting new one")
                    self._connection = win32com.client.Dispatch("AutoCAD.Application")
                    self._connection.Visible = True

                # Validate connection
                if self._validate_connection():
                    self._connection_attempts = 0
                    self._last_connection_time = time.time()
                    self._connection_stats["total_connections"] += 1
                    self._connection_stats["successful_connections"] += 1
                    logger.info("AutoCAD connection established successfully")
                    return
                else:
                    raise ConnectionError("Connection validation failed")

            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                self._connection_stats["failed_connections"] += 1

                if attempt < self._max_retry_attempts - 1:
                    logger.info(f"Retrying in {self._retry_delay} seconds...")
                    time.sleep(self._retry_delay)
                else:
                    self._connection_stats["total_connections"] += 1
                    error_msg = f"Failed to establish AutoCAD connection after {self._max_retry_attempts} attempts"
                    logger.error(error_msg)
                    raise ConnectionError(error_msg)

    def _validate_connection(self) -> bool:
        """
        Validate that AutoCAD connection is functional.

        Returns:
            True if connection is valid and functional
        """
        try:
            if not self._connection:
                return False

            # Test basic connection functionality
            _ = self._connection.Name
            _ = self._connection.Documents

            # Ensure at least one document is available
            if self._connection.Documents.Count == 0:
                logger.info("No documents open, creating new document")
                self._connection.Documents.Add()

            return True

        except Exception as e:
            logger.warning(f"Connection validation failed: {str(e)}")
            return False

    def _is_connection_healthy(self) -> bool:
        """
        Check if current connection is healthy and responsive.

        Returns:
            True if connection is healthy
        """
        if not self._connection:
            return False

        try:
            # Quick health check - access basic properties
            _ = self._connection.Name
            _ = self._connection.Documents.Count
            return True

        except Exception as e:
            logger.warning(f"Connection health check failed: {str(e)}")
            return False

    def recover_connection(self) -> bool:
        """
        Attempt to recover failed connection.

        Returns:
            True if recovery successful
        """
        logger.info("Attempting connection recovery")
        self._connection_stats["recovery_attempts"] += 1

        try:
            self._connection = None
            self._establish_connection()
            self._connection_stats["successful_recoveries"] += 1
            logger.info("Connection recovery successful")
            return True

        except Exception as e:
            logger.error(f"Connection recovery failed: {str(e)}")
            return False

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status and statistics.

        Returns:
            Dictionary containing connection status and metrics
        """
        is_connected = self._is_connection_healthy()

        status = {
            "connected": is_connected,
            "last_connection_time": self._last_connection_time,
            "connection_age_seconds": (
                time.time() - self._last_connection_time if self._last_connection_time else None
            ),
            "statistics": self._connection_stats.copy(),
        }

        if is_connected and self._connection:
            try:
                status.update(
                    {
                        "autocad_version": getattr(self._connection, "Version", "Unknown"),
                        "autocad_name": getattr(self._connection, "Name", "Unknown"),
                        "documents_count": self._connection.Documents.Count,
                        "active_document": (
                            self._connection.ActiveDocument.Name
                            if self._connection.Documents.Count > 0
                            else None
                        ),
                    }
                )
            except Exception as e:
                logger.warning(f"Error getting detailed connection status: {str(e)}")
                status["status_error"] = str(e)

        return status

    def close_connection(self) -> None:
        """
        Properly close AutoCAD connection and cleanup resources.
        """
        with self._connection_lock:
            if self._connection:
                try:
                    logger.info("Closing AutoCAD connection")
                    # Note: We don't close AutoCAD application itself as it may be used by other processes
                    self._connection = None
                    if COM_AVAILABLE:
                        pythoncom.CoUninitialize()
                except Exception as e:
                    logger.warning(f"Error during connection cleanup: {str(e)}")

                self._last_connection_time = None

    def __enter__(self):
        """Context manager entry."""
        return self.get_connection()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Don't close connection on context exit to allow reuse
        pass
