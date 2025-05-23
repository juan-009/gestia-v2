from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ...db.dependencies import get_db
from ...schemas.role import RoleCreate, RoleRead, RoleUpdate
from ...crud import crud_role

router = APIRouter(prefix="/roles", tags=["Roles"])

# TODO: Add authentication and authorization (e.g., admin only) for CUD operations.
# TODO: Consider what happens to users with a role when that role is deleted/modified.

@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_new_role(role: RoleCreate, db: Session = Depends(get_db)):
    """
    Create a new role.
    """
    # TODO: Add authentication and authorization (e.g., admin only)
    existing_role = crud_role.get_role_by_name(db, name=role.name)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists."
        )
    try:
        created_role = crud_role.create_role(db=db, role=role)
    except ValueError as e: # Catch specific ValueError from CRUD
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    return created_role

@router.get("/", response_model=List[RoleRead])
async def read_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all roles with pagination.
    """
    # TODO: Consider pagination best practices for larger datasets
    roles = crud_role.get_roles(db, skip=skip, limit=limit)
    return roles

@router.get("/{role_id}", response_model=RoleRead)
async def read_role(role_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific role by its ID.
    """
    db_role = crud_role.get_role(db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return db_role

@router.put("/{role_id}", response_model=RoleRead)
async def update_existing_role(role_id: int, role_in: RoleUpdate, db: Session = Depends(get_db)):
    """
    Update an existing role.
    """
    # TODO: Add authentication and authorization
    db_role = crud_role.get_role(db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Check for name conflict if name is being updated and is different from current
    if role_in.name is not None and role_in.name != db_role.name:
        existing_role_with_new_name = crud_role.get_role_by_name(db, name=role_in.name)
        if existing_role_with_new_name and existing_role_with_new_name.id != role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another role with name '{role_in.name}' already exists."
            )
    try:
        updated_role = crud_role.update_role(db=db, role_id=role_id, role_in=role_in)
    except ValueError as e: # Catch specific ValueError from CRUD (e.g., name conflict during update)
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    if updated_role is None: # Should not happen if previous check passed, but good for safety
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found after attempting update")
    return updated_role

@router.delete("/{role_id}", response_model=RoleRead)
async def delete_existing_role(role_id: int, db: Session = Depends(get_db)):
    """
    Delete an existing role.
    """
    # TODO: Add authentication and authorization. 
    # TODO: Consider what happens to users with this role. (e.g., disallow deletion if in use, or reassign users)
    deleted_role = crud_role.delete_role(db=db, role_id=role_id)
    if deleted_role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return deleted_role
