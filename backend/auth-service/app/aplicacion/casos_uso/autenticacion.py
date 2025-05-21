import time
import pyotp
from datetime import datetime, timedelta
from typing import Optional, Tuple
from aioredis import Redis
from pydantic import EmailStr
from app.dominio.excepciones import AuthError, InvalidCredentials, MFARequired
from app.dominio.modelos import Usuario
from app.dominio.value_objects import JWTClaims
from app.infraestructura.seguridad import jwt_manager, hasher, JWTError
from app.infraestructura.persistencia.repositorios import UserRepository
from app.infraestructura.mensajeria.adapters import AuditProducer

class LoginUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        token_manager: jwt_manager.JWTManager,
        hasher: hasher.PasswordHasher,
        audit_producer: AuditProducer
    ):
        self.user_repo = user_repo
        self.token_manager = token_manager
        self.hasher = hasher
        self.audit_producer = audit_producer

    async def execute(self, email: EmailStr, password: str, mfa_code: Optional[str] = None) -> Tuple[str, str]:
        user = await self._validate_credentials(email, password)
        self._check_account_status(user)
        
        if user.mfa_enabled:
            if not mfa_code:
                await self._audit_login_attempt(user, "MFA_REQUIRED")
                raise MFARequired("MFA authentication required")
            self._validate_mfa(user, mfa_code)

        access_token, refresh_token = self._generate_tokens(user)
        await self._audit_login_attempt(user, "SUCCESS")
        
        return access_token, refresh_token

    async def _validate_credentials(self, email: str, password: str) -> Usuario:
        user = await self.user_repo.get_by_email(email)
        if not user or not self.hasher.verify(password, user.hashed_password):
            await self._audit_login_attempt(user or email, "INVALID_CREDENTIALS")
            raise InvalidCredentials("Credenciales inválidas")
        return user

    def _check_account_status(self, user: Usuario):
        if not user.is_active:
            raise AuthError("Cuenta desactivada", code="account_inactive")
        if user.password_expired:
            raise AuthError("Contraseña expirada", code="password_expired")

    def _validate_mfa(self, user: Usuario, code: str):
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(code, valid_window=1):
            raise InvalidCredentials("Código MFA inválido")

    def _generate_tokens(self, user: Usuario) -> Tuple[str, str]:
        access_claims = JWTClaims(
            sub=user.id,
            roles=user.roles,
            mfa_verified=user.mfa_enabled
        )
        
        refresh_claims = JWTClaims(
            sub=user.id,
            token_type="refresh"
        )
        
        access_token = self.token_manager.issue_token(access_claims)
        refresh_token = self.token_manager.issue_token(
            refresh_claims, 
            expires_delta=timedelta(days=7)
        )
        
        return access_token, refresh_token

    async def _audit_login_attempt(self, user: Usuario, status: str):
        await self.audit_producer.send(
            event_type="AUTH_ATTEMPT",
            payload={
                "user_id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "mfa_used": bool(user.mfa_enabled)
            }
        )

class RefreshUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        token_manager: jwt_manager.JWTManager,
        redis: Redis
    ):
        self.user_repo = user_repo
        self.token_manager = token_manager
        self.redis = redis

    async def execute(self, refresh_token: str) -> str:
        claims = await self._validate_refresh_token(refresh_token)
        user = await self._validate_user(claims.sub)
        
        new_claims = JWTClaims(
            sub=user.id,
            roles=user.roles,
            mfa_verified=user.mfa_enabled
        )
        
        return self.token_manager.issue_token(new_claims)

    async def _validate_refresh_token(self, token: str) -> JWTClaims:
        try:
            claims = self.token_manager.validate_token(token)
            if claims.token_type != "refresh":
                raise AuthError("Tipo de token inválido")
                
            if await self.redis.exists(f"revoked:{token}"):
                raise AuthError("Token revocado")
                
            return claims
        except JWTError as e:
            raise AuthError("Token de refresh inválido") from e

    async def _validate_user(self, user_id: str) -> Usuario:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthError("Usuario no válido")
        return user

class LogoutUseCase:
    def __init__(self, redis: Redis, token_manager: jwt_manager.JWTManager):
        self.redis = redis
        self.token_manager = token_manager

    async def execute(self, access_token: str, refresh_token: str):
        access_claims = self.token_manager.validate_token(access_token)
        refresh_claims = self.token_manager.validate_token(refresh_token)
        
        await self._revoke_token(access_token, access_claims.exp)
        await self._revoke_token(refresh_token, refresh_claims.exp)

    async def _revoke_token(self, token: str, exp: int):
        ttl = exp - int(time.time())
        if ttl > 0:
            await self.redis.setex(
                f"revoked:{token}",
                ttl,
                "revoked"
            )

class InitiateMFAUseCase:
    def __init__(self, user_repo: UserRepository, audit_producer: AuditProducer):
        self.user_repo = user_repo
        self.audit_producer = audit_producer

    async def execute(self, user_id: str) -> Tuple[str, str]:
        user = await self.user_repo.get_by_id(user_id)
        if not user.mfa_secret:
            user.mfa_secret = pyotp.random_base32()
            await self.user_repo.update(user)
            
        totp = pyotp.TOTP(user.mfa_secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Auth Service"
        )
        
        await self.audit_producer.send(
            event_type="MFA_INITIATED",
            payload={"user_id": user.id}
        )
        
        return user.mfa_secret, provisioning_uri

class VerifyMFAUseCase:
    def __init__(self, user_repo: UserRepository, audit_producer: AuditProducer):
        self.user_repo = user_repo
        self.audit_producer = audit_producer

    async def execute(self, user_id: str, code: str) -> bool:
        user = await self.user_repo.get_by_id(user_id)
        if not user.mfa_secret:
            raise AuthError("MFA no configurado")
            
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(code, valid_window=1):
            user.mfa_enabled = True
            await self.user_repo.update(user)
            await self.audit_producer.send(
                event_type="MFA_ENABLED",
                payload={"user_id": user.id}
            )
            return True
            
        await self.audit_producer.send(
            event_type="MFA_FAILED",
            payload={"user_id": user.id}
        )
        return False