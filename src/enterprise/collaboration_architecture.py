"""
Multi-User Collaboration Architecture
===================================

Enterprise-grade collaboration system for distributed AutoCAD development teams including:
- Real-time collaborative editing with conflict resolution
- Distributed workspace management and synchronization
- Role-based access control and permission management
- Team communication and notification systems
- Version control integration with collaborative workflows
"""

import logging
import time
import json
import uuid
import threading
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import asyncio
import websockets
import hashlib

# Import existing components
from ..enhanced_autocad.performance_monitor import PerformanceMonitor
from ..enhanced_autocad.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class CollaborationEventType(Enum):
    """Types of collaboration events."""
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    CODE_EDIT = "code_edit"
    FILE_OPEN = "file_open"
    FILE_CLOSE = "file_close"
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"
    COMMENT_ADD = "comment_add"
    COMMENT_REPLY = "comment_reply"
    BREAKPOINT_ADD = "breakpoint_add"
    BREAKPOINT_REMOVE = "breakpoint_remove"
    EXECUTION_START = "execution_start"
    EXECUTION_STOP = "execution_stop"
    WORKSPACE_SYNC = "workspace_sync"
    PERMISSION_CHANGE = "permission_change"


class UserRole(Enum):
    """User roles in the collaboration system."""
    OWNER = "owner"           # Full control over workspace
    ADMIN = "admin"           # Administrative privileges
    DEVELOPER = "developer"   # Full development access
    REVIEWER = "reviewer"     # Read access + review capabilities
    OBSERVER = "observer"     # Read-only access
    GUEST = "guest"          # Limited temporary access


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving edit conflicts."""
    LAST_WRITE_WINS = "last_write_wins"
    OPERATIONAL_TRANSFORM = "operational_transform"
    THREE_WAY_MERGE = "three_way_merge"
    MANUAL_RESOLUTION = "manual_resolution"
    AUTOMATIC_MERGE = "automatic_merge"


@dataclass
class CollaborationEvent:
    """A single collaboration event."""
    id: str
    event_type: CollaborationEventType
    user_id: str
    workspace_id: str
    timestamp: float
    
    # Event data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # File context
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    
    # Synchronization
    sequence_number: int = 0
    parent_event_id: Optional[str] = None
    
    # Metadata
    client_timestamp: Optional[float] = None
    processed: bool = False
    propagated: bool = False


@dataclass
class UserSession:
    """Active user session in the collaboration system."""
    user_id: str
    session_id: str
    workspace_id: str
    role: UserRole
    
    # Connection info
    websocket_connection: Optional[Any] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Session state
    active_files: Set[str] = field(default_factory=set)
    current_cursor_position: Optional[Tuple[str, int, int]] = None
    last_activity: float = field(default_factory=time.time)
    
    # Preferences
    preferences: Dict[str, Any] = field(default_factory=dict)
    notification_settings: Dict[str, bool] = field(default_factory=dict)
    
    # Statistics
    total_edits: int = 0
    total_comments: int = 0
    session_duration: float = 0.0


@dataclass
class Workspace:
    """Collaborative workspace containing files and users."""
    id: str
    name: str
    owner_id: str
    
    # Access control
    members: Dict[str, UserRole] = field(default_factory=dict)
    public: bool = False
    
    # Files and structure
    files: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    file_locks: Dict[str, str] = field(default_factory=dict)  # file -> user_id
    
    # Collaboration state
    active_sessions: Dict[str, UserSession] = field(default_factory=dict)
    event_history: deque = field(default_factory=lambda: deque(maxlen=10000))
    
    # Configuration
    settings: Dict[str, Any] = field(default_factory=dict)
    conflict_resolution: ConflictResolutionStrategy = ConflictResolutionStrategy.OPERATIONAL_TRANSFORM
    
    # Metadata
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    version: int = 1


@dataclass
class EditOperation:
    """An edit operation for operational transformation."""
    operation_type: str  # 'insert', 'delete', 'retain'
    position: int
    content: Optional[str] = None
    length: Optional[int] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    user_id: str = ""
    timestamp: float = field(default_factory=time.time)
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class OperationalTransform:
    """Operational transformation engine for collaborative editing."""
    
    def __init__(self):
        """Initialize the operational transform engine."""
        self.pending_operations = defaultdict(list)
        self.applied_operations = defaultdict(list)
    
    def transform_operation(self, 
                          op1: EditOperation, 
                          op2: EditOperation) -> Tuple[EditOperation, EditOperation]:
        """
        Transform two concurrent operations to maintain consistency.
        
        Args:
            op1: First operation
            op2: Second operation
            
        Returns:
            Tuple of transformed operations (op1', op2')
        """
        # Implementation of operational transformation algorithm
        # This is a simplified version - a full implementation would be more complex
        
        if op1.operation_type == 'insert' and op2.operation_type == 'insert':
            if op1.position <= op2.position:
                # op1 comes before op2, adjust op2's position
                op2_transformed = EditOperation(
                    operation_type=op2.operation_type,
                    position=op2.position + len(op1.content or ""),
                    content=op2.content,
                    user_id=op2.user_id,
                    timestamp=op2.timestamp,
                    operation_id=op2.operation_id
                )
                return op1, op2_transformed
            else:
                # op2 comes before op1, adjust op1's position
                op1_transformed = EditOperation(
                    operation_type=op1.operation_type,
                    position=op1.position + len(op2.content or ""),
                    content=op1.content,
                    user_id=op1.user_id,
                    timestamp=op1.timestamp,
                    operation_id=op1.operation_id
                )
                return op1_transformed, op2
        
        elif op1.operation_type == 'delete' and op2.operation_type == 'delete':
            # Handle concurrent deletions
            if op1.position < op2.position:
                if op1.position + (op1.length or 0) <= op2.position:
                    # Non-overlapping deletions
                    op2_transformed = EditOperation(
                        operation_type=op2.operation_type,
                        position=op2.position - (op1.length or 0),
                        length=op2.length,
                        user_id=op2.user_id,
                        timestamp=op2.timestamp,
                        operation_id=op2.operation_id
                    )
                    return op1, op2_transformed
                else:
                    # Overlapping deletions - need conflict resolution
                    return self._resolve_delete_conflict(op1, op2)
            else:
                return self.transform_operation(op2, op1)[::-1]  # Swap and reverse
        
        elif op1.operation_type == 'insert' and op2.operation_type == 'delete':
            return self._transform_insert_delete(op1, op2)
        
        elif op1.operation_type == 'delete' and op2.operation_type == 'insert':
            op2_t, op1_t = self._transform_insert_delete(op2, op1)
            return op1_t, op2_t
        
        # Default: return operations unchanged
        return op1, op2
    
    def _transform_insert_delete(self, 
                               insert_op: EditOperation, 
                               delete_op: EditOperation) -> Tuple[EditOperation, EditOperation]:
        """Transform insert and delete operations."""
        if insert_op.position <= delete_op.position:
            # Insert comes before delete
            delete_transformed = EditOperation(
                operation_type=delete_op.operation_type,
                position=delete_op.position + len(insert_op.content or ""),
                length=delete_op.length,
                user_id=delete_op.user_id,
                timestamp=delete_op.timestamp,
                operation_id=delete_op.operation_id
            )
            return insert_op, delete_transformed
        elif insert_op.position >= delete_op.position + (delete_op.length or 0):
            # Insert comes after delete
            insert_transformed = EditOperation(
                operation_type=insert_op.operation_type,
                position=insert_op.position - (delete_op.length or 0),
                content=insert_op.content,
                user_id=insert_op.user_id,
                timestamp=insert_op.timestamp,
                operation_id=insert_op.operation_id
            )
            return insert_transformed, delete_op
        else:
            # Insert is within delete range - complex case
            return self._resolve_insert_delete_conflict(insert_op, delete_op)
    
    def _resolve_delete_conflict(self, 
                               op1: EditOperation, 
                               op2: EditOperation) -> Tuple[EditOperation, EditOperation]:
        """Resolve conflicting delete operations."""
        # Simple resolution: merge the delete ranges
        start = min(op1.position, op2.position)
        end1 = op1.position + (op1.length or 0)
        end2 = op2.position + (op2.length or 0)
        end = max(end1, end2)
        
        merged_delete = EditOperation(
            operation_type='delete',
            position=start,
            length=end - start,
            user_id=op1.user_id,  # Prefer first operation's user
            timestamp=max(op1.timestamp, op2.timestamp),
            operation_id=str(uuid.uuid4())
        )
        
        # Return merged operation for both
        return merged_delete, merged_delete
    
    def _resolve_insert_delete_conflict(self, 
                                      insert_op: EditOperation, 
                                      delete_op: EditOperation) -> Tuple[EditOperation, EditOperation]:
        """Resolve insert/delete conflict when insert is within delete range."""
        # Strategy: Apply the insert at the delete position
        insert_transformed = EditOperation(
            operation_type=insert_op.operation_type,
            position=delete_op.position,
            content=insert_op.content,
            user_id=insert_op.user_id,
            timestamp=insert_op.timestamp,
            operation_id=insert_op.operation_id
        )
        
        return insert_transformed, delete_op


class CollaborationServer:
    """
    Multi-user collaboration server managing real-time collaboration.
    
    Handles user sessions, workspace management, real-time synchronization,
    and conflict resolution for distributed AutoCAD development teams.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Initialize the collaboration server.
        
        Args:
            host: Server host address
            port: Server port number
        """
        self.host = host
        self.port = port
        
        # Core components
        self.workspaces: Dict[str, Workspace] = {}
        self.user_sessions: Dict[str, UserSession] = {}
        self.operational_transform = OperationalTransform()
        
        # Event handling
        self.event_handlers: Dict[CollaborationEventType, List[Callable]] = defaultdict(list)
        self.event_queue = deque()
        self.event_processor_running = False
        
        # WebSocket connections
        self.websocket_connections: Dict[str, Any] = {}
        self.connection_lock = threading.RLock()
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        self.error_handler = ErrorHandler()
        
        # Configuration
        self.max_concurrent_users = 100
        self.session_timeout = 3600  # 1 hour
        self.file_lock_timeout = 300  # 5 minutes
        self.auto_save_interval = 30  # 30 seconds
        
        # Statistics
        self.server_stats = {
            'total_events_processed': 0,
            'active_workspaces': 0,
            'active_users': 0,
            'total_edits': 0,
            'server_uptime': time.time()
        }
        
        logger.info(f"Collaboration server initialized on {host}:{port}")
    
    async def start_server(self):
        """Start the collaboration server."""
        try:
            # Start event processor
            self.event_processor_running = True
            event_processor_task = asyncio.create_task(self._process_events())
            
            # Start WebSocket server
            server = await websockets.serve(
                self._handle_websocket_connection, 
                self.host, 
                self.port
            )
            
            logger.info(f"Collaboration server started on ws://{self.host}:{self.port}")
            
            # Keep server running
            await asyncio.gather(
                server.wait_closed(),
                event_processor_task
            )
            
        except Exception as e:
            logger.error(f"Failed to start collaboration server: {e}")
            raise
    
    async def stop_server(self):
        """Stop the collaboration server."""
        self.event_processor_running = False
        
        # Close all WebSocket connections
        with self.connection_lock:
            for connection in self.websocket_connections.values():
                if not connection.closed:
                    await connection.close()
        
        logger.info("Collaboration server stopped")
    
    def create_workspace(self, 
                        name: str, 
                        owner_id: str, 
                        settings: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new collaborative workspace.
        
        Args:
            name: Workspace name
            owner_id: ID of the workspace owner
            settings: Optional workspace settings
            
        Returns:
            Workspace ID
        """
        workspace_id = str(uuid.uuid4())
        
        workspace = Workspace(
            id=workspace_id,
            name=name,
            owner_id=owner_id,
            settings=settings or {}
        )
        
        # Add owner as admin member
        workspace.members[owner_id] = UserRole.OWNER
        
        self.workspaces[workspace_id] = workspace
        self.server_stats['active_workspaces'] = len(self.workspaces)
        
        logger.info(f"Created workspace '{name}' ({workspace_id}) for user {owner_id}")
        return workspace_id
    
    def join_workspace(self, 
                      workspace_id: str, 
                      user_id: str, 
                      role: Optional[UserRole] = None) -> bool:
        """
        Join a user to a workspace.
        
        Args:
            workspace_id: ID of workspace to join
            user_id: ID of user joining
            role: Role to assign (if authorized)
            
        Returns:
            True if successfully joined
        """
        if workspace_id not in self.workspaces:
            logger.error(f"Workspace {workspace_id} not found")
            return False
        
        workspace = self.workspaces[workspace_id]
        
        # Check if user is already a member
        if user_id in workspace.members:
            existing_role = workspace.members[user_id]
            logger.info(f"User {user_id} already in workspace {workspace_id} with role {existing_role.value}")
            return True
        
        # Determine role to assign
        if role is None:
            # Default role for new members
            assigned_role = UserRole.DEVELOPER if not workspace.public else UserRole.OBSERVER
        else:
            assigned_role = role
        
        # Add user to workspace
        workspace.members[user_id] = assigned_role
        
        # Create user session
        session_id = str(uuid.uuid4())
        session = UserSession(
            user_id=user_id,
            session_id=session_id,
            workspace_id=workspace_id,
            role=assigned_role
        )
        
        self.user_sessions[session_id] = session
        workspace.active_sessions[session_id] = session
        
        # Generate join event
        join_event = CollaborationEvent(
            id=str(uuid.uuid4()),
            event_type=CollaborationEventType.USER_JOIN,
            user_id=user_id,
            workspace_id=workspace_id,
            timestamp=time.time(),
            data={'role': assigned_role.value, 'session_id': session_id}
        )
        
        self._queue_event(join_event)
        
        logger.info(f"User {user_id} joined workspace {workspace_id} with role {assigned_role.value}")
        return True
    
    def leave_workspace(self, session_id: str) -> bool:
        """
        Remove a user from a workspace.
        
        Args:
            session_id: Session ID of user leaving
            
        Returns:
            True if successfully left
        """
        if session_id not in self.user_sessions:
            return False
        
        session = self.user_sessions[session_id]
        workspace_id = session.workspace_id
        user_id = session.user_id
        
        # Remove from workspace active sessions
        if workspace_id in self.workspaces:
            workspace = self.workspaces[workspace_id]
            if session_id in workspace.active_sessions:
                del workspace.active_sessions[session_id]
            
            # Release any file locks held by this user
            files_to_unlock = [
                file_path for file_path, lock_user in workspace.file_locks.items()
                if lock_user == user_id
            ]
            for file_path in files_to_unlock:
                del workspace.file_locks[file_path]
        
        # Remove user session
        del self.user_sessions[session_id]
        
        # Generate leave event
        leave_event = CollaborationEvent(
            id=str(uuid.uuid4()),
            event_type=CollaborationEventType.USER_LEAVE,
            user_id=user_id,
            workspace_id=workspace_id,
            timestamp=time.time(),
            data={'session_id': session_id, 'files_unlocked': files_to_unlock}
        )
        
        self._queue_event(leave_event)
        
        logger.info(f"User {user_id} left workspace {workspace_id}")
        return True
    
    def handle_edit_operation(self, 
                            session_id: str, 
                            file_path: str, 
                            operation: EditOperation) -> bool:
        """
        Handle an edit operation from a user.
        
        Args:
            session_id: Session ID of user making edit
            file_path: Path of file being edited
            operation: Edit operation to apply
            
        Returns:
            True if operation was successfully processed
        """
        if session_id not in self.user_sessions:
            logger.error(f"Session {session_id} not found")
            return False
        
        session = self.user_sessions[session_id]
        workspace_id = session.workspace_id
        
        if workspace_id not in self.workspaces:
            logger.error(f"Workspace {workspace_id} not found")
            return False
        
        workspace = self.workspaces[workspace_id]
        
        # Check permissions
        if not self._can_edit_file(session, file_path):
            logger.warning(f"User {session.user_id} lacks permission to edit {file_path}")
            return False
        
        # Apply operational transformation
        transformed_operation = self._apply_operational_transform(
            workspace_id, file_path, operation
        )
        
        # Apply the operation to the file
        success = self._apply_edit_operation(workspace_id, file_path, transformed_operation)
        
        if success:
            # Update session statistics
            session.total_edits += 1
            session.last_activity = time.time()
            
            # Generate edit event
            edit_event = CollaborationEvent(
                id=str(uuid.uuid4()),
                event_type=CollaborationEventType.CODE_EDIT,
                user_id=session.user_id,
                workspace_id=workspace_id,
                timestamp=time.time(),
                file_path=file_path,
                data={
                    'operation': {
                        'type': transformed_operation.operation_type,
                        'position': transformed_operation.position,
                        'content': transformed_operation.content,
                        'length': transformed_operation.length,
                        'operation_id': transformed_operation.operation_id
                    }
                }
            )
            
            self._queue_event(edit_event)
            self.server_stats['total_edits'] += 1
        
        return success
    
    def get_workspace_state(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of a workspace.
        
        Args:
            workspace_id: ID of workspace
            
        Returns:
            Workspace state dictionary or None if not found
        """
        if workspace_id not in self.workspaces:
            return None
        
        workspace = self.workspaces[workspace_id]
        
        return {
            'id': workspace.id,
            'name': workspace.name,
            'owner_id': workspace.owner_id,
            'members': {user_id: role.value for user_id, role in workspace.members.items()},
            'active_sessions': len(workspace.active_sessions),
            'files': list(workspace.files.keys()),
            'file_locks': workspace.file_locks.copy(),
            'last_activity': workspace.last_activity,
            'settings': workspace.settings,
            'version': workspace.version
        }
    
    def get_server_statistics(self) -> Dict[str, Any]:
        """Get server performance and usage statistics."""
        current_time = time.time()
        uptime = current_time - self.server_stats['server_uptime']
        
        stats = self.server_stats.copy()
        stats.update({
            'current_timestamp': current_time,
            'uptime_seconds': uptime,
            'uptime_hours': uptime / 3600,
            'active_workspaces': len(self.workspaces),
            'active_users': len(self.user_sessions),
            'total_websocket_connections': len(self.websocket_connections),
            'pending_events': len(self.event_queue)
        })
        
        # Add performance metrics if available
        try:
            perf_metrics = self.performance_monitor.get_current_metrics()
            stats['performance'] = perf_metrics
        except Exception:
            pass
        
        return stats
    
    async def _handle_websocket_connection(self, websocket, path):
        """Handle a new WebSocket connection."""
        connection_id = str(uuid.uuid4())
        
        try:
            with self.connection_lock:
                self.websocket_connections[connection_id] = websocket
            
            logger.info(f"New WebSocket connection: {connection_id}")
            
            # Handle messages from this connection
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_websocket_message(connection_id, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from connection {connection_id}")
                except Exception as e:
                    logger.error(f"Error handling message from {connection_id}: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error for connection {connection_id}: {e}")
        finally:
            # Clean up connection
            with self.connection_lock:
                if connection_id in self.websocket_connections:
                    del self.websocket_connections[connection_id]
    
    async def _handle_websocket_message(self, connection_id: str, data: Dict[str, Any]):
        """Handle a message from a WebSocket connection."""
        message_type = data.get('type')
        
        if message_type == 'join_workspace':
            await self._handle_join_workspace_message(connection_id, data)
        elif message_type == 'edit_operation':
            await self._handle_edit_operation_message(connection_id, data)
        elif message_type == 'cursor_update':
            await self._handle_cursor_update_message(connection_id, data)
        elif message_type == 'file_open':
            await self._handle_file_open_message(connection_id, data)
        elif message_type == 'file_close':
            await self._handle_file_close_message(connection_id, data)
        else:
            logger.warning(f"Unknown message type '{message_type}' from connection {connection_id}")
    
    async def _process_events(self):
        """Process collaboration events in the background."""
        while self.event_processor_running:
            try:
                if self.event_queue:
                    event = self.event_queue.popleft()
                    await self._process_event(event)
                else:
                    await asyncio.sleep(0.01)  # Small delay when no events
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_event(self, event: CollaborationEvent):
        """Process a single collaboration event."""
        try:
            # Update statistics
            self.server_stats['total_events_processed'] += 1
            
            # Call registered event handlers
            handlers = self.event_handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Event handler error for {event.event_type}: {e}")
            
            # Broadcast event to relevant users
            await self._broadcast_event(event)
            
            # Mark event as processed
            event.processed = True
            
        except Exception as e:
            logger.error(f"Failed to process event {event.id}: {e}")
    
    async def _broadcast_event(self, event: CollaborationEvent):
        """Broadcast an event to relevant users in the workspace."""
        if event.workspace_id not in self.workspaces:
            return
        
        workspace = self.workspaces[event.workspace_id]
        
        # Prepare event message
        message = {
            'type': 'collaboration_event',
            'event': {
                'id': event.id,
                'type': event.event_type.value,
                'user_id': event.user_id,
                'workspace_id': event.workspace_id,
                'timestamp': event.timestamp,
                'data': event.data,
                'file_path': event.file_path,
                'line_number': event.line_number,
                'column_number': event.column_number
            }
        }
        
        message_json = json.dumps(message)
        
        # Send to all active sessions in the workspace
        for session in workspace.active_sessions.values():
            # Don't send event back to the originator
            if session.user_id == event.user_id:
                continue
            
            try:
                if session.websocket_connection and not session.websocket_connection.closed:
                    await session.websocket_connection.send(message_json)
            except Exception as e:
                logger.error(f"Failed to send event to user {session.user_id}: {e}")
    
    def _queue_event(self, event: CollaborationEvent):
        """Queue an event for processing."""
        self.event_queue.append(event)
    
    def _can_edit_file(self, session: UserSession, file_path: str) -> bool:
        """Check if a user session can edit a specific file."""
        # Check role permissions
        if session.role in [UserRole.OBSERVER, UserRole.GUEST]:
            return False
        
        # Check file locks
        if session.workspace_id in self.workspaces:
            workspace = self.workspaces[session.workspace_id]
            if file_path in workspace.file_locks:
                lock_user = workspace.file_locks[file_path]
                return lock_user == session.user_id
        
        return True
    
    def _apply_operational_transform(self, 
                                   workspace_id: str, 
                                   file_path: str, 
                                   operation: EditOperation) -> EditOperation:
        """Apply operational transformation to resolve conflicts."""
        # This is a simplified implementation
        # In practice, you'd maintain operation histories and apply transformations
        # against all concurrent operations
        
        return operation  # For now, return unchanged
    
    def _apply_edit_operation(self, 
                            workspace_id: str, 
                            file_path: str, 
                            operation: EditOperation) -> bool:
        """Apply an edit operation to a file."""
        try:
            workspace = self.workspaces[workspace_id]
            
            # Get or create file content
            if file_path not in workspace.files:
                workspace.files[file_path] = {
                    'content': '',
                    'version': 1,
                    'last_modified': time.time(),
                    'last_modified_by': operation.user_id
                }
            
            file_data = workspace.files[file_path]
            content = file_data['content']
            
            # Apply operation based on type
            if operation.operation_type == 'insert':
                content = (content[:operation.position] + 
                          (operation.content or '') + 
                          content[operation.position:])
            elif operation.operation_type == 'delete':
                end_pos = operation.position + (operation.length or 0)
                content = content[:operation.position] + content[end_pos:]
            
            # Update file data
            file_data['content'] = content
            file_data['version'] += 1
            file_data['last_modified'] = time.time()
            file_data['last_modified_by'] = operation.user_id
            
            # Update workspace
            workspace.last_activity = time.time()
            workspace.version += 1
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to apply edit operation: {e}")
            return False