from passlib.context import CryptContext
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt

# --- JWT Configuration ---
ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# --- Password Hashing ---

# TODO: IMPORTANT - In a production environment, this PASSWORD_PEPPER 
# MUST be loaded from a secure environment variable or a secrets management system.
# DO NOT hardcode this value in the final production version.
# For development purposes, a hardcoded string is used here.
PASSWORD_PEPPER = "a_very_secret_and_long_pepper_string_for_development_only"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# --- JWT Key Management ---

# Determine the base directory of the auth_service package
# This assumes security.py is in auth_service/core/
# So, two levels up is the project root where auth_service/ directory sits.
# Or, if this script is run directly, __file__ might be relative to current dir.
# For robustness, especially for the __main__ block, we'll define paths
# assuming the script or app is run from the project root.

KEYS_DIR = "auth_service/keys"
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "private_key.pem")
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "public_key.pem")

# Ensure the keys directory exists
os.makedirs(KEYS_DIR, exist_ok=True)

def generate_rsa_keys():
    """
    Generates RSA private and public keys and saves them to PEM files.
    This function is intended for development setup. In production, keys
    should be managed securely, potentially using a secrets management system,
    and not generated on the fly or stored in the codebase directly.
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Serialize private key to PEM format
    pem_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    with open(PRIVATE_KEY_PATH, 'wb') as f:
        f.write(pem_private_key)
    print(f"Private key saved to {PRIVATE_KEY_PATH}")

    # Derive public key
    public_key = private_key.public_key()

    # Serialize public key to PEM format
    pem_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open(PUBLIC_KEY_PATH, 'wb') as f:
        f.write(pem_public_key)
    print(f"Public key saved to {PUBLIC_KEY_PATH}")

def load_private_key() -> rsa.RSAPrivateKey:
    """Loads the RSA private key from the PEM file."""
    if not os.path.exists(PRIVATE_KEY_PATH):
        raise FileNotFoundError(f"Private key file not found at {PRIVATE_KEY_PATH}. "
                                "Run 'python -m auth_service.core.security' to generate keys.")
    with open(PRIVATE_KEY_PATH, 'rb') as f:
        private_key_data = f.read()
    private_key = serialization.load_pem_private_key(
        private_key_data,
        password=None
    )
    return private_key

def load_public_key() -> rsa.RSAPublicKey:
    """Loads the RSA public key from the PEM file."""
    if not os.path.exists(PUBLIC_KEY_PATH):
        raise FileNotFoundError(f"Public key file not found at {PUBLIC_KEY_PATH}. "
                                "Run 'python -m auth_service.core.security' to generate keys.")
    with open(PUBLIC_KEY_PATH, 'rb') as f:
        public_key_data = f.read()
    public_key = serialization.load_pem_public_key(
        public_key_data
    )
    return public_key

# --- Token Creation ---

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates an access token.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        # "sub" should be provided in the data dictionary (e.g., user_id or username)
    })
    
    private_key = load_private_key()
    encoded_jwt = jwt.encode(to_encode, private_key, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates a refresh token.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        # "sub" should be provided in the data dictionary
    })
    
    private_key = load_private_key()
    encoded_jwt = jwt.encode(to_encode, private_key, algorithm=ALGORITHM)
    return encoded_jwt

# --- Token Decoding ---

def decode_token(token: str) -> "TokenData | None":
    """
    Decodes a JWT token and returns the token data.
    Returns None if the token is invalid or expired.
    """
    # This import is here to avoid circular dependency issues
    # as schemas.token might import something from core.security indirectly later
    from ..schemas.token import TokenData 

    try:
        public_key = load_public_key()
        payload = jwt.decode(token, public_key, algorithms=[ALGORITHM])
        sub: str | None = payload.get("sub")
        
        if sub is None:
            return None
        return TokenData(sub=sub)
    except JWTError:
        return None

def hash_password(password: str) -> str:
    """
    Hashes a password using bcrypt, including a pepper.
    """
    password_with_pepper = password + PASSWORD_PEPPER
    return pwd_context.hash(password_with_pepper)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password, including a pepper.
    """
    password_with_pepper = plain_password + PASSWORD_PEPPER
    try:
        return pwd_context.verify(password_with_pepper, hashed_password)
    except Exception:
        # Handle potential errors during verification, e.g., malformed hash
        return False

if __name__ == "__main__":
    print(f"Looking for keys in: {os.path.abspath(KEYS_DIR)}")
    if not os.path.exists(PRIVATE_KEY_PATH) or not os.path.exists(PUBLIC_KEY_PATH):
        print("RSA key pair not found. Generating new keys...")
        generate_rsa_keys()
    else:
        print("RSA key pair already exists. Skipping generation.")
        # Optionally, you could add a way to force regeneration, e.g., via command-line argument
        # For now, we just confirm they exist.
        try:
            load_private_key()
            load_public_key()
            print("Successfully loaded existing private and public keys.")
        except Exception as e:
            print(f"Error loading existing keys: {e}. You might need to delete them and regenerate.")
