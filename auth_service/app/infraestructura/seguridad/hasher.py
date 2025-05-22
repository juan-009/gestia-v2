from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def hash_password(password: str, pepper: str) -> str:
    """
    Hashes a password using bcrypt, including a pepper.
    The pepper should be a system-wide secret.
    """
    return pwd_context.hash(password + pepper)

def verify_password(plain_password: str, hashed_password: str, pepper: str) -> bool:
    """
    Verifies a plain password against a hashed password, including a pepper.
    """
    try:
        return pwd_context.verify(plain_password + pepper, hashed_password)
    except Exception:
        # Handles potential errors during verification, e.g., malformed hash or other issues.
        return False
