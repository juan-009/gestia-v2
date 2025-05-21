from typing import Annotated, AsyncGenerator
from fastapi import Depends, HTTPException, status
from jose import JWTError

from app.infraestructura.persistencia.orm import UnitOfWork
from app.infraestructura.seguridad.jwt_manager import jwt_manager
from app.infraestructura.seguridad.hasher import password_hasher
from app.dominio.excepciones import (
    PermissionDeniedError,
    UserNotFoundError,
    TokenRevokedError
)
from app.aplicacion.servicios import (
    AuthService,
    UserService,
    RoleService
)
from app.interfaces.api.v1.esquemas import TokenPayload, UserOut

async def get_db() -> AsyncGenerator[UnitOfWork, None]:
    """Provee una instancia de UnitOfWork con manejo transaccional"""
    async with UnitOfWork() as uow:
        try:
            yield uow
        except Exception as e:
            await uow.rollback()
            raise
        else:
            await uow.commit()

async def get_current_user(
    uow: Annotated[UnitOfWork, Depends(get_db)],
    token: str = Depends(jwt_manager.oauth2_scheme)
) -> UserOut:
    """Dependencia para obtener el usuario autenticado actual"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt_manager.validate_token(token)
        if payload is None:
            raise credentials_exception
            
        user_repo = uow.users
        user = await user_repo.get_by_id(payload.sub)
        if user is None:
            raise UserNotFoundError(payload.sub)
            
        return UserOut.model_validate(user)
    except (JWTError, TokenRevokedError, UserNotFoundError) as e:
        raise credentials_exception from e

async def get_current_active_user(
    current_user: Annotated[UserOut, Depends(get_current_user)]
) -> UserOut:
    """Verifica que el usuario esté activo"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    return current_user

def require_permission(permission: str):
    """Factory para dependencias de verificación de permisos"""
    async def permission_checker(
        user: Annotated[UserOut, Depends(get_current_active_user)]
    ) -> UserOut:
        if not any(permission in role.permissions for role in user.roles):
            raise PermissionDeniedError(permission)
        return user
    return permission_checker

def get_auth_service(
    uow: Annotated[UnitOfWork, Depends(get_db)]
) -> AuthService:
    """Provee el servicio de autenticación con sus dependencias"""
    return AuthService(
        user_repo=uow.users,
        role_repo=uow.roles,
        hasher=password_hasher,
        jwt_manager=jwt_manager
    )

def get_user_service(
    uow: Annotated[UnitOfWork, Depends(get_db)]
) -> UserService:
    """Provee el servicio de gestión de usuarios"""
    return UserService(
        user_repo=uow.users,
        role_repo=uow.roles,
        session_repo=uow.sessions
    )

def get_role_service(
    uow: Annotated[UnitOfWork, Depends(get_db)]
) -> RoleService:
    """Provee el servicio de gestión de roles"""
    return RoleService(
        role_repo=uow.roles,
        permission_repo=uow.permissions
    )

# Atajos de tipos para uso en endpoints
CurrentUser = Annotated[UserOut, Depends(get_current_active_user)]
AdminUser = Annotated[UserOut, Depends(require_permission("admin:full"))]
DBSession = Annotated[UnitOfWork, Depends(get_db)]
AuthServices = Annotated[AuthService, Depends(get_auth_service)]
UserServices = Annotated[UserService, Depends(get_user_service)]
RoleServices = Annotated[RoleService, Depends(get_role_service)]