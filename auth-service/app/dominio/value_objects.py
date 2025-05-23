from pydantic import BaseModel, EmailStr
from typing import List, Optional

# Type alias for Pydantic's EmailStr for semantic clarity in domain
Email = EmailStr

# Type alias for representing password hashes for semantic clarity
PasswordHash = str

class JWTClaims(BaseModel):
    sub: str  # Subject (user identifier, e.g., username or user_id)
    exp: int  # Expiration time (Unix timestamp)
    iat: int  # Issued at (Unix timestamp)
    nbf: Optional[int] = None # Not before (Unix timestamp)
    jti: Optional[str] = None # JWT ID (for revocation)
    roles: List[str] = [] # Custom claim for user roles
    permissions: List[str] = [] # Custom claim for user permissions
