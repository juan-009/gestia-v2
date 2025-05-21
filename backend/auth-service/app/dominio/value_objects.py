from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import re
import uuid

from pydantic import BaseModel, EmailStr, field_validator
import phonenumbers

from app.shared.config.constants import (
    SecurityConstants,
    RBACConstants,
    MFAConstants
)
from app.dominio.excepciones import (
    InvalidEmailError,
    WeakPasswordError,
    InvalidPhoneNumberError,
    InvalidJWTClaimsError
)

@dataclass(frozen=True)
class Email:
    """Value Object para gestión de emails con validación RFC 5322"""
    value: str

    def __post_init__(self):
        # Validación básica de formato
        if not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", self.value):
            raise InvalidEmailError("Formato de email inválido")
        
        # Validación adicional de dominio
        if self.value.split('@')[1].startswith('example'):
            raise InvalidEmailError("Dominio no permitido")

    @property
    def domain(self) -> str:
        return self.value.split('@')[1]

    @property
    def normalized(self) -> str:
        return self.value.strip().lower()

@dataclass(frozen=True)
class PasswordHash:
    """Value Object para contraseñas hasheadas con validación de fortaleza"""
    value: str
    pepper: Optional[str] = None

    def __post_init__(self):
        self._validate_strength()
    
    def _validate_strength(self):
        """Valida que el hash cumpla con los requisitos de seguridad"""
        if not self.value.startswith("$2b$"):
            raise WeakPasswordError("Formato de hash inválido")
        
        # Verificar costo mínimo de bcrypt
        cost = int(self.value.split('$')[2])
        if cost < SecurityConstants.BCRYPT_COST:
            raise WeakPasswordError("Costo de hashing insuficiente")

    def verify(self, password: str) -> bool:
        """Verifica una contraseña contra el hash"""
        from app.infraestructura.seguridad.hasher import verify_password
        return verify_password(password, self.value, self.pepper)

@dataclass(frozen=True)
class JWTClaims:
    """Value Object para claims JWT con validación de estructura"""
    sub: uuid.UUID  # User ID
    iss: str
    aud: str
    jti: uuid.UUID
    roles: List[str]
    exp: datetime
    iat: datetime = datetime.utcnow()

    @field_validator('roles')
    def validate_roles(cls, roles):
        if not roles:
            raise InvalidJWTClaimsError("Se requieren roles en el token")
        return roles

    @field_validator('iss')
    def validate_issuer(cls, iss):
        if iss != SecurityConstants.JWT_ISSUER:
            raise InvalidJWTClaimsError("Issuer no válido")
        return iss

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_permission(self, permission: str) -> bool:
        # Implementar lógica de permisos según RBAC
        return any(
            permission.startswith(f"{scope}{RBACConstants.PERMISSION_SCOPE_DELIMITER}") and
            permission.split(RBACConstants.PERMISSION_SCOPE_DELIMITER)[1] in RBACConstants.CORE_PERMISSIONS.get(scope, [])
            for scope in RBACConstants.CORE_PERMISSIONS.keys()
        )

@dataclass(frozen=True)
class PhoneNumber:
    """Value Object para números telefónicos internacionales"""
    number: str
    country_code: str = "US"

    def __post_init__(self):
        try:
            parsed = phonenumbers.parse(self.number, self.country_code)
            if not phonenumbers.is_valid_number(parsed):
                raise InvalidPhoneNumberError("Número telefónico inválido")
        except phonenumbers.NumberParseException:
            raise InvalidPhoneNumberError("Formato no reconocido")

    @property
    def international_format(self) -> str:
        parsed = phonenumbers.parse(self.number, self.country_code)
        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )

@dataclass(frozen=True)
class TOTPSecret:
    """Value Object para secretos TOTP con validación de formato"""
    secret: str
    length: int = MFAConstants.TOTP_CODE_LENGTH
    interval: int = MFAConstants.TOTP_TIME_STEP

    def __post_init__(self):
        if len(self.secret) != 32:
            raise ValueError("Secreto TOTP debe tener 32 caracteres")
        if not self.secret.isalnum():
            raise ValueError("Secreto contiene caracteres inválidos")

@dataclass(frozen=True)
class RecoveryCodes:
    """Value Object para códigos de recuperación de MFA"""
    codes: List[str]
    code_length: int = MFAConstants.RECOVERY_CODE_LENGTH

    def __post_init__(self):
        if len(self.codes) != MFAConstants.MFA_RECOVERY_CODES:
            raise ValueError("Cantidad incorrecta de códigos")
        
        for code in self.codes:
            if len(code) != self.code_length:
                raise ValueError(f"Longitud de código inválida: {code}")

class LoginAttempt(BaseModel):
    """Value Object para tracking de intentos de login"""
    ip_address: str
    user_agent: str
    timestamp: datetime = datetime.utcnow()
    successful: bool = False
    mfa_used: bool = False

    @field_validator('ip_address')
    def validate_ip(cls, ip):
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
            raise ValueError("Dirección IP inválida")
        return ip

class Permission(BaseModel):
    """Value Object para permisos RBAC con validación de formato"""
    scope: str
    action: str

    @field_validator('scope')
    def validate_scope(cls, scope):
        valid_scopes = list(RBACConstants.CORE_PERMISSIONS.keys())
        if scope not in valid_scopes:
            raise ValueError(f"Scope inválido. Válidos: {valid_scopes}")
        return scope

    @field_validator('action')
    def validate_action(cls, action):
        valid_actions = {"read", "write", "delete", "manage", "*"}
        if action not in valid_actions:
            raise ValueError(f"Acción inválida. Válidas: {valid_actions}")
        return action

    @property
    def full_permission(self) -> str:
        return f"{self.scope}{RBACConstants.PERMISSION_SCOPE_DELIMITER}{self.action}"