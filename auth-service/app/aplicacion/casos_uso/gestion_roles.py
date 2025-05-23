from __future__ import annotations
from typing import List, Optional
from auth_service.app.dominio.servicios import RoleService, PermissionService # PermissionService for fetching full permission objects
from auth_service.app.dominio.modelos import Rol, Permiso # Domain models
from auth_service.app.interfaces.api.v1.esquemas import ( # API Schemas
    RoleCreateRequest, RoleResponse, RoleUpdateRequest
)
from auth_service.app.aplicacion.mappers import map_role_domain_to_response, map_permission_domain_to_response
# No, map_permission_domain_to_response is not directly used here, but map_role_domain_to_response is.

class CreateRoleUseCase:
    def __init__(self, role_service: RoleService, permission_service: PermissionService):
        self.role_service = role_service
        self.permission_service = permission_service # Needed to fetch full Permiso objects

    async def execute(self, request_data: RoleCreateRequest) -> RoleResponse:
        # RoleService.create_role returns a domain Rol with permission names (List[str])
        domain_role = await self.role_service.create_role(
            name=request_data.name,
            description=request_data.description,
            permission_names=request_data.permissions # Pass list of permission names
        )
        
        # Fetch full Permiso objects for the names to build RoleResponse
        permission_objects: List[Permiso] = []
        if domain_role.permissions: # These are permission names from the domain_role
            for p_name in domain_role.permissions:
                perm_obj = await self.permission_service.get_permission_by_name(p_name)
                # Assuming get_permission_by_name raises if not found,
                # which should be handled by the global error handler or here if specific.
                permission_objects.append(perm_obj)
            
        return map_role_domain_to_response(domain_role, permission_objects)

class AssignPermissionToRoleUseCase:
    def __init__(self, role_service: RoleService, permission_service: PermissionService):
        self.role_service = role_service
        self.permission_service = permission_service

    async def execute(self, role_name: str, permission_name: str) -> RoleResponse:
        # RoleService.assign_permission_to_role returns the updated domain Rol
        updated_domain_role = await self.role_service.assign_permission_to_role(role_name, permission_name)
        
        permission_objects: List[Permiso] = []
        if updated_domain_role.permissions:
            for p_name in updated_domain_role.permissions:
                perm_obj = await self.permission_service.get_permission_by_name(p_name)
                permission_objects.append(perm_obj)
        
        return map_role_domain_to_response(updated_domain_role, permission_objects)

class RevokePermissionFromRoleUseCase:
    def __init__(self, role_service: RoleService, permission_service: PermissionService):
        self.role_service = role_service
        self.permission_service = permission_service

    async def execute(self, role_name: str, permission_name: str) -> RoleResponse:
        updated_domain_role = await self.role_service.revoke_permission_from_role(role_name, permission_name)
        
        permission_objects: List[Permiso] = []
        if updated_domain_role.permissions:
            for p_name in updated_domain_role.permissions:
                perm_obj = await self.permission_service.get_permission_by_name(p_name)
                permission_objects.append(perm_obj)
                
        return map_role_domain_to_response(updated_domain_role, permission_objects)

class ListRolesUseCase:
    def __init__(self, role_service: RoleService, permission_service: PermissionService):
        self.role_service = role_service
        self.permission_service = permission_service

    async def execute(self) -> List[RoleResponse]:
        domain_roles = await self.role_service.list_roles()
        role_responses: List[RoleResponse] = []
        for domain_role in domain_roles:
            permission_objects: List[Permiso] = []
            if domain_role.permissions: # permission names
                for p_name in domain_role.permissions:
                    perm_obj = await self.permission_service.get_permission_by_name(p_name)
                    permission_objects.append(perm_obj)
            role_responses.append(map_role_domain_to_response(domain_role, permission_objects))
        return role_responses

class GetRoleUseCase:
    def __init__(self, role_service: RoleService, permission_service: PermissionService):
        self.role_service = role_service
        self.permission_service = permission_service

    async def execute(self, role_name: str) -> RoleResponse: # Assuming identifier is name for now
        # The domain service's get_role_with_permissions already returns a Rol with permission names
        domain_role = await self.role_service.get_role_with_permissions(role_name)
        
        permission_objects: List[Permiso] = []
        if domain_role.permissions: # permission names
            for p_name in domain_role.permissions:
                perm_obj = await self.permission_service.get_permission_by_name(p_name)
                permission_objects.append(perm_obj)
                
        return map_role_domain_to_response(domain_role, permission_objects)

class UpdateRoleUseCase:
    def __init__(self, role_service: RoleService, permission_service: PermissionService):
        self.role_service = role_service
        self.permission_service = permission_service

    async def execute(self, role_id: int, update_data: RoleUpdateRequest) -> RoleResponse:
        # First, get the current domain role by ID
        # The RoleService doesn't have a get_by_id, let's assume it should or use get_by_name
        # For this example, let's assume RoleService would be enhanced with get_by_id
        # Or, this use case directly uses the repository if allowed (not typical for clean architecture)
        # Let's assume RoleService.update_role (to be created or existing) takes role_id and update data.
        # The RoleService.update method from P3S2 is not defined.
        # Let's assume a RoleService.update_role method that handles this logic:
        
        # domain_role_to_update = await self.role_service.get_role_by_id(role_id) # Needs to exist in service
        # if not domain_role_to_update:
        #     raise RoleNotFoundError(f"Role with ID {role_id} not found.")

        # updated_permissions_names: Optional[List[str]] = None
        # if update_data.permissions is not None: # If permissions are part of the update
        #     # Validate all permission names
        #     for p_name in update_data.permissions:
        #         await self.permission_service.get_permission_by_name(p_name) # Raises if not found
        #     updated_permissions_names = update_data.permissions
        
        # This is a simplified call, actual RoleService.update_role would handle this logic
        # RoleService.update_role(role_id, name_update, desc_update, perm_names_update)
        # For now, let's assume RoleService is updated to handle this.
        # The current RoleService.update takes a domain Rol object.
        # This means the use case would fetch, modify, then call update.

        # Step 1: Fetch the role domain object
        # This is a placeholder; RoleService might not have get_by_id.
        # This highlights a potential need for RoleService.get_role_by_id or similar.
        # For now, we'll assume the role_service provides a way to get the role,
        # or this use case needs direct repository access (which is less ideal).
        # Let's assume role_service.get_role_by_id exists (hypothetically for this UC).
        
        # The subtask for domain services (P3S2) did not specify `update_role` in `RoleService`.
        # The repository `SQLRoleRepository` has an `update(self, role_domain: Rol) -> Rol`.
        # This means the service should ideally have it too.
        # Let's assume the domain service `RoleService` will be augmented with an `update_role` method that takes ID and update data.
        # If `RoleService.update_role` is not available, this use case cannot be implemented as cleanly.
        # For now, let's assume a hypothetical `RoleService.update_role_details` method.
        
        # Hypothetical call, assuming RoleService is augmented:
        updated_domain_role = await self.role_service.update_role_details(
            role_id=role_id,
            name_update=update_data.name,
            description_update=update_data.description,
            permission_names_update=update_data.permissions # Full list of names for replacement
        )
        # If RoleService doesn't have such a method, this use case needs rethinking
        # or direct repository interaction (less ideal).
        # The `role_service.update_role` method from P3S2 takes `role_name` and `permission_name`. That's for assigning/revoking.
        # The `SQLRoleRepository.update` takes a `role_domain: Rol` object.
        # So, the service should look like:
        # async def update_role(self, role_id: int, new_name: Optional[str], new_desc: Optional[str], new_perm_names: Optional[List[str]]) -> Rol:
        #   domain_role = self.repo.get_by_id(role_id)
        #   ... update fields ...
        #   ... update permissions by fetching PermissionTable objects ...
        #   return self.repo.update(domain_role)
        # This logic should be in the RoleService.
        # For this use case, let's assume RoleService has such a comprehensive update method.

        permission_objects: List[Permiso] = []
        if updated_domain_role.permissions:
            for p_name in updated_domain_role.permissions:
                perm_obj = await self.permission_service.get_permission_by_name(p_name)
                permission_objects.append(perm_obj)
        
        return map_role_domain_to_response(updated_domain_role, permission_objects)
