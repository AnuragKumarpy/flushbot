"""
Redis Cache Manager for FlushBot
Handles message caching, rate limiting, and performance optimization
"""

import json
import pickle
import hashlib
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import asyncio

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
except ImportError:
    import redis
    Redis = redis.Redis

from loguru import logger
from config.settings import settings


class CacheManager:
    """Redis-based cache manager for FlushBot"""
    
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.connected = False
        self._connect_lock = asyncio.Lock()
    
    async def connect(self):
        """Connect to Redis server"""
        if self.connected:
            return
        
        async with self._connect_lock:
            if self.connected:
                return
            
            try:
                # Parse Redis URL
                redis_config = {
                    "decode_responses": False,  # We'll handle encoding ourselves
                    "socket_keepalive": True,
                    "socket_keepalive_options": {},
                    "health_check_interval": 30
                }
                
                if settings.redis_password:
                    redis_config["password"] = settings.redis_password
                
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    **redis_config
                )
                
                # Test connection
                await self.redis_client.ping()
                self.connected = True
                logger.info("Connected to Redis successfully")
                
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis_client = None
                self.connected = False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.connected = False
            logger.info("Disconnected from Redis")
    
    def _ensure_connected(self):
        """Ensure Redis connection is active"""
        if not self.connected:
            raise ConnectionError("Redis not connected. Call connect() first.")
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for Redis storage"""
        if isinstance(value, (str, int, float)):
            return json.dumps(value).encode('utf-8')
        else:
            return pickle.dumps(value)
    
    def _deserialize_value(self, value: bytes) -> Any:
        """Deserialize value from Redis storage"""
        try:
            # Try JSON first (for simple types)
            return json.loads(value.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(value)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in cache with optional TTL
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time to live in seconds (default: settings.cache_ttl)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_connected()
            
            serialized_value = self._serialize_value(value)
            ttl = ttl or settings.cache_ttl
            
            result = await self.redis_client.setex(key, ttl, serialized_value)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from cache
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            self._ensure_connected()
            
            value = await self.redis_client.get(key)
            if value is None:
                return default
            
            return self._deserialize_value(value)
            
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return default
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        try:
            self._ensure_connected()
            return await self.redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Cache delete failed: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            self._ensure_connected()
            return bool(await self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Increment a counter"""
        try:
            self._ensure_connected()
            
            # Use pipeline for atomic operation
            pipe = self.redis_client.pipeline()
            pipe.incr(key, amount)
            if ttl:
                pipe.expire(key, ttl)
            
            results = await pipe.execute()
            return results[0]
            
        except Exception as e:
            logger.error(f"Cache increment failed for key {key}: {e}")
            return 0
    
    async def set_hash(self, key: str, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set hash fields"""
        try:
            self._ensure_connected()
            
            # Serialize hash values
            serialized_mapping = {
                field: self._serialize_value(value)
                for field, value in mapping.items()
            }
            
            pipe = self.redis_client.pipeline()
            pipe.hset(key, mapping=serialized_mapping)
            if ttl:
                pipe.expire(key, ttl)
            
            await pipe.execute()
            return True
            
        except Exception as e:
            logger.error(f"Cache hash set failed for key {key}: {e}")
            return False
    
    async def get_hash(self, key: str, field: Optional[str] = None) -> Union[Dict, Any, None]:
        """Get hash field(s)"""
        try:
            self._ensure_connected()
            
            if field:
                value = await self.redis_client.hget(key, field)
                return self._deserialize_value(value) if value else None
            else:
                hash_data = await self.redis_client.hgetall(key)
                return {
                    k.decode('utf-8'): self._deserialize_value(v)
                    for k, v in hash_data.items()
                } if hash_data else {}
                
        except Exception as e:
            logger.error(f"Cache hash get failed for key {key}: {e}")
            return None
    
    async def add_to_set(self, key: str, *values: Any, ttl: Optional[int] = None) -> int:
        """Add values to a set"""
        try:
            self._ensure_connected()
            
            serialized_values = [self._serialize_value(v) for v in values]
            
            pipe = self.redis_client.pipeline()
            pipe.sadd(key, *serialized_values)
            if ttl:
                pipe.expire(key, ttl)
            
            results = await pipe.execute()
            return results[0]
            
        except Exception as e:
            logger.error(f"Cache set add failed for key {key}: {e}")
            return 0
    
    async def is_in_set(self, key: str, value: Any) -> bool:
        """Check if value is in set"""
        try:
            self._ensure_connected()
            serialized_value = self._serialize_value(value)
            return bool(await self.redis_client.sismember(key, serialized_value))
        except Exception as e:
            logger.error(f"Cache set membership check failed: {e}")
            return False


class MessageCache:
    """Specialized cache for message processing"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        self.message_prefix = "msg:"
        self.user_prefix = "user:"
        self.chat_prefix = "chat:"
        self.analysis_prefix = "analysis:"
    
    def _message_key(self, message_id: Union[int, str], chat_id: int) -> str:
        """Generate message cache key"""
        return f"{self.message_prefix}{chat_id}:{message_id}"
    
    def _user_key(self, user_id: int) -> str:
        """Generate user cache key"""
        return f"{self.user_prefix}{user_id}"
    
    def _chat_key(self, chat_id: int) -> str:
        """Generate chat cache key"""
        return f"{self.chat_prefix}{chat_id}"
    
    def _analysis_key(self, text: str) -> str:
        """Generate analysis cache key based on message text hash"""
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{self.analysis_prefix}{text_hash}"
    
    async def cache_message(self, message_data: Dict, ttl: Optional[int] = None) -> bool:
        """Cache message data"""
        key = self._message_key(message_data["message_id"], message_data["chat_id"])
        return await self.cache.set(key, message_data, ttl)
    
    async def get_message(self, message_id: Union[int, str], chat_id: int) -> Optional[Dict]:
        """Get cached message"""
        key = self._message_key(message_id, chat_id)
        return await self.cache.get(key)
    
    async def cache_user_info(self, user_data: Dict, ttl: Optional[int] = None) -> bool:
        """Cache user information"""
        key = self._user_key(user_data["user_id"])
        return await self.cache.set(key, user_data, ttl)
    
    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Get cached user information"""
        key = self._user_key(user_id)
        return await self.cache.get(key)
    
    async def cache_chat_settings(self, chat_data: Dict, ttl: Optional[int] = None) -> bool:
        """Cache chat settings"""
        key = self._chat_key(chat_data["chat_id"])
        return await self.cache.set(key, chat_data, ttl)
    
    async def get_chat_settings(self, chat_id: int) -> Optional[Dict]:
        """Get cached chat settings"""
        key = self._chat_key(chat_id)
        return await self.cache.get(key)
    
    async def cache_analysis_result(self, text: str, analysis: Dict, ttl: Optional[int] = None) -> bool:
        """Cache analysis result for identical messages"""
        key = self._analysis_key(text)
        ttl = ttl or 3600  # 1 hour default for analysis cache
        return await self.cache.set(key, analysis, ttl)
    
    async def get_cached_analysis(self, text: str) -> Optional[Dict]:
        """Get cached analysis result"""
        key = self._analysis_key(text)
        return await self.cache.get(key)
    
    async def increment_user_violations(self, user_id: int, ttl: int = 86400) -> int:
        """Increment user violation count (daily reset)"""
        key = f"violations:{user_id}"
        return await self.cache.increment(key, ttl=ttl)
    
    async def get_user_violations(self, user_id: int) -> int:
        """Get user violation count"""
        key = f"violations:{user_id}"
        return await self.cache.get(key, default=0)


class RateLimiter:
    """Rate limiting using Redis"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    async def is_rate_limited(self, key: str, limit: int, window: int) -> Tuple[bool, int]:
        """
        Check if action is rate limited
        
        Args:
            key: Rate limiting key (e.g., user_id, chat_id)
            limit: Maximum actions allowed in window
            window: Time window in seconds
            
        Returns:
            Tuple of (is_limited, current_count)
        """
        try:
            current_count = await self.cache.increment(f"rate:{key}", ttl=window)
            return current_count > limit, current_count
        except Exception as e:
            logger.error(f"Rate limit check failed for {key}: {e}")
            return False, 0
    
    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit for key"""
        try:
            await self.cache.delete(f"rate:{key}")
            return True
        except Exception as e:
            logger.error(f"Rate limit reset failed for {key}: {e}")
            return False


# Global instances
cache_manager = CacheManager()
message_cache = MessageCache(cache_manager)
rate_limiter = RateLimiter(cache_manager)