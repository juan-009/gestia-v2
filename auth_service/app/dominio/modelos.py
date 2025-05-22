from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class Usuario(BaseModel):
    id: Optional[int] = None
    email: str # Will be validated by Email value object in practice
    hashed_password: str # Represents a stored hash
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    roles: List[str] = [] # List of role names, simple representation in domain model

class Rol(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    permissions: List[str] = [] # List of permission names

class Permiso(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
