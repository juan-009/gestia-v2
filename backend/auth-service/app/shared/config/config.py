import os
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseSettings, PostgresDsn, validator, RedisDsn, SecretStr




class Settings(BaseSettings):
    # Configuración Base
    ENVIRONMENT: str = "dev"
    APP_NAME: str = "auth-service"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    
    # Seguridad JWT
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    JWT_PUBLIC_KEY: SecretStr
    JWT_PRIVATE_KEY: SecretStr
    JWT_AUDIENCE: str = "crm-platform"
    JWT_ISSUER: str = "auth-service"

    # Base de Datos
    POSTGRES_DSN: PostgresDsn
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 5
    
    # Redis
    REDIS_DSN: RedisDsn
    REDIS_CACHE_TTL: int = 300  # 5 minutos
    REDIS_JTI_BLACKLIST: str = "jti_blacklist"
    
    # Kafka (Eventos)
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_AUTH_TOPIC: str = "auth-events"
    KAFKA_GROUP_ID: Optional[str] = None
    
    # MFA
    MFA_ENABLED: bool = True
    MFA_TOTP_WINDOW: int = 2
    MFA_RECOVERY_CODES: int = 10
    
    # Vault (Secret Management)
    VAULT_ENABLED: bool = False
    VAULT_ADDR: Optional[str]
    VAULT_ROLE_ID: Optional[SecretStr]
    VAULT_SECRET_ID: Optional[SecretStr]
    
    # CORS
    CORS_ALLOW_ORIGINS: list[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @validator("JWT_PUBLIC_KEY", "JWT_PRIVATE_KEY", pre=True)
    def load_keys(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            env = values.get("ENVIRONMENT", "dev")
            key_type = "public" if "PUBLIC" in cls.__fields__[values["field"].name].name else "private"
            
            key_path = Path(f"secrets/jwt/{env}.{key_type}.pem")
            if not key_path.exists():
                raise ValueError(f"JWT {key_type} key not found at {key_path}")
            
            return key_path.read_text()
        return v

    @validator("ENVIRONMENT")
    def validate_environment(cls, v: str) -> str:
        allowed = ["dev", "test", "prod"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "prod"
    
    @property
    def jwt_config(self) -> Dict[str, Any]:
        return {
            "algorithm": self.JWT_ALGORITHM,
            "private_key": self.JWT_PRIVATE_KEY.get_secret_value(),
            "public_key": self.JWT_PUBLIC_KEY.get_secret_value(),
            "access_expire": self.JWT_ACCESS_EXPIRE_MINUTES * 60,
            "refresh_expire": self.JWT_REFRESH_EXPIRE_DAYS * 86400,
            "audience": self.JWT_AUDIENCE,
            "issuer": self.JWT_ISSUER
        }


def get_settings() -> Settings:
    """Factory para inyección de dependencias"""
    return Settings()


# Configuración global accesible
settings = get_settings()
