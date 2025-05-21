import base64
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from uuid import UUID, uuid4

import pyotp
import webauthn
from webauthn.helpers import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
    base64url_to_bytes,
    bytes_to_base64url
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    RegistrationCredential,
    AuthenticationCredential,
    PublicKeyCredentialDescriptor
)

from app.shared.config.config import settings
from app.shared.config.constants import MFAConstants
from app.dominio.excepciones import (
    InvalidMFACodeError,
    MFANotConfiguredError,
    MFAValidationError
)
from app.infraestructura.cache.redis import get_redis_client

logger = logging.getLogger(__name__)

class MFAHandler:
    """Gestión completa de autenticación multifactor (TOTP + WebAuthn)"""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.rp_id = os.getenv('RP_ID', 'example.com')
        self.rp_name = os.getenv('RP_NAME', 'CRM Platform')
        self.origin = os.getenv('MFA_ORIGIN', 'https://crm.example.com')
    
    # ==================== TOTP ====================
    def generate_totp_secret(self) -> Dict[str, str]:
        """Genera un nuevo secreto TOTP con códigos de recuperación"""
        secret = pyotp.random_base32()
        recovery_codes = self._generate_recovery_codes()
        
        return {
            "secret": secret,
            "provisioning_uri": self._get_totp_uri(secret),
            "recovery_codes": recovery_codes
        }
    
    def verify_totp(self, secret: str, code: str, user_id: UUID) -> bool:
        """Verifica un código TOTP con protección contra fuerza bruta"""
        self._check_mfa_attempts(user_id)
        
        totp = pyotp.TOTP(secret)
        if totp.verify(code, valid_window=MFAConstants.TOTP_VALID_WINDOW):
            self._reset_mfa_attempts(user_id)
            return True
        
        self._increment_mfa_attempts(user_id)
        raise InvalidMFACodeError(self._remaining_attempts(user_id))
    
    def _get_totp_uri(self, secret: str) -> str:
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=settings.JWT_ISSUER,
            issuer_name=self.rp_name
        )
    
    def _generate_recovery_codes(self) -> List[str]:
        return [self._generate_recovery_code() for _ in range(MFAConstants.MFA_RECOVERY_CODES)]
    
    def _generate_recovery_code(self) -> str:
        return f"{os.urandom(8).hex()[:5]}-{os.urandom(8).hex()[:5]}".upper()
    
    # ==================== WebAuthn ====================
    def webauthn_registration_options(self, user_id: UUID, username: str) -> Dict:
        """Genera opciones de registro para WebAuthn"""
        user_handle = base64.urlsafe_b64encode(user_id.bytes).decode().rstrip('=')
        
        options = generate_registration_options(
            rp_id=self.rp_id,
            rp_name=self.rp_name,
            user_id=user_handle,
            user_name=username,
            user_display_name=username,
            authenticator_selection=AuthenticatorSelectionCriteria(
                user_verification=UserVerificationRequirement.PREFERRED
            ),
            challenge=self._generate_challenge()
        )
        
        self._store_challenge(user_id, options.challenge, "registration")
        return json.loads(options_to_json(options))
    
    def verify_webauthn_registration(self, user_id: UUID, credential: Dict) -> Dict:
        """Verifica la respuesta de registro WebAuthn"""
        stored_challenge = self._get_challenge(user_id, "registration")
        if not stored_challenge:
            raise MFAValidationError("Challenge no encontrado")
        
        try:
            credential = RegistrationCredential.parse_raw(json.dumps(credential))
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(stored_challenge),
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                require_user_verification=True
            )
            
            return {
                "credential_id": bytes_to_base64url(verification.credential_id),
                "public_key": bytes_to_base64url(verification.credential_public_key),
                "sign_count": verification.sign_count
            }
        except Exception as e:
            logger.error("Error validando registro WebAuthn: %s", str(e))
            raise MFAValidationError("Validación de registro fallida") from e
    
    def webauthn_authentication_options(self, user_id: UUID) -> Dict:
        """Genera opciones de autenticación WebAuthn"""
        options = generate_authentication_options(
            rp_id=self.rp_id,
            challenge=self._generate_challenge(),
            allow_credentials=self._get_user_credentials(user_id)
        )
        
        self._store_challenge(user_id, options.challenge, "authentication")
        return json.loads(options_to_json(options))
    
    def verify_webauthn_authentication(self, user_id: UUID, credential: Dict) -> bool:
        """Verifica la respuesta de autenticación WebAuthn"""
        stored_challenge = self._get_challenge(user_id, "authentication")
        if not stored_challenge:
            raise MFAValidationError("Challenge no encontrado")
        
        try:
            credential = AuthenticationCredential.parse_raw(json.dumps(credential))
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(stored_challenge),
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                credential_public_key=base64url_to_bytes(credential.public_key),
                credential_current_sign_count=0
            )
            
            self._update_sign_count(user_id, credential.id, verification.new_sign_count)
            return True
        except Exception as e:
            logger.error("Error validando autenticación WebAuthn: %s", str(e))
            raise MFAValidationError("Validación de autenticación fallida") from e
    
    # ==================== Gestión de Credenciales ====================
    def _get_user_credentials(self, user_id: UUID) -> List[PublicKeyCredentialDescriptor]:
        """Obtiene las credenciales WebAuthn del usuario desde almacenamiento seguro"""
        # Implementación real dependería de tu sistema de almacenamiento
        return []
    
    def _update_sign_count(self, user_id: UUID, credential_id: str, sign_count: int):
        """Actualiza el contador de firmas para una credencial"""
        # Implementar según sistema de almacenamiento
        pass
    
    # ==================== Helpers Generales ====================
    def _generate_challenge(self) -> bytes:
        return os.urandom(32)
    
    def _store_challenge(self, user_id: UUID, challenge: bytes, type: str):
        key = f"mfa:challenge:{type}:{user_id}"
        self.redis.setex(key, 300, base64.urlsafe_b64encode(challenge).decode())
    
    def _get_challenge(self, user_id: UUID, type: str) -> Optional[bytes]:
        key = f"mfa:challenge:{type}:{user_id}"
        challenge = self.redis.get(key)
        if challenge:
            return base64.urlsafe_b64decode(challenge)
        return None
    
    # ==================== Gestión de Intentos ====================
    def _check_mfa_attempts(self, user_id: UUID):
        attempts = self._get_mfa_attempts(user_id)
        if attempts >= MFAConstants.LOGIN_ATTEMPTS_LIMIT:
            raise InvalidMFACodeError(0)
    
    def _increment_mfa_attempts(self, user_id: UUID):
        key = f"mfa:attempts:{user_id}"
        self.redis.incr(key)
        self.redis.expire(key, MFAConstants.LOGIN_LOCKOUT_MINUTES * 60)
    
    def _reset_mfa_attempts(self, user_id: UUID):
        key = f"mfa:attempts:{user_id}"
        self.redis.delete(key)
    
    def _remaining_attempts(self, user_id: UUID) -> int:
        return MFAConstants.LOGIN_ATTEMPTS_LIMIT - self._get_mfa_attempts(user_id)
    
    def _get_mfa_attempts(self, user_id: UUID) -> int:
        key = f"mfa:attempts:{user_id}"
        return int(self.redis.get(key) or 0)

# Singleton para inyección de dependencias
mfa_handler = MFAHandler()