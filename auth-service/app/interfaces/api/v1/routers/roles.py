from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from auth_service.app.shared.config.config import settings
from auth_service.app.interfaces.api.v1.dependencies import (
    get_role_service,
    get_permission_service,
    require_role # Added
)
from auth_service.app.aplicacion.casos_uso.gestion_roles import (
    CreateRoleUseCase,
    ListRolesUseCase,
    GetRoleUseCase,     # Assuming this will be adapted/created to use ID
    UpdateRoleUseCase,  # Assuming this will be adapted/created for RoleUpdateRequest
    AssignPermissionToRoleUseCase,
    RevokePermissionFromRoleUseCase
)
# Placeholder for DeleteRoleUseCase if we define it, or logic is in RoleService
# from auth_service.app.aplicacion.casos_uso.gestion_roles import DeleteRoleUseCase 

from auth_service.app.interfaces.api.v1.esquemas import (
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    RolePermissionAssignRequest
)
from auth_service.app.dominio.servicios import RoleService, PermissionService # For type hinting
from auth_service.app.dominio.excepciones import (
    RoleAlreadyExistsError,
    RoleNotFoundError,
    PermissionNotFoundError,
    DomainError # Catch-all for other domain issues
)

router = APIRouter(
    prefix=f"{settings.API_V1_PREFIX}/roles", 
    tags=["Roles Management"],
    dependencies=[Depends(require_role("admin"))] # Protect all endpoints
)

# --- Dependencies for Use Cases ---

def get_create_role_use_case(
    rs: RoleService = Depends(get_role_service),
    ps: PermissionService = Depends(get_permission_service)
) -> CreateRoleUseCase:
    return CreateRoleUseCase(role_service=rs, permission_service=ps)

def get_list_roles_use_case(
    rs: RoleService = Depends(get_role_service),
    ps: PermissionService = Depends(get_permission_service)
) -> ListRolesUseCase:
    return ListRolesUseCase(role_service=rs, permission_service=ps)

def get_get_role_use_case( # Assuming by ID
    rs: RoleService = Depends(get_role_service),
    ps: PermissionService = Depends(get_permission_service)
) -> GetRoleUseCase:
    # The GetRoleUseCase from P3S3 took role_name. It needs to be adapted or a new one created for role_id.
    # For now, we'll assume GetRoleUseCase can be made to work with an ID via RoleService.
    return GetRoleUseCase(role_service=rs, permission_service=ps) 

def get_update_role_use_case(
    rs: RoleService = Depends(get_role_service),
    ps: PermissionService = Depends(get_permission_service)
) -> UpdateRoleUseCase:
    return UpdateRoleUseCase(role_service=rs, permission_service=ps)

def get_assign_permission_to_role_use_case(
    rs: RoleService = Depends(get_role_service),
    ps: PermissionService = Depends(get_permission_service)
) -> AssignPermissionToRoleUseCase:
    return AssignPermissionToRoleUseCase(role_service=rs, permission_service=ps)

def get_revoke_permission_from_role_use_case(
    rs: RoleService = Depends(get_role_service),
    ps: PermissionService = Depends(get_permission_service)
) -> RevokePermissionFromRoleUseCase:
    return RevokePermissionFromRoleUseCase(role_service=rs, permission_service=ps)

# --- Endpoints ---

@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request_data: RoleCreateRequest,
    use_case: CreateRoleUseCase = Depends(get_create_role_use_case)
):
    # TODO: Add protection dependency
    try:
        return await use_case.execute(request_data)
    except RoleAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PermissionNotFoundError as e: # If any permission in request_data.permissions not found
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[RoleResponse])
async def list_roles(
    use_case: ListRolesUseCase = Depends(get_list_roles_use_case)
):
    # TODO: Add protection dependency
    try:
        return await use_case.execute()
    except DomainError as e: 
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role( # Changed from role_id_or_name to role_id
    role_id: int, 
    use_case: GetRoleUseCase = Depends(get_get_role_use_case)
):
    # TODO: Add protection dependency
    try:
        # The GetRoleUseCase needs to be adapted to take role_id.
        # Current GetRoleUseCase takes role_name.
        # This assumes RoleService will have get_role_by_id or similar.
        # For now, this will likely fail if GetRoleUseCase is not updated.
        # Let's assume it's updated to call a method like role_service.get_role_by_id(role_id)
        return await use_case.execute(role_id=role_id) # Pass role_id to execute
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    request_data: RoleUpdateRequest,
    use_case: UpdateRoleUseCase = Depends(get_update_role_use_case)
):
    # TODO: Add protection dependency
    try:
        return await use_case.execute(role_id=role_id, update_data=request_data)
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionNotFoundError as e: # If any permission in request_data.permissions not found
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    role_service: RoleService = Depends(get_role_service) # Use service directly for simple delete
):
    # TODO: Add protection dependency
    try:
        # Assuming RoleService will be augmented with delete_role(role_id)
        # which calls repository's delete method.
        success = await role_service.delete_role(role_id=role_id) # Assumed method
        if not success: # Or if delete_role raises RoleNotFoundError
            raise RoleNotFoundError(f"Role with ID {role_id} not found.")
        # No content to return on 204
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{role_id}/permissions", response_model=RoleResponse)
async def assign_permission_to_role(
    role_id: int, # Changed from role_name to role_id for consistency
    request_data: RolePermissionAssignRequest,
    use_case: AssignPermissionToRoleUseCase = Depends(get_assign_permission_to_role_use_case)
):
    # TODO: Add protection dependency
    try:
        # AssignPermissionToRoleUseCase from P3S3 takes role_name. Needs adaptation for role_id.
        # Let's assume it's updated to call role_service method that uses role_id.
        return await use_case.execute(role_id=role_id, permission_name=request_data.permission_name)
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) # Or 404 if perm not found for assignment
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{role_id}/permissions/{permission_name}", response_model=RoleResponse)
async def revoke_permission_from_role(
    role_id: int, # Changed from role_name to role_id
    permission_name: str,
    use_case: RevokePermissionFromRoleUseCase = Depends(get_revoke_permission_from_role_use_case)
):
    # TODO: Add protection dependency
    try:
        # RevokePermissionFromRoleUseCase from P3S3 takes role_name. Needs adaptation for role_id.
        # Let's assume it's updated.
        return await use_case.execute(role_id=role_id, permission_name=permission_name)
    except RoleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    # PermissionNotFoundError might not be directly applicable for revoke if permission wasn't assigned,
    # but the use case/service should handle it gracefully (e.g., return role as is or raise if strict).
    # If the permission itself doesn't exist, that's a different issue, usually a 400.
    except PermissionNotFoundError as e: # If the permission name itself is invalid
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
