from sqlalchemy.orm import Session
from ..models.models import Role as RoleModel
from ..schemas.role import RoleCreate, RoleUpdate

def get_role(db: Session, role_id: int) -> RoleModel | None:
    """
    Retrieves a role from the database by its ID.
    """
    return db.query(RoleModel).filter(RoleModel.id == role_id).first()

def get_role_by_name(db: Session, name: str) -> RoleModel | None:
    """
    Retrieves a role from the database by its name.
    """
    return db.query(RoleModel).filter(RoleModel.name == name).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100) -> list[RoleModel]:
    """
    Retrieves a list of roles from the database.
    """
    return db.query(RoleModel).offset(skip).limit(limit).all()

def create_role(db: Session, role: RoleCreate) -> RoleModel:
    """
    Creates a new role in the database.
    Raises ValueError if a role with the same name already exists.
    """
    if get_role_by_name(db, name=role.name):
        # This check should ideally be handled in the API layer to return a proper HTTP response
        # For now, we raise ValueError as per the instruction for CRUD layer.
        raise ValueError(f"Role with name '{role.name}' already exists.")
        
    db_role = RoleModel(name=role.name, description=role.description)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def update_role(db: Session, role_id: int, role_in: RoleUpdate) -> RoleModel | None:
    """
    Updates an existing role in the database.
    """
    db_role = get_role(db, role_id=role_id)
    if not db_role:
        return None

    update_data = role_in.model_dump(exclude_unset=True) # Pydantic v2
    # For Pydantic v1, use: update_data = role_in.dict(exclude_unset=True)

    if "name" in update_data and update_data["name"] != db_role.name:
        # If name is being changed, check for conflict
        existing_role_with_new_name = get_role_by_name(db, name=update_data["name"])
        if existing_role_with_new_name and existing_role_with_new_name.id != role_id:
            # This check is also better handled in API layer for HTTP response
            raise ValueError(f"Another role with name '{update_data['name']}' already exists.")
            
    for field, value in update_data.items():
        setattr(db_role, field, value)
    
    db.add(db_role) # or just db.commit() if attributes are directly modified on db_role
    db.commit()
    db.refresh(db_role)
    return db_role

def delete_role(db: Session, role_id: int) -> RoleModel | None:
    """
    Deletes a role from the database.
    """
    db_role = get_role(db, role_id=role_id)
    if not db_role:
        return None
    
    db.delete(db_role)
    db.commit()
    return db_role
