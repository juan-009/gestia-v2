from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Any, Dict # Added Dict

class DomainEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_data: Optional[Dict[str, Any]] = None # Generic event data

class RoleCreatedEvent(DomainEvent):
    role_name: str
    description: Optional[str] = None
    permissions: List[str] = []

class PermissionAssignedToRoleEvent(DomainEvent):
    role_name: str
    permission_name: str

class PermissionRevokedFromRoleEvent(DomainEvent):
    role_name: str
    permission_name: str

class UserAssignedRoleEvent(DomainEvent):
    user_id: int
    role_name: str

class UserRevokedRoleEvent(DomainEvent):
    user_id: int
    role_name: str

class PermissionCreatedEvent(DomainEvent):
    permission_name: str
    description: Optional[str] = None
