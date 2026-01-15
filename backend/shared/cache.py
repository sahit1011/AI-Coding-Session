"""
Caching layer for search results.

Uses Redis for distributed caching with TTL.
"""

import json
import hashlib
from typing import Optional, Dict, Any
import os

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis-py not installed. Caching disabled.")
    print("Install with: pip install redis")


class SearchCache:
    """Cache for search results using Redis."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl: int = 3600,  # 1 hour
        enabled: bool = True
    ):
        """
        Initialize cache.
        
        Args:
            redis_url: Redis connection URL
            ttl: Time to live in seconds
            enabled: Whether caching is enabled
        """
        self.enabled = enabled and REDIS_AVAILABLE
        self.ttl = ttl
        
        if self.enabled:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()  # Test connection
                print(f"✓ Redis cache enabled (TTL: {ttl}s)")
            except Exception as e:
                print(f"✗ Redis connection failed: {e}")
                print("  Caching disabled. Install Redis: https://redis.io/download")
                self.enabled = False
                self.redis_client = None
        else:
            self.redis_client = None
    
    def cache_key(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 10) -> str:
        """Generate cache key from query, filters, and limit."""
        cache_data = {
            "query": query.lower().strip(),
            "filters": filters or {},
            "limit": limit
        }
        key_string = json.dumps(cache_data, sort_keys=True)
        return f"search:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def get(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 10) -> Optional[Dict[str, Any]]:
        """Get cached results."""
        if not self.enabled:
            return None
        
        try:
            key = self.cache_key(query, filters, limit)
            cached = self.redis_client.get(key)
            
            if cached:
                return json.loads(cached)
            
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(
        self,
        query: str,
        results: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> bool:
        """Cache results."""
        if not self.enabled:
            return False
        
        try:
            key = self.cache_key(query, filters, limit)
            self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(results)
            )
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def invalidate(self, pattern: str = "search:*") -> int:
        """Invalidate cache entries matching pattern."""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache invalidate error: {e}")
            return 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False, "message": "Redis not available"}
        
        try:
            info = self.redis_client.info("stats")
            keys_count = len(self.redis_client.keys("search:*"))
            
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total_requests = hits + misses
            
            return {
                "enabled": True,
                "total_keys": keys_count,
                "hits": hits,
                "misses": misses,
                "total_requests": total_requests,
                "hit_rate": round(hits / max(total_requests, 1), 3),
                "ttl_seconds": self.ttl
            }
        except Exception as e:
            print(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}


# Global cache instance
_cache: Optional[SearchCache] = None


def get_cache() -> SearchCache:
    """Get or create cache instance."""
    global _cache
    if _cache is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        ttl = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
        enabled = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        
        _cache = SearchCache(redis_url=redis_url, ttl=ttl, enabled=enabled)
    
    return _cache

