"""
Simple in-memory cache utility for dashboard data.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Callable
import json
import hashlib
import logging

logger = logging.getLogger(__name__)


class MemoryCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.utcnow() < entry['expires_at']:
                    return entry['value']
                else:
                    # Expired entry
                    del self._cache[key]
        return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set value in cache with TTL."""
        async with self._lock:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
    
    async def delete(self, key: str):
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self):
        """Remove expired entries."""
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now >= entry['expires_at']
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global cache instance
_cache_instance = MemoryCache()


def cached(ttl_seconds: int = 300):
    """Decorator for caching function results."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _cache_instance._generate_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = await _cache_instance.get(cache_key)
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


async def get_cache_instance() -> MemoryCache:
    """Get the global cache instance."""
    return _cache_instance


async def invalidate_dashboard_cache(user_id: str):
    """Invalidate all dashboard-related cache entries for a user."""
    # In a more sophisticated implementation, we'd use pattern-based invalidation
    # For now, we'll clear the entire cache when data changes
    await _cache_instance.clear()
    logger.info(f"Invalidated dashboard cache for user {user_id}")


# Cleanup task
async def start_cache_cleanup_task():
    """Start background task to clean up expired cache entries."""
    async def cleanup_loop():
        while True:
            try:
                await _cache_instance.cleanup_expired()
                await asyncio.sleep(60)  # Run every minute
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)
    
    # Start the cleanup task
    asyncio.create_task(cleanup_loop())