from __future__ import annotations # For type hinting with forward references
from typing import List, Optional
from auth_service.app.dominio.modelos import Usuario, Rol, Permiso
from auth_service.app.infraestructura.persistencia.repositorios import (
     SQLUserRepository, SQLRoleRepository, SQLPermissionRepository
)
# Import for cache
from auth_service.app.infraestructura.cache.redis import RolePermissionsCache
from auth_service.app.dominio.excepciones import (
    UserNotFoundError, RoleNotFoundError, PermissionNotFoundError,
    RoleAlreadyExistsError, PermissionAlreadyExistsError, DomainError
)

class PermissionService:
    def __init__(self, permission_repository: SQLPermissionRepository):
        self.permission_repository = permission_repository

    async def create_permission(self, name: str, description: Optional[str] = None) -> Permiso:
        if self.permission_repository.get_by_name(name): 
            raise PermissionAlreadyExistsError(f"Permission '{name}' already exists.")
        permission = Permiso(name=name, description=description)
        # No cache interaction for creating individual permissions, 
        # as RolePermissionsCache is specific to role->permissions mapping.
        return self.permission_repository.add(permission)

    async def get_permission_by_name(self, name: str) -> Permiso:
        permission = self.permission_repository.get_by_name(name)
        if not permission:
            raise PermissionNotFoundError(f"Permission '{name}' not found.")
        return permission

    async def list_permissions(self) -> List[Permiso]:
        return self.permission_repository.list_all()

class RoleService:
    def __init__(
        self, 
        role_repository: SQLRoleRepository, 
        permission_repository: SQLPermissionRepository,
        cache: Optional[RolePermissionsCache] = None # Added cache
    ):
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.cache = cache # Store cache instance

    async def create_role(self, name: str, description: Optional[str] = None, permission_names: Optional[List[str]] = None) -> Rol:
        if self.role_repository.get_by_name(name):
            raise RoleAlreadyExistsError(f"Role '{name}' already exists.")
        
        valid_permission_names = [] # Store names as per Rol domain model
        if permission_names:
            for p_name in permission_names:
                p = self.permission_repository.get_by_name(p_name)
                if not p:
                    raise PermissionNotFoundError(f"Permission '{p_name}' not found during role creation.")
                valid_permission_names.append(p.name)

        role = Rol(name=name, description=description, permissions=valid_permission_names)
        created_role = self.role_repository.add(role) # This repo method handles associating by names
        
        if self.cache and created_role.permissions is not None: # Cache initial permissions
            await self.cache.set_role_permissions(created_role.name, created_role.permissions)
            
        return created_role

    async def assign_permission_to_role(self, role_name: str, permission_name: str) -> Rol:
        role = self.role_repository.get_by_name(role_name)
        if not role:
            raise RoleNotFoundError(f"Role '{role_name}' not found.")
        permission = self.permission_repository.get_by_name(permission_name)
        if not permission:
            raise PermissionNotFoundError(f"Permission '{permission_name}' not found.")
        
        updated_role = role
        if permission.name not in role.permissions:
            role.permissions.append(permission.name)
            updated_role = self.role_repository.update(role) # Repo update handles persisting this
            if self.cache:
                await self.cache.clear_role_permissions(updated_role.name)
        return updated_role

    async def revoke_permission_from_role(self, role_name: str, permission_name: str) -> Rol:
        role = self.role_repository.get_by_name(role_name)
        if not role:
            raise RoleNotFoundError(f"Role '{role_name}' not found.")
        
        updated_role = role
        if permission_name in role.permissions:
            # Ensure permission exists before trying to remove; good for robustness though `in` check is primary
            # permission = self.permission_repository.get_by_name(permission_name)
            # if not permission:
            #     raise PermissionNotFoundError(f"Permission '{permission_name}' to revoke not found (consistency issue).")
            role.permissions.remove(permission_name)
            updated_role = self.role_repository.update(role)
            if self.cache:
                await self.cache.clear_role_permissions(updated_role.name)
        return updated_role
    
    async def get_role_with_permissions(self, role_name: str) -> Rol:
        # This method is primarily for fetching. Cache interaction for reads
        # would typically be here or at a higher level (e.g., use case).
        # For now, UserRoleService.get_user_permissions handles the read-caching.
        # If direct role fetching needs caching, it would be similar.
        role = self.role_repository.get_by_name(role_name) 
        if not role:
            raise RoleNotFoundError(f"Role '{role_name}' not found.")
        # `role.permissions` are just names here from the repo.
        return role

    async def list_roles(self) -> List[Rol]:
        # Listing roles might not directly benefit from RolePermissionsCache unless
        # we were to cache each role individually, which is not the current cache design.
        return self.role_repository.list_all()

    async def update_role_details(self, role_id: int, name_update: Optional[str], description_update: Optional[str], permission_names_update: Optional[List[str]]) -> Rol:
        """
        Updates a role's name, description, and its full list of permissions.
        If permission_names_update is None, permissions are not changed.
        If it's an empty list, all permissions are removed.
        """
        domain_role = self.role_repository.get_by_id(role_id)
        if not domain_role:
            raise RoleNotFoundError(f"Role with ID {role_id} not found.")

        if name_update is not None:
            # If name changes, we might need to invalidate old cache key and update new one
            # This also implies checking for name uniqueness if it changes
            if name_update != domain_role.name:
                existing_with_new_name = self.role_repository.get_by_name(name_update)
                if existing_with_new_name and existing_with_new_name.id != role_id:
                    raise RoleAlreadyExistsError(f"Another role with name '{name_update}' already exists.")
                if self.cache: # Invalidate cache for old role name if name changes
                    await self.cache.clear_role_permissions(domain_role.name)
            domain_role.name = name_update
        
        if description_update is not None:
            domain_role.description = description_update

        permissions_changed = False
        if permission_names_update is not None:
            permissions_changed = True
            valid_new_permission_names = []
            for p_name in permission_names_update:
                perm = self.permission_repository.get_by_name(p_name)
                if not perm:
                    raise PermissionNotFoundError(f"Permission '{p_name}' not found during role update.")
                valid_new_permission_names.append(perm.name)
            domain_role.permissions = valid_new_permission_names
        
        updated_role = self.role_repository.update(domain_role) # repo.update persists changes

        if self.cache and permissions_changed: # If permissions were part of the update
            await self.cache.clear_role_permissions(updated_role.name)
        elif self.cache and name_update and name_update != domain_role.name: # If only name changed, still update cache key
             # Re-set cache with new name if only name changed and permissions were not part of this update call
             # This assumes updated_role.permissions are current.
            if updated_role.permissions is not None: # Check if permissions list is not None
                 await self.cache.set_role_permissions(updated_role.name, updated_role.permissions)

        return updated_role

    async def delete_role(self, role_id: int) -> bool:
        """Deletes a role and clears its cache."""
        role_to_delete = self.role_repository.get_by_id(role_id)
        if not role_to_delete:
            # Or raise RoleNotFoundError if preferred for router to catch
            return False 
            
        deleted = self.role_repository.delete(role_id)
        if deleted and self.cache:
            await self.cache.clear_role_permissions(role_to_delete.name)
        return deleted

class UserRoleService:
    def __init__(
        self, 
        user_repository: SQLUserRepository, 
        role_repository: SQLRoleRepository, 
        permission_repository: SQLPermissionRepository, # Retain for direct perm checks if needed elsewhere
        cache: Optional[RolePermissionsCache] = None # Added cache
    ):
        self.user_repository = user_repository
        self.role_repository = role_repository
        self.permission_repository = permission_repository
        self.cache = cache # Store cache instance

    async def assign_role_to_user(self, user_id: int, role_name: str) -> Usuario:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User ID '{user_id}' not found.")
        role = self.role_repository.get_by_name(role_name)
        if not role:
            raise RoleNotFoundError(f"Role '{role_name}' not found.")
        
        updated_user = user
        if role.name not in user.roles:
            user.roles.append(role.name)
            # User repository update handles persisting this change.
            updated_user = self.user_repository.update(user) 
            # No direct cache impact here for RolePermissionsCache,
            # as user-role assignment changes don't alter role-permission definitions.
        return updated_user

    async def revoke_role_from_user(self, user_id: int, role_name: str) -> Usuario:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User ID '{user_id}' not found.")
        
        updated_user = user
        if role_name in user.roles:
            # Role existence check (self.role_repository.get_by_name(role_name)) is implicitly done
            # if we need to ensure the role string being removed is a valid role.
            # For now, just remove if name is in list.
            user.roles.remove(role_name)
            updated_user = self.user_repository.update(user)
        return updated_user

    async def get_user_roles(self, user_id: int) -> List[Rol]:
        user = self.user_repository.get_by_id(user_id) # This loads user with role names
        if not user:
            raise UserNotFoundError(f"User ID '{user_id}' not found.")
        
        roles_list: List[Rol] = []
        if user.roles: # List of role names
            for role_name in user.roles:
                # Fetch the full Rol domain model (which includes its permission names)
                role_domain = self.role_repository.get_by_name(role_name)
                if role_domain: 
                    roles_list.append(role_domain)
        return roles_list

    async def get_user_permissions(self, user_id: int) -> List[Permiso]:
        user_domain_roles = await self.get_user_roles(user_id) # Gets List[Rol]
        
        effective_permission_names: set[str] = set()
        for role_domain in user_domain_roles: # role_domain is a Rol domain model
            
            role_permission_names_from_cache: Optional[List[str]] = None
            if self.cache:
                role_permission_names_from_cache = await self.cache.get_role_permissions(role_domain.name)
            
            current_role_permissions: List[str]
            if role_permission_names_from_cache is not None:
                current_role_permissions = role_permission_names_from_cache
                # print(f"Cache hit for role {role_domain.name} permissions.") # Debugging
            else:
                # Cache miss or no cache: role_domain.permissions are names from DB (via repo)
                current_role_permissions = role_domain.permissions 
                # print(f"Cache miss for role {role_domain.name}. Using DB permissions: {current_role_permissions}") # Debugging
                if self.cache and current_role_permissions is not None: # Cache if fetched from DB
                    await self.cache.set_role_permissions(role_domain.name, current_role_permissions)
            
            if current_role_permissions: # Ensure it's not None
                for p_name in current_role_permissions:
                    effective_permission_names.add(p_name)
        
        # Fetch full Permiso domain objects for the unique names
        permissions_list: List[Permiso] = []
        if effective_permission_names:
            for p_name in list(effective_permission_names):
                # This still requires fetching each permission.
                # An alternative could be a permission_repo.get_by_names_list([...])
                permission_domain = self.permission_repository.get_by_name(p_name)
                if permission_domain: 
                    permissions_list.append(permission_domain)
        return permissions_list
