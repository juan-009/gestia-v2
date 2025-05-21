import logging
import time
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.infraestructura.seguridad.jwt_manager import jwt_manager
from app.infraestructura.cache.redis import get_redis_client
from app.shared.config.config import settings
from app.shared.config.constants import (
    SecurityConstants,
    APIConstants
)
from app.dominio.excepciones import (
    InvalidTokenError,
    TokenRevokedError,
    RateLimitExceededError
)

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware principal para gestión de autenticación y seguridad"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.redis = get_redis_client()
        self.unprotected_routes = {
            "/auth/login",
            "/auth/refresh",
            "/docs",
            "/openapi.json",
            "/redoc"
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        # Paso 1: Verificación de ruta protegida
        if request.url.path not in self.unprotected_routes:
            try:
                # Paso 2: Extraer y validar token
                token = self._extract_token(request)
                claims = jwt_manager.validate_token(token)
                
                # Paso 3: Verificar revocación del token
                await self._check_token_revocation(claims.jti)
                
                # Paso 4: Adjuntar usuario al request
                request.state.user = claims
                
                # Paso 5: Rate Limiting
                await self._apply_rate_limits(request, claims.sub)
                
            except (InvalidTokenError, TokenRevokedError) as e:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Credenciales inválidas o token expirado"}
                )
            except RateLimitExceededError as e:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Límite de peticiones excedido",
                        "retry_after": e.details["retry_after"]
                    },
                    headers={"Retry-After": str(e.details["retry_after"])}
                )
        
        # Paso 6: Headers de seguridad
        response = await call_next(request)
        self._add_security_headers(response)
        
        return response
    
    def _extract_token(self, request: Request) -> str:
        """Extrae el token JWT del header Authorization"""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise InvalidTokenError("Formato de token inválido")
        return auth_header.split(" ")[1]
    
    async def _check_token_revocation(self, jti: str):
        """Verifica si el token está en la lista de revocados"""
        if await self.redis.exists(f"{SecurityConstants.JWT_REVOCATION_PREFIX}:{jti}"):
            raise TokenRevokedError("Token revocado")
    
    async def _apply_rate_limits(self, request: Request, user_id: str):
        """Aplica rate limiting por IP y usuario"""
        client_ip = request.client.host
        user_key = f"rate_limit:user:{user_id}"
        ip_key = f"rate_limit:ip:{client_ip}"
        
        # Limitar por usuario
        user_count = await self.redis.incr(user_key)
        if user_count == 1:
            await self.redis.expire(user_key, APIConstants.RATE_LIMIT_WINDOW)
        if user_count > APIConstants.RATE_LIMIT_USER_MAX:
            raise RateLimitExceededError(APIConstants.RATE_LIMIT_WINDOW)
        
        # Limitar por IP
        ip_count = await self.redis.incr(ip_key)
        if ip_count == 1:
            await self.redis.expire(ip_key, APIConstants.RATE_LIMIT_WINDOW)
        if ip_count > APIConstants.RATE_LIMIT_IP_MAX:
            raise RateLimitExceededError(APIConstants.RATE_LIMIT_WINDOW)
    
    def _add_security_headers(self, response):
        """Agrega headers de seguridad HTTP"""
        security_headers = {
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=()"
        }
        response.headers.update(security_headers)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging detallado de peticiones"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        
        logger.info(
            "Method=%s Path=%s Status=%d Duration=%.2fms",
            request.method,
            request.url.path,
            response.status_code,
            process_time
        )
        
        return response

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware global para manejo de errores"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.error("Error no manejado: %s", str(e), exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Error interno del servidor"}
            )