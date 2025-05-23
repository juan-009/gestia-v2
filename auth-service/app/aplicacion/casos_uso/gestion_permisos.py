from __future__ import annotations
from typing import List
from auth_service.app.dominio.servicios import PermissionService
from auth_service.app.dominio.modelos import Permiso # Domain model
from auth_service.app.interfaces.api.v1.esquemas import ( # API Schemas
    PermissionCreateRequest, PermissionResponse
)
from auth_service.app.aplicacion.mappers import map_permission_domain_to_response

class CreatePermissionUseCase:
    def __init__(self, permission_service: PermissionService):
        self.permission_service = permission_service

    async def execute(self, request_data: PermissionCreateRequest) -> PermissionResponse:
        # Domain service create_permission is expected to handle PermissionAlreadyExistsError
        # and return a domain Permiso object.
        domain_permission = await self.permission_service.create_permission(
            name=request_data.name,
            description=request_data.description
        )
        return map_permission_domain_to_response(domain_permission)

class ListPermissionsUseCase:
    def __init__(self, permission_service: PermissionService):
        self.permission_service = permission_service

    async def execute(self) -> List[PermissionResponse]:
        domain_permissions = await self.permission_service.list_permissions()
        return [map_permission_domain_to_response(p) for p in domain_permissions]

class GetPermissionUseCase:
    def __init__(self, permission_service: PermissionService):
        self.permission_service = permission_service

    async def execute(self, name: str) -> PermissionResponse:
        # Domain service get_permission_by_name is expected to handle PermissionNotFoundError
        domain_permission = await self.permission_service.get_permission_by_name(name)
        return map_permission_domain_to_response(domain_permission)
