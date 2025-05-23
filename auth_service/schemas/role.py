from pydantic import BaseModel

class RoleBase(BaseModel):
    name: str
    description: str | None = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel): # Using BaseModel directly for all optional fields
    name: str | None = None
    description: str | None = None

class RoleRead(RoleBase):
    id: int

    model_config = {'from_attributes': True} # Pydantic v2
    # For Pydantic v1, you would use:
    # class Config:
    #     orm_mode = True
