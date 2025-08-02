import redis
import json
import os
from datetime import datetime, timedelta
import hashlib

class CacheManager:
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
        except:
            self.redis_available = False
            self.memory_cache = {}  # Fallback to memory cache
            print("Redis not available, using memory cache")

    def get(self, key):
        """Get value from cache"""
        try:
            if self.redis_available:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                # Memory cache fallback
                if key in self.memory_cache:
                    item = self.memory_cache[key]
                    if datetime.now() < item['expires']:
                        return item['value']
                    else:
                        del self.memory_cache[key]
            return None
        except Exception as e:
            print(f"Cache get error: {str(e)}")
            return None

    def set(self, key, value, ttl=3600):
        """Set value in cache with TTL"""
        try:
            if self.redis_available:
                self.redis_client.setex(key, ttl, json.dumps(value, default=str))
            else:
                # Memory cache fallback
                self.memory_cache[key] = {
                    'value': value,
                    'expires': datetime.now() + timedelta(seconds=ttl)
                }
                
                # Clean expired items periodically
                if len(self.memory_cache) > 1000:
                    self._clean_memory_cache()
                    
            return True
        except Exception as e:
            print(f"Cache set error: {str(e)}")
            return False

    def delete(self, key):
        """Delete key from cache"""
        try:
            if self.redis_available:
                return self.redis_client.delete(key)
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    return True
            return False
        except Exception as e:
            print(f"Cache delete error: {str(e)}")
            return False

    def _clean_memory_cache(self):
        """Clean expired items from memory cache"""
        now = datetime.now()
        expired_keys = [
            key for key, item in self.memory_cache.items()
            if now >= item['expires']
        ]
        for key in expired_keys:
            del self.memory_cache[key]

    def generate_cache_key(self, *args):
        """Generate a cache key from arguments"""
        key_string = ':'.join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()

    def flush_all(self):
        """Clear all cache"""
        try:
            if self.redis_available:
                return self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
                return True
        except Exception as e:
            print(f"Cache flush error: {str(e)}")
            return False