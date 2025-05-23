from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import NoEncryption
import os
import json # Not strictly used in this file, but often related
import base64

def _base64url_encode_int(val: int) -> str:
    """
    Helper function to convert an integer to its base64url-encoded representation.
    Used for JWK 'n' (modulus) and 'e' (exponent) values.
    """
    if val < 0:
        raise ValueError("Value must be a non-negative integer")
    # Convert int to bytes (big-endian)
    # The number of bytes is determined by the bit length of the integer
    val_bytes = val.to_bytes((val.bit_length() + 7) // 8, 'big')
    # Base64url encode: standard base64 with '+' replaced by '-', '/' by '_', and no padding '='
    return base64.urlsafe_b64encode(val_bytes).rstrip(b'=').decode('utf-8')

def generate_rsa_key_pair(key_size: int = 2048) -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """
    Generates an RSA private and public key pair.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size
    )
    public_key = private_key.public_key()
    return private_key, public_key

def save_pem_key(key, filename: str, is_private: bool):
    """
    Saves an RSA key (private or public) to a PEM file.
    """
    if is_private:
        pem_bytes = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption() # For simplicity, no password on private key file
        )
    else:
        pem_bytes = key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    # Ensure the directory exists before trying to save the file
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, "wb") as f:
        f.write(pem_bytes)

def load_pem_private_key(filename: str) -> rsa.RSAPrivateKey:
    """
    Loads an RSA private key from a PEM file.
    """
    with open(filename, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None # Assuming no password if saved with NoEncryption()
        )
    return private_key

def load_pem_public_key(filename: str) -> rsa.RSAPublicKey:
    """
    Loads an RSA public key from a PEM file.
    """
    with open(filename, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())
    return public_key

def get_jwks(public_key: rsa.RSAPublicKey, key_id: str = "default-key-id") -> dict:
    """
    Generates a JWKS (JSON Web Key Set) from an RSA public key.
    """
    numbers = public_key.public_numbers()
    
    # 'n' (Modulus) and 'e' (Exponent) must be base64urlUInt-encoded
    n = _base64url_encode_int(numbers.n)
    e = _base64url_encode_int(numbers.e)
    
    jwk = {
        "kty": "RSA",         # Key Type
        "use": "sig",         # Public Key Use (signature)
        "alg": "RS256",       # Algorithm
        "kid": key_id,        # Key ID
        "n": n,               # Modulus
        "e": e                # Exponent
    }
    
    return {"keys": [jwk]}
