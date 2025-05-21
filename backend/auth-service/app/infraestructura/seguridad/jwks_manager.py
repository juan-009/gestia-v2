import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from jose import jwk
import pytz

from app.shared.config.config import settings
from app.shared.config.constants import SecurityConstants
from app.dominio.excepciones import ConfigurationError, SecurityException

logger = logging.getLogger(__name__)

class JWKSManager:
    """Gestión centralizada de claves JWT (JWKS) con rotación automática"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JWKSManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Inicialización singleton"""
        self.keys: List[Dict] = []
        self.key_rotation_interval = timedelta(days=90)
        self.key_grace_period = timedelta(days=7)
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self):
        """Carga claves existentes o genera nuevas"""
        key_dir = Path("secrets/jwt")
        key_dir.mkdir(parents=True, exist_ok=True)
        
        if settings.is_production and settings.VAULT_ENABLED:
            self._load_keys_from_vault()
        else:
            self._load_keys_from_filesystem(key_dir)
        
        if not self.keys:
            self._generate_new_key_pair(key_dir)
        
        self._clean_expired_keys()
    
    def _generate_new_key_pair(self, key_dir: Path):
        """Genera nuevo par de claves RSA"""
        logger.info("Generando nuevo par de claves RSA...")
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        
        kid = str(uuid4())
        timestamp = datetime.now(pytz.utc).isoformat()
        
        # Guardar clave privada
        priv_key_path = key_dir / f"{settings.ENVIRONMENT}.private.pem"
        with open(priv_key_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
            )
        os.chmod(priv_key_path, 0o600)
        
        # Construir JWK
        public_jwk = jwk.RSAKey(
            algorithm=SecurityConstants.JWT_ALGORITHM,
            key=private_key.public_key()
        ).to_dict()
        
        public_jwk.update({
            "kid": kid,
            "use": "sig",
            "exp": (datetime.now(pytz.utc) + self.key_rotation_interval).timestamp(),
            "iat": datetime.now(pytz.utc).timestamp()
        })
        
        self.keys.append(public_jwk)
        logger.info("Nuevo par de claves generado con KID: %s", kid)
    
    def _load_keys_from_filesystem(self, key_dir: Path):
        """Carga claves desde el sistema de archivos"""
        try:
            public_key_path = key_dir / f"{settings.ENVIRONMENT}.public.pem"
            if public_key_path.exists():
                with open(public_key_path, "r") as f:
                    public_key = serialization.load_pem_public_key(
                        f.read().encode(),
                        backend=default_backend()
                    )
                
                jwk_key = jwk.RSAKey(
                    algorithm=SecurityConstants.JWT_ALGORITHM,
                    key=public_key
                ).to_dict()
                
                self.keys.append(jwk_key)
        except Exception as e:
            logger.error("Error cargando claves desde filesystem: %s", str(e))
            raise SecurityException("KEY_LOAD_ERROR", "Error loading keys from filesystem") from e
    
    def _load_keys_from_vault(self):
        """Carga claves desde Vault (Implementación de ejemplo)"""
        # Implementación real dependería de la configuración de Vault
        try:
            logger.info("Intentando cargar claves desde Vault...")
            # TODO: Implementar integración real con Vault
            raise NotImplementedError("Vault integration not implemented yet")
        except Exception as e:
            logger.error("Error cargando claves desde Vault: %s", str(e))
            raise SecurityException("VAULT_ERROR", "Error loading keys from Vault") from e
    
    def _clean_expired_keys(self):
        """Elimina claves expiradas después del periodo de gracia"""
        now = datetime.now(pytz.utc).timestamp()
        self.keys = [
            k for k in self.keys
            if k.get("exp", 0) + self.key_grace_period.total_seconds() > now
        ]
    
    def get_jwks(self) -> Dict:
        """Retorna el conjunto actual de claves públicas en formato JWKS"""
        return {"keys": self.keys}
    
    def get_current_private_key(self) -> str:
        """Retorna la clave privada actual para firma"""
        if settings.is_production and settings.VAULT_ENABLED:
            return self._get_private_key_from_vault()
        
        key_path = Path(f"secrets/jwt/{settings.ENVIRONMENT}.private.pem")
        if not key_path.exists():
            raise ConfigurationError("JWT_PRIVATE_KEY")
        
        with open(key_path, "r") as f:
            return f.read()
    
    def _get_private_key_from_vault(self) -> str:
        """Obtiene la clave privada desde Vault"""
        # Implementación real dependería de la configuración de Vault
        try:
            # TODO: Implementar integración real con Vault
            logger.info("Intentando obtener clave privada desde Vault...")
            # Aquí se debería realizar la llamada a Vault para obtener la clave privada
            
            raise NotImplementedError("Vault integration not implemented yet")
        except Exception as e:
            logger.error("Error obteniendo clave privada desde Vault: %s", str(e))
            raise SecurityException("VAULT_ERROR", "Error retrieving private key") from e
    
    def rotate_keys(self):
        """Inicia rotación de claves programada"""
        logger.info("Iniciando rotación de claves...")
        self._generate_new_key_pair(Path("secrets/jwt"))
        self._clean_expired_keys()
        logger.info("Rotación de claves completada. Nuevo JWKS: %s", json.dumps(self.get_jwks(), indent=2))

def get_jwks_manager() -> JWKSManager:
    """Factory para inyección de dependencias"""
    return JWKSManager()