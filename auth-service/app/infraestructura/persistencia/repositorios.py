from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

# Domain Models - adjust path if your domain models are structured differently
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
from .orm import UserTable, RoleTable, PermissionTable

# --- Mapper Functions ---

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
        roles=[role.name for role in user_orm.roles] # Assuming roles relationship loads RoleTable objects
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
        users_orm = self.db_session.query(UserTable).offset(skip).limit(limit).all()
        return [_map_user_orm_to_domain(user) for user in users_orm]

    # TODO: Implement update and delete methods
    # TODO: Implement methods for managing user roles

class SQLRoleRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
    # TODO: Implement CRUD methods for Roles
    # TODO: Implement methods for managing role permissions

class SQLPermissionRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
    # TODO: Implement CRUD methods for Permissions
