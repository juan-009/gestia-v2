from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import Optional

from uuid import UUID
from app.shared.config.config import settings

from app.aplicacion.casos_uso.autenticacion import AuthUseCases
from app.dominio.excepciones import (
    InvalidCredentialsError,
    AccountLockedError,
    MFARequiredError
)
from app.infraestructura.seguridad.jwt_manager import jwt_manager
from app.infraestructura.seguridad.hasher import password_hasher
from app.interfaces.api.v1.dependencias import get_auth_service
from app.interfaces.api.middlewares.auth import oauth2_scheme
from app.interfaces.api.v1.esquemas import usuario as schemas

router = APIRouter(prefix="/auth", tags=["Autenticación"])

class TokenResponse(BaseModel):
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(default="bearer", example="bearer")
    expires_in: int = Field(..., example=900)
    refresh_token: Optional[str] = Field(None, example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")

class MFAResponse(BaseModel):
    mfa_required: bool = Field(default=True)
    mfa_type: str = Field(..., example="TOTP")
    mfa_challenge: Optional[str] = Field(None, example="base64encodeddata")

@router.post("/login", response_model=TokenResponse, responses={
    200: {"description": "Autenticación exitosa"},
    202: {"description": "MFA requerido", "model": MFAResponse},
    401: {"description": "Credenciales inválidas"},
    423: {"description": "Cuenta bloqueada temporalmente"}
})
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthUseCases = Depends(get_auth_service)
):
    """
    Autentica un usuario y devuelve tokens JWT.
    
    - **username**: Email del usuario
    - **password**: Contraseña del usuario
    """
    try:
        user = await auth_service.authenticate_user(form_data.username, form_data.password)
        
        # Verificar si requiere MFA
        if user.mfa_enabled:
            challenge = await auth_service.generate_mfa_challenge(user.id)
            return {
                "mfa_required": True,
                "mfa_type": "TOTP",
                "mfa_challenge": challenge
            }
        
        # Generar tokens
        access_token = jwt_manager.create_access_token(
            subject=str(user.id),
            payload={"roles": [role.name for role in user.roles]}
        )
        refresh_token = jwt_manager.create_refresh_token(str(user.id))
        
        # Configurar cookie segura para refresh token
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="lax",
            max_age=settings.JWT_REFRESH_EXPIRE_DAYS * 86400
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_EXPIRE_MINUTES * 60
        }

    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Cuenta bloqueada temporalmente",
            headers={"Retry-After": str(e.details["unlock_in_seconds"])}
        )
    except MFARequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail=e.details
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_token: str = Depends(oauth2_scheme)
):
    """Obtiene un nuevo access token usando el refresh token"""
    try:
        claims = jwt_manager.validate_token(refresh_token)
        if claims.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
        
        new_access_token = jwt_manager.create_access_token(
            subject=claims.sub,
            payload={"roles": claims.roles}
        )
        
        # Rotar refresh token
        new_refresh_token = jwt_manager.create_refresh_token(claims.sub)
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="lax",
            max_age=settings.JWT_REFRESH_EXPIRE_DAYS * 86400
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_EXPIRE_MINUTES * 60
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresh inválido o expirado"
        )

@router.post("/logout")
async def logout(
    response: Response,
    token: str = Depends(oauth2_scheme),
    current_user: schemas.User = Depends(jwt_manager.get_current_user)
):
    """Invalida el token actual y cierra la sesión"""
    claims = jwt_manager.validate_token(token)
    jwt_manager.revoke_token(claims.jti, expire_in=settings.JWT_ACCESS_EXPIRE_MINUTES * 60)
    
    # Eliminar cookie de refresh token
    response.delete_cookie("refresh_token")
    
    return {"message": "Sesión cerrada exitosamente"}

@router.get("/me", response_model=schemas.User)
async def get_current_user(
    current_user: schemas.User = Depends(jwt_manager.get_current_user)
):
    """Devuelve la información del usuario autenticado"""
    return current_user