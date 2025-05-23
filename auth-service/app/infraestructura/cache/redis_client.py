from redis.asyncio import Redis as AIORedis # Explicit import
from typing import Optional
from auth_service.app.shared.config.config import settings

redis_pool: Optional[AIORedis] = None

async def get_redis_pool() -> AIORedis:
    global redis_pool
    if redis_pool is None:
        print(f"Initializing Redis pool with URL: {settings.REDIS_URL}") # For debugging
        redis_pool = AIORedis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True # Important for getting strings back
        )
        try:
            # Test connection
            await redis_pool.ping()
            print("Successfully connected to Redis.")
        except Exception as e:
            print(f"Error connecting to Redis: {e}")
            # Depending on policy, could raise an error here or let it fail on first use
            # For now, we'll let it be, and operations will fail if Redis is down.
            # In a real app, more robust error handling or startup checks might be needed.
            # If Redis is critical, the app might not start.
            # Closing the pool if ping fails, so it can be retried
            if redis_pool:
                await redis_pool.close()
                redis_pool = None # Reset so it can be retried
            raise ConnectionError(f"Failed to connect to Redis: {e}") # Raise to prevent app from starting if Redis is critical

    return redis_pool

async def close_redis_pool():
    global redis_pool
    if redis_pool:
        print("Closing Redis pool...")
        await redis_pool.close()
        redis_pool = None # Ensure it's reset for potential restarts or tests
        print("Redis pool closed.")
