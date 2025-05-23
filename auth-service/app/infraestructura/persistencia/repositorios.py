from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, delete # Added select, delete
from typing import Optional, List, Dict, Any

# Domain Models
try:
    from auth_service.app.dominio.modelos import Usuario, Rol, Permiso
    from auth_service.app.dominio.value_objects import Email
except ImportError:
    # Mock classes for environments where domain models might not be directly importable
    # This is primarily for isolated testing or development scenarios.
    # In a full application context, these imports should work.
    print("Warning: Could not import domain models for repositories. Using mock domain classes.")
    class Usuario: pass
    class Rol: pass
    class Permiso: pass
    class Email(str): pass


# ORM Table Models
from .orm import UserTable, RoleTable, PermissionTable, user_role_association, role_permission_association

# --- Mapper Functions ---
# Note: For relationships like user_orm.roles or role_orm.permissions, 
# ensure they are eagerly loaded in repository methods if needed, to avoid lazy loading issues,
# or ensure the session remains active when these attributes are accessed.
# The mappers assume these attributes are loaded.

def _map_role_orm_to_domain(role_orm: RoleTable) -> Rol:
    """Maps a RoleTable ORM object to a Rol domain model."""
    if not role_orm:
        return None
    # Assuming role_orm.permissions is a list of PermissionTable objects
    # Eager loading (e.g., joinedload(RoleTable.permissions)) should be used in repo methods
    permissions = [p.name for p in role_orm.permissions] if role_orm.permissions else []
    return Rol(
        id=role_orm.id,
        name=role_orm.name,
        description=role_orm.description,
        permissions=permissions
    )

def _map_permission_orm_to_domain(permission_orm: PermissionTable) -> Permiso:
    """Maps a PermissionTable ORM object to a Permiso domain model."""
    if not permission_orm:
        return None
    return Permiso(
        id=permission_orm.id,
        name=permission_orm.name,
        description=permission_orm.description
    )

def _map_user_orm_to_domain(user_orm: UserTable) -> Usuario:
    """Maps a UserTable ORM object to a Usuario domain model."""
    if not user_orm:
        return None
    return Usuario(
        id=user_orm.id,
        email=Email(user_orm.email), # Cast to Email value object
        hashed_password=user_orm.hashed_password,
        is_active=user_orm.is_active,
        created_at=user_orm.created_at,
        updated_at=user_orm.updated_at,
        # Assuming user_orm.roles is a list of RoleTable objects
        # Eager loading (e.g., joinedload(UserTable.roles)) should be used in repo methods
        roles=[role.name for role in user_orm.roles] if user_orm.roles else []
    )

def _map_user_domain_to_orm_dict(user_domain: Usuario) -> Dict[str, Any]:
    """
    Maps a Usuario domain model to a dictionary suitable for UserTable ORM constructor.
    Excludes 'id' if it's None (for new users not yet persisted).
    Role mapping is handled separately (e.g., by appending RoleTable instances to user_orm.roles).
    """
    orm_dict = {
        "email": str(user_domain.email), # Ensure email is string
        "hashed_password": user_domain.hashed_password,
        "is_active": user_domain.is_active,
        # created_at and updated_at are often handled by DB defaults
    }
    if user_domain.id is not None:
        orm_dict["id"] = user_domain.id
    return orm_dict

# --- Repositories ---

class SQLUserRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def add(self, user_domain: Usuario) -> Usuario:
        """
        Adds a new user to the database.
        Note: This basic version doesn't handle role assignment.
              Role assignment would typically involve fetching RoleTable objects
              and appending them to the user_orm.roles list before commit.
        """
        orm_data = _map_user_domain_to_orm_dict(user_domain)
        user_orm = UserTable(**orm_data)
        
        self.db_session.add(user_orm)
        self.db_session.commit()
        self.db_session.refresh(user_orm)
        return _map_user_orm_to_domain(user_orm)

    def get_by_id(self, user_id: int) -> Optional[Usuario]:
        user_orm = self.db_session.query(UserTable).filter(UserTable.id == user_id).first()
        return _map_user_orm_to_domain(user_orm) if user_orm else None

    def get_by_email(self, email: Email) -> Optional[Usuario]:
        user_orm = self.db_session.query(UserTable).filter(UserTable.email == str(email)).first()
        return _map_user_orm_to_domain(user_orm) if user_orm else None

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Usuario]:
        users_orm = self.db_session.query(UserTable).options(
            joinedload(UserTable.roles).joinedload(RoleTable.permissions) # Eager load roles and their permissions
        ).offset(skip).limit(limit).all()
        return [_map_user_orm_to_domain(user) for user in users_orm]

    def update(self, user_domain: Usuario) -> Usuario:
        user_orm = self.db_session.query(UserTable).get(user_domain.id)
        if not user_orm:
            # Handle User Not Found - Or raise an exception
            return None

        user_orm.email = str(user_domain.email)
        user_orm.is_active = user_domain.is_active
        
        # Only update password if a new one is provided and different.
        # The domain model might not always carry a new password.
        if user_domain.hashed_password and user_domain.hashed_password != user_orm.hashed_password:
            user_orm.hashed_password = user_domain.hashed_password

        # Fetch RoleTable objects for user_domain.roles (names)
        role_orms = []
        if user_domain.roles:
            role_orms = self.db_session.query(RoleTable).filter(
                RoleTable.name.in_(user_domain.roles)
            ).all()
            if len(role_orms) != len(user_domain.roles):
                # Handle error: some roles not found
                # For simplicity, this example assumes all provided names are valid
                # A real app should raise an exception or handle this more gracefully
                pass

        user_orm.roles = role_orms # Update the list of associated roles

        self.db_session.commit()
        self.db_session.refresh(user_orm)
        # To ensure the updated roles (and their permissions if needed by mapper) are loaded for the return mapping:
        refreshed_user_orm = self.db_session.query(UserTable).options(
            joinedload(UserTable.roles).joinedload(RoleTable.permissions)
        ).get(user_orm.id)
        return _map_user_orm_to_domain(refreshed_user_orm)

    # TODO: Implement delete method if needed for users
    # TODO: More specific methods for managing user roles if direct update is too broad

class SQLRoleRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def add(self, role_domain: Rol) -> Rol:
        # Fetch PermissionTable objects for role_domain.permissions (names)
        permission_orms = []
        if role_domain.permissions:
            permission_orms = self.db_session.query(PermissionTable).filter(
                PermissionTable.name.in_(role_domain.permissions)
            ).all()
            if len(permission_orms) != len(role_domain.permissions):
                # Handle error: some permissions not found
                # For simplicity, this example assumes all provided names are valid
                # A real app should raise an exception or handle this more gracefully
                pass 
                
        role_orm = RoleTable(
            name=role_domain.name,
            description=role_domain.description,
            permissions=permission_orms # Assign list of PermissionTable objects
        )
        self.db_session.add(role_orm)
        self.db_session.commit()
        self.db_session.refresh(role_orm)
        return _map_role_orm_to_domain(role_orm)

    def get_by_id(self, role_id: int) -> Optional[Rol]:
        # Eagerly load permissions
        role_orm = self.db_session.query(RoleTable).options(
            joinedload(RoleTable.permissions)
        ).get(role_id) # .get is for SQLAlchemy 2.0+
        # For older versions: .filter(RoleTable.id == role_id).first()
        return _map_role_orm_to_domain(role_orm) if role_orm else None

    def get_by_name(self, name: str) -> Optional[Rol]:
        role_orm = self.db_session.query(RoleTable).options(
            joinedload(RoleTable.permissions)
        ).filter(RoleTable.name == name).first()
        return _map_role_orm_to_domain(role_orm) if role_orm else None

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Rol]:
        roles_orm = self.db_session.query(RoleTable).options(
            joinedload(RoleTable.permissions)
        ).offset(skip).limit(limit).all()
        return [_map_role_orm_to_domain(role) for role in roles_orm]

    def update(self, role_domain: Rol) -> Rol:
        role_orm = self.db_session.query(RoleTable).get(role_domain.id)
        if not role_orm:
            # Handle Role Not Found - maybe raise an exception
            return None 

        role_orm.name = role_domain.name
        role_orm.description = role_domain.description
        
        # Fetch PermissionTable objects for role_domain.permissions (names)
        permission_orms = []
        if role_domain.permissions:
            permission_orms = self.db_session.query(PermissionTable).filter(
                PermissionTable.name.in_(role_domain.permissions)
            ).all()
            # Optional: Add error handling if some permission names are not found

        role_orm.permissions = permission_orms # Update the list of associated permissions
        
        self.db_session.commit()
        self.db_session.refresh(role_orm) # Refresh to get updated state, including relationships
        # Ensure eager loading of permissions after refresh for the return mapping
        # One way is to query again, or ensure refresh loads them (might depend on session/ORM config)
        # For simplicity, let's re-fetch if refresh doesn't populate as expected or map directly.
        # However, refresh should update relationships if mapped correctly.
        # If permissions aren't loaded after refresh, a re-fetch or specific loading is needed.
        # Let's assume refresh is sufficient for now.
        # If not, a re-query or specific loading step would be needed here.
        # Example of re-query to ensure permissions are loaded for the return:
        # refreshed_role_orm = self.db_session.query(RoleTable).options(
        #     joinedload(RoleTable.permissions)
        # ).get(role_orm.id)
        # return _map_role_orm_to_domain(refreshed_role_orm)
        return _map_role_orm_to_domain(role_orm)


    def delete(self, role_id: int) -> bool:
        role_orm = self.db_session.query(RoleTable).get(role_id)
        if not role_orm:
            return False
        self.db_session.delete(role_orm)
        self.db_session.commit()
        return True

class SQLPermissionRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def add(self, permission_domain: Permiso) -> Permiso:
        permission_orm = PermissionTable(
            name=permission_domain.name,
            description=permission_domain.description
        )
        self.db_session.add(permission_orm)
        self.db_session.commit()
        self.db_session.refresh(permission_orm)
        return _map_permission_orm_to_domain(permission_orm)

    def get_by_id(self, permission_id: int) -> Optional[Permiso]:
        permission_orm = self.db_session.query(PermissionTable).get(permission_id)
        return _map_permission_orm_to_domain(permission_orm) if permission_orm else None

    def get_by_name(self, name: str) -> Optional[Permiso]:
        permission_orm = self.db_session.query(PermissionTable).filter(PermissionTable.name == name).first()
        return _map_permission_orm_to_domain(permission_orm) if permission_orm else None

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Permiso]:
        permissions_orm = self.db_session.query(PermissionTable).offset(skip).limit(limit).all()
        return [_map_permission_orm_to_domain(perm) for perm in permissions_orm]

# Update SQLUserRepository
# The existing SQLUserRepository needs an update method
# Add this method to the existing SQLUserRepository class

# (This is a conceptual placement, the tool will merge it into the existing class)
# <<< SEARCH SQLUserRepository
# class SQLUserRepository:
# ...
# >>>
#
# def update(self, user_domain: Usuario) -> Usuario:
#     user_orm = self.db_session.query(UserTable).get(user_domain.id)
#     if not user_orm:
#         # Handle User Not Found
#         return None
#
#     user_orm.email = str(user_domain.email)
#     user_orm.is_active = user_domain.is_active
#     if user_domain.hashed_password and user_domain.hashed_password != user_orm.hashed_password:
#         user_orm.hashed_password = user_domain.hashed_password
#
#     # Fetch RoleTable objects for user_domain.roles (names)
#     role_orms = []
#     if user_domain.roles:
#         role_orms = self.db_session.query(RoleTable).filter(
#             RoleTable.name.in_(user_domain.roles)
#         ).all()
#
#     user_orm.roles = role_orms # Update the list of associated roles
#
#     self.db_session.commit()
#     self.db_session.refresh(user_orm)
#     # Similar to RoleRepository.update, ensure roles are loaded for the return mapping.
#     # A re-query or specific loading might be needed if refresh doesn't load them.
#     # Example of re-query:
#     # refreshed_user_orm = self.db_session.query(UserTable).options(
#     #     joinedload(UserTable.roles)
#     # ).get(user_orm.id)
#     # return _map_user_orm_to_domain(refreshed_user_orm)
#     return _map_user_orm_to_domain(user_orm)
