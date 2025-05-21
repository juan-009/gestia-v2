"""
Constantes centralizadas del sistema de autenticación

Mantener consistencia con los requerimientos aprobados:
- RFC-001: Políticas de Seguridad JWT
- RFC-003: Especificación RBAC
- RFC-007: Estándar de Eventos
"""

from enum import Enum
from typing import Final

# ==================== SEGURIDAD ====================
class SecurityConstants:
    """Constantes relacionadas con seguridad y autenticación"""
    
    # JWT
    JWT_CLAIM_ISSUER: Final[str] = "iss"
    JWT_CLAIM_AUDIENCE: Final[str] = "aud"
    JWT_CLAIM_SUBJECT: Final[str] = "sub"
    JWT_CLAIM_JTI: Final[str] = "jti"
    JWT_CLAIM_ROLES: Final[str] = "roles"
    
    TOKEN_TYPE_BEARER: Final[str] = "Bearer"
    TOKEN_HEADER_NAME: Final[str] = "Authorization"
    
    # Password Policies
    PASSWORD_MIN_LENGTH: Final[int] = 12
    PASSWORD_REGEX: Final[str] = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$"
    PASSWORD_HASHER: Final[str] = "bcrypt"
    
    # Rate Limiting
    LOGIN_ATTEMPTS_LIMIT: Final[int] = 5
    LOGIN_LOCKOUT_MINUTES: Final[int] = 15

# ==================== RBAC ====================
class RBACConstants:
    """Constantes para el sistema de Roles y Permisos"""
    
    class DefaultRoles(str, Enum):
        SUPER_ADMIN = "superadmin"
        ADMIN = "admin"
        MANAGER = "manager"
        USER = "user"
    
    PERMISSION_SCOPE_DELIMITER: Final[str] = ":"
    WILDCARD_PERMISSION: Final[str] = "*"
    
    # Permisos predefinidos
    CORE_PERMISSIONS: Final[dict] = {
        "auth": ["read", "write", "delete"],
        "users": ["read", "write", "delete"],
        "roles": ["read", "assign", "manage"]
    }

# ==================== MFA ====================
class MFAConstants:
    """Configuraciones para Autenticación Multifactor"""
    
    TOTP_TIME_STEP: Final[int] = 30  # segundos
    TOTP_CODE_LENGTH: Final[int] = 6
    TOTP_VALID_WINDOW: Final[int] = 2  # ventanas de tiempo válidas
    
    RECOVERY_CODE_LENGTH: Final[int] = 10
    RECOVERY_CODE_FORMAT: Final[str] = "XXXX-XXXX-XX"

# ==================== API ====================
class APIConstants:
    """Constantes relacionadas con la API y HTTP"""
    
    class ErrorCodes(int, Enum):
        VALIDATION_ERROR = 1001
        AUTH_FAILED = 2001
        PERMISSION_DENIED = 2003
        INVALID_TOKEN = 2004
        MFA_REQUIRED = 2005
    
    DEFAULT_PAGINATION_LIMIT: Final[int] = 50
    MAX_PAGINATION_LIMIT: Final[int] = 1000
    
    CACHE_CONTROL_HEADER: Final[str] = "max-age=300, private"

# ==================== CACHING ====================
class CacheConstants:
    """Configuraciones de caché y claves"""
    
    REDIS_KEY_PREFIX: Final[str] = "auth_service"
    
    class Keys:
        ROLE_PERMISSIONS = "role_permissions:{role_id}"
        JTI_BLACKLIST = "jti_blacklist"
        MFA_ATTEMPTS = "mfa_attempts:{user_id}"
    
    DEFAULT_TTL: Final[int] = 300  # 5 minutos

# ==================== EVENTOS ====================
class EventConstants:
    """Nombres y tipos de eventos del sistema"""
    
    EVENT_PREFIX: Final[str] = "auth"
    
    class Types(str, Enum):
        USER_LOGIN_SUCCESS = "user.login.success"
        USER_LOGIN_FAILED = "user.login.failed"
        ROLE_UPDATED = "role.updated"
        PERMISSION_CHANGED = "permission.changed"
    
    EVENT_SCHEMA_VERSION: Final[str] = "1.2.0"

# ==================== ERRORES ====================
class ErrorMessages:
    """Mensajes de error estandarizados"""
    
    INVALID_CREDENTIALS: Final[str] = "Credenciales inválidas"
    MFA_REQUIRED: Final[str] = "Se requiere autenticación multifactor"
    PERMISSION_DENIED: Final[str] = "No tienes permiso para realizar esta acción"
    
    @staticmethod
    def invalid_field(field: str) -> str:
        return f"El campo {field} es inválido"

# Exportación explícita
__all__ = [
    "SecurityConstants",
    "RBACConstants",
    "MFAConstants",
    "APIConstants",
    "CacheConstants",
    "EventConstants",
    "ErrorMessages"
]