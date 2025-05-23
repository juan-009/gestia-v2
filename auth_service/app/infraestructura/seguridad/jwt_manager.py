from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from typing import Dict, Optional

# Assuming the project structure allows these imports
# If 'auth_service' is the root package name discoverable in PYTHONPATH:
from app.shared.config.config import settings
from app.infraestructura.seguridad.jwks_manager import load_pem_private_key, load_pem_public_key
from app.dominio.value_objects import JWTClaims
from app.dominio.excepciones import InvalidTokenError


def create_access_token(
    subject: str, 
    additional_claims: Optional[Dict] = None,
    expiry_delta_minutes: Optional[int] = None
) -> str:
    if expiry_delta_minutes is None:
        expiry_delta_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    expire = datetime.utcnow() + timedelta(minutes=expiry_delta_minutes)
    to_encode = {
        "exp": expire,
        "sub": subject,
        "iat": datetime.utcnow()
    }
    if additional_claims:
        to_encode.update(additional_claims)
    
    private_key = load_pem_private_key(settings.JWT_PRIVATE_KEY_PATH)
    encoded_jwt = jwt.encode(to_encode, private_key, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(
    subject: str, 
    expiry_delta_days: Optional[int] = None
) -> str:
    if expiry_delta_days is None:
        expiry_delta_days = settings.REFRESH_TOKEN_EXPIRE_DAYS
    
    expire = datetime.utcnow() + timedelta(days=expiry_delta_days)
    to_encode = {
        "exp": expire,
        "sub": subject,
        "iat": datetime.utcnow()
        # Refresh tokens might also include a jti if we plan to enable
        # refresh token revocation via a denylist.
    }
    
    private_key = load_pem_private_key(settings.JWT_PRIVATE_KEY_PATH)
    encoded_jwt = jwt.encode(to_encode, private_key, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def validate_token(token: str) -> JWTClaims:
    try:
        public_key = load_pem_public_key(settings.JWT_PUBLIC_KEY_PATH)
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[settings.JWT_ALGORITHM]
            # Options can be added here, e.g., audience, issuer
        )

        # Validate essential claims exist before creating JWTClaims model
        # The JWTClaims model itself will validate types
        if not payload.get("sub") or not payload.get("exp") or not payload.get("iat"):
             raise InvalidTokenError("Essential claims missing in token.")

        # Pydantic model JWTClaims will perform validation on its fields
        return JWTClaims(**payload)

    except ExpiredSignatureError:
        raise InvalidTokenError("Token has expired.")
    except JWTError as e: # Generic JWT error (includes invalid claims)
        raise InvalidTokenError(f"Invalid token: {str(e)}")
    except FileNotFoundError as e: # Handle case where key files are not found
        # This is a server-side configuration issue, but it's good to catch it.
        # Log this error appropriately in a real application.
        print(f"Error: Key file not found - {e}. Ensure keys are generated and paths are correct.")
        raise InvalidTokenError("Token validation configuration error.")
    except Exception as e:
        # Catch any other unexpected errors during token validation
        print(f"Unexpected error during token validation: {e}") # Log this
        raise InvalidTokenError("An unexpected error occurred during token validation.")
