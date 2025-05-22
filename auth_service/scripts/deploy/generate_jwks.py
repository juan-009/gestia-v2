import os
import sys

# Adjust the Python path to allow importing from the 'app' directory
# This assumes the script is in 'auth-service/scripts/deploy/'
# and the 'app' directory is at 'auth-service/app/'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from app.infraestructura.seguridad.jwks_manager import generate_rsa_key_pair, save_pem_key
    from app.shared.config.config import settings
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure that the script is run from the 'auth-service' directory,")
    print("or that the 'auth-service' directory is in your PYTHONPATH.")
    print("Current sys.path:", sys.path)
    print("Current working directory:", os.getcwd())
    exit(1)


if __name__ == "__main__":
    print("Starting key generation process...")
    
    # Ensure the target directories for keys exist, using paths from settings
    # This is important as save_pem_key expects the directory to exist
    # It's also handled within save_pem_key, but good to be explicit here too.
    private_key_dir = os.path.dirname(settings.JWT_PRIVATE_KEY_PATH)
    public_key_dir = os.path.dirname(settings.JWT_PUBLIC_KEY_PATH)

    if private_key_dir: # Check if the path string is not empty
        os.makedirs(private_key_dir, exist_ok=True)
        print(f"Ensured directory exists: {private_key_dir}")
    if public_key_dir: # Check if the path string is not empty
        os.makedirs(public_key_dir, exist_ok=True)
        print(f"Ensured directory exists: {public_key_dir}")

    private_key, public_key = generate_rsa_key_pair()
    print("RSA key pair generated.")

    print(f"Attempting to save private key to: {os.path.abspath(settings.JWT_PRIVATE_KEY_PATH)}")
    save_pem_key(private_key, settings.JWT_PRIVATE_KEY_PATH, is_private=True)
    
    print(f"Attempting to save public key to: {os.path.abspath(settings.JWT_PUBLIC_KEY_PATH)}")
    save_pem_key(public_key, settings.JWT_PUBLIC_KEY_PATH, is_private=False)
    
    print(f"Keys generated and saved successfully to {os.path.abspath(settings.JWT_PRIVATE_KEY_PATH)} and {os.path.abspath(settings.JWT_PUBLIC_KEY_PATH)}")
    print("Script finished.")
