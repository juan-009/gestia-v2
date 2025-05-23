import json
from typing import List, Optional
from redis.asyncio import Redis as AIORedis # Use the same import for clarity

class RolePermissionsCache:
    CACHE_PREFIX = "role_permissions:"
    DEFAULT_TTL_SECONDS = 300 # 5 minutes

    def __init__(self, redis_client: AIORedis):
        self.redis = redis_client

    async def get_role_permissions(self, role_name: str) -> Optional[List[str]]:
        cache_key = f"{self.CACHE_PREFIX}{role_name}"
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            try:
                # Assuming cached_data is a JSON string
                return json.loads(cached_data) 
            except json.JSONDecodeError:
                # Handle malformed data, e.g., log and return None or clear cache
                # For now, clear bad data and return None
                await self.redis.delete(cache_key) 
                return None
        return None

    async def set_role_permissions(self, role_name: str, permissions: List[str], ttl_seconds: Optional[int] = None):
        cache_key = f"{self.CACHE_PREFIX}{role_name}"
        ttl = ttl_seconds if ttl_seconds is not None else self.DEFAULT_TTL_SECONDS
        # Ensure permissions is a list of strings before serializing
        if not isinstance(permissions, list) or not all(isinstance(p, str) for p in permissions):
            # Or log a warning, or raise an error, depending on how strict you want to be.
            # This indicates a potential issue with the data being cached.
            # For now, we'll assume the caller provides correct data.
            pass
        await self.redis.setex(cache_key, ttl, json.dumps(permissions))

    async def clear_role_permissions(self, role_name: str):
        cache_key = f"{self.CACHE_PREFIX}{role_name}"
        await self.redis.delete(cache_key)
