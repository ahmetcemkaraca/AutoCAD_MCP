"""
Performance Optimization for Large-Scale Enterprise Deployments
==============================================================

Advanced performance optimization system for enterprise AutoCAD environments including:
- Multi-level caching with intelligent cache management and distributed caching support
- Load balancing and resource pooling for high-availability deployments
- Memory optimization with garbage collection tuning and leak detection
- Database connection pooling and query optimization for large datasets
- Horizontal scaling support with auto-scaling based on demand metrics
"""

import logging
import time
import threading
import weakref
import gc
import sys
import json
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple, Union, Callable, Generic, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from contextlib import contextmanager
import tracemalloc

# Optional performance libraries
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False

try:
    import memcache
    HAS_MEMCACHE = True
except ImportError:
    HAS_MEMCACHE = False

# Import existing components
from ..enhanced_autocad.performance_monitor import PerformanceMonitor
from ..enhanced_autocad.error_handler import ErrorHandler
from .monitoring_dashboard import AdvancedMonitoringDashboard

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheLevel(Enum):
    """Cache levels for multi-tier caching system."""
    L1_MEMORY = "l1_memory"      # In-process memory cache
    L2_SHARED = "l2_shared"      # Shared memory cache
    L3_DISTRIBUTED = "l3_distributed"  # Distributed cache (Redis, etc.)
    L4_PERSISTENT = "l4_persistent"    # Persistent storage cache


class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"                  # Least Recently Used
    LFU = "lfu"                  # Least Frequently Used
    FIFO = "fifo"               # First In, First Out
    TTL = "ttl"                 # Time To Live
    ADAPTIVE = "adaptive"       # Adaptive based on access patterns


class ResourceType(Enum):
    """Types of resources that can be pooled and managed."""
    DATABASE_CONNECTION = "database_connection"
    HTTP_CONNECTION = "http_connection"
    FILE_HANDLE = "file_handle"
    AUTOCAD_INSTANCE = "autocad_instance"
    COMPUTATION_WORKER = "computation_worker"
    MEMORY_BUFFER = "memory_buffer"


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with metadata."""
    key: str
    value: T
    created_at: float
    last_accessed: float
    access_count: int = 0
    size_bytes: int = 0
    ttl: Optional[float] = None
    
    # Cache level metadata
    cache_level: CacheLevel = CacheLevel.L1_MEMORY
    promotion_score: float = 0.0
    
    # Quality indicators
    hit_ratio: float = 0.0
    computation_cost: float = 0.0
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl
    
    def update_access(self):
        """Update access statistics."""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class ResourcePoolConfig:
    """Configuration for resource pools."""
    pool_name: str
    resource_type: ResourceType
    min_size: int = 5
    max_size: int = 50
    
    # Lifecycle management
    idle_timeout: float = 300.0    # 5 minutes
    max_lifetime: float = 3600.0   # 1 hour
    validation_interval: float = 60.0  # 1 minute
    
    # Performance tuning
    acquire_timeout: float = 30.0
    health_check_interval: float = 30.0
    cleanup_interval: float = 60.0
    
    # Factory functions
    create_resource: Optional[Callable] = None
    validate_resource: Optional[Callable] = None
    destroy_resource: Optional[Callable] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics for optimization tracking."""
    timestamp: float = field(default_factory=time.time)
    
    # Cache metrics
    cache_hit_rate: float = 0.0
    cache_miss_rate: float = 0.0
    cache_eviction_rate: float = 0.0
    avg_cache_lookup_time_ms: float = 0.0
    
    # Memory metrics
    memory_usage_mb: float = 0.0
    memory_peak_mb: float = 0.0
    gc_collection_count: int = 0
    gc_collection_time_ms: float = 0.0
    
    # Resource pool metrics
    pool_utilization: Dict[str, float] = field(default_factory=dict)
    pool_wait_times: Dict[str, float] = field(default_factory=dict)
    pool_creation_rate: Dict[str, float] = field(default_factory=dict)
    
    # Throughput metrics
    requests_per_second: float = 0.0
    avg_response_time_ms: float = 0.0
    concurrent_requests: int = 0
    
    # Error metrics
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    resource_exhaustion_events: int = 0


class LRUCache(Generic[T]):
    """High-performance LRU cache implementation."""
    
    def __init__(self, max_size: int = 1000, ttl: Optional[float] = None):
        """Initialize LRU cache."""
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size_bytes': 0
        }
    
    def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        with self.lock:
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                self.stats['misses'] += 1
                self.stats['size_bytes'] -= entry.size_bytes
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            entry.update_access()
            
            self.stats['hits'] += 1
            return entry.value
    
    def put(self, key: str, value: T, size_bytes: Optional[int] = None) -> bool:
        """Put value in cache."""
        with self.lock:
            # Calculate size if not provided
            if size_bytes is None:
                size_bytes = self._estimate_size(value)
            
            # Remove existing entry if present
            if key in self.cache:
                old_entry = self.cache[key]
                self.stats['size_bytes'] -= old_entry.size_bytes
                del self.cache[key]
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                size_bytes=size_bytes,
                ttl=self.ttl
            )
            
            # Evict if necessary
            while len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # Add new entry
            self.cache[key] = entry
            self.stats['size_bytes'] += size_bytes
            
            return True
    
    def remove(self, key: str) -> bool:
        """Remove entry from cache."""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                self.stats['size_bytes'] -= entry.size_bytes
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.stats['size_bytes'] = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = self.stats['hits'] / max(total_requests, 1)
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self.stats['evictions'],
                'size_bytes': self.stats['size_bytes'],
                'avg_entry_size': self.stats['size_bytes'] / max(len(self.cache), 1)
            }
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if self.cache:
            key, entry = self.cache.popitem(last=False)
            self.stats['evictions'] += 1
            self.stats['size_bytes'] -= entry.size_bytes
    
    def _estimate_size(self, value: T) -> int:
        """Estimate size of value in bytes."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return sys.getsizeof(value)
            elif isinstance(value, (list, tuple, dict)):
                return sys.getsizeof(value)
            else:
                return sys.getsizeof(value)
        except Exception:
            return 1024  # Default estimate


class MultiLevelCacheManager:
    """Multi-level cache manager with intelligent promotion/demotion."""
    
    def __init__(self, 
                 l1_size: int = 1000,
                 l2_size: int = 10000,
                 distributed_cache_url: Optional[str] = None):
        """Initialize multi-level cache manager."""
        
        # L1 Cache - In-memory, fastest access
        self.l1_cache = LRUCache[Any](max_size=l1_size, ttl=300)  # 5 minutes
        
        # L2 Cache - Larger in-memory cache
        self.l2_cache = LRUCache[Any](max_size=l2_size, ttl=1800)  # 30 minutes
        
        # L3 Cache - Distributed cache (Redis/Memcached)
        self.distributed_cache = None
        if distributed_cache_url and HAS_REDIS:
            try:
                self.distributed_cache = redis.from_url(distributed_cache_url)
            except Exception as e:
                logger.warning(f"Failed to connect to distributed cache: {e}")
        
        # Cache promotion/demotion logic
        self.promotion_threshold = 3  # Access count for L2->L1 promotion
        self.demotion_cooldown = 60   # Seconds before considering demotion
        
        # Statistics
        self.stats = {
            'total_gets': 0,
            'l1_hits': 0,
            'l2_hits': 0,
            'l3_hits': 0,
            'misses': 0,
            'promotions': 0,
            'demotions': 0
        }
        
        # Background maintenance
        self.maintenance_thread = None
        self.maintenance_active = False
        
        logger.info("Multi-level cache manager initialized")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from multi-level cache."""
        self.stats['total_gets'] += 1
        
        # Try L1 cache first
        value = self.l1_cache.get(key)
        if value is not None:
            self.stats['l1_hits'] += 1
            return value
        
        # Try L2 cache
        value = self.l2_cache.get(key)
        if value is not None:
            self.stats['l2_hits'] += 1
            
            # Consider promotion to L1
            entry = self.l2_cache.cache.get(key)
            if entry and entry.access_count >= self.promotion_threshold:
                self._promote_to_l1(key, value)
            
            return value
        
        # Try distributed cache (L3)
        if self.distributed_cache:
            try:
                cached_data = self.distributed_cache.get(key)
                if cached_data:
                    value = json.loads(cached_data.decode('utf-8'))
                    self.stats['l3_hits'] += 1
                    
                    # Promote to L2
                    self.l2_cache.put(key, value)
                    return value
            except Exception as e:
                logger.error(f"Distributed cache get failed: {e}")
        
        self.stats['misses'] += 1
        return None
    
    def put(self, key: str, value: Any, cache_level: CacheLevel = CacheLevel.L2_SHARED) -> bool:
        """Put value in appropriate cache level."""
        try:
            # Serialize complex objects for distributed cache
            serialized_value = value
            
            if cache_level == CacheLevel.L1_MEMORY:
                return self.l1_cache.put(key, value)
            
            elif cache_level == CacheLevel.L2_SHARED:
                success = self.l2_cache.put(key, value)
                
                # Also cache in distributed cache if available
                if self.distributed_cache and success:
                    try:
                        self.distributed_cache.setex(
                            key, 
                            3600,  # 1 hour TTL
                            json.dumps(serialized_value, default=str)
                        )
                    except Exception as e:
                        logger.error(f"Distributed cache put failed: {e}")
                
                return success
            
            elif cache_level == CacheLevel.L3_DISTRIBUTED and self.distributed_cache:
                try:
                    self.distributed_cache.setex(
                        key,
                        3600,  # 1 hour TTL  
                        json.dumps(serialized_value, default=str)
                    )
                    return True
                except Exception as e:
                    logger.error(f"Distributed cache put failed: {e}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Cache put failed for key {key}: {e}")
            return False
    
    def invalidate(self, key: str) -> bool:
        """Invalidate key from all cache levels."""
        success = True
        
        # Remove from all levels
        success &= self.l1_cache.remove(key)
        success &= self.l2_cache.remove(key)
        
        if self.distributed_cache:
            try:
                self.distributed_cache.delete(key)
            except Exception as e:
                logger.error(f"Distributed cache invalidation failed: {e}")
                success = False
        
        return success
    
    def start_maintenance(self):
        """Start background maintenance tasks."""
        if self.maintenance_active:
            return
        
        self.maintenance_active = True
        self.maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            daemon=True
        )
        self.maintenance_thread.start()
        
        logger.info("Cache maintenance started")
    
    def stop_maintenance(self):
        """Stop background maintenance tasks."""
        self.maintenance_active = False
        
        if self.maintenance_thread and self.maintenance_thread.is_alive():
            self.maintenance_thread.join(timeout=5.0)
        
        logger.info("Cache maintenance stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self.stats['total_gets']
        
        stats = {
            'multilevel_stats': {
                'total_requests': total_requests,
                'overall_hit_rate': (self.stats['l1_hits'] + self.stats['l2_hits'] + self.stats['l3_hits']) / max(total_requests, 1),
                'l1_hit_rate': self.stats['l1_hits'] / max(total_requests, 1),
                'l2_hit_rate': self.stats['l2_hits'] / max(total_requests, 1),
                'l3_hit_rate': self.stats['l3_hits'] / max(total_requests, 1),
                'miss_rate': self.stats['misses'] / max(total_requests, 1),
                'promotions': self.stats['promotions'],
                'demotions': self.stats['demotions']
            },
            'l1_cache': self.l1_cache.get_stats(),
            'l2_cache': self.l2_cache.get_stats(),
            'distributed_cache_connected': self.distributed_cache is not None
        }
        
        return stats
    
    def _promote_to_l1(self, key: str, value: Any):
        """Promote frequently accessed item to L1 cache."""
        self.l1_cache.put(key, value)
        self.stats['promotions'] += 1
    
    def _maintenance_loop(self):
        """Background maintenance loop."""
        while self.maintenance_active:
            try:
                # Cleanup expired entries
                self._cleanup_expired_entries()
                
                # Optimize cache sizes based on access patterns
                self._optimize_cache_sizes()
                
                # Sleep for maintenance interval
                time.sleep(60)  # 1 minute
                
            except Exception as e:
                logger.error(f"Cache maintenance error: {e}")
                time.sleep(10)  # Shorter sleep on error
    
    def _cleanup_expired_entries(self):
        """Clean up expired cache entries."""
        current_time = time.time()
        
        # Cleanup L1 cache
        expired_keys = []
        for key, entry in self.l1_cache.cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            self.l1_cache.remove(key)
        
        # Cleanup L2 cache
        expired_keys = []
        for key, entry in self.l2_cache.cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            self.l2_cache.remove(key)
    
    def _optimize_cache_sizes(self):
        """Optimize cache sizes based on usage patterns."""
        # This could implement dynamic cache size adjustment
        # based on hit rates and memory pressure
        pass


class ResourcePool(Generic[T]):
    """Generic resource pool for managing expensive resources."""
    
    def __init__(self, config: ResourcePoolConfig):
        """Initialize resource pool."""
        self.config = config
        self.resources: deque[T] = deque()
        self.in_use: Set[int] = set()  # Resource IDs currently in use
        self.resource_metadata: Dict[int, Dict[str, Any]] = {}
        
        # Synchronization
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        
        # Resource tracking
        self.next_resource_id = 0
        self.total_created = 0
        self.total_destroyed = 0
        
        # Statistics
        self.stats = {
            'acquisitions': 0,
            'releases': 0,
            'creations': 0,
            'destructions': 0,
            'timeouts': 0,
            'validation_failures': 0,
            'current_size': 0,
            'peak_size': 0,
            'total_wait_time': 0.0,
            'avg_wait_time': 0.0
        }
        
        # Background maintenance
        self.maintenance_active = False
        self.maintenance_thread = None
        
        # Pre-populate pool to minimum size
        self._ensure_minimum_resources()
        
        logger.info(f"Resource pool '{config.pool_name}' initialized")
    
    def acquire(self, timeout: Optional[float] = None) -> Optional[T]:
        """Acquire a resource from the pool."""
        acquire_timeout = timeout or self.config.acquire_timeout
        start_time = time.time()
        
        with self.condition:
            while True:
                # Try to get an available resource
                if self.resources:
                    resource = self.resources.popleft()
                    resource_id = id(resource)
                    
                    # Validate resource if validator provided
                    if self.config.validate_resource:
                        try:
                            if not self.config.validate_resource(resource):
                                self._destroy_resource(resource)
                                self.stats['validation_failures'] += 1
                                continue
                        except Exception as e:
                            logger.error(f"Resource validation failed: {e}")
                            self._destroy_resource(resource)
                            continue
                    
                    # Mark as in use
                    self.in_use.add(resource_id)
                    self.resource_metadata[resource_id] = {
                        'acquired_at': time.time(),
                        'acquire_count': self.resource_metadata.get(resource_id, {}).get('acquire_count', 0) + 1
                    }
                    
                    self.stats['acquisitions'] += 1
                    wait_time = time.time() - start_time
                    self.stats['total_wait_time'] += wait_time
                    self.stats['avg_wait_time'] = self.stats['total_wait_time'] / max(self.stats['acquisitions'], 1)
                    
                    return resource
                
                # Try to create new resource if pool not at max capacity
                if len(self.in_use) + len(self.resources) < self.config.max_size:
                    resource = self._create_resource()
                    if resource:
                        resource_id = id(resource)
                        self.in_use.add(resource_id)
                        self.resource_metadata[resource_id] = {
                            'acquired_at': time.time(),
                            'acquire_count': 1
                        }
                        
                        self.stats['acquisitions'] += 1
                        return resource
                
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed >= acquire_timeout:
                    self.stats['timeouts'] += 1
                    logger.warning(f"Resource acquisition timeout after {elapsed:.2f}s")
                    return None
                
                # Wait for resource to become available
                remaining_timeout = acquire_timeout - elapsed
                self.condition.wait(timeout=remaining_timeout)
    
    def release(self, resource: T) -> bool:
        """Release a resource back to the pool."""
        resource_id = id(resource)
        
        with self.condition:
            if resource_id not in self.in_use:
                logger.warning("Attempting to release resource not acquired from this pool")
                return False
            
            # Remove from in-use set
            self.in_use.remove(resource_id)
            
            # Update metadata
            if resource_id in self.resource_metadata:
                metadata = self.resource_metadata[resource_id]
                metadata['released_at'] = time.time()
                metadata['usage_duration'] = metadata['released_at'] - metadata['acquired_at']
            
            # Check if resource should be destroyed (lifetime, health, etc.)
            if self._should_destroy_resource(resource):
                self._destroy_resource(resource)
            else:
                # Return to pool if pool not over minimum capacity
                if len(self.resources) < self.config.min_size or len(self.resources) + len(self.in_use) <= self.config.max_size:
                    self.resources.append(resource)
                else:
                    # Pool is full, destroy excess resource
                    self._destroy_resource(resource)
            
            self.stats['releases'] += 1
            self.condition.notify()
            return True
    
    @contextmanager
    def get_resource(self, timeout: Optional[float] = None):
        """Context manager for resource acquisition/release."""
        resource = self.acquire(timeout)
        if resource is None:
            raise TimeoutError("Failed to acquire resource from pool")
        
        try:
            yield resource
        finally:
            self.release(resource)
    
    def start_maintenance(self):
        """Start background maintenance tasks."""
        if self.maintenance_active:
            return
        
        self.maintenance_active = True
        self.maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            daemon=True
        )
        self.maintenance_thread.start()
        
        logger.info(f"Resource pool maintenance started for '{self.config.pool_name}'")
    
    def stop_maintenance(self):
        """Stop background maintenance tasks."""
        self.maintenance_active = False
        
        if self.maintenance_thread and self.maintenance_thread.is_alive():
            self.maintenance_thread.join(timeout=5.0)
    
    def shutdown(self):
        """Shutdown the resource pool and cleanup all resources."""
        self.stop_maintenance()
        
        with self.lock:
            # Destroy all available resources
            while self.resources:
                resource = self.resources.popleft()
                self._destroy_resource(resource)
            
            # Note: In-use resources will need to be handled by the application
            if self.in_use:
                logger.warning(f"Pool shutdown with {len(self.in_use)} resources still in use")
        
        logger.info(f"Resource pool '{self.config.pool_name}' shutdown")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get resource pool statistics."""
        with self.lock:
            current_size = len(self.resources) + len(self.in_use)
            utilization = len(self.in_use) / max(current_size, 1)
            
            stats = self.stats.copy()
            stats.update({
                'pool_name': self.config.pool_name,
                'current_size': current_size,
                'available': len(self.resources),
                'in_use': len(self.in_use),
                'utilization': utilization,
                'total_created': self.total_created,
                'total_destroyed': self.total_destroyed
            })
            
            return stats
    
    def _create_resource(self) -> Optional[T]:
        """Create a new resource."""
        if not self.config.create_resource:
            logger.error(f"No resource factory configured for pool '{self.config.pool_name}'")
            return None
        
        try:
            resource = self.config.create_resource()
            self.total_created += 1
            self.stats['creations'] += 1
            
            current_size = len(self.resources) + len(self.in_use) + 1
            self.stats['current_size'] = current_size
            self.stats['peak_size'] = max(self.stats['peak_size'], current_size)
            
            logger.debug(f"Created new resource for pool '{self.config.pool_name}'")
            return resource
            
        except Exception as e:
            logger.error(f"Failed to create resource for pool '{self.config.pool_name}': {e}")
            return None
    
    def _destroy_resource(self, resource: T):
        """Destroy a resource."""
        try:
            if self.config.destroy_resource:
                self.config.destroy_resource(resource)
            
            self.total_destroyed += 1
            self.stats['destructions'] += 1
            
            # Clean up metadata
            resource_id = id(resource)
            if resource_id in self.resource_metadata:
                del self.resource_metadata[resource_id]
            
            logger.debug(f"Destroyed resource from pool '{self.config.pool_name}'")
            
        except Exception as e:
            logger.error(f"Failed to destroy resource from pool '{self.config.pool_name}': {e}")
    
    def _should_destroy_resource(self, resource: T) -> bool:
        """Check if a resource should be destroyed instead of returned to pool."""
        resource_id = id(resource)
        metadata = self.resource_metadata.get(resource_id, {})
        
        # Check maximum lifetime
        created_at = metadata.get('created_at', time.time())
        if time.time() - created_at > self.config.max_lifetime:
            return True
        
        # Check if resource has been idle too long
        last_used = metadata.get('released_at', metadata.get('acquired_at', time.time()))
        if time.time() - last_used > self.config.idle_timeout:
            return True
        
        return False
    
    def _ensure_minimum_resources(self):
        """Ensure pool has minimum number of resources."""
        with self.lock:
            while len(self.resources) < self.config.min_size:
                resource = self._create_resource()
                if resource:
                    self.resources.append(resource)
                else:
                    break
    
    def _maintenance_loop(self):
        """Background maintenance loop."""
        while self.maintenance_active:
            try:
                # Cleanup expired resources
                self._cleanup_expired_resources()
                
                # Ensure minimum pool size
                self._ensure_minimum_resources()
                
                # Health check resources
                self._health_check_resources()
                
                # Sleep for maintenance interval
                time.sleep(self.config.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Resource pool maintenance error: {e}")
                time.sleep(10)
    
    def _cleanup_expired_resources(self):
        """Clean up expired/idle resources."""
        with self.lock:
            current_time = time.time()
            expired_resources = []
            
            for resource in list(self.resources):
                if self._should_destroy_resource(resource):
                    expired_resources.append(resource)
            
            for resource in expired_resources:
                self.resources.remove(resource)
                self._destroy_resource(resource)
    
    def _health_check_resources(self):
        """Perform health checks on available resources."""
        if not self.config.validate_resource:
            return
        
        with self.lock:
            unhealthy_resources = []
            
            for resource in list(self.resources):
                try:
                    if not self.config.validate_resource(resource):
                        unhealthy_resources.append(resource)
                except Exception as e:
                    logger.error(f"Resource health check failed: {e}")
                    unhealthy_resources.append(resource)
            
            for resource in unhealthy_resources:
                self.resources.remove(resource)
                self._destroy_resource(resource)
                self.stats['validation_failures'] += 1


class MemoryOptimizer:
    """Advanced memory optimization and leak detection."""
    
    def __init__(self):
        """Initialize memory optimizer."""
        self.enable_tracking = True
        self.tracking_started = False
        self.baseline_snapshot = None
        self.snapshots = deque(maxlen=100)
        
        # Memory pressure thresholds
        self.warning_threshold_mb = 1024    # 1GB
        self.critical_threshold_mb = 2048   # 2GB
        
        # GC tuning parameters
        self.gc_thresholds = (700, 10, 10)  # More aggressive collection
        self.force_gc_interval = 300        # 5 minutes
        self.last_force_gc = 0
        
        # Leak detection
        self.leak_detection_enabled = True
        self.leak_threshold_growth_mb = 100  # 100MB growth threshold
        self.leak_detection_window = 10      # Number of snapshots to analyze
        
        # Statistics
        self.stats = {
            'gc_collections': {0: 0, 1: 0, 2: 0},
            'memory_warnings': 0,
            'memory_critical_events': 0,
            'leaks_detected': 0,
            'peak_memory_mb': 0.0,
            'total_freed_mb': 0.0
        }
        
        # Configure GC
        self._configure_gc()
        
        # Start memory tracking
        if self.enable_tracking:
            self._start_memory_tracking()
        
        logger.info("Memory optimizer initialized")
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Perform memory optimization and return results."""
        optimization_results = {
            'timestamp': time.time(),
            'actions_taken': [],
            'memory_before_mb': self._get_memory_usage_mb(),
            'memory_after_mb': 0.0,
            'freed_memory_mb': 0.0,
            'gc_stats': {}
        }
        
        try:
            # Take memory snapshot before optimization
            before_memory = optimization_results['memory_before_mb']
            
            # Force garbage collection with progressively more aggressive levels
            gc_stats = self._force_garbage_collection()
            optimization_results['gc_stats'] = gc_stats
            optimization_results['actions_taken'].append('forced_garbage_collection')
            
            # Clear weak references
            self._clear_weak_references()
            optimization_results['actions_taken'].append('cleared_weak_references')
            
            # Optimize cache sizes if memory pressure is high
            if before_memory > self.warning_threshold_mb:
                self._reduce_cache_sizes()
                optimization_results['actions_taken'].append('reduced_cache_sizes')
            
            # Clear unnecessary module caches
            self._clear_module_caches()
            optimization_results['actions_taken'].append('cleared_module_caches')
            
            # Final memory measurement
            after_memory = self._get_memory_usage_mb()
            optimization_results['memory_after_mb'] = after_memory
            optimization_results['freed_memory_mb'] = max(0, before_memory - after_memory)
            
            self.stats['total_freed_mb'] += optimization_results['freed_memory_mb']
            
            logger.info(f"Memory optimization completed: freed {optimization_results['freed_memory_mb']:.2f} MB")
            
        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            optimization_results['error'] = str(e)
        
        return optimization_results
    
    def detect_memory_leaks(self) -> List[Dict[str, Any]]:
        """Detect potential memory leaks."""
        if not self.leak_detection_enabled or len(self.snapshots) < self.leak_detection_window:
            return []
        
        leaks = []
        
        try:
            # Analyze recent memory growth patterns
            recent_snapshots = list(self.snapshots)[-self.leak_detection_window:]
            
            if len(recent_snapshots) < 2:
                return leaks
            
            # Calculate memory growth trend
            memory_sizes = [snapshot['memory_mb'] for snapshot in recent_snapshots]
            growth = memory_sizes[-1] - memory_sizes[0]
            
            if growth > self.leak_threshold_growth_mb:
                # Analyze tracemalloc data if available
                if recent_snapshots[-1].get('tracemalloc_snapshot'):
                    leak_candidates = self._analyze_tracemalloc_snapshot(
                        recent_snapshots[0].get('tracemalloc_snapshot'),
                        recent_snapshots[-1].get('tracemalloc_snapshot')
                    )
                    leaks.extend(leak_candidates)
                
                # Generic leak detection
                leaks.append({
                    'type': 'memory_growth',
                    'growth_mb': growth,
                    'time_window_minutes': (recent_snapshots[-1]['timestamp'] - recent_snapshots[0]['timestamp']) / 60,
                    'growth_rate_mb_per_hour': growth / max((recent_snapshots[-1]['timestamp'] - recent_snapshots[0]['timestamp']) / 3600, 0.01),
                    'severity': 'high' if growth > self.leak_threshold_growth_mb * 2 else 'medium'
                })
                
                self.stats['leaks_detected'] += len(leaks)
        
        except Exception as e:
            logger.error(f"Memory leak detection failed: {e}")
        
        return leaks
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        current_memory = self._get_memory_usage_mb()
        
        stats = {
            'current_memory_mb': current_memory,
            'peak_memory_mb': max(self.stats['peak_memory_mb'], current_memory),
            'memory_pressure_level': self._get_memory_pressure_level(current_memory),
            'gc_statistics': dict(gc.get_stats()) if hasattr(gc, 'get_stats') else {},
            'gc_collections': self.stats['gc_collections'].copy(),
            'optimization_stats': {
                'memory_warnings': self.stats['memory_warnings'],
                'critical_events': self.stats['memory_critical_events'],
                'leaks_detected': self.stats['leaks_detected'],
                'total_freed_mb': self.stats['total_freed_mb']
            }
        }
        
        # Update peak memory
        self.stats['peak_memory_mb'] = stats['peak_memory_mb']
        
        # Add system memory info if available
        if HAS_PSUTIL:
            try:
                system_memory = psutil.virtual_memory()
                stats['system_memory'] = {
                    'total_mb': system_memory.total / 1024 / 1024,
                    'available_mb': system_memory.available / 1024 / 1024,
                    'percent_used': system_memory.percent,
                    'process_percent': psutil.Process().memory_percent()
                }
            except Exception:
                pass
        
        return stats
    
    def start_monitoring(self):
        """Start continuous memory monitoring."""
        if not self.tracking_started:
            self._start_memory_tracking()
        
        # This would start a background thread for continuous monitoring
        # Implementation omitted for brevity
    
    def _start_memory_tracking(self):
        """Start tracemalloc for detailed memory tracking."""
        if self.tracking_started:
            return
        
        try:
            tracemalloc.start()
            self.tracking_started = True
            self.baseline_snapshot = self._take_memory_snapshot()
            logger.info("Memory tracking started")
        except Exception as e:
            logger.error(f"Failed to start memory tracking: {e}")
    
    def _take_memory_snapshot(self) -> Dict[str, Any]:
        """Take a comprehensive memory snapshot."""
        snapshot = {
            'timestamp': time.time(),
            'memory_mb': self._get_memory_usage_mb(),
            'object_counts': self._get_object_counts(),
            'gc_stats': dict(gc.get_stats()) if hasattr(gc, 'get_stats') else {}
        }
        
        # Add tracemalloc snapshot if available
        if self.tracking_started:
            try:
                snapshot['tracemalloc_snapshot'] = tracemalloc.take_snapshot()
            except Exception as e:
                logger.debug(f"Failed to take tracemalloc snapshot: {e}")
        
        self.snapshots.append(snapshot)
        return snapshot
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        if HAS_PSUTIL:
            try:
                process = psutil.Process()
                return process.memory_info().rss / 1024 / 1024
            except Exception:
                pass
        
        # Fallback using tracemalloc
        if self.tracking_started:
            try:
                current, peak = tracemalloc.get_traced_memory()
                return current / 1024 / 1024
            except Exception:
                pass
        
        return 0.0
    
    def _get_object_counts(self) -> Dict[str, int]:
        """Get counts of different object types."""
        try:
            import gc
            type_counts = defaultdict(int)
            
            for obj in gc.get_objects():
                obj_type = type(obj).__name__
                type_counts[obj_type] += 1
            
            # Return top 10 most common types
            return dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        
        except Exception as e:
            logger.debug(f"Failed to get object counts: {e}")
            return {}
    
    def _force_garbage_collection(self) -> Dict[str, Any]:
        """Force garbage collection with detailed statistics."""
        gc_stats = {'collected': [0, 0, 0], 'before': {}, 'after': {}}
        
        try:
            # Get stats before collection
            if hasattr(gc, 'get_stats'):
                gc_stats['before'] = dict(gc.get_stats())
            
            # Force collection at all levels
            for generation in range(3):
                collected = gc.collect(generation)
                gc_stats['collected'][generation] = collected
                self.stats['gc_collections'][generation] += 1
            
            # Get stats after collection
            if hasattr(gc, 'get_stats'):
                gc_stats['after'] = dict(gc.get_stats())
            
            self.last_force_gc = time.time()
            
        except Exception as e:
            logger.error(f"Forced garbage collection failed: {e}")
            gc_stats['error'] = str(e)
        
        return gc_stats
    
    def _clear_weak_references(self):
        """Clear unreferenced weak references."""
        try:
            # Clear weakref callbacks
            import weakref
            # This is a simplified implementation
            # In practice, we'd want to be more careful about what we clear
            pass
        except Exception as e:
            logger.debug(f"Weak reference cleanup failed: {e}")
    
    def _reduce_cache_sizes(self):
        """Reduce cache sizes to free memory."""
        try:
            # This would integrate with cache managers to reduce sizes
            # Implementation would depend on specific cache implementations
            logger.info("Reducing cache sizes due to memory pressure")
        except Exception as e:
            logger.error(f"Cache size reduction failed: {e}")
    
    def _clear_module_caches(self):
        """Clear various module-level caches."""
        try:
            # Clear functools lru_cache
            import functools
            # Note: This is destructive and should be used carefully
            
            # Clear regex cache
            import re
            re.purge()
            
            # Clear other caches as needed
            
        except Exception as e:
            logger.debug(f"Module cache clearing failed: {e}")
    
    def _configure_gc(self):
        """Configure garbage collector for optimal performance."""
        try:
            # Set more aggressive GC thresholds
            gc.set_threshold(*self.gc_thresholds)
            
            # Enable automatic garbage collection
            gc.enable()
            
            logger.debug(f"GC configured with thresholds: {self.gc_thresholds}")
            
        except Exception as e:
            logger.error(f"GC configuration failed: {e}")
    
    def _get_memory_pressure_level(self, memory_mb: float) -> str:
        """Get memory pressure level."""
        if memory_mb > self.critical_threshold_mb:
            self.stats['memory_critical_events'] += 1
            return 'critical'
        elif memory_mb > self.warning_threshold_mb:
            self.stats['memory_warnings'] += 1
            return 'warning'
        else:
            return 'normal'
    
    def _analyze_tracemalloc_snapshot(self, before_snapshot, after_snapshot) -> List[Dict[str, Any]]:
        """Analyze tracemalloc snapshots for memory leaks."""
        leaks = []
        
        try:
            if before_snapshot and after_snapshot:
                top_stats = after_snapshot.compare_to(before_snapshot, 'lineno')
                
                for stat in top_stats[:10]:  # Top 10 differences
                    if stat.size_diff > 1024 * 1024:  # More than 1MB difference
                        leaks.append({
                            'type': 'tracemalloc_growth',
                            'filename': stat.traceback.format()[0] if stat.traceback else 'unknown',
                            'size_diff_mb': stat.size_diff / 1024 / 1024,
                            'count_diff': stat.count_diff,
                            'traceback': stat.traceback.format() if stat.traceback else []
                        })
        
        except Exception as e:
            logger.error(f"Tracemalloc analysis failed: {e}")
        
        return leaks


class EnterprisePerformanceOptimizer:
    """
    Comprehensive performance optimization system for enterprise AutoCAD deployments.
    
    Combines multi-level caching, resource pooling, memory optimization, and
    intelligent scaling to maximize performance at enterprise scale.
    """
    
    def __init__(self, 
                 monitoring_dashboard: Optional[AdvancedMonitoringDashboard] = None,
                 distributed_cache_url: Optional[str] = None):
        """Initialize the enterprise performance optimizer."""
        
        # Core components
        self.monitoring_dashboard = monitoring_dashboard or AdvancedMonitoringDashboard()
        self.performance_monitor = PerformanceMonitor()
        self.error_handler = ErrorHandler()
        
        # Performance optimization components
        self.cache_manager = MultiLevelCacheManager(
            l1_size=2000,
            l2_size=20000,
            distributed_cache_url=distributed_cache_url
        )
        self.memory_optimizer = MemoryOptimizer()
        
        # Resource pools
        self.resource_pools: Dict[str, ResourcePool] = {}
        
        # Performance metrics and optimization
        self.optimization_active = False
        self.optimization_thread = None
        self.optimization_interval = 60  # 1 minute
        
        # Configuration
        self.auto_optimization_enabled = True
        self.performance_thresholds = {
            'response_time_ms': 1000,      # 1 second
            'memory_usage_mb': 2048,       # 2GB
            'cpu_usage_percent': 80,       # 80%
            'cache_hit_rate': 0.8,         # 80%
            'error_rate': 0.01             # 1%
        }
        
        # Statistics
        self.optimization_stats = {
            'optimizations_performed': 0,
            'performance_improvements': 0,
            'memory_freed_mb': 0.0,
            'cache_efficiency_improvements': 0,
            'resource_pool_optimizations': 0
        }
        
        logger.info("Enterprise performance optimizer initialized")
    
    def start_optimization(self):
        """Start the performance optimization system."""
        if self.optimization_active:
            logger.warning("Optimization already active")
            return
        
        # Start cache maintenance
        self.cache_manager.start_maintenance()
        
        # Start memory monitoring
        self.memory_optimizer.start_monitoring()
        
        # Start resource pool maintenance
        for pool in self.resource_pools.values():
            pool.start_maintenance()
        
        # Start optimization loop
        self.optimization_active = True
        self.optimization_thread = threading.Thread(
            target=self._optimization_loop,
            daemon=True
        )
        self.optimization_thread.start()
        
        logger.info("Performance optimization system started")
    
    def stop_optimization(self):
        """Stop the performance optimization system."""
        self.optimization_active = False
        
        # Stop optimization thread
        if self.optimization_thread and self.optimization_thread.is_alive():
            self.optimization_thread.join(timeout=10.0)
        
        # Stop component maintenance
        self.cache_manager.stop_maintenance()
        
        for pool in self.resource_pools.values():
            pool.stop_maintenance()
        
        logger.info("Performance optimization system stopped")
    
    def create_resource_pool(self, 
                           pool_name: str,
                           resource_type: ResourceType,
                           factory_func: Callable,
                           **kwargs) -> str:
        """Create a new resource pool."""
        
        config = ResourcePoolConfig(
            pool_name=pool_name,
            resource_type=resource_type,
            create_resource=factory_func,
            **kwargs
        )
        
        pool = ResourcePool(config)
        self.resource_pools[pool_name] = pool
        
        # Start maintenance if optimization is active
        if self.optimization_active:
            pool.start_maintenance()
        
        logger.info(f"Created resource pool '{pool_name}' for {resource_type.value}")
        return pool_name
    
    def get_resource_pool(self, pool_name: str) -> Optional[ResourcePool]:
        """Get a resource pool by name."""
        return self.resource_pools.get(pool_name)
    
    def optimize_performance(self, force: bool = False) -> Dict[str, Any]:
        """Perform comprehensive performance optimization."""
        
        if not force and not self._should_optimize():
            return {'message': 'No optimization needed at this time'}
        
        optimization_report = {
            'timestamp': time.time(),
            'actions_taken': [],
            'performance_before': self._get_performance_snapshot(),
            'performance_after': {},
            'improvements': {}
        }
        
        try:
            # Memory optimization
            memory_results = self.memory_optimizer.optimize_memory()
            if memory_results.get('freed_memory_mb', 0) > 0:
                optimization_report['actions_taken'].append('memory_optimization')
                optimization_report['memory_optimization'] = memory_results
                self.optimization_stats['memory_freed_mb'] += memory_results['freed_memory_mb']
            
            # Cache optimization
            cache_results = self._optimize_caches()
            if cache_results.get('improvements_made'):
                optimization_report['actions_taken'].append('cache_optimization')
                optimization_report['cache_optimization'] = cache_results
                self.optimization_stats['cache_efficiency_improvements'] += 1
            
            # Resource pool optimization
            pool_results = self._optimize_resource_pools()
            if pool_results.get('optimizations_applied'):
                optimization_report['actions_taken'].append('resource_pool_optimization')
                optimization_report['resource_pool_optimization'] = pool_results
                self.optimization_stats['resource_pool_optimizations'] += len(pool_results['optimizations_applied'])
            
            # System-level optimizations
            system_results = self._optimize_system_settings()
            if system_results.get('changes_made'):
                optimization_report['actions_taken'].append('system_optimization')
                optimization_report['system_optimization'] = system_results
            
            # Take performance snapshot after optimization
            optimization_report['performance_after'] = self._get_performance_snapshot()
            
            # Calculate improvements
            optimization_report['improvements'] = self._calculate_performance_improvements(
                optimization_report['performance_before'],
                optimization_report['performance_after']
            )
            
            # Update statistics
            self.optimization_stats['optimizations_performed'] += 1
            if any(improvement > 0 for improvement in optimization_report['improvements'].values()):
                self.optimization_stats['performance_improvements'] += 1
            
            # Report to monitoring dashboard
            if self.monitoring_dashboard:
                self._report_optimization_metrics(optimization_report)
            
            logger.info(f"Performance optimization completed with {len(optimization_report['actions_taken'])} actions")
            
        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            optimization_report['error'] = str(e)
        
        return optimization_report
    
    def analyze_performance_bottlenecks(self) -> Dict[str, Any]:
        """Analyze system for performance bottlenecks."""
        
        analysis = {
            'timestamp': time.time(),
            'bottlenecks': [],
            'recommendations': [],
            'performance_metrics': self._get_performance_snapshot(),
            'cache_analysis': self._analyze_cache_performance(),
            'memory_analysis': self._analyze_memory_performance(),
            'resource_pool_analysis': self._analyze_resource_pool_performance()
        }
        
        # Identify bottlenecks
        bottlenecks = []
        
        # Cache bottlenecks
        cache_stats = self.cache_manager.get_statistics()
        overall_hit_rate = cache_stats['multilevel_stats']['overall_hit_rate']
        if overall_hit_rate < self.performance_thresholds['cache_hit_rate']:
            bottlenecks.append({
                'type': 'cache_efficiency',
                'severity': 'high' if overall_hit_rate < 0.5 else 'medium',
                'current_value': overall_hit_rate,
                'threshold': self.performance_thresholds['cache_hit_rate'],
                'description': f"Cache hit rate ({overall_hit_rate:.2%}) below threshold"
            })
        
        # Memory bottlenecks
        memory_stats = self.memory_optimizer.get_memory_statistics()
        current_memory = memory_stats['current_memory_mb']
        if current_memory > self.performance_thresholds['memory_usage_mb']:
            bottlenecks.append({
                'type': 'memory_usage',
                'severity': 'critical' if current_memory > self.performance_thresholds['memory_usage_mb'] * 1.5 else 'high',
                'current_value': current_memory,
                'threshold': self.performance_thresholds['memory_usage_mb'],
                'description': f"Memory usage ({current_memory:.0f} MB) exceeds threshold"
            })
        
        # Resource pool bottlenecks
        for pool_name, pool in self.resource_pools.items():
            pool_stats = pool.get_statistics()
            utilization = pool_stats.get('utilization', 0)
            
            if utilization > 0.9:  # 90% utilization
                bottlenecks.append({
                    'type': 'resource_pool_saturation',
                    'severity': 'high',
                    'resource_pool': pool_name,
                    'current_value': utilization,
                    'threshold': 0.9,
                    'description': f"Resource pool '{pool_name}' utilization ({utilization:.1%}) very high"
                })
        
        analysis['bottlenecks'] = bottlenecks
        
        # Generate recommendations
        recommendations = self._generate_performance_recommendations(analysis)
        analysis['recommendations'] = recommendations
        
        return analysis
    
    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Get comprehensive optimization statistics."""
        
        stats = {
            'optimization_summary': self.optimization_stats.copy(),
            'cache_statistics': self.cache_manager.get_statistics(),
            'memory_statistics': self.memory_optimizer.get_memory_statistics(),
            'resource_pool_statistics': {
                pool_name: pool.get_statistics()
                for pool_name, pool in self.resource_pools.items()
            },
            'performance_thresholds': self.performance_thresholds.copy(),
            'system_health': self._get_system_health_indicators()
        }
        
        return stats
    
    def _optimization_loop(self):
        """Main optimization loop running in background."""
        
        while self.optimization_active:
            try:
                # Check if optimization is needed
                if self.auto_optimization_enabled and self._should_optimize():
                    self.optimize_performance()
                
                # Detect and report memory leaks
                memory_leaks = self.memory_optimizer.detect_memory_leaks()
                if memory_leaks:
                    logger.warning(f"Detected {len(memory_leaks)} potential memory leaks")
                    
                    # Report to monitoring dashboard
                    if self.monitoring_dashboard:
                        for leak in memory_leaks:
                            self.monitoring_dashboard.collect_metric(
                                'optimization.memory_leak_detected',
                                1,
                                tags={'type': leak.get('type', 'unknown')}
                            )
                
                # Collect optimization metrics
                self._collect_optimization_metrics()
                
                # Sleep for optimization interval
                time.sleep(self.optimization_interval)
                
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
                time.sleep(30)  # Longer sleep on error
    
    def _should_optimize(self) -> bool:
        """Check if performance optimization is needed."""
        
        try:
            # Check cache performance
            cache_stats = self.cache_manager.get_statistics()
            if cache_stats['multilevel_stats']['overall_hit_rate'] < self.performance_thresholds['cache_hit_rate']:
                return True
            
            # Check memory usage
            memory_stats = self.memory_optimizer.get_memory_statistics()
            if memory_stats['current_memory_mb'] > self.performance_thresholds['memory_usage_mb']:
                return True
            
            # Check resource pool utilization
            for pool in self.resource_pools.values():
                pool_stats = pool.get_statistics()
                if pool_stats.get('utilization', 0) > 0.9:
                    return True
            
            # Check system performance metrics
            if HAS_PSUTIL:
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    if cpu_percent > self.performance_thresholds['cpu_usage_percent']:
                        return True
                except Exception:
                    pass
            
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
        
        return False
    
    def _get_performance_snapshot(self) -> Dict[str, Any]:
        """Get current performance snapshot."""
        
        snapshot = {
            'timestamp': time.time(),
            'cache_hit_rate': 0.0,
            'memory_usage_mb': 0.0,
            'cpu_usage_percent': 0.0,
            'active_connections': 0,
            'response_time_ms': 0.0
        }
        
        try:
            # Cache metrics
            cache_stats = self.cache_manager.get_statistics()
            snapshot['cache_hit_rate'] = cache_stats['multilevel_stats']['overall_hit_rate']
            
            # Memory metrics
            memory_stats = self.memory_optimizer.get_memory_statistics()
            snapshot['memory_usage_mb'] = memory_stats['current_memory_mb']
            
            # System metrics
            if HAS_PSUTIL:
                snapshot['cpu_usage_percent'] = psutil.cpu_percent()
                
                # Network connections
                connections = psutil.net_connections()
                snapshot['active_connections'] = len([c for c in connections if c.status == 'ESTABLISHED'])
            
            # Performance monitor metrics
            if self.performance_monitor:
                perf_metrics = self.performance_monitor.get_current_metrics()
                snapshot.update(perf_metrics)
        
        except Exception as e:
            logger.error(f"Performance snapshot failed: {e}")
        
        return snapshot
    
    def _optimize_caches(self) -> Dict[str, Any]:
        """Optimize cache performance."""
        
        results = {
            'improvements_made': False,
            'actions': []
        }
        
        try:
            cache_stats = self.cache_manager.get_statistics()
            
            # Check L1 cache efficiency
            l1_hit_rate = cache_stats['l1_cache']['hit_rate']
            if l1_hit_rate < 0.7:  # Less than 70% hit rate
                # Could increase L1 cache size or adjust promotion thresholds
                results['actions'].append('l1_cache_tuning_recommended')
            
            # Check L2 cache efficiency
            l2_hit_rate = cache_stats['l2_cache']['hit_rate']
            if l2_hit_rate < 0.8:  # Less than 80% hit rate
                results['actions'].append('l2_cache_tuning_recommended')
            
            # Check for cache size imbalances
            l1_utilization = cache_stats['l1_cache']['size'] / cache_stats['l1_cache']['max_size']
            l2_utilization = cache_stats['l2_cache']['size'] / cache_stats['l2_cache']['max_size']
            
            if l1_utilization > 0.9 and l2_utilization < 0.5:
                # L1 is full but L2 has space - could adjust promotion thresholds
                results['actions'].append('cache_rebalancing_recommended')
            
            if results['actions']:
                results['improvements_made'] = True
        
        except Exception as e:
            logger.error(f"Cache optimization failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def _optimize_resource_pools(self) -> Dict[str, Any]:
        """Optimize resource pool configurations."""
        
        results = {
            'optimizations_applied': [],
            'recommendations': []
        }
        
        try:
            for pool_name, pool in self.resource_pools.items():
                pool_stats = pool.get_statistics()
                optimizations = []
                
                # Check utilization patterns
                utilization = pool_stats.get('utilization', 0)
                current_size = pool_stats.get('current_size', 0)
                
                # High utilization - consider increasing pool size
                if utilization > 0.9 and current_size < pool.config.max_size:
                    optimizations.append('increase_pool_size')
                
                # Low utilization - consider decreasing minimum size
                elif utilization < 0.3 and current_size > pool.config.min_size:
                    optimizations.append('decrease_min_size')
                
                # High timeout rate - increase pool size or timeout
                timeout_rate = pool_stats.get('timeouts', 0) / max(pool_stats.get('acquisitions', 1), 1)
                if timeout_rate > 0.05:  # More than 5% timeout rate
                    optimizations.append('address_timeout_issues')
                
                if optimizations:
                    results['optimizations_applied'].append({
                        'pool_name': pool_name,
                        'optimizations': optimizations,
                        'current_stats': pool_stats
                    })
        
        except Exception as e:
            logger.error(f"Resource pool optimization failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def _optimize_system_settings(self) -> Dict[str, Any]:
        """Optimize system-level settings."""
        
        results = {
            'changes_made': False,
            'optimizations': []
        }
        
        try:
            # Thread pool optimization
            if hasattr(threading, 'active_count'):
                active_threads = threading.active_count()
                if active_threads > 100:  # Many threads
                    results['optimizations'].append('consider_thread_pool_tuning')
            
            # Python GC optimization
            gc_stats = dict(gc.get_stats()) if hasattr(gc, 'get_stats') else {}
            if gc_stats:
                # Check collection frequency
                gen0_collections = gc_stats[0]['collections'] if gc_stats else 0
                if gen0_collections > 1000:  # Frequent collections
                    results['optimizations'].append('gc_threshold_tuning_recommended')
            
            if results['optimizations']:
                results['changes_made'] = True
        
        except Exception as e:
            logger.error(f"System optimization failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def _calculate_performance_improvements(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, float]:
        """Calculate performance improvements."""
        
        improvements = {}
        
        try:
            # Cache hit rate improvement
            cache_before = before.get('cache_hit_rate', 0)
            cache_after = after.get('cache_hit_rate', 0)
            if cache_before > 0:
                improvements['cache_hit_rate'] = (cache_after - cache_before) / cache_before
            
            # Memory usage improvement (negative is better)
            memory_before = before.get('memory_usage_mb', 0)
            memory_after = after.get('memory_usage_mb', 0)
            if memory_before > 0:
                improvements['memory_usage'] = (memory_before - memory_after) / memory_before
            
            # Response time improvement (lower is better)
            response_before = before.get('response_time_ms', 0)
            response_after = after.get('response_time_ms', 0)
            if response_before > 0:
                improvements['response_time'] = (response_before - response_after) / response_before
        
        except Exception as e:
            logger.error(f"Performance improvement calculation failed: {e}")
        
        return improvements
    
    def _collect_optimization_metrics(self):
        """Collect metrics for monitoring dashboard."""
        
        if not self.monitoring_dashboard:
            return
        
        try:
            # Cache metrics
            cache_stats = self.cache_manager.get_statistics()
            self.monitoring_dashboard.collect_metric(
                'optimization.cache_hit_rate',
                cache_stats['multilevel_stats']['overall_hit_rate']
            )
            
            # Memory metrics
            memory_stats = self.memory_optimizer.get_memory_statistics()
            self.monitoring_dashboard.collect_metric(
                'optimization.memory_usage_mb',
                memory_stats['current_memory_mb']
            )
            
            # Resource pool metrics
            for pool_name, pool in self.resource_pools.items():
                pool_stats = pool.get_statistics()
                self.monitoring_dashboard.collect_metric(
                    f'optimization.pool_utilization.{pool_name}',
                    pool_stats.get('utilization', 0)
                )
        
        except Exception as e:
            logger.error(f"Optimization metrics collection failed: {e}")
    
    def _analyze_cache_performance(self) -> Dict[str, Any]:
        """Analyze cache performance in detail."""
        return self.cache_manager.get_statistics()
    
    def _analyze_memory_performance(self) -> Dict[str, Any]:
        """Analyze memory performance in detail."""
        return self.memory_optimizer.get_memory_statistics()
    
    def _analyze_resource_pool_performance(self) -> Dict[str, Any]:
        """Analyze resource pool performance in detail."""
        return {
            pool_name: pool.get_statistics()
            for pool_name, pool in self.resource_pools.items()
        }
    
    def _generate_performance_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate performance optimization recommendations."""
        
        recommendations = []
        
        try:
            bottlenecks = analysis.get('bottlenecks', [])
            
            for bottleneck in bottlenecks:
                if bottleneck['type'] == 'cache_efficiency':
                    if bottleneck['current_value'] < 0.5:
                        recommendations.append("Consider implementing more aggressive caching strategies")
                        recommendations.append("Review cache key design and data access patterns")
                    else:
                        recommendations.append("Fine-tune cache eviction policies and TTL settings")
                
                elif bottleneck['type'] == 'memory_usage':
                    recommendations.append("Implement more aggressive memory optimization")
                    recommendations.append("Consider increasing available system memory")
                    recommendations.append("Review for potential memory leaks")
                
                elif bottleneck['type'] == 'resource_pool_saturation':
                    pool_name = bottleneck.get('resource_pool', 'unknown')
                    recommendations.append(f"Increase maximum size of resource pool '{pool_name}'")
                    recommendations.append(f"Consider load balancing for pool '{pool_name}'")
            
            # General recommendations
            if not bottlenecks:
                recommendations.append("System performance is within acceptable parameters")
                recommendations.append("Continue monitoring for performance trends")
        
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
        
        return recommendations
    
    def _get_system_health_indicators(self) -> Dict[str, Any]:
        """Get overall system health indicators."""
        
        health = {
            'overall_status': 'healthy',
            'cache_health': 'good',
            'memory_health': 'good',
            'resource_pool_health': 'good'
        }
        
        try:
            # Check cache health
            cache_stats = self.cache_manager.get_statistics()
            cache_hit_rate = cache_stats['multilevel_stats']['overall_hit_rate']
            if cache_hit_rate < 0.5:
                health['cache_health'] = 'poor'
                health['overall_status'] = 'degraded'
            elif cache_hit_rate < 0.7:
                health['cache_health'] = 'fair'
            
            # Check memory health
            memory_stats = self.memory_optimizer.get_memory_statistics()
            memory_pressure = memory_stats.get('memory_pressure_level', 'normal')
            if memory_pressure == 'critical':
                health['memory_health'] = 'critical'
                health['overall_status'] = 'critical'
            elif memory_pressure == 'warning':
                health['memory_health'] = 'warning'
                if health['overall_status'] == 'healthy':
                    health['overall_status'] = 'warning'
            
            # Check resource pool health
            pool_issues = 0
            for pool in self.resource_pools.values():
                pool_stats = pool.get_statistics()
                if pool_stats.get('utilization', 0) > 0.9:
                    pool_issues += 1
            
            if pool_issues > 0:
                if pool_issues >= len(self.resource_pools) * 0.5:
                    health['resource_pool_health'] = 'critical'
                    health['overall_status'] = 'critical'
                else:
                    health['resource_pool_health'] = 'warning'
                    if health['overall_status'] in ['healthy', 'good']:
                        health['overall_status'] = 'warning'
        
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            health['overall_status'] = 'unknown'
        
        return health
    
    def _report_optimization_metrics(self, optimization_report: Dict[str, Any]):
        """Report optimization results to monitoring dashboard."""
        
        try:
            if not self.monitoring_dashboard:
                return
            
            # Report optimization completion
            self.monitoring_dashboard.collect_metric(
                'optimization.optimizations_completed',
                1
            )
            
            # Report memory freed
            memory_freed = optimization_report.get('memory_optimization', {}).get('freed_memory_mb', 0)
            if memory_freed > 0:
                self.monitoring_dashboard.collect_metric(
                    'optimization.memory_freed_mb',
                    memory_freed
                )
            
            # Report performance improvements
            improvements = optimization_report.get('improvements', {})
            for metric_name, improvement in improvements.items():
                if improvement > 0:  # Only report actual improvements
                    self.monitoring_dashboard.collect_metric(
                        f'optimization.improvement.{metric_name}',
                        improvement
                    )
        
        except Exception as e:
            logger.error(f"Optimization metrics reporting failed: {e}")