from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import List, Optional
import re

class UsuarioBaseDTO(BaseModel):
    email: EmailStr
    nombres: str = Field(..., min_length=2, max_length=50)
    apellidos: str = Field(..., min_length=2, max_length=50)

class UsuarioCreacionDTO(UsuarioBaseDTO):
    password: str
    
    @validator('password')
    def validar_password(cls, v):
        if len(v) < 12:
            raise ValueError("La contraseña debe tener al menos 12 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Debe contener al menos una mayúscula")
        if not re.search(r"\d", v):
            raise ValueError("Debe contener al menos un número")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Debe contener al menos un carácter especial")
        return v

class UsuarioActualizacionDTO(BaseModel):
    nombres: Optional[str] = Field(None, min_length=2, max_length=50)
    apellidos: Optional[str] = Field(None, min_length=2, max_length=50)
    telefono: Optional[str] = Field(None, regex=r"^\+\d{1,3}\d{9,15}$")

class UsuarioRespuestaDTO(UsuarioBaseDTO):
    id: str
    roles: List[str] = []
    esta_activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        orm_mode = True

class AutenticacionEntradaDTO(BaseModel):
    email: EmailStr
    password: str
    codigo_mfa: Optional[str] = Field(None, min_length=6, max_length=6)

class TokensRespuestaDTO(BaseModel):
    access_token: str
    refresh_token: str
    tipo_token: str = "Bearer"
    expira_en: int

class RolBaseDTO(BaseModel):
    nombre: str = Field(..., min_length=3, max_length=50, regex=r"^[a-z_]+$")
    descripcion: str = Field(..., max_length=255)

class RolCreacionDTO(RolBaseDTO):
    permisos: List[str] = []
    hereda: List[str] = []

    @validator('permisos', each_item=True)
    def validar_formato_permiso(cls, v):
        if not re.match(r"^[a-z]+:[a-z]+$", v):
            raise ValueError("Formato de permiso inválido. Usar: 'recurso:accion'")
        return v

class RolRespuestaDTO(RolBaseDTO):
    permisos: List[str] = []
    hereda: List[str] = []
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        orm_mode = True

class AsignacionRolesDTO(BaseModel):
    usuario_id: str
    roles: List[str]
    
    @validator('roles', each_item=True)
    def validar_nombre_rol(cls, v):
        if not re.match(r"^[a-z_]+$", v):
            raise ValueError("Formato de rol inválido. Solo minúsculas y guiones bajos")
        return v

class OperacionAuditoriaDTO(BaseModel):
    tipo_evento: str
    usuario_id: str
    detalles: dict
    direccion_ip: str
    user_agent: str

class ErrorRespuestaDTO(BaseModel):
    codigo: str
    mensaje: str
    detalles: Optional[dict] = None

class PaginacionDTO(BaseModel):
    pagina: int = Field(1, ge=1)
    tamano_pagina: int = Field(25, ge=1, le=100)

class BusquedaUsuariosDTO(PaginacionDTO):
    filtro_nombre: Optional[str] = None
    filtro_rol: Optional[str] = None
    solo_activos: bool = True

class ConfiguracionMFADTO(BaseModel):
    tipo_mfa: str = Field(..., regex="^(TOTP|WebAuthn)$")
    dispositivo: Optional[str] = None

class RecuperacionPasswordDTO(BaseModel):
    email: EmailStr
    token_recuperacion: Optional[str] = None
    nueva_password: Optional[str] = None