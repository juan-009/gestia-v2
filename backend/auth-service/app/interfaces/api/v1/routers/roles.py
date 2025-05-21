from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import EmailStr
from app.dominio.modelos import Usuario, Rol
from app.dominio.excepciones import (
    InvalidCredentialsError,
    AccountLockedError,
    MFARequiredError,
    InvalidMFACodeError,
    MFANotConfiguredError,
    PermissionDeniedError,
    RoleConflictError,
    InvalidEmailError,
    WeakPasswordError,
    InvalidPermissionFormatError,
    DatabaseError,
    CacheConnectionError,
    InvalidTokenError
)
from app.infraestructura.seguridad import (
    JWTManager,
    PasswordHasher,
    MFAService
)
from app.infraestructura.persistencia.repositorios import (
    UserRepository,
    RoleRepository
)
from app.infraestructura.cache import RedisCache
from app.infraestructura.mensajeria import AuditProducer
from app.dominio.servicios import (
    PermissionChecker,
    RoleHierarchyService
)
from app.shared.config import settings
import re

class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        jwt_manager: JWTManager,
        hasher: PasswordHasher,
        cache: RedisCache,
        audit: AuditProducer,
        mfa_service: MFAService
    ):
        self.user_repo = user_repo
        self.jwt_manager = jwt_manager
        self.hasher = hasher
        self.cache = cache
        self.audit = audit
        self.mfa_service = mfa_service

    async def autenticar(self, email: str, password: str) -> Usuario:
        try:
            if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                raise InvalidEmailError(email=email)
            
            usuario = await self.user_repo.obtener_por_email(email)
            
            if await self._cuenta_bloqueada(usuario):
                tiempo_desbloqueo = await self._tiempo_desbloqueo(usuario)
                raise AccountLockedError(unlock_in=tiempo_desbloqueo)
            
            if not usuario or not self.hasher.verify(password, usuario.hashed_password):
                await self._registrar_intento_fallido(usuario)
                raise InvalidCredentialsError()
            
            if usuario.mfa_habilitado:
                raise MFARequiredError(mfa_type="TOTP")
            
            return usuario
            
        except DatabaseError as e:
            await self.audit.registrar_error("ERROR_DB", str(e))
            raise

    async def verificar_mfa(self, usuario: Usuario, codigo: str) -> bool:
        if not usuario.mfa_secreto:
            raise MFANotConfiguredError()
            
        if not self.mfa_service.validar_codigo(usuario.mfa_secreto, codigo):
            intentos = await self._registrar_intento_mfa_fallido(usuario)
            raise InvalidMFACodeError(attempts_left=5 - intentos)
            
        return True

class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        hasher: PasswordHasher,
        audit: AuditProducer
    ):
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.hasher = hasher
        self.audit = audit
        self.hierarchy_service = RoleHierarchyService(role_repo)

    async def crear_usuario(self, datos: Dict, creador: Usuario) -> Usuario:
        try:
            if not await PermissionChecker.tiene_permiso(creador, "usuarios:crear"):
                raise PermissionDeniedError(permission="usuarios:crear")
            
            if not self._validar_password(datos['password']):
                raise WeakPasswordError(reason="No cumple política de complejidad")
            
            usuario = Usuario(**datos)
            usuario.hashed_password = self.hasher.hash(datos['password'])
            
            await self._validar_roles(usuario.roles)
            usuario_creado = await self.user_repo.guardar(usuario)
            
            await self.audit.registrar_evento(
                tipo="USUARIO_CREADO",
                detalles={
                    "creador_id": creador.id,
                    "usuario_id": usuario_creado.id
                }
            )
            return usuario_creado
            
        except DatabaseError as e:
            await self.audit.registrar_error("ERROR_DB", str(e))
            raise

    def _validar_password(self, password: str) -> bool:
        if len(password) < 12:
            raise WeakPasswordError(reason="Longitud mínima no alcanzada")
        if not re.search(r"[A-Z]", password):
            raise WeakPasswordError(reason="Falta mayúscula")
        if not re.search(r"\d", password):
            raise WeakPasswordError(reason="Falta número")
        return True

class RoleService:
    def __init__(
        self,
        role_repo: RoleRepository,
        permission_checker: PermissionChecker,
        audit: AuditProducer
    ):
        self.role_repo = role_repo
        self.permission_checker = permission_checker
        self.audit = audit

    async def asignar_permisos(self, rol_id: str, permisos: List[str], ejecutor: Usuario) -> Rol:
        try:
            await self.permission_checker.verificar(ejecutor, "roles:gestionar")
            
            for permiso in permisos:
                if not self._validar_formato_permiso(permiso):
                    raise InvalidPermissionFormatError(permission=permiso)
            
            rol = await self.role_repo.obtener_por_id(rol_id)
            rol.permisos = list(set(rol.permisos + permisos))
            
            rol_actualizado = await self.role_repo.guardar(rol)
            
            await self.audit.registrar_evento(
                tipo="PERMISOS_ASIGNADOS",
                detalles={
                    "ejecutor_id": ejecutor.id,
                    "rol_id": rol_id,
                    "permisos": permisos
                }
            )
            return rol_actualizado
            
        except DatabaseError as e:
            await self.audit.registrar_error("ERROR_DB", str(e))
            raise

    def _validar_formato_permiso(self, permiso: str) -> bool:
        partes = permiso.split(':')
        if len(partes) != 2 or not all(partes):
            return False
        return True

class SecurityService:
    def __init__(
        self,
        cache: RedisCache,
        jwt_manager: JWTManager,
        audit: AuditProducer
    ):
        self.cache = cache
        self.jwt_manager = jwt_manager
        self.audit = audit

    async def verificar_token(self, token: str) -> Usuario:
        try:
            claims = self.jwt_manager.validar_token(token)
            usuario = await self.user_repo.obtener_por_id(claims['sub'])
            
            if await self.cache.obtener(f"token_revocado:{token}"):
                raise InvalidTokenError(reason="Token revocado")
                
            return usuario
            
        except Exception as e:
            await self.audit.registrar_evento(
                tipo="TOKEN_INVALIDO",
                detalles={"token": token[:10] + "***"}
            )
            raise InvalidTokenError(reason=str(e))