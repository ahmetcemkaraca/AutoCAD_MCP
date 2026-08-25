"""
Session Manager for Interactive Development
==========================================

Manages REPL sessions with persistence, state management, and session lifecycle.
Provides session isolation, variable persistence, and session-based security policies.
Integrates with context manager and supports session serialization/restoration.
"""

import logging
import time
import json
import pickle
import threading
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session state enumeration."""
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended" 
    TERMINATED = "terminated"


@dataclass
class SessionInfo:
    """Session information data class."""
    session_id: str
    created_at: float
    last_accessed: float
    state: SessionState
    command_count: int
    memory_usage: float
    execution_count: int
    variables_count: int
    metadata: Dict[str, Any]


class SessionManager:
    """
    Manages interactive development sessions with persistence and lifecycle management.
    """

    def __init__(self, session_storage_path: Optional[str] = None, 
                 max_sessions: int = 50, session_timeout: int = 3600):
        """
        Initialize session manager.

        Args:
            session_storage_path: Path for session persistence (None = no persistence)
            max_sessions: Maximum number of concurrent sessions
            session_timeout: Session timeout in seconds
        """
        self.sessions = {}
        self.session_locks = {}
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        
        # Session persistence
        self.storage_path = Path(session_storage_path) if session_storage_path else None
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Session management
        self.cleanup_thread = None
        self.start_cleanup_thread()
        
        logger.info(f"Session Manager initialized (max_sessions={max_sessions}, timeout={session_timeout}s)")

    def create_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new interactive session.

        Args:
            session_id: Unique session identifier
            metadata: Optional session metadata

        Returns:
            Dictionary containing session creation result
        """
        if session_id in self.sessions:
            return {
                "success": False,
                "error": f"Session {session_id} already exists",
                "session_id": session_id
            }

        # Check session limit
        if len(self.sessions) >= self.max_sessions:
            # Try to clean up old sessions
            self._cleanup_expired_sessions()
            
            if len(self.sessions) >= self.max_sessions:
                return {
                    "success": False,
                    "error": f"Maximum sessions limit reached ({self.max_sessions})",
                    "session_id": session_id
                }

        try:
            current_time = time.time()
            
            # Create session data
            session_data = {
                "session_id": session_id,
                "created_at": current_time,
                "last_accessed": current_time,
                "state": SessionState.ACTIVE,
                "command_count": 0,
                "execution_count": 0,
                "variables": {},
                "globals": {},
                "locals": {},
                "history": [],
                "metadata": metadata or {},
                "performance_stats": {
                    "total_execution_time": 0.0,
                    "average_execution_time": 0.0,
                    "memory_peak": 0.0,
                    "errors_count": 0
                }
            }
            
            # Create session lock
            self.session_locks[session_id] = threading.RLock()
            
            # Store session
            self.sessions[session_id] = session_data
            
            # Persist if storage is enabled
            if self.storage_path:
                self._persist_session(session_id)
            
            logger.info(f"Session {session_id} created successfully")
            
            return {
                "success": True,
                "session_id": session_id,
                "created_at": current_time,
                "state": SessionState.ACTIVE.value,
                "message": f"Session {session_id} created successfully"
            }

        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create session: {str(e)}",
                "session_id": session_id
            }

    def get_session(self, session_id: str, touch: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get session data.

        Args:
            session_id: Session identifier
            touch: Whether to update last_accessed timestamp

        Returns:
            Session data or None if not found
        """
        if session_id not in self.sessions:
            # Try to restore from storage
            if self.storage_path:
                restored = self._restore_session(session_id)
                if not restored:
                    return None
            else:
                return None

        with self.session_locks.get(session_id, threading.RLock()):
            session = self.sessions[session_id]
            
            if touch:
                session["last_accessed"] = time.time()
                session["state"] = SessionState.ACTIVE
            
            return session

    def update_session_variables(self, session_id: str, variables: Dict[str, Any]) -> bool:
        """
        Update session variables.

        Args:
            session_id: Session identifier
            variables: Variables to update

        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            return False

        with self.session_locks[session_id]:
            # Update variables
            session["variables"].update(variables)
            
            # Update stats
            session["command_count"] += 1
            
            # Persist changes
            if self.storage_path:
                self._persist_session(session_id)
        
        return True

    def add_session_history(self, session_id: str, history_entry: Dict[str, Any]) -> bool:
        """
        Add entry to session history.

        Args:
            session_id: Session identifier
            history_entry: History entry to add

        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            return False

        with self.session_locks[session_id]:
            session["history"].append(history_entry)
            session["execution_count"] += 1
            
            # Keep history manageable
            if len(session["history"]) > 1000:
                session["history"] = session["history"][-1000:]
            
            # Update performance stats
            if "execution_time" in history_entry:
                exec_time = history_entry["execution_time"]
                stats = session["performance_stats"]
                
                stats["total_execution_time"] += exec_time
                stats["average_execution_time"] = (
                    stats["total_execution_time"] / session["execution_count"]
                )
                
                if not history_entry.get("success", True):
                    stats["errors_count"] += 1
            
            # Persist changes
            if self.storage_path:
                self._persist_session(session_id)
        
        return True

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information summary."""
        session = self.get_session(session_id, touch=False)
        if not session:
            return None

        return SessionInfo(
            session_id=session_id,
            created_at=session["created_at"],
            last_accessed=session["last_accessed"],
            state=session["state"],
            command_count=session["command_count"],
            memory_usage=0.0,  # Would be calculated from actual usage
            execution_count=session["execution_count"],
            variables_count=len(session["variables"]),
            metadata=session["metadata"]
        )

    def list_sessions(self, include_terminated: bool = False) -> List[SessionInfo]:
        """
        List all sessions.

        Args:
            include_terminated: Whether to include terminated sessions

        Returns:
            List of session information
        """
        sessions_info = []
        
        for session_id in self.sessions:
            session_info = self.get_session_info(session_id)
            if session_info:
                if include_terminated or session_info.state != SessionState.TERMINATED:
                    sessions_info.append(session_info)
        
        # Sort by last accessed (most recent first)
        sessions_info.sort(key=lambda x: x.last_accessed, reverse=True)
        
        return sessions_info

    def suspend_session(self, session_id: str) -> bool:
        """
        Suspend a session (save state and reduce memory usage).

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        session = self.get_session(session_id, touch=False)
        if not session:
            return False

        with self.session_locks[session_id]:
            session["state"] = SessionState.SUSPENDED
            
            # Persist state
            if self.storage_path:
                self._persist_session(session_id)
        
        logger.info(f"Session {session_id} suspended")
        return True

    def resume_session(self, session_id: str) -> bool:
        """
        Resume a suspended session.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            return False

        with self.session_locks[session_id]:
            if session["state"] == SessionState.SUSPENDED:
                session["state"] = SessionState.ACTIVE
                session["last_accessed"] = time.time()
                
                logger.info(f"Session {session_id} resumed")
                return True
        
        return False

    def terminate_session(self, session_id: str, cleanup: bool = True) -> bool:
        """
        Terminate a session.

        Args:
            session_id: Session identifier
            cleanup: Whether to clean up session data

        Returns:
            True if successful
        """
        if session_id not in self.sessions:
            return False

        with self.session_locks.get(session_id, threading.RLock()):
            if cleanup:
                # Clean up session data
                del self.sessions[session_id]
                if session_id in self.session_locks:
                    del self.session_locks[session_id]
                
                # Clean up persistent storage
                if self.storage_path:
                    session_file = self.storage_path / f"{session_id}.json"
                    if session_file.exists():
                        session_file.unlink()
            else:
                # Just mark as terminated
                self.sessions[session_id]["state"] = SessionState.TERMINATED
        
        logger.info(f"Session {session_id} terminated (cleanup={cleanup})")
        return True

    def get_session_statistics(self) -> Dict[str, Any]:
        """Get overall session statistics."""
        total_sessions = len(self.sessions)
        active_sessions = sum(1 for s in self.sessions.values() if s["state"] == SessionState.ACTIVE)
        idle_sessions = sum(1 for s in self.sessions.values() if s["state"] == SessionState.IDLE)
        suspended_sessions = sum(1 for s in self.sessions.values() if s["state"] == SessionState.SUSPENDED)
        
        # Calculate average session age
        current_time = time.time()
        session_ages = [current_time - s["created_at"] for s in self.sessions.values()]
        avg_session_age = sum(session_ages) / len(session_ages) if session_ages else 0
        
        # Total commands across all sessions
        total_commands = sum(s["command_count"] for s in self.sessions.values())
        total_executions = sum(s["execution_count"] for s in self.sessions.values())

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "idle_sessions": idle_sessions,
            "suspended_sessions": suspended_sessions,
            "average_session_age_seconds": avg_session_age,
            "total_commands": total_commands,
            "total_executions": total_executions,
            "max_sessions_limit": self.max_sessions,
            "session_timeout": self.session_timeout,
            "persistent_storage_enabled": self.storage_path is not None
        }

    def start_cleanup_thread(self):
        """Start background cleanup thread."""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            return

        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)  # Check every 5 minutes
                    self._cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Session cleanup error: {str(e)}")

        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()

    def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            last_accessed = session["last_accessed"]
            if current_time - last_accessed > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired session: {session_id}")
            self.terminate_session(session_id, cleanup=True)

    def _persist_session(self, session_id: str):
        """Persist session to storage."""
        if not self.storage_path:
            return

        try:
            session = self.sessions[session_id]
            session_file = self.storage_path / f"{session_id}.json"
            
            # Create serializable copy (exclude non-serializable objects)
            serializable_session = {
                k: v for k, v in session.items() 
                if k not in ["globals", "locals"]  # Skip complex objects
            }
            
            # Convert enum to string
            if isinstance(serializable_session["state"], SessionState):
                serializable_session["state"] = serializable_session["state"].value
            
            with open(session_file, 'w') as f:
                json.dump(serializable_session, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to persist session {session_id}: {str(e)}")

    def _restore_session(self, session_id: str) -> bool:
        """Restore session from storage."""
        if not self.storage_path:
            return False

        try:
            session_file = self.storage_path / f"{session_id}.json"
            if not session_file.exists():
                return False

            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Convert state back to enum
            if "state" in session_data:
                session_data["state"] = SessionState(session_data["state"])
            
            # Restore missing fields
            session_data.setdefault("globals", {})
            session_data.setdefault("locals", {})
            
            # Create session lock
            self.session_locks[session_id] = threading.RLock()
            
            # Store restored session
            self.sessions[session_id] = session_data
            
            logger.info(f"Session {session_id} restored from storage")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore session {session_id}: {str(e)}")
            return False