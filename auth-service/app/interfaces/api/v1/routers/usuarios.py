from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from auth_service.app.shared.config.config import settings
from auth_service.app.interfaces.api.v1.esquemas import (
    UserResponse, PermissionResponse, UserRoleAssignRequest
)
from auth_service.app.aplicacion.casos_uso.gestion_usuarios import (
    AssignRoleToUserUseCase, RevokeRoleFromUserUseCase,
    GetUserPermissionsUseCase, GetUserUseCase
)
from auth_service.app.interfaces.api.v1.dependencies import (
    get_user_role_service,
    get_permission_service,
    require_role # Added
)
from auth_service.app.dominio.excepciones import UserNotFoundError, RoleNotFoundError, DomainError
from auth_service.app.aplicacion.servicios import UserRoleService, PermissionService # For type hinting

router = APIRouter(
    prefix=f"{settings.API_V1_PREFIX}/users", 
    tags=["Users Management"],
    dependencies=[Depends(require_role("admin"))] # Protect all user management endpoints
)

# --- Dependencies for Use Cases ---

def get_assign_role_to_user_use_case(
    urs: UserRoleService = Depends(get_user_role_service),
    ps: PermissionService = Depends(get_permission_service) # Added as per P3S3 use case def
) -> AssignRoleToUserUseCase:
    return AssignRoleToUserUseCase(user_role_service=urs, permission_service=ps)

def get_revoke_role_from_user_use_case(
    urs: UserRoleService = Depends(get_user_role_service),
    ps: PermissionService = Depends(get_permission_service) # Added as per P3S3 use case def
) -> RevokeRoleFromUserUseCase:
    return RevokeRoleFromUserUseCase(user_role_service=urs, permission_service=ps)

def get_get_user_permissions_use_case(
    urs: UserRoleService = Depends(get_user_role_service)
) -> GetUserPermissionsUseCase:
    return GetUserPermissionsUseCase(user_role_service=urs)

def get_get_user_use_case(
    urs: UserRoleService = Depends(get_user_role_service),
    ps: PermissionService = Depends(get_permission_service) # Corrected dependency
) -> GetUserUseCase:
    # GetUserUseCase from P3S3 __init__ takes (user_role_service, permission_service)
    return GetUserUseCase(user_role_service=urs, permission_service=ps)

# --- Endpoints ---

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int, 
    use_case: GetUserUseCase = Depends(get_get_user_use_case)
):
    # Protection is now handled at router level by require_role("admin")
    # Individual endpoint TODOs for protection can be removed or refined later if needed
    # for more granular checks (e.g., user can access their own info).
    try:
        return await use_case.execute(user_id=user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{user_id}/roles", response_model=UserResponse)
async def assign_role_to_user(
    user_id: int, 
    assignment_request: UserRoleAssignRequest, 
    use_case: AssignRoleToUserUseCase = Depends(get_assign_role_to_user_use_case)
):
    try:
        return await use_case.execute(user_id=user_id, role_name=assignment_request.role_name)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RoleNotFoundError as e:
        # Role to be assigned not found
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{user_id}/roles/{role_name}", response_model=UserResponse)
async def revoke_role_from_user(
    user_id: int, 
    role_name: str, 
    use_case: RevokeRoleFromUserUseCase = Depends(get_revoke_role_from_user_use_case)
):
    try:
        return await use_case.execute(user_id=user_id, role_name=role_name)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RoleNotFoundError as e: 
        # This might mean the role itself doesn't exist, or was not assigned to the user.
        # The use case / service should clarify. If role name is invalid, 400. If role valid but not assigned, maybe 200 OK.
        # For now, assume service handles "role not assigned to user" gracefully,
        # and RoleNotFoundError means "the role definition itself was not found".
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{user_id}/permissions", response_model=List[PermissionResponse])
async def get_user_permissions(
    user_id: int, 
    use_case: GetUserPermissionsUseCase = Depends(get_get_user_permissions_use_case)
):
    try:
        return await use_case.execute(user_id=user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
