from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from auth_service.app.shared.config.config import settings
from auth_service.app.interfaces.api.v1.dependencies import (
    get_permission_service, 
    require_role, # Added
    # get_current_active_user # Not directly used in endpoint signatures, but by require_role
    # get_uow is indirectly used by get_permission_service
)
# from auth_service.app.aplicacion.dto import UserDTO # For type hinting current_user if needed
from auth_service.app.aplicacion.casos_uso.gestion_permisos import (
    CreatePermissionUseCase,
    ListPermissionsUseCase,
    GetPermissionUseCase
)
from auth_service.app.interfaces.api.v1.esquemas import (
    PermissionCreateRequest,
    PermissionResponse
)
from auth_service.app.dominio.servicios import PermissionService # For type hinting
from auth_service.app.dominio.excepciones import (
    PermissionAlreadyExistsError,
    PermissionNotFoundError,
    DomainError # Catch-all for other domain issues
)

router = APIRouter(
    prefix=f"{settings.API_V1_PREFIX}/permissions", 
    tags=["Permissions Management"],
    dependencies=[Depends(require_role("admin"))] # Protect all endpoints in this router
)

# --- Dependencies for Use Cases ---

def get_create_permission_use_case(
    ps: PermissionService = Depends(get_permission_service)
) -> CreatePermissionUseCase:
    return CreatePermissionUseCase(permission_service=ps)

def get_list_permissions_use_case(
    ps: PermissionService = Depends(get_permission_service)
) -> ListPermissionsUseCase:
    return ListPermissionsUseCase(permission_service=ps)

def get_get_permission_use_case(
    ps: PermissionService = Depends(get_permission_service)
) -> GetPermissionUseCase:
    return GetPermissionUseCase(permission_service=ps)

# --- Endpoints ---

@router.post(
    "/", 
    response_model=PermissionResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_permission(
    request_data: PermissionCreateRequest,
    use_case: CreatePermissionUseCase = Depends(get_create_permission_use_case)
):
    # TODO: Add protection dependency (e.g., require admin privileges)
    try:
        return await use_case.execute(request_data)
    except PermissionAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except DomainError as e: # Catch other specific domain errors
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # Unhandled exceptions will be caught by global_exception_handler_middleware

@router.get("/", response_model=List[PermissionResponse])
async def list_permissions(
    use_case: ListPermissionsUseCase = Depends(get_list_permissions_use_case)
):
    # TODO: Add protection dependency (e.g., authenticated user, specific permissions)
    try:
        return await use_case.execute()
    except DomainError as e: 
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{permission_name}", response_model=PermissionResponse)
async def get_permission(
    permission_name: str,
    use_case: GetPermissionUseCase = Depends(get_get_permission_use_case)
):
    # TODO: Add protection dependency
    try:
        return await use_case.execute(name=permission_name)
    except PermissionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DomainError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
