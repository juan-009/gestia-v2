from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

class HTTPError(BaseModel):
    """Esquema base para respuestas de error"""
    detail: str = Field(..., example="Error detallado")
    code: str = Field(..., example="ERROR_CODE")
    status_code: int = Field(..., example=400)

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Error específico ocurrido",
                "code": "ESPECIFIC_ERROR_CODE",
                "status_code": 400
            }
        }

class UserBase(BaseModel):
    """Esquema base para usuarios"""
    email: EmailStr = Field(..., example="usuario@example.com")
    full_name: Optional[str] = Field(None, example="Juan Pérez")

class UserCreate(UserBase):
    """Esquema para creación de usuarios"""
    password: str = Field(..., min_length=12, example="Str0ngP@ssw0rd!")
    
    @field_validator('password')
    def validate_password(cls, v):
        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$", v):
            raise ValueError("La contraseña no cumple con los requisitos de seguridad")
        return v

class UserUpdate(BaseModel):
    """Esquema para actualización de usuarios"""
    full_name: Optional[str] = Field(None, example="Juan Pérez Actualizado")
    is_active: Optional[bool] = Field(None, example=True)
    mfa_enabled: Optional[bool] = Field(None, example=False)

class UserOut(UserBase):
    """Esquema de respuesta para usuarios"""
    id: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    is_active: bool = Field(..., example=True)
    mfa_enabled: bool = Field(..., example=False)
    created_at: datetime = Field(..., example="2023-01-01T00:00:00Z")
    updated_at: datetime = Field(..., example="2023-01-01T00:00:00Z")
    roles: List[str] = Field(..., example=["user", "admin"])

    class Config:
        from_attributes = True

class Token(BaseModel):
    """Esquema para respuesta de tokens JWT"""
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", example="bearer")
    expires_in: int = Field(..., example=900)

class TokenPayload(BaseModel):
    """Esquema para el payload del token JWT"""
    sub: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    roles: List[str] = Field(..., example=["user"])
    exp: datetime = Field(..., example=1735689600)
    iat: datetime = Field(..., example=1635689600)
    jti: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")

class MFAEnable(BaseModel):
    """Esquema para habilitación de MFA"""
    secret: str = Field(..., example="JBSWY3DPEHPK3PXP")
    code: str = Field(..., min_length=6, max_length=6, example="123456")

class MFAResponse(BaseModel):
    """Respuesta para flujos MFA"""
    mfa_required: bool = Field(default=True, example=True)
    mfa_type: str = Field(..., example="TOTP")
    recovery_codes: Optional[List[str]] = Field(
        None,
        example=["ABCDE-12345", "FGHIJ-67890"]
    )

class RoleBase(BaseModel):
    """Esquema base para roles"""
    name: str = Field(..., min_length=3, example="admin")
    description: Optional[str] = Field(None, example="Administrador del sistema")

    @field_validator('name')
    def validate_role_name(cls, v):
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError("El nombre del rol solo puede contener letras minúsculas, números y guiones bajos")
        return v

class RoleCreate(RoleBase):
    """Esquema para creación de roles"""
    pass

class RoleOut(RoleBase):
    """Esquema de respuesta para roles"""
    id: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    is_system: bool = Field(..., example=False)
    created_at: datetime = Field(..., example="2023-01-01T00:00:00Z")
    updated_at: datetime = Field(..., example="2023-01-01T00:00:00Z")
    permissions: List[str] = Field(..., example=["users:read", "users:write"])

    class Config:
        from_attributes = True

class PermissionBase(BaseModel):
    """Esquema base para permisos"""
    name: str = Field(..., example="users:write")
    description: Optional[str] = Field(None, example="Permite modificar usuarios")

    @field_validator('name')
    def validate_permission_format(cls, v):
        if not re.match(r"^[a-z]+:[a-z]+$", v):
            raise ValueError("Formato de permiso inválido. Usar: 'recurso:accion'")
        return v

class PermissionCreate(PermissionBase):
    """Esquema para creación de permisos"""
    pass

class PermissionOut(PermissionBase):
    """Esquema de respuesta para permisos"""
    id: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    created_at: datetime = Field(..., example="2023-01-01T00:00:00Z")
    updated_at: datetime = Field(..., example="2023-01-01T00:00:00Z")

    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    """Esquema base para respuestas paginadas"""
    data: List[BaseModel]
    total: int = Field(..., example=100)
    limit: int = Field(..., example=50)
    offset: int = Field(..., example=0)

# Ejemplos de esquemas paginados
class PaginatedUsers(PaginatedResponse):
    data: List[UserOut]

class PaginatedRoles(PaginatedResponse):
    data: List[RoleOut]

class PasswordResetRequest(BaseModel):
    """Esquema para solicitud de reseteo de contraseña"""
    email: EmailStr = Field(..., example="usuario@example.com")

class PasswordResetConfirm(BaseModel):
    """Esquema para confirmación de reseteo de contraseña"""
    token: str = Field(..., example="reset_token_123")
    new_password: str = Field(..., min_length=12, example="NewStr0ngP@ss!")

class WebAuthnRegistrationRequest(BaseModel):
    """Esquema para registro de WebAuthn"""
    credential_name: str = Field(..., example="Llave de seguridad principal")
    credential_type: str = Field(..., example="public-key")

class SessionInfo(BaseModel):
    """Esquema para información de sesión activa"""
    id: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    device_info: Optional[str] = Field(None, example="Chrome/Windows")
    ip_address: str = Field(..., example="192.168.1.1")
    last_activity: datetime = Field(..., example="2023-01-01T00:00:00Z")
    expires_at: datetime = Field(..., example="2023-01-01T01:00:00Z")