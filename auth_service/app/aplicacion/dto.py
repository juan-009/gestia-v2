from pydantic import BaseModel, EmailStr
from typing import List, Optional

class UserDTO(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    roles: List[str] = []
    hashed_password: Optional[str] = None # DTO might carry this for service layer

    # For Pydantic v2
    model_config = {'from_attributes': True}
    # For Pydantic v1, you would use:
    # class Config:
    #     orm_mode = True

class TokenPairDTO(BaseModel):
    access_token: str
    refresh_token: str