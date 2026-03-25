# Cache Invalidation
# 
import json
from typing import Any


class CacheManager:
    """ Manages Cache operations with a proper invalidation Strategy. """
    def __init__(self, redis_client) -> None:
        self.redis =redis_client
    
    def get(self, key) -> Any | None:
        """ Get value from cache """
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def set(self, key, value, ttl =300, tags= None):
        """ 
            Set the value in cache with optional arguements for group invalidation.
            
            Tags Allow you invalidate related cache entries together.
            Example:- tag all user-related caches ith 'user:123' to clear
            them all when the user is updated.
        """
        
        self.redis.setex(key, ttl, json.dumps(value))
        
        # Track cache Keys by tag for Cache invalidation
        if tags:
            for tag in tags:
                self.redis.sadd(f"cache_tag:{tag}", key)
                # Set expiry on tag to prevent memory leaks
                self.redis.expire(f"cache_tag: {tag}", ttl+60)
    
    def invalidate_by_tag(self, tag):
        """ Invalidate all cache entries with a specific tag """
        tag_key = f"cache_tag:{tag}"
        keys = self.redis.smembers(tag_key)
        
        if keys:
            self.redis.delete(*keys, tag_key)
        return len(keys)
                