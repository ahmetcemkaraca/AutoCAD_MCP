"""
Context Manager for Interactive Development Sessions
==================================================

Manages session context, variable persistence, and state management
for interactive development workflows in VS Code and other environments.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


class SessionContext:
    """Individual session context for interactive development."""

    def __init__(self, session_id: str):
        """
        Initialize session context.

        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.variables = {}
        self.execution_history = []
        self.metadata = {}

    def update_access_time(self):
        """Update last accessed timestamp."""
        self.last_accessed = time.time()

    def add_execution(self, code: str, result: Any, duration: float):
        """
        Add execution to history.

        Args:
            code: Executed code
            result: Execution result
            duration: Execution duration in seconds
        """
        self.execution_history.append(
            {"timestamp": time.time(), "code": code, "result": str(result), "duration": duration}
        )

        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

    def get_age_seconds(self) -> float:
        """Get session age in seconds."""
        return time.time() - self.created_at

    def get_idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self.last_accessed


class ContextManager:
    """
    Manages interactive development session contexts.
    """

    def __init__(self, max_sessions: int = 10, session_timeout: float = 3600):
        """
        Initialize context manager.

        Args:
            max_sessions: Maximum number of concurrent sessions
            session_timeout: Session timeout in seconds (default: 1 hour)
        """
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.sessions: Dict[str, SessionContext] = {}
        self.sessions_lock = threading.Lock()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_sessions, daemon=True)
        self.cleanup_thread.start()

        logger.info(
            f"Context Manager initialized (max_sessions: {max_sessions}, timeout: {session_timeout}s)"
        )

    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        Create new interactive session.

        Args:
            session_id: Optional specific session ID, or auto-generate

        Returns:
            Session ID
        """
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:8]}"

        with self.sessions_lock:
            # Clean up old sessions if at capacity
            if len(self.sessions) >= self.max_sessions:
                self._cleanup_old_sessions()

            # Create new session
            session = SessionContext(session_id)
            self.sessions[session_id] = session

            logger.info(f"Created new session: {session_id}")
            return session_id

    def get_session_context(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get session context, creating if necessary.

        Args:
            session_id: Session ID, or create new if None

        Returns:
            Session context dictionary
        """
        if session_id is None:
            session_id = self.create_session()

        with self.sessions_lock:
            if session_id not in self.sessions:
                # Create session if it doesn't exist
                session = SessionContext(session_id)
                self.sessions[session_id] = session
                logger.info(f"Auto-created session: {session_id}")
            else:
                session = self.sessions[session_id]
                session.update_access_time()

            return {
                "session_id": session.session_id,
                "variables": session.variables.copy(),
                "execution_history": session.execution_history.copy(),
                "metadata": session.metadata.copy(),
                "created_at": session.created_at,
                "last_accessed": session.last_accessed,
            }

    def update_session_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """
        Update session context.

        Args:
            session_id: Session ID
            context: Updated context data

        Returns:
            True if update successful
        """
        with self.sessions_lock:
            if session_id not in self.sessions:
                logger.warning(f"Attempt to update non-existent session: {session_id}")
                return False

            session = self.sessions[session_id]
            session.update_access_time()

            # Update session data
            if "variables" in context:
                session.variables.update(context["variables"])

            if "metadata" in context:
                session.metadata.update(context["metadata"])

            return True

    def add_execution_to_session(
        self, session_id: str, code: str, result: Any, duration: float
    ) -> bool:
        """
        Add execution record to session.

        Args:
            session_id: Session ID
            code: Executed code
            result: Execution result
            duration: Execution duration

        Returns:
            True if added successfully
        """
        with self.sessions_lock:
            if session_id not in self.sessions:
                logger.warning(f"Attempt to add execution to non-existent session: {session_id}")
                return False

            session = self.sessions[session_id]
            session.add_execution(code, result, duration)
            session.update_access_time()

            return True

    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get execution history for session.

        Args:
            session_id: Session ID
            limit: Maximum number of history items

        Returns:
            List of execution history items
        """
        with self.sessions_lock:
            if session_id not in self.sessions:
                return []

            session = self.sessions[session_id]
            session.update_access_time()

            history = session.execution_history[-limit:] if limit > 0 else session.execution_history
            return history.copy()

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session and clean up resources.

        Args:
            session_id: Session ID to delete

        Returns:
            True if session was deleted
        """
        with self.sessions_lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Deleted session: {session_id}")
                return True

            return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions.

        Returns:
            List of session information
        """
        with self.sessions_lock:
            sessions_info = []

            for session_id, session in self.sessions.items():
                sessions_info.append(
                    {
                        "session_id": session_id,
                        "created_at": session.created_at,
                        "last_accessed": session.last_accessed,
                        "age_seconds": session.get_age_seconds(),
                        "idle_seconds": session.get_idle_seconds(),
                        "variables_count": len(session.variables),
                        "execution_count": len(session.execution_history),
                    }
                )

            return sessions_info

    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get context manager statistics.

        Returns:
            Dictionary containing statistics
        """
        with self.sessions_lock:
            if not self.sessions:
                return {
                    "total_sessions": 0,
                    "active_sessions": 0,
                    "average_age_seconds": 0,
                    "total_executions": 0,
                }

            current_time = time.time()
            ages = [current_time - session.created_at for session in self.sessions.values()]
            idle_times = [
                current_time - session.last_accessed for session in self.sessions.values()
            ]
            total_executions = sum(
                len(session.execution_history) for session in self.sessions.values()
            )

            return {
                "total_sessions": len(self.sessions),
                "active_sessions": len(
                    [s for s in self.sessions.values() if s.get_idle_seconds() < 300]
                ),  # Active in last 5 minutes
                "average_age_seconds": sum(ages) / len(ages),
                "average_idle_seconds": sum(idle_times) / len(idle_times),
                "total_executions": total_executions,
                "max_sessions": self.max_sessions,
                "session_timeout": self.session_timeout,
            }

    def _cleanup_sessions(self):
        """Background thread to clean up expired sessions."""
        while True:
            try:
                time.sleep(300)  # Run cleanup every 5 minutes
                self._cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Error in session cleanup: {str(e)}")

    def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        with self.sessions_lock:
            current_time = time.time()
            expired_sessions = []

            for session_id, session in self.sessions.items():
                if current_time - session.last_accessed > self.session_timeout:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self.sessions[session_id]
                logger.info(f"Cleaned up expired session: {session_id}")

            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

    def _cleanup_old_sessions(self):
        """Clean up oldest sessions when at capacity."""
        if len(self.sessions) < self.max_sessions:
            return

        # Find oldest session by last access time
        oldest_session_id = min(
            self.sessions.keys(), key=lambda sid: self.sessions[sid].last_accessed
        )

        del self.sessions[oldest_session_id]
        logger.info(f"Cleaned up oldest session to make room: {oldest_session_id}")

    def clear_all_sessions(self):
        """Clear all sessions (for testing/maintenance)."""
        with self.sessions_lock:
            session_count = len(self.sessions)
            self.sessions.clear()
            logger.info(f"Cleared all {session_count} sessions")
