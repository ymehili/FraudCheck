"""
Simple in-memory cache utility for dashboard data.
"""

from typing import Any, Optional, Callable, TYPE_CHECKING
import json
import hashlib
import logging
from .redis_cache import RedisConnection, serialize_value, deserialize_value

if TYPE_CHECKING:
    import redis.asyncio as redis

logger = logging.getLogger(__name__)


class DistributedCache:
    """Redis-backed distributed cache with TTL support."""
    
    def __init__(self):
        self._redis: Optional["redis.Redis"] = None
    
    async def _get_redis(self):
        """Get Redis client instance."""
        if self._redis is None:
            self._redis = await RedisConnection.get_redis_client()
        return self._redis
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments - preserves existing logic."""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from distributed cache."""
        try:
            redis_client = await self._get_redis()
            value = await redis_client.get(key)
            if value is None:
                return None
            return deserialize_value(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set value in distributed cache with TTL."""
        try:
            redis_client = await self._get_redis()
            serialized_value = serialize_value(value)
            await redis_client.setex(key, ttl_seconds, serialized_value)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
    
    async def delete(self, key: str):
        """Delete key from distributed cache."""
        try:
            redis_client = await self._get_redis()
            await redis_client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
    
    async def clear(self):
        """Clear all cache entries."""
        try:
            redis_client = await self._get_redis()
            await redis_client.flushdb()
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
    
    async def cleanup_expired(self):
        """No-op: Redis handles TTL automatically."""
        pass  # Redis automatically handles expired keys


# Global cache instance
_cache_instance = DistributedCache()


def cached(ttl_seconds: int = 300):
    """Decorator for caching function results."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _cache_instance._generate_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await _cache_instance.get(cache_key)
            # Backward compatibility: older cache entries may have stored Pydantic
            # models as their string repr ("field=value ..."), which breaks FastAPI
            # response validation. Treat those as cache misses and overwrite.
            if isinstance(cached_result, str):
                logger.warning(
                    f"Invalid cached value type for {func.__name__} (str). "
                    "Deleting and recomputing."
                )
                await _cache_instance.delete(cache_key)
                cached_result = None

            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await _cache_instance.set(cache_key, result, ttl_seconds)
            logger.debug(f"Cached result for {func.__name__}")
            return result
        
        return wrapper
    return decorator


async def get_cache_instance() -> DistributedCache:
    """Get the global cache instance."""
    return _cache_instance


async def invalidate_dashboard_cache(user_id: str):
    """Invalidate all dashboard-related cache entries for a user."""
    # In a more sophisticated implementation, we'd use pattern-based invalidation
    # For now, we'll clear the entire cache when data changes
    await _cache_instance.clear()
    logger.info(f"Invalidated dashboard cache for user {user_id}")


# Cleanup task (no-op for Redis-backed cache)
async def start_cache_cleanup_task():
    """Start background task to clean up expired cache entries.
    
    No-op for Redis-backed cache since Redis handles TTL automatically.
    Kept for backward compatibility.
    """
    logger.info("Cache cleanup task: No-op for Redis-backed cache (TTL handled automatically)")
    pass