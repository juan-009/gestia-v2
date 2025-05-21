from pydantic import (
    BaseSettings, 
    PostgresDsn,
    RedisDsn,
    Field,
    validator,
    AnyUrl
)
from typing import Optional, List, Dict, Any
from pathlib import Path
import os

class Settings(BaseSettings):
    # Configuración base
    APP_ENV: str = Field(..., env="APP_ENV")
    DEBUG: bool = Field(default=False, env="DEBUG")
    SECRET_KEY: str = Field(..., min_length=64, env="SECRET_KEY")
    ENCRYPTION_KEY: str = Field(..., min_length=32, env="ENCRYPTION_KEY")
    
    # Configuración de base de datos
    DATABASE_URL: PostgresDsn = Field(..., env="DATABASE_URL")
    SYNC_DATABASE_URL: Optional[PostgresDsn] = Field(None, env="SYNC_DATABASE_URL")
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")

    # Configuración de autenticación
    SECURITY_PEPPER: str = Field(..., min_length=32, env="SECURITY_PEPPER")
    PASSWORD_HASHING_ROUNDS: int = Field(default=12, ge=10, le=15, env="PASSWORD_HASHING_ROUNDS")
    TOKEN_REVOCATION_GRACE_PERIOD: int = Field(..., env="TOKEN_REVOCATION_GRACE_PERIOD")  # En segundos

    # Configuración MFA 
    MFA_ISSUER_NAME: str = Field(..., env="MFA_ISSUER_NAME")
    MFA_VALID_WINDOW: int = Field(default=1, env="MFA_VALID_WINDOW")  # Ventana de validación de códigos TOTP
    MFA_BACKUP_CODE_COUNT: int = Field(default=6, env="MFA_BACKUP_CODE_COUNT")


    # Configuración de permisos y roles
    PERMISSION_CACHE_TTL: int = Field(..., env="PERMISSION_CACHE_TTL")  # En segundos
    CIRCUIT_BREAKER_MAX_FAILURES: int = 5
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = 60
    
    # Configuración Redis
    REDIS_URL: RedisDsn = Field(..., env="REDIS_URL")
    REDIS_DB_TOKENS: int = Field(default=0, env="REDIS_DB_TOKENS")
    REDIS_DB_CACHE: int = Field(default=1, env="REDIS_DB_CACHE")
    REDIS_POOL_SIZE: int = Field(default=20, env="REDIS_POOL_SIZE")
    REDIS_POOL_TIMEOUT: int = Field(default=5, env="REDIS_POOL_TIMEOUT")
    REDIS_SOCKET_TIMEOUT: int = Field(default=3, env="REDIS_SOCKET_TIMEOUT")
    
    # Seguridad JWT
    JWT_PRIVATE_KEY_PATH: Path = Field(..., env="JWT_PRIVATE_KEY_PATH")
    JWT_PUBLIC_KEY_PATH: Path = Field(..., env="JWT_PUBLIC_KEY_PATH")
    JWT_ALGORITHM: str = Field(default="RS256", env="JWT_ALGORITHM")
    JWT_ACCESS_EXPIRE_MINUTES: int = Field(..., env="JWT_ACCESS_EXPIRE_MINUTES")
    JWT_REFRESH_EXPIRE_DAYS: int = Field(..., env="JWT_REFRESH_EXPIRE_DAYS")
    JWT_TOKEN_VERSION: str = Field(..., env="JWT_TOKEN_VERSION")
    
    # Políticas de seguridad
    MAX_LOGIN_ATTEMPTS: int = Field(..., env="MAX_LOGIN_ATTEMPTS")
    ACCOUNT_LOCK_MINUTES: int = Field(..., env="ACCOUNT_LOCK_MINUTES")
    MIN_PASSWORD_LENGTH: int = Field(..., env="MIN_PASSWORD_LENGTH")
    MFA_ENABLED: bool = Field(..., env="MFA_ENABLED")
    
    # Observabilidad
    PROMETHEUS_ENDPOINT: str = Field(default="/metrics", env="PROMETHEUS_ENDPOINT")
    OTEL_ENABLED: bool = Field(default=False, env="OTEL_ENABLED")
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[AnyUrl] = Field(None, env="OTEL_EXPORTER_OTLP_ENDPOINT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    METRICS_HISTOGRAM_BUCKETS: List[float] = Field(
    default=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
    env="METRICS_HISTOGRAM_BUCKETS"
)
    # CORS
    CORS_ALLOWED_ORIGINS: List[str] = Field(..., env="CORS_ALLOWED_ORIGINS")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    CORS_ALLOW_METHODS: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], env="CORS_ALLOW_METHODS")       
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")  



    # Configuración de auditoría
    AUDIT_ENABLED: bool = Field(default=False, env="AUDIT_ENABLED")
    AUDIT_HMAC_SECRET: str
    AUDIT_KAFKA_TOPIC: str = "audit-logs"
    AUDIT_RETENTION_DAYS: int = 365
    AUDIT_LOG_LEVEL: str = "INFO"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(..., env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_MINUTES: int = Field(..., env="RATE_LIMIT_MINUTES")
    
    # Validadores
    @validator("CORS_ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, value: str) -> List[str]:
        return [origin.strip() for origin in value.split(",")]
    
    @validator("JWT_ALGORITHM")
    def validate_jwt_algorithm(cls, value: str) -> str:
        if value not in ["RS256", "RS384", "RS512"]:
            raise ValueError("Algoritmo JWT debe ser RS256, RS384 o RS512")
        return value
    
    @validator("SYNC_DATABASE_URL", pre=True)
    def set_sync_database_url(cls, value: Optional[str], values: Dict[str, Any]) -> str:
        if value is None:
            return str(values["DATABASE_URL"]).replace("+asyncpg", "")
        return value
    
    @validator("ENCRYPTION_KEY")
    def validate_encryption_key_length(cls, value: str) -> str:
        if len(value.encode('utf-8')) != 32:
         raise ValueError("La clave de encriptación debe ser de 32 bytes")
        return value

    @validator("JWT_PRIVATE_KEY_PATH", "JWT_PUBLIC_KEY_PATH")
    def validate_key_paths(cls, value: Path, field) -> Path:
        if not value.exists():
            raise ValueError(f"{field.name} no existe en la ruta especificada")
        if not os.access(value, os.R_OK):
            raise ValueError(f"Permiso denegado para leer {field.name}")
        return value
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


        

# Instancia singleton para toda la aplicación
settings = Settings()

# Ejemplo de uso:
# from app.infraestructura.config.settings import settings
# print(settings.DATABASE_URL)