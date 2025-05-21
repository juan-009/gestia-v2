import logging
import os
import re
from typing import Optional

import bcrypt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.shared.config.constants import SecurityConstants
from app.dominio.excepciones import WeakPasswordError, SecurityException

logger = logging.getLogger(__name__)

class PasswordHasher:
    """Gestión segura de hashing y verificación de contraseñas"""
    
    def __init__(self):
        self._pepper = self._get_pepper()
        self.crypt_ctx = CryptContext(
            schemes=["bcrypt"],
            bcrypt__rounds=SecurityConstants.BCRYPT_COST,
            deprecated="auto"
        )
    
    def _get_pepper(self) -> bytes:
        """Obtiene el pepper desde variables de entorno"""
        pepper = os.getenv("PEPPER", "")
        if not pepper and os.getenv("ENVIRONMENT") == "prod":
            logger.error("Pepper no configurado en producción")
            raise SecurityException(
                code="MISSING_PEPPER",
                message="Pepper no configurado en entorno de producción"
            )
        return pepper.encode()
    
    def hash_password(self, password: str) -> str:
        """
        Genera un hash seguro de la contraseña usando bcrypt + pepper
        
        Args:
            password: Contraseña en texto plano
        Returns:
            str: Hash seguro de la contraseña
        Raises:
            WeakPasswordError: Si la contraseña no cumple la política
        """
        self._validate_password_policy(password)
        
        try:
            # Combina password con pepper antes de hashear
            peppered_password = password.encode() + self._pepper
            return self.crypt_ctx.hash(peppered_password)
        except Exception as e:
            logger.error("Error generando hash: %s", str(e))
            raise SecurityException("HASH_ERROR", "Error al hashear contraseña") from e
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verifica una contraseña contra su hash almacenado
        
        Args:
            password: Contraseña en texto plano
            hashed_password: Hash almacenado
        Returns:
            bool: True si la contraseña coincide
        Raises:
            SecurityException: Si el hash es inválido o inseguro
        """
        try:
            self._validate_hash_security(hashed_password)
            peppered_password = password.encode() + self._pepper
            return self.crypt_ctx.verify(peppered_password, hashed_password)
        except UnknownHashError as e:
            logger.error("Hash inválido: %s", str(e))
            raise SecurityException("INVALID_HASH", "Formato de hash no reconocido") from e
        except Exception as e:
            logger.error("Error verificando contraseña: %s", str(e))
            raise SecurityException("VERIFY_ERROR", "Error al verificar contraseña") from e
    
    def _validate_password_policy(self, password: str):
        """Valida que la contraseña cumpla la política de seguridad"""
        if not re.match(SecurityConstants.PASSWORD_REGEX, password):
            raise WeakPasswordError(
                reason="No cumple con la política de complejidad"
            )
    
    def _validate_hash_security(self, hashed_password: str):
        """Valida que el hash sea seguro y actual"""
        if not self.crypt_ctx.identify(hashed_password):
            raise SecurityException(
                code="INSECURE_HASH",
                message="El hash no es compatible o es inseguro"
            )
        
        # Verificar costo mínimo de bcrypt
        _, cost, *_ = hashed_password.split("$")
        if int(cost) < SecurityConstants.BCRYPT_COST:
            raise SecurityException(
                code="WEAK_HASH",
                message="El hash fue generado con un costo insuficiente"
            )
    
    def needs_rehash(self, hashed_password: str) -> bool:
        """Determina si el hash necesita actualización"""
        return self.crypt_ctx.needs_update(hashed_password)
    
    def upgrade_hash(self, password: str, hashed_password: str) -> Optional[str]:
        """
        Actualiza un hash antiguo a la configuración actual
        
        Args:
            password: Contraseña en texto plano
            hashed_password: Hash almacenado
        Returns:
            str: Nuevo hash o None si no es necesario
        """
        if self.needs_rehash(hashed_password):
            return self.hash_password(password)
        return None

# Instancia singleton para inyección de dependencias
password_hasher = PasswordHasher()