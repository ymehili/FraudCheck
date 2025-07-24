"""
Redis connection utilities for distributed caching.
"""

import redis.asyncio as redis
from typing import Optional, Any
import json
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)


class RedisConnection:
    """Singleton Redis connection manager with connection pooling."""
    
    _pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    
    @classmethod
    async def get_redis_client(cls) -> redis.Redis:
        """Get Redis client with connection pooling."""
        if cls._client is None:
            try:
                redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
                cls._pool = redis.ConnectionPool.from_url(
                    redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    decode_responses=False  # We'll handle JSON serialization manually
                )
                cls._client = redis.Redis(connection_pool=cls._pool)
                
                # Test the connection
                await cls._client.ping()
                logger.info(f"Redis connection established: {redis_url}")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
                
        return cls._client
    
    @classmethod
    async def close(cls):
        """Close Redis connections and cleanup."""
        if cls._client:
            try:
                await cls._client.aclose()
                cls._client = None
                logger.info("Redis client closed")
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
                
        if cls._pool:
            try:
                await cls._pool.aclose()
                cls._pool = None
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error(f"Error closing Redis pool: {e}")


def serialize_value(value: Any) -> str:
    """Serialize value to JSON string for Redis storage."""
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to serialize value {type(value)}: {e}")
        # Fallback to string representation
        return str(value)


def deserialize_value(value: bytes) -> Any:
    """Deserialize JSON string from Redis to Python object."""
    if value is None:
        return None
        
    try:
        # Convert bytes to string
        if isinstance(value, bytes):
            value_str = value.decode('utf-8')
        else:
            value_str = value
            
        # Try to parse as JSON
        return json.loads(value_str)
        
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Fallback: return as decoded string for backward compatibility
        if isinstance(value, bytes):
            return value.decode('utf-8')
        return value
    except Exception as e:
        logger.error(f"Failed to deserialize value: {e}")
        return None