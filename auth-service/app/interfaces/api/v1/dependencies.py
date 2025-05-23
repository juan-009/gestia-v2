from fastapi import Request, HTTPException, status, Depends # Updated imports
from typing import Optional, Callable, List # Added List

# Domain Value Objects & DTOs
from auth_service.app.dominio.value_objects import JWTClaims
from auth_service.app.aplicacion.dto import UserDTO

# UoW Imports & Repositories
from auth_service.app.infraestructura.persistencia.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from auth_service.app.infraestructura.persistencia.repositorios import SQLUserRepository, SQLRoleRepository

# Cache Imports
from auth_service.app.infraestructura.cache.redis_client import get_redis_pool
from auth_service.app.infraestructura.cache.redis import RolePermissionsCache
from redis.asyncio import Redis as AIORedis # For type hinting

# Service Imports
from auth_service.app.aplicacion.servicios import AuthService, PermissionService, RoleService, UserRoleService

# Repository Imports (needed for service instantiation if UoW provides them directly)
# These are implicitly used via uow.users, uow.roles, uow.permissions
# from auth_service.app.infraestructura.persistencia.repositorios import (
#     SQLUserRepository, 
#     SQLRoleRepository, 
#     SQLPermissionRepository
# )

# --- Unit of Work Dependency ---
async def get_uow() -> AbstractUnitOfWork:
    """
    Provides an asynchronous unit of work instance.
    """
    async with SqlAlchemyUnitOfWork() as uow:
        yield uow

# --- Service Dependencies ---

def get_auth_service(uow: AbstractUnitOfWork = Depends(get_uow)) -> AuthService:
    """
    Provides an instance of AuthService, initialized with the user repository from the UoW.
    """
    # Assuming uow.users is correctly initialized by SqlAlchemyUnitOfWork.__aenter__
    return AuthService(user_repository=uow.users)

# --- Cache Dependencies ---
async def get_redis_client() -> AIORedis:
    return await get_redis_pool()

def get_role_permissions_cache(redis_client: AIORedis = Depends(get_redis_client)) -> RolePermissionsCache:
    return RolePermissionsCache(redis_client)

# --- Service Dependencies (Updated) ---

def get_permission_service(uow: AbstractUnitOfWork = Depends(get_uow)) -> PermissionService:
    """
    Provides an instance of PermissionService, initialized with the permission repository from the UoW.
    (PermissionService currently does not use caching directly)
    """
    return PermissionService(permission_repository=uow.permissions)

def get_role_service(
    uow: AbstractUnitOfWork = Depends(get_uow),
    cache: RolePermissionsCache = Depends(get_role_permissions_cache) # Added cache dependency
) -> RoleService:
    """
    Provides an instance of RoleService, initialized with repositories from the UoW and cache.
    """
    return RoleService(
        role_repository=uow.roles, 
        permission_repository=uow.permissions,
        cache=cache
    )

def get_user_role_service(
    uow: AbstractUnitOfWork = Depends(get_uow),
    cache: RolePermissionsCache = Depends(get_role_permissions_cache) # Added cache dependency
) -> UserRoleService:
    """
    Provides an instance of UserRoleService, initialized with repositories from the UoW and cache.
    """
    return UserRoleService(
        user_repository=uow.users,
        role_repository=uow.roles,
        permission_repository=uow.permissions,
        cache=cache
    )

# --- JWT Claims & Current User Dependencies ---

async def get_user_claims_from_state(request: Request) -> Optional[JWTClaims]:
    """
    Retrieves JWT claims stored in request.state by the JWTAuthMiddleware.
    """
    return getattr(request.state, "user_claims", None)

async def get_current_active_user(
    uow: AbstractUnitOfWork = Depends(get_uow), 
    claims: Optional[JWTClaims] = Depends(get_user_claims_from_state)
) -> UserDTO:
    """
    Retrieves the current authenticated and active user based on JWT claims.
    Raises HTTPException if not authenticated, user not found, or user inactive.
    """
    if claims is None or claims.sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(claims.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo: SQLUserRepository = uow.users # uow.users is SQLUserRepository
    # Adapt to async if repository methods become async
    # Current repository methods are synchronous.
    user_domain = user_repo.get_by_id(user_id) 

    if not user_domain or not user_domain.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Map domain Usuario to UserDTO. UserDTO.roles expects List[str] (role names)
    # user_domain.roles is already List[str] as per P3S1 update of modelos.py
    # UserDTO (P2S1) has: id, email, is_active, roles: List[str], hashed_password: Optional[str]
    return UserDTO(
        id=user_domain.id,
        email=str(user_domain.email), # Ensure email (EmailStr) is converted to str if needed by DTO, though Pydantic usually handles it.
        is_active=user_domain.is_active,
        roles=user_domain.roles, # Directly use the list of role names
        hashed_password=user_domain.hashed_password # UserDTO can carry this
    )

# --- Role-based Authorization Dependency ---

def require_role(required_role: str): # No '-> Callable' hint for simplicity
    """
    Factory for a dependency that checks if the current user has a specific role.
    Raises HTTPException (403 Forbidden) if the user does not have the role.
    """
    async def role_checker(current_user: UserDTO = Depends(get_current_active_user)) -> None:
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have the required '{required_role}' role."
            )
        # return current_user # Can return user if endpoint needs it, otherwise None is fine for a check
    return role_checker


# Note: SQLUserRepository, SQLRoleRepository, SQLPermissionRepository are not directly exposed as dependencies
# because services depend on their abstractions (or concrete types if directly used by services,
# which are then wrapped by the UoW). The UoW provides the concrete repository instances.
