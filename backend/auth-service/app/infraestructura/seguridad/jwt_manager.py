import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from jose import JWTError
from pydantic import ValidationError

from app.shared.config.config import settings
from app.shared.config.constants import SecurityConstants
from app.dominio.excepciones import InvalidTokenError, TokenRevokedError
from app.dominio.value_objects import JWTClaims
from app.infraestructura.seguridad.jwks_manager import get_jwks_manager
from app.infraestructura.cache.redis import get_redis_client

logger = logging.getLogger(__name__)

class JWTManager:
    """Gestión completa de tokens JWT con validación y revocación"""

    def __init__(self):
        self.jwks_manager = get_jwks_manager()
        self.redis = get_redis_client()
        self.algorithm = SecurityConstants.JWT_ALGORITHM

    def create_access_token(self, subject: str, payload: Dict[str, Any]) -> str:
        """
        Crea un JWT access token con los claims requeridos
        Args:
            subject: Identificador del sujeto (usuario)
            payload: Datos adicionales para incluir en el token
        Returns:
            str: Token JWT firmado
        """
        current_time = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
        
        claims = {
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "sub": subject,
            "exp": current_time + expires_delta,
            "iat": current_time,
            "nbf": current_time,
            "jti": str(uuid.uuid4()),
            **payload
        }

        try:
            return jwt.encode(
                claims,
                self.jwks_manager.get_current_private_key(),
                algorithm=self.algorithm,
                headers={"kid": self._get_current_kid()}
            )
        except Exception as e:
            logger.error("Error creando token: %s", str(e))
            raise InvalidTokenError("TOKEN_CREATION_ERROR") from e

    def create_refresh_token(self, subject: str) -> str:
        """
        Crea un refresh token con mayor tiempo de expiración
        Args:
            subject: Identificador del sujeto (usuario)
        Returns:
            str: Refresh token JWT
        """
        current_time = datetime.now(timezone.utc)
        expires_delta = timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
        
        claims = {
            "iss": settings.JWT_ISSUER,
            "sub": subject,
            "exp": current_time + expires_delta,
            "iat": current_time,
            "jti": str(uuid.uuid4()),
            "type": "refresh"
        }

        try:
            token = jwt.encode(
                claims,
                self.jwks_manager.get_current_private_key(),
                algorithm=self.algorithm,
                headers={"kid": self._get_current_kid()}
            )
            
            # Almacenar refresh token en Redis
            self.redis.setex(
                f"refresh_token:{claims['jti']}",
                time=expires_delta,
                value=json.dumps({
                    "sub": subject,
                    "exp": claims["exp"].timestamp()
                })
            )
            return token
        except Exception as e:
            logger.error("Error creando refresh token: %s", str(e))
            raise InvalidTokenError("REFRESH_TOKEN_CREATION_ERROR") from e

    def validate_token(self, token: str) -> JWTClaims:
        """
        Valida y decodifica un token JWT
        Args:
            token: Token JWT a validar
        Returns:
            JWTClaims: Objeto con los claims validados
        Raises:
            InvalidTokenError: Si el token es inválido o revocado
        """
        try:
            # Obtener clave pública para verificación
            public_key = self.jwks_manager.get_jwks()["keys"][0]
            key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(public_key))
            
            # Decodificar y validar claims
            payload = jwt.decode(
                token,
                key,
                algorithms=[self.algorithm],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "require": ["exp", "iat", "sub", "jti"]
                }
            )
            
            # Validar revocación
            if self._is_token_revoked(payload["jti"]):
                raise TokenRevokedError("Token revocado")

            return JWTClaims(**payload)
        except jwt.ExpiredSignatureError as e:
            logger.warning("Token expirado: %s", str(e))
            raise InvalidTokenError("TOKEN_EXPIRED") from e
        except JWTError as e:
            logger.warning("Error decodificando token: %s", str(e))
            raise InvalidTokenError("INVALID_TOKEN") from e
        except ValidationError as e:
            logger.error("Claims inválidos: %s", str(e))
            raise InvalidTokenError("INVALID_CLAIMS") from e

    def revoke_token(self, jti: str, expire_in: Optional[int] = None):
        """
        Revoca un token agregando su JTI a la lista negra
        Args:
            jti: Identificador único del token
            expire_in: Tiempo en segundos hasta expiración (default: tiempo de acceso token)
        """
        if not expire_in:
            expire_in = settings.JWT_ACCESS_EXPIRE_MINUTES * 60
            
        self.redis.setex(
            f"{settings.REDIS_JTI_BLACKLIST}:{jti}",
            time=expire_in,
            value="revoked"
        )
        logger.info("Token revocado: %s", jti)

    def _get_current_kid(self) -> str:
        """Obtiene el ID de la clave actual del JWKS"""
        return self.jwks_manager.get_jwks()["keys"][0]["kid"]

    def _is_token_revoked(self, jti: str) -> bool:
        """Verifica si el token está en la lista negra"""
        return self.redis.exists(f"{settings.REDIS_JTI_BLACKLIST}:{jti}") == 1

# Singleton para inyección de dependencias
jwt_manager = JWTManager()