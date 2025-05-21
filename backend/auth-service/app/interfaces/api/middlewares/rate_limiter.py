import logging
import time
from typing import Callable, Tuple
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from app.shared.config import settings
from app.dominio.excepciones import AuthError

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.circuit_open = False
        self.circuit_last_failure = 0
        
    async def check_limit(
        self, 
        request: Request,
        identifier: str,
        limit: int, 
        window: int
    ) -> Tuple[bool, dict]:
        """Sliding window rate limiter using sorted sets"""
        if self.circuit_open:
            if time.time() - self.circuit_last_failure > 30:
                self.circuit_open = False
            return True, {}
            
        route_key = f"rate_limit:{request.url.path}:{identifier}"
        now = int(time.time())
        pipeline = self.redis.pipeline()
        
        try:
            # Remove old timestamps
            pipeline.zremrangebyscore(route_key, 0, now - window)
            
            # Get current count
            pipeline.zcard(route_key)
            
            # Add new timestamp
            pipeline.zadd(route_key, {now: now})
            pipeline.expire(route_key, window)
            
            _, current_count, _, _ = await pipeline.execute()
        except Exception as e:
            await self._handle_redis_failure()
            return True, {}
            
        remaining = limit - current_count
        reset_time = now + window
        
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time)
        }
        
        if remaining < 0:
            await self._block_request(route_key, now, window)
            return False, headers
            
        return True, headers

    async def _get_client_identifier(self, request: Request) -> str:
        """Get unique client ID combining IP and user"""
        ip = request.client.host
        user = getattr(request.state, "user_id", "anonymous")
        return f"{ip}:{user}"

    async def _block_request(self, key: str, timestamp: int, window: int):
        retry_after = window - (int(time.time()) - timestamp)
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": str(retry_after)}
        )

    async def _handle_redis_failure(self):
        self.circuit_open = True
        self.logger.error("Redis failure - Rate limiter circuit open")
        # Log critical error but allow request to proceed
        logger.error("Redis failure - Rate limiter circuit open")

class RateLimitMiddleware:
    def __init__(self, app, **config):
        self.app = app
        self.config = {
            "default": {"limit": 100, "window": 60},
            "auth": {"login": {"limit": 5, "window": 300}},
            "admin": {"limit": 1000, "window": 60}
        }
        
    async def __call__(self, request: Request, call_next):
        if request.url.path in self._get_excluded_paths():
            return await call_next(request)
            
        limiter = RateLimiter(request.app.state.redis)
        identifier = await limiter._get_client_identifier(request)
        
        route_config = self._get_route_config(request)
        success, headers = await limiter.check_limit(
            request,
            identifier,
            route_config["limit"],
            route_config["window"]
        )
        
        if not success:
            return JSONResponse(
                content={"detail": "Too many requests"},
                status_code=429,
                headers=headers
            )
            
        response = await call_next(request)
        response.headers.update(headers)
        return response

    def _get_route_config(self, request: Request) -> dict:
        path_parts = request.url.path.split("/")
        if "admin" in path_parts:
            return self.config["admin"]
        if request.url.path == "/auth/login":
            return self.config["auth"]["login"]
        return self.config["default"]
        
    def _get_excluded_paths(self):
        return ["/health", "/metrics"]