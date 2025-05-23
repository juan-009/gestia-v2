from __future__ import annotations
from typing import List, Optional
from auth_service.app.dominio.servicios import UserRoleService, PermissionService # PermissionService for GetUserUseCase
from auth_service.app.dominio.modelos import Usuario, Rol, Permiso # Domain models
from auth_service.app.interfaces.api.v1.esquemas import ( # API Schemas
    UserResponse, PermissionResponse, RoleResponse # RoleResponse for GetUserUseCase
)
from auth_service.app.aplicacion.mappers import (
    map_user_domain_to_response, 
    map_role_domain_to_response, 
    map_permission_domain_to_response
)
# SQLUserRepository is not directly used here, UserRoleService abstracts user fetching.

class AssignRoleToUserUseCase:
    def __init__(self, user_role_service: UserRoleService, permission_service: PermissionService):
        self.user_role_service = user_role_service
        self.permission_service = permission_service # Needed to construct full UserResponse

    async def execute(self, user_id: int, role_name: str) -> UserResponse:
        # UserRoleService.assign_role_to_user returns the updated domain Usuario
        updated_domain_user = await self.user_role_service.assign_role_to_user(user_id, role_name)
        
        # To build UserResponse, we need List[RoleResponse].
        # Each RoleResponse needs List[PermissionResponse].
        # The updated_domain_user.roles contains list of role names.
        
        role_responses: List[RoleResponse] = []
        if updated_domain_user.roles:
            for r_name in updated_domain_user.roles:
                # Fetch the full Rol domain model
                # UserRoleService.get_user_roles returns List[Rol], but we need one role.
                # RoleService.get_role_with_permissions returns Rol with permission names.
                # This implies UserRoleService might need a get_role_by_name or similar,
                # or we use RoleService here. Let's assume UserRoleService can provide it.
                # For now, let's use user_role_service.get_user_roles and filter.
                # This is inefficient. Ideally, RoleService.get_role_by_name is used.
                # Let's assume we have access to RoleService or a way to get full Rol object.
                # The UserRoleService has role_repository.
                
                # Correct approach: Use UserRoleService to get roles, then PermissionService for permissions
                domain_role = await self.user_role_service.role_repository.get_by_name(r_name) # Direct repo access or service method
                if domain_role:
                    permission_objects: List[Permiso] = []
                    if domain_role.permissions: # these are permission names
                        for p_name in domain_role.permissions:
                            perm_obj = await self.permission_service.get_permission_by_name(p_name)
                            permission_objects.append(perm_obj)
                    role_responses.append(map_role_domain_to_response(domain_role, permission_objects))
            
        return map_user_domain_to_response(updated_domain_user, role_responses)

class RevokeRoleFromUserUseCase:
    def __init__(self, user_role_service: UserRoleService, permission_service: PermissionService):
        self.user_role_service = user_role_service
        self.permission_service = permission_service # Needed to construct full UserResponse

    async def execute(self, user_id: int, role_name: str) -> UserResponse:
        updated_domain_user = await self.user_role_service.revoke_role_from_user(user_id, role_name)
        
        role_responses: List[RoleResponse] = []
        if updated_domain_user.roles:
            for r_name in updated_domain_user.roles:
                domain_role = await self.user_role_service.role_repository.get_by_name(r_name)
                if domain_role:
                    permission_objects: List[Permiso] = []
                    if domain_role.permissions:
                        for p_name in domain_role.permissions:
                            perm_obj = await self.permission_service.get_permission_by_name(p_name)
                            permission_objects.append(perm_obj)
                    role_responses.append(map_role_domain_to_response(domain_role, permission_objects))
            
        return map_user_domain_to_response(updated_domain_user, role_responses)

class GetUserPermissionsUseCase:
    def __init__(self, user_role_service: UserRoleService):
        self.user_role_service = user_role_service

    async def execute(self, user_id: int) -> List[PermissionResponse]:
        # UserRoleService.get_user_permissions returns List[Permiso] (domain models)
        domain_permissions = await self.user_role_service.get_user_permissions(user_id)
        return [map_permission_domain_to_response(p) for p in domain_permissions]

class GetUserUseCase:
    def __init__(self, user_role_service: UserRoleService, permission_service: PermissionService):
        # user_role_service for fetching user and their roles (domain)
        # permission_service for fetching permission details for each role (domain)
        self.user_role_service = user_role_service
        self.permission_service = permission_service

    async def execute(self, user_id: int) -> UserResponse:
        # 1. Fetch the domain Usuario object
        # UserRoleService has user_repository. We need a method like get_user_by_id from UserRoleService
        # or use user_repository directly. Let's assume UserRoleService.user_repository.get_by_id
        domain_user = await self.user_role_service.user_repository.get_by_id(user_id)
        if not domain_user:
            # UserRoleService.get_user_roles would raise UserNotFoundError, so this is consistent
            from auth_service.app.dominio.excepciones import UserNotFoundError
            raise UserNotFoundError(f"User with ID {user_id} not found.")

        # 2. Fetch the list of domain Rol objects for the user
        # UserRoleService.get_user_roles returns List[Rol]
        user_domain_roles: List[Rol] = await self.user_role_service.get_user_roles(user_id)
        
        # 3. For each domain Rol, fetch its domain Permiso objects and map to RoleResponse
        role_responses: List[RoleResponse] = []
        for domain_role in user_domain_roles:
            permission_objects: List[Permiso] = []
            if domain_role.permissions: # These are permission names
                for p_name in domain_role.permissions:
                    # Use PermissionService to get full Permiso domain objects
                    perm_obj = await self.permission_service.get_permission_by_name(p_name)
                    permission_objects.append(perm_obj)
            # Map the domain Rol and its domain Permiso objects to a RoleResponse
            role_responses.append(map_role_domain_to_response(domain_role, permission_objects))
            
        # 4. Map the domain Usuario and the list of RoleResponse objects to UserResponse
        return map_user_domain_to_response(domain_user, role_responses)
