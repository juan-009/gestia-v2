from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import EmailStr
import re

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
from app.dominio.servicios import (
    ServicioRBAC,
    ServicioJerarquiaRoles,
    ServicioPermisos
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
from app.shared.config import settings

class PermissionChecker:
    def __init__(self, servicio_rbac: ServicioRBAC, audit: AuditProducer):
        self.servicio_rbac = servicio_rbac
        self.audit = audit

    async def verificar(self, usuario: Usuario, permiso: str) -> bool:
        try:
            if not await self.servicio_rbac.verificar_permiso(usuario, permiso):
                raise PermissionDeniedError(permission=permiso)
            return True
        except PermissionDeniedError as e:
            await self.audit.registrar_evento(
                tipo="ACCESO_DENEGADO",
                detalles={
                    "usuario_id": usuario.id,
                    "permiso": permiso,
                    "razon": str(e)
                }
            )
            raise

class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        jwt_manager: JWTManager,
        hasher: PasswordHasher,
        cache: RedisCache,
        audit: AuditProducer,
        mfa_service: MFAService,
        servicio_rbac: ServicioRBAC
    ):
        self.user_repo = user_repo
        self.jwt_manager = jwt_manager
        self.hasher = hasher
        self.cache = cache
        self.audit = audit
        self.mfa_service = mfa_service
        self.servicio_rbac = servicio_rbac
        self.max_intentos = 5
        self.tiempo_bloqueo = 300  # 5 minutos

    async def autenticar(self, email: str, password: str) -> Usuario:
        try:
            if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
                raise InvalidEmailError(email=email)
            
            usuario = await self.user_repo.obtener_por_email(email)
            
            if await self._cuenta_bloqueada(usuario):
                tiempo_desbloqueo = self._calcular_tiempo_desbloqueo(usuario)
                raise AccountLockedError(unlock_in=tiempo_desbloqueo)
            
            if not usuario or not self.hasher.verify(password, usuario.hashed_password):
                await self._registrar_intento_fallido(usuario)
                raise InvalidCredentialsError()
            
            if usuario.mfa_habilitado:
                raise MFARequiredError(mfa_type="TOTP")
            
            await self._reiniciar_intentos(usuario)
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

    async def _cuenta_bloqueada(self, usuario: Usuario) -> bool:
        return usuario.intentos_fallidos >= self.max_intentos

    def _calcular_tiempo_desbloqueo(self, usuario: Usuario) -> int:
        ultimo_intento = usuario.ultimo_intento_fallido or datetime.min
        return max(0, self.tiempo_bloqueo - int((datetime.utcnow() - ultimo_intento).total_seconds()))

    async def _registrar_intento_fallido(self, usuario: Usuario):
        usuario.intentos_fallidos += 1
        usuario.ultimo_intento_fallido = datetime.utcnow()
        await self.user_repo.guardar(usuario)

    async def _reiniciar_intentos(self, usuario: Usuario):
        usuario.intentos_fallidos = 0
        await self.user_repo.guardar(usuario)

class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        hasher: PasswordHasher,
        audit: AuditProducer,
        permission_checker: PermissionChecker,
        servicio_jerarquia: ServicioJerarquiaRoles
    ):
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.hasher = hasher
        self.audit = audit
        self.permission_checker = permission_checker
        self.servicio_jerarquia = servicio_jerarquia

    async def crear_usuario(self, datos: Dict, creador: Usuario) -> Usuario:
        try:
            await self.permission_checker.verificar(creador, "usuarios:crear")
            self._validar_password(datos['password'])
            
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

    def _validar_password(self, password: str):
        if len(password) < 12:
            raise WeakPasswordError(reason="Longitud mínima no alcanzada")
        if not re.search(r"[A-Z]", password):
            raise WeakPasswordError(reason="Falta mayúscula")
        if not re.search(r"\d", password):
            raise WeakPasswordError(reason="Falta número")

    async def _validar_roles(self, roles: List[str]):
        for rol in roles:
            if not await self.role_repo.existe(rol):
                raise RoleConflictError(rol=rol, razon="Rol no existente")

class RoleService:
    def __init__(
        self,
        role_repo: RoleRepository,
        permission_checker: PermissionChecker,
        audit: AuditProducer,
        servicio_jerarquia: ServicioJerarquiaRoles,
        servicio_permisos: ServicioPermisos
    ):
        self.role_repo = role_repo
        self.permission_checker = permission_checker
        self.audit = audit
        self.servicio_jerarquia = servicio_jerarquia
        self.servicio_permisos = servicio_permisos

    async def asignar_permisos(self, rol_id: str, permisos: List[str], ejecutor: Usuario) -> Rol:
        try:
            await self.permission_checker.verificar(ejecutor, "roles:gestionar")
            
            for permiso in permisos:
                self.servicio_permisos.validar_formato_permiso(permiso)
            
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

class SecurityService:
    def __init__(
        self,
        user_repo: UserRepository,
        cache: RedisCache,
        jwt_manager: JWTManager,
        audit: AuditProducer,
        servicio_rbac: ServicioRBAC
    ):
        self.user_repo = user_repo
        self.cache = cache
        self.jwt_manager = jwt_manager
        self.audit = audit
        self.servicio_rbac = servicio_rbac

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