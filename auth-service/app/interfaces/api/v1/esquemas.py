from __future__ import annotations # For forward references like List[RoleResponse]
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    roles: List[str] = []
    
    # For Pydantic v2
    model_config = {'from_attributes': True}
    # For Pydantic v1, you would use:
    # class Config:
    #     orm_mode = True

# --- Permission Schemas ---
class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None

class PermissionCreateRequest(PermissionBase):
    pass

class PermissionResponse(PermissionBase):
    id: int
    
    model_config = {'from_attributes': True}

# --- Role Schemas ---
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreateRequest(RoleBase):
    permissions: List[str] = [] # List of permission names

class RoleUpdateRequest(BaseModel): 
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None # Full list of permission names

class RoleResponse(RoleBase):
    id: int
    permissions: List[PermissionResponse] = [] # List of detailed permission objects
    
    model_config = {'from_attributes': True}

# --- Assignment Schemas ---
class UserRoleAssignRequest(BaseModel):
    role_name: str

class RolePermissionAssignRequest(BaseModel): 
    permission_name: str

# --- Update UserResponse (ensure it replaces the old one if it exists) ---
# Original UserResponse from P2S1 (for reference):
# class UserResponse(BaseModel):
#     id: int
#     email: EmailStr
#     is_active: bool
#     roles: List[str] = [] 
#     model_config = {'from_attributes': True}

# Updated UserResponse:
class UserResponse(BaseModel): 
    id: int
    email: EmailStr
    is_active: bool
    roles: List[RoleResponse] = [] # Now returns a list of detailed RoleResponse objects
            
    model_config = {'from_attributes': True}

# --- Token Schemas (Ensure NewAccessTokenResponse is still here if needed by other parts) ---
class NewAccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
