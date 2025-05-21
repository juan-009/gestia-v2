from dataclasses import dataclass
from http import HTTPStatus
from typing import Optional, Dict, Any

class DomainException(Exception):
    """Clase base para todas las excepciones del dominio"""
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: HTTPStatus = HTTPStatus.BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

# ==================== EXCEPCIONES BASE ====================
@dataclass
class AuthenticationException(DomainException):
    """Clase base para errores de autenticación"""
    status_code: HTTPStatus = HTTPStatus.UNAUTHORIZED

@dataclass
class AuthorizationException(DomainException):
    """Clase base para errores de autorización"""
    status_code: HTTPStatus = HTTPStatus.FORBIDDEN

@dataclass
class ValidationException(DomainException):
    """Clase base para errores de validación"""
    status_code: HTTPStatus = HTTPStatus.UNPROCESSABLE_ENTITY

# ==================== AUTENTICACIÓN ====================
class InvalidCredentialsError(AuthenticationException):
    """Credenciales inválidas proporcionadas"""
    def __init__(self, details: Optional[Dict] = None):
        super().__init__(
            code="AUTH_001",
            message="Credenciales inválidas",
            details=details
        )

class AccountLockedError(AuthenticationException):
    """Cuenta bloqueada por intentos fallidos"""
    def __init__(self, unlock_in: int):
        super().__init__(
            code="AUTH_002",
            message="Cuenta temporalmente bloqueada",
            details={"unlock_in_seconds": unlock_in}
        )

class InvalidTokenError(AuthenticationException):
    """Token JWT inválido o expirado"""
    def __init__(self, reason: str):
        super().__init__(
            code="AUTH_003",
            message=f"Token inválido: {reason}",
            details={"reason": reason}
        )

# ==================== AUTORIZACIÓN ====================
class PermissionDeniedError(AuthorizationException):
    """Usuario no tiene los permisos requeridos"""
    def __init__(self, permission: str):
        super().__init__(
            code="RBAC_001",
            message="Acceso no autorizado",
            details={
                "required_permission": permission,
                "hint": "Verifique los roles asignados al usuario"
            }
        )

class RoleConflictError(AuthorizationException):
    """Conflicto en asignación de roles"""
    def __init__(self, role: str):
        super().__init__(
            code="RBAC_002",
            message=f"Conflicto con el rol '{role}'",
            details={
                "conflicting_role": role,
                "resolution": "Revise la jerarquía de roles"
            }
        )

# ==================== MFA ====================
class MFARequiredError(AuthenticationException):
    """Se requiere autenticación multifactor"""
    def __init__(self, mfa_type: str):
        super().__init__(
            code="MFA_001",
            message="Autenticación multifactor requerida",
            details={
                "mfa_type": mfa_type,
                "supported_methods": ["TOTP", "WebAuthn"]
            },
            status_code=HTTPStatus.PRECONDITION_REQUIRED
        )

class InvalidMFACodeError(AuthenticationException):
    """Código MFA incorrecto"""
    def __init__(self, attempts_left: int):
        super().__init__(
            code="MFA_002",
            message="Código de verificación inválido",
            details={
                "attempts_left": attempts_left,
                "max_attempts": 5
            }
        )

class MFANotConfiguredError(AuthenticationException):
    """MFA no configurado para el usuario"""
    def __init__(self):
        super().__init__(
            code="MFA_003",
            message="MFA no configurado para esta cuenta",
            details={"action_required": "Configure MFA primero"}
        )

# ==================== VALIDACIÓN ====================
class InvalidEmailError(ValidationException):
    """Email no cumple con el formato requerido"""
    def __init__(self, email: str):
        super().__init__(
            code="VAL_001",
            message=f"Email inválido: {email}",
            details={
                "invalid_field": "email",
                "expected_format": "RFC 5322"
            }
        )

class WeakPasswordError(ValidationException):
    """Contraseña no cumple política de seguridad"""
    def __init__(self, reason: str):
        super().__init__(
            code="VAL_002",
            message="La contraseña no cumple los requisitos de seguridad",
            details={
                "invalid_field": "password",
                "requirements": {
                    "min_length": 12,
                    "complexity": "Mínimo: 1 mayúscula, 1 número, 1 carácter especial"
                },
                "reason": reason
            }
        )

class InvalidPermissionFormatError(ValidationException):
    """Formato de permiso inválido"""
    def __init__(self, permission: str):
        super().__init__(
            code="VAL_003",
            message=f"Formato de permiso inválido: {permission}",
            details={
                "expected_format": "scope:action",
                "examples": ["users:read", "inventory:write"]
            }
        )

# ==================== INFRAESTRUCTURA ====================
class DatabaseError(DomainException):
    """Error genérico de base de datos"""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    def __init__(self, operation: str):
        super().__init__(
            code="INFRA_001",
            message=f"Error en operación de base de datos: {operation}",
            details={
                "component": "database",
                "recommended_action": "Verifique la conexión y los logs"
            }
        )

class CacheConnectionError(DomainException):
    """Error de conexión con Redis"""
    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    def __init__(self):
        super().__init__(
            code="INFRA_002",
            message="Error de conexión con el servicio de caché",
            details={
                "component": "redis",
                "recovery_steps": [
                    "Verifique la configuración de conexión",
                    "Revise el estado del servicio Redis"
                ]
            }
        )

class EventPublishingError(DomainException):
    """Error al publicar evento en Kafka"""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    def __init__(self, event_type: str):
        super().__init__(
            code="INFRA_003",
            message=f"Error publicando evento: {event_type}",
            details={
                "event_type": event_type,
                "recommended_action": "Revise los brokers de Kafka"
            }
        )

# ==================== USO GENERAL ====================
class ConfigurationError(DomainException):
    """Error en configuración del sistema"""
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    def __init__(self, key: str):
        super().__init__(
            code="CONFIG_001",
            message=f"Error de configuración: variable {key} no definida",
            details={
                "missing_key": key,
                "environment_variables": "Verifique el archivo .env"
            }
        )

class RateLimitExceededError(DomainException):
    """Límite de peticiones excedido"""
    status_code = HTTPStatus.TOO_MANY_REQUESTS
    def __init__(self, retry_after: int):
        super().__init__(
            code="RATE_001",
            message="Límite de peticiones excedido",
            details={
                "retry_after_seconds": retry_after,
                "documentation": "https://api.example.com/rate-limits"
            }
        )

class RecoveryCodeUsedError(DomainException):
    """Código de recuperación ya utilizado"""
    status_code = HTTPStatus.BAD_REQUEST
    def __init__(self):
        super().__init__(
            code="RECOV_001",
            message="Código de recuperación ya utilizado",
            details={
                "action_required": "Genere nuevos códigos de recuperación"
            }
        )