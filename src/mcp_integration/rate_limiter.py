"""
Rate limiting system for MCP tools.

This module provides comprehensive rate limiting functionality to prevent
abuse and ensure fair resource usage across all MCP tools and sessions.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Types of rate limiting."""
    SESSION_GLOBAL = "session_global"
    TOOL_SPECIFIC = "tool_specific"
    CATEGORY_BASED = "category_based"
    IP_BASED = "ip_based"


@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests: int
    window_seconds: int
    burst_allowance: int = 0
    
    def __post_init__(self):
        if self.requests <= 0:
            raise ValueError("Requests must be positive")
        if self.window_seconds <= 0:
            raise ValueError("Window seconds must be positive")


@dataclass
class SessionInfo:
    """Session information for rate limiting."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    total_requests: int = 0
    violations: int = 0
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class TokenBucket:
    """
    Token bucket algorithm implementation for rate limiting.
    
    This provides smooth rate limiting with burst capacity.
    """
    
    def __init__(self, capacity: int, refill_rate: float, initial_tokens: Optional[int] = None):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
            initial_tokens: Initial token count (defaults to capacity)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        with self._lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds (0 if tokens already available)
        """
        with self._lock:
            if self.tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


class SlidingWindowCounter:
    """
    Sliding window counter for precise rate limiting.
    
    Tracks requests in a sliding time window.
    """
    
    def __init__(self, window_seconds: int):
        self.window_seconds = window_seconds
        self.requests = deque()
        self._lock = threading.Lock()
    
    def add_request(self, timestamp: Optional[float] = None) -> None:
        """Add a request to the window."""
        if timestamp is None:
            timestamp = time.time()
            
        with self._lock:
            self.requests.append(timestamp)
            self._cleanup_old_requests(timestamp)
    
    def get_request_count(self, timestamp: Optional[float] = None) -> int:
        """Get current request count in the window."""
        if timestamp is None:
            timestamp = time.time()
            
        with self._lock:
            self._cleanup_old_requests(timestamp)
            return len(self.requests)
    
    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove requests outside the window."""
        cutoff_time = current_time - self.window_seconds
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()


class RateLimiter:
    """
    Comprehensive rate limiting system for MCP tools.
    
    Supports multiple rate limiting strategies:
    - Token bucket for smooth rate limiting
    - Sliding window for precise limits
    - Multiple limit types (session, tool, category, IP)
    """
    
    def __init__(self):
        """Initialize rate limiter with default configurations."""
        self.sessions: Dict[str, SessionInfo] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, SlidingWindowCounter] = {}
        self._lock = threading.Lock()
        
        # Default rate limit configurations
        self.default_limits = {
            RateLimitType.SESSION_GLOBAL: RateLimit(requests=100, window_seconds=60, burst_allowance=20),
            RateLimitType.TOOL_SPECIFIC: {
                'ai_features': RateLimit(requests=5, window_seconds=60),
                'code_generation': RateLimit(requests=10, window_seconds=60),
                'testing': RateLimit(requests=20, window_seconds=60),
                'debugging': RateLimit(requests=15, window_seconds=60),
                'inspection': RateLimit(requests=30, window_seconds=60),
                'general': RateLimit(requests=50, window_seconds=60)
            },
            RateLimitType.CATEGORY_BASED: {
                'heavy_computation': RateLimit(requests=3, window_seconds=60),
                'file_operations': RateLimit(requests=20, window_seconds=60),
                'network_requests': RateLimit(requests=10, window_seconds=60),
                'database_operations': RateLimit(requests=25, window_seconds=60)
            },
            RateLimitType.IP_BASED: RateLimit(requests=200, window_seconds=60, burst_allowance=50)
        }
    
    def check_rate_limit(self, session_id: str, tool_name: str, 
                        tool_category: str = 'general',
                        ip_address: Optional[str] = None) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Check if request is allowed under all applicable rate limits.
        
        Args:
            session_id: Session identifier
            tool_name: Name of the MCP tool being called
            tool_category: Category of the tool
            ip_address: Client IP address (optional)
            
        Returns:
            Tuple of (allowed, error_message, rate_limit_info)
        """
        with self._lock:
            # Update session info
            session = self._get_or_create_session(session_id, ip_address)
            session.last_activity = time.time()
            session.total_requests += 1
            
            rate_limit_info = {
                'checks_performed': [],
                'limits_hit': [],
                'session_info': {
                    'total_requests': session.total_requests,
                    'violations': session.violations,
                    'session_age': time.time() - session.created_at
                }
            }
            
            # Check session-level rate limit
            session_allowed, session_error = self._check_session_limit(session_id)
            rate_limit_info['checks_performed'].append('session_global')
            if not session_allowed:
                rate_limit_info['limits_hit'].append('session_global')
                session.violations += 1
                return False, session_error, rate_limit_info
            
            # Check tool-specific rate limit
            tool_allowed, tool_error = self._check_tool_limit(session_id, tool_name)
            rate_limit_info['checks_performed'].append('tool_specific')
            if not tool_allowed:
                rate_limit_info['limits_hit'].append('tool_specific')
                session.violations += 1
                return False, tool_error, rate_limit_info
            
            # Check category-based rate limit
            category_allowed, category_error = self._check_category_limit(session_id, tool_category)
            rate_limit_info['checks_performed'].append('category_based')
            if not category_allowed:
                rate_limit_info['limits_hit'].append('category_based')
                session.violations += 1
                return False, category_error, rate_limit_info
            
            # Check IP-based rate limit (if IP provided)
            if ip_address:
                ip_allowed, ip_error = self._check_ip_limit(ip_address)
                rate_limit_info['checks_performed'].append('ip_based')
                if not ip_allowed:
                    rate_limit_info['limits_hit'].append('ip_based')
                    session.violations += 1
                    return False, ip_error, rate_limit_info
            
            # All checks passed
            return True, None, rate_limit_info
    
    def _get_or_create_session(self, session_id: str, ip_address: Optional[str] = None) -> SessionInfo:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionInfo(
                session_id=session_id,
                ip_address=ip_address
            )
        return self.sessions[session_id]
    
    def _check_session_limit(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """Check session-level rate limit."""
        limit = self.default_limits[RateLimitType.SESSION_GLOBAL]
        bucket_key = f"session:{session_id}"
        
        if bucket_key not in self.token_buckets:
            self.token_buckets[bucket_key] = TokenBucket(
                capacity=limit.requests + limit.burst_allowance,
                refill_rate=limit.requests / limit.window_seconds
            )
        
        bucket = self.token_buckets[bucket_key]
        if bucket.consume():
            return True, None
        
        wait_time = bucket.get_wait_time()
        return False, f"Session rate limit exceeded. Try again in {wait_time:.1f} seconds"
    
    def _check_tool_limit(self, session_id: str, tool_name: str) -> Tuple[bool, Optional[str]]:
        """Check tool-specific rate limit."""
        tool_limits = self.default_limits[RateLimitType.TOOL_SPECIFIC]
        
        # Find the most specific limit for this tool
        limit = None
        for pattern, tool_limit in tool_limits.items():
            if pattern in tool_name.lower() or pattern == 'general':
                limit = tool_limit
                break
        
        if limit is None:
            limit = tool_limits['general']
        
        window_key = f"tool:{session_id}:{tool_name}"
        
        if window_key not in self.sliding_windows:
            self.sliding_windows[window_key] = SlidingWindowCounter(limit.window_seconds)
        
        window = self.sliding_windows[window_key]
        current_count = window.get_request_count()
        
        if current_count >= limit.requests:
            return False, f"Tool rate limit exceeded for '{tool_name}'. Limit: {limit.requests} requests per {limit.window_seconds} seconds"
        
        window.add_request()
        return True, None
    
    def _check_category_limit(self, session_id: str, category: str) -> Tuple[bool, Optional[str]]:
        """Check category-based rate limit."""
        category_limits = self.default_limits[RateLimitType.CATEGORY_BASED]
        
        if category not in category_limits:
            return True, None  # No limit for this category
        
        limit = category_limits[category]
        window_key = f"category:{session_id}:{category}"
        
        if window_key not in self.sliding_windows:
            self.sliding_windows[window_key] = SlidingWindowCounter(limit.window_seconds)
        
        window = self.sliding_windows[window_key]
        current_count = window.get_request_count()
        
        if current_count >= limit.requests:
            return False, f"Category rate limit exceeded for '{category}'. Limit: {limit.requests} requests per {limit.window_seconds} seconds"
        
        window.add_request()
        return True, None
    
    def _check_ip_limit(self, ip_address: str) -> Tuple[bool, Optional[str]]:
        """Check IP-based rate limit."""
        limit = self.default_limits[RateLimitType.IP_BASED]
        bucket_key = f"ip:{ip_address}"
        
        if bucket_key not in self.token_buckets:
            self.token_buckets[bucket_key] = TokenBucket(
                capacity=limit.requests + limit.burst_allowance,
                refill_rate=limit.requests / limit.window_seconds
            )
        
        bucket = self.token_buckets[bucket_key]
        if bucket.consume():
            return True, None
        
        wait_time = bucket.get_wait_time()
        return False, f"IP rate limit exceeded. Try again in {wait_time:.1f} seconds"
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a session."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        bucket_key = f"session:{session_id}"
        
        stats = {
            'session_id': session_id,
            'created_at': session.created_at,
            'last_activity': session.last_activity,
            'total_requests': session.total_requests,
            'violations': session.violations,
            'session_age': time.time() - session.created_at,
            'ip_address': session.ip_address
        }
        
        if bucket_key in self.token_buckets:
            bucket = self.token_buckets[bucket_key]
            stats['tokens_available'] = int(bucket.tokens)
            stats['token_capacity'] = bucket.capacity
        
        return stats
    
    def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up expired sessions and associated data.
        
        Args:
            max_age_seconds: Maximum age for sessions (default 1 hour)
            
        Returns:
            Number of sessions cleaned up
        """
        with self._lock:
            current_time = time.time()
            expired_sessions = []
            
            for session_id, session in self.sessions.items():
                if current_time - session.last_activity > max_age_seconds:
                    expired_sessions.append(session_id)
            
            # Clean up expired sessions
            for session_id in expired_sessions:
                del self.sessions[session_id]
                
                # Clean up associated rate limiting data
                bucket_key = f"session:{session_id}"
                if bucket_key in self.token_buckets:
                    del self.token_buckets[bucket_key]
                
                # Clean up sliding windows
                windows_to_remove = [key for key in self.sliding_windows.keys() 
                                   if key.startswith(f"tool:{session_id}:") or 
                                      key.startswith(f"category:{session_id}:")]
                for key in windows_to_remove:
                    del self.sliding_windows[key]
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            return len(expired_sessions)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        with self._lock:
            return {
                'active_sessions': len(self.sessions),
                'total_token_buckets': len(self.token_buckets),
                'total_sliding_windows': len(self.sliding_windows),
                'memory_usage': {
                    'sessions': len(self.sessions),
                    'token_buckets': len(self.token_buckets),
                    'sliding_windows': sum(len(w.requests) for w in self.sliding_windows.values())
                }
            }


# Global rate limiter instance
_global_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


def rate_limit_decorator(tool_category: str = 'general'):
    """
    Decorator for MCP tools to apply rate limiting.
    
    Args:
        tool_category: Category of the tool for rate limiting
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract session information from context
            # This would be integrated with the MCP server context
            session_id = kwargs.get('session_id', 'default')
            tool_name = func.__name__
            
            rate_limiter = get_rate_limiter()
            allowed, error_msg, info = rate_limiter.check_rate_limit(
                session_id=session_id,
                tool_name=tool_name,
                tool_category=tool_category
            )
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {tool_name}: {error_msg}")
                raise Exception(f"Rate limit exceeded: {error_msg}")
            
            # Log rate limiting info for monitoring
            logger.debug(f"Rate limit check passed for {tool_name}: {info}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test the rate limiting system
    import time
    
    print("Testing rate limiting system...")
    
    limiter = RateLimiter()
    
    # Test session-level limiting
    print("\n1. Testing session-level rate limiting:")
    session_id = "test_session_1"
    
    for i in range(105):  # Exceed the default limit of 100
        allowed, error, info = limiter.check_rate_limit(
            session_id=session_id,
            tool_name="test_tool",
            tool_category="general"
        )
        
        if not allowed:
            print(f"Request {i+1}: BLOCKED - {error}")
            break
        elif i % 20 == 0:
            print(f"Request {i+1}: ALLOWED")
    
    # Test tool-specific limiting
    print("\n2. Testing tool-specific rate limiting:")
    session_id = "test_session_2"
    
    for i in range(12):  # Exceed AI tools limit of 5
        allowed, error, info = limiter.check_rate_limit(
            session_id=session_id,
            tool_name="ai_code_generator",
            tool_category="ai_features"
        )
        
        if not allowed:
            print(f"AI request {i+1}: BLOCKED - {error}")
            break
        else:
            print(f"AI request {i+1}: ALLOWED")
    
    # Test system stats
    print("\n3. System statistics:")
    stats = limiter.get_system_stats()
    print(f"Active sessions: {stats['active_sessions']}")
    print(f"Token buckets: {stats['total_token_buckets']}")
    print(f"Sliding windows: {stats['total_sliding_windows']}")
    
    # Test session stats
    print(f"\n4. Session statistics for {session_id}:")
    session_stats = limiter.get_session_stats(session_id)
    if session_stats:
        print(f"Total requests: {session_stats['total_requests']}")
        print(f"Violations: {session_stats['violations']}")
        print(f"Session age: {session_stats['session_age']:.1f} seconds")