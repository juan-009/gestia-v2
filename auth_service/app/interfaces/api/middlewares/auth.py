from fastapi import Request

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from starlette.responses import Response
from app.infraestructura.seguridad import jwt_manager
from app.dominio.value_objects import JWTClaims
from app.dominio.excepciones import InvalidTokenError
from typing import Optional

class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.user_claims = None  # type: Optional[JWTClaims]  # Initialize with None

        auth_header = request.headers.get("Authorization")
        token: Optional[str] = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if token:
            try:
                # This will raise InvalidTokenError if token is bad, which error_handler_middleware can catch
                # Or we can handle it here specifically if we don't want it to bubble to global handler for this specific case
                request.state.user_claims = jwt_manager.validate_token(token)
            except InvalidTokenError: 
                # Token is invalid, claims remain None. 
                # Specific endpoint security will check request.state.user_claims.
                # No immediate error response here unless a global policy dictates all invalid tokens are rejected.
                pass 

        response = await call_next(request)
        return response