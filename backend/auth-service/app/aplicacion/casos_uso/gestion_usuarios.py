from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import EmailStr, BaseModel
from aioredis import Redis
from app.shared.config.config import settings
from app.dominio.excepciones import AuthError, PermissionDenied, ValidationError
from app.dominio.modelos import Usuario, Rol
from app.dominio.value_objects import PasswordResetToken
from app.infraestructura.seguridad import hasher
from app.infraestructura.persistencia.repositorios import UserRepository, RoleRepository
from app.infraestructura.mensajeria.adapters import AuditProducer

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    roles: List[str] = []
    is_active: bool = True
    metadata: Dict[str, Any] = {}

class CreateUserUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        hasher: hasher.PasswordHasher,
        audit: AuditProducer
    ):
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.hasher = hasher
        self.audit = audit

    async def execute(self, request: CreateUserRequest, current_user: Usuario) -> Usuario:
        self._check_permissions(current_user)
        await self._validate_roles(request.roles)
        
        hashed_password = self.hasher.hash(request.password)
        user = Usuario(
            email=request.email,
            hashed_password=hashed_password,
            roles=request.roles,
            is_active=request.is_active,
            metadata=request.metadata,
            password_changed_at=datetime.utcnow()
        )
        
        created_user = await self.user_repo.create(user)
        await self.audit.send(
            event_type="USER_CREATED",
            payload={
                "by_user": current_user.id,
                "user_id": created_user.id,
                "roles": created_user.roles
            }
        )
        return created_user

    def _check_permissions(self, user: Usuario):
        if not user.has_role("admin") and not user.has_permission("users:create"):
            raise PermissionDenied("No tienes permisos para crear usuarios")

    async def _validate_roles(self, roles: List[str]):
        valid_roles = await self.role_repo.list_all()
        for role in roles:
            if role not in [r.name for r in valid_roles]:
                raise ValidationError(f"Rol inválido: {role}")

class UpdateUserUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        audit: AuditProducer,
        hasher: hasher.PasswordHasher
    ):
        self.user_repo = user_repo
        self.audit = audit
        self.hasher = hasher

    async def execute(
        self,
        user_id: str,
        update_data: Dict[str, Any],
        current_user: Usuario,
        password_confirm: Optional[str] = None
    ) -> Usuario:
        target_user = await self._get_user(user_id)
        self._validate_ownership(current_user, target_user)
        
        updated_user = await self._apply_updates(target_user, update_data, password_confirm)
        await self.audit.send(
            event_type="USER_UPDATED",
            payload={
                "by_user": current_user.id,
                "user_id": user_id,
                "changes": self._get_changes(target_user, updated_user)
            }
        )
        return await self.user_repo.update(updated_user)

    async def _get_user(self, user_id: str) -> Usuario:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("Usuario no encontrado")
        return user

    def _validate_ownership(self, current_user: Usuario, target_user: Usuario):
        if current_user.id != target_user.id and not current_user.has_role("admin"):
            raise PermissionDenied("No puedes modificar este usuario")

    async def _apply_updates(self, user: Usuario, data: Dict, password_confirm: str) -> Usuario:
        if "password" in data:
            if not password_confirm or not self.hasher.verify(password_confirm, user.hashed_password):
                raise AuthError("Confirmación de contraseña inválida")
            user.hashed_password = self.hasher.hash(data.pop("password"))
            user.password_changed_at = datetime.utcnow()
        
        if "roles" in data and not user.has_role("admin"):
            raise PermissionDenied("Solo administradores pueden modificar roles")
        
        return user.copy(update=data)

    def _get_changes(self, original: Usuario, updated: Usuario) -> Dict:
        changes = {}
        for field in ["email", "roles", "is_active"]:
            if getattr(original, field) != getattr(updated, field):
                changes[field] = {
                    "old": getattr(original, field),
                    "new": getattr(updated, field)
                }
        return changes

class AssignRolesUseCase:
    def __init__(self, user_repo: UserRepository, audit: AuditProducer):
        self.user_repo = user_repo
        self.audit = audit

    async def execute(self, user_id: str, roles: List[str], current_user: Usuario) -> Usuario:
        self._validate_permissions(current_user)
        
        user = await self.user_repo.get_by_id(user_id)
        self._validate_role_hierarchy(current_user, user, roles)
        
        user.roles = list(set(roles))  # Eliminar duplicados
        updated_user = await self.user_repo.update(user)
        
        await self.audit.send(
            event_type="ROLES_ASSIGNED",
            payload={
                "by_user": current_user.id,
                "user_id": user_id,
                "assigned_roles": roles
            }
        )
        return updated_user

    def _validate_permissions(self, user: Usuario):
        if not user.has_permission("roles:assign"):
            raise PermissionDenied("No tienes permisos para asignar roles")

    def _validate_role_hierarchy(self, current_user: Usuario, target_user: Usuario, new_roles: List[str]):
        if "admin" in new_roles and not current_user.has_role("superadmin"):
            raise PermissionDenied("Solo superadmins pueden asignar rol admin")

class PasswordResetUseCase:
    def __init__(
        self,
        user_repo: UserRepository,
        redis: Redis,
        audit: AuditProducer,
        token_ttl: int = 3600
    ):
        self.user_repo = user_repo
        self.redis = redis
        self.audit = audit
        self.token_ttl = token_ttl

    async def execute(self, email: EmailStr) -> PasswordResetToken:
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise ValidationError("Usuario no encontrado")
        
        token = PasswordResetToken.generate()
        await self.redis.setex(
            f"pwd_reset:{token.value}",
            self.token_ttl,
            user.id
        )
        
        await self.audit.send(
            event_type="PASSWORD_RESET_REQUESTED",
            payload={"user_id": user.id}
        )
        return token

    async def confirm_reset(self, token: str, new_password: str) -> Usuario:
        user_id = await self.redis.get(f"pwd_reset:{token}")
        if not user_id:
            raise AuthError("Token de reset inválido o expirado")
        
        user = await self.user_repo.get_by_id(user_id)
        user.hashed_password = hasher.hash(new_password)
        user.password_changed_at = datetime.utcnow()
        
        await self.redis.delete(f"pwd_reset:{token}")
        await self.audit.send(
            event_type="PASSWORD_RESET_COMPLETED",
            payload={"user_id": user.id}
        )
        return await self.user_repo.update(user)

class PasswordExpirationUseCase:
    def __init__(self, user_repo: UserRepository, audit: AuditProducer):
        self.user_repo = user_repo
        self.audit = audit

    async def execute(self, user: Usuario) -> bool:
        expiration_days = settings.PASSWORD_EXPIRATION_DAYS
        if not expiration_days:
            return False
        
        expiration_date = user.password_changed_at + timedelta(days=expiration_days)
        if datetime.utcnow() > expiration_date:
            await self.audit.send(
                event_type="PASSWORD_EXPIRED",
                payload={"user_id": user.id}
            )
            user.password_expired = True
            await self.user_repo.update(user)
            return True
        return False