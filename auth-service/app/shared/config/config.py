from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

# Explicitly load .env file at the project root
# Adjust path if .env is located elsewhere or if this script moves
# __file__ is auth-service/app/shared/config/config.py
# os.path.dirname(__file__) is auth-service/app/shared/config
# os.path.dirname(os.path.dirname(__file__)) is auth-service/app/shared
# os.path.dirname(os.path.dirname(os.path.dirname(__file__))) is auth-service/app
# os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) is auth-service
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '.env')
# Use load_dotenv(dotenv_path=dotenv_path, override=True) if you want .env to take precedence over system env vars
# For default behavior (system env vars take precedence), just load_dotenv() can be enough if .env is in the root
# or if SettingsConfigDict properly finds it. However, explicit loading is safer.
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    # This case might occur if .env.example is used and .env is not created yet.
    # Or if the app is deployed in an environment where .env files are not used (e.g., Docker with env vars).
    print(f"Warning: .env file not found at {dotenv_path}. Using system environment variables or defaults.")


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_ALGORITHM: str = "RS256"
    JWT_PRIVATE_KEY_PATH: str
    JWT_PUBLIC_KEY_PATH: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_PEPPER: str

    REDIS_URL: str = "redis://localhost:6379/0"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    APP_NAME: str = "AuthService"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # For Pydantic V2, model_config is a class variable (dict)
    # env_file_encoding='utf-8' is default
    # extra='ignore' means it won't fail if there are extra vars in .env or environment
    # env_prefix='' means it looks for variables like 'DATABASE_URL', not 'APP_DATABASE_URL'
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

settings = Settings()

# For debugging purposes, you can print the loaded settings
# print("Loaded settings:")
# print(f"  DATABASE_URL: {settings.DATABASE_URL}")
# print(f"  JWT_PRIVATE_KEY_PATH: {settings.JWT_PRIVATE_KEY_PATH}")
# print(f"  DEBUG: {settings.DEBUG}")
