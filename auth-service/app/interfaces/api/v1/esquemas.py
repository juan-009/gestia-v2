from pydantic import BaseModel, EmailStr
from typing import List

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

class NewAccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
