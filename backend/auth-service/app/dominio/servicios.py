from datetime import datetime
from typing import List, Optional, Set
from app.dominio.modelos import Usuario, Rol, Permiso
from app.dominio.excepciones import (
    InvalidCredentialsError,
    AccountLockedError,
    PermissionDeniedError,
    RoleConflictError,
    InvalidPermissionFormatError,
    WeakPasswordError,
    MFARequiredError
)
from app.infraestructura.seguridad import PasswordHasher
import re

class ServicioPermisos:
    @staticmethod
    def validar_formato_permiso(permiso: str) -> bool:
        """Valida el formato 'recurso:accion' usando regex"""
        if not re.match(r"^[a-z]+:[a-z]+$", permiso):
            raise InvalidPermissionFormatError(permiso=permiso)
        return True

    @classmethod
    def extraer_scope_accion(cls, permiso: str) -> tuple:
        cls.validar_formato_permiso(permiso)
        return tuple(permiso.split(':'))

class ServicioJerarquiaRoles:
    def __init__(self, repositorio_roles):
        self.repositorio_roles = repositorio_roles
        self.cache_herencia = {}

    async def obtener_permisos_heredados(self, rol: Rol) -> Set[str]:
        """Obtiene todos los permisos heredados recursivamente"""
        permisos = set(rol.permisos)
        for rol_heredado in rol.hereda:
            rol_padre = await self.repositorio_roles.obtener_por_nombre(rol_heredado)
            if rol_padre:
                permisos.update(await self.obtener_permisos_heredados(rol_padre))
        return permisos

    async def validar_jerarquia(self, rol: Rol, rol_padre: Rol) -> bool:
        """Valida que no se creen ciclos en la herencia de roles"""
        if rol.nombre == rol_padre.nombre:
            raise RoleConflictError(rol=rol.nombre, razon="Auto-herencia no permitida")
            
        roles_visitados = set()
        cola = [rol_padre.nombre]
        
        while cola:
            actual = cola.pop(0)
            if actual == rol.nombre:
                raise RoleConflictError(
                    rol=rol.nombre,
                    razon="Ciclo detectado en la jerarquía"
                )
            if actual not in roles_visitados:
                roles_visitados.add(actual)
                rol_actual = await self.repositorio_roles.obtener_por_nombre(actual)
                cola.extend(rol_actual.hereda)
        
        return True

class ServicioAutenticacion:
    def __init__(self, repositorio_usuarios, hasher: PasswordHasher):
        self.repositorio_usuarios = repositorio_usuarios
        self.hasher = hasher
        self.max_intentos = 5
        self.tiempo_bloqueo = 300  # 5 minutos

    async def autenticar(self, email: str, password: str) -> Usuario:
        usuario = await self.repositorio_usuarios.obtener_por_email(email)
        
        self._validar_bloqueo(usuario)
        self._validar_credenciales(usuario, password)
        
        if usuario.mfa_habilitado:
            raise MFARequiredError(mfa_type="TOTP")
            
        await self._reiniciar_intentos(usuario)
        return usuario

    def _validar_bloqueo(self, usuario: Usuario):
        if usuario.intentos_fallidos >= self.max_intentos:
            tiempo_restante = self._calcular_tiempo_desbloqueo(usuario)
            if tiempo_restante > 0:
                raise AccountLockedError(tiempo_restante)

    def _calcular_tiempo_desbloqueo(self, usuario: Usuario) -> int:
        ultimo_intento = usuario.ultimo_intento_fallido or datetime.min
        tiempo_transcurrido = (datetime.utcnow() - ultimo_intento).total_seconds()
        return max(0, self.tiempo_bloqueo - int(tiempo_transcurrido))

class ServicioUsuarios:
    def __init__(self, repositorio_usuarios, hasher: PasswordHasher):
        self.repositorio_usuarios = repositorio_usuarios
        self.hasher = hasher

    async def crear_usuario(self, datos_usuario: dict) -> Usuario:
        self._validar_password(datos_usuario['password'])
        
        usuario = Usuario(**datos_usuario)
        usuario.hashed_password = self.hasher.hash(datos_usuario['password'])
        
        return await self.repositorio_usuarios.guardar(usuario)

    def _validar_password(self, password: str):
        if len(password) < 12:
            raise WeakPasswordError(razon="Longitud mínima no alcanzada")
        if not re.search(r"[A-Z]", password):
            raise WeakPasswordError(razon="Falta mayúscula")
        if not re.search(r"\d", password):
            raise WeakPasswordError(razon="Falta número")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise WeakPasswordError(razon="Falta carácter especial")

class ServicioRBAC:
    def __init__(self, repositorio_roles, cache):
        self.repositorio_roles = repositorio_roles
        self.cache = cache

    async def verificar_permiso(self, usuario: Usuario, permiso_requerido: str) -> bool:
        if not usuario.esta_activo:
            raise PermissionDeniedError(permiso=permiso_requerido)
            
        cache_key = f"permisos:{usuario.id}"
        permisos_cache = await self.cache.obtener(cache_key)
        
        if permisos_cache:
            return permiso_requerido in permisos_cache
            
        permisos = await self._obtener_permisos_usuario(usuario)
        await self.cache.guardar(cache_key, permisos, ttl=300)
        
        return permiso_requerido in permisos

    async def _obtener_permisos_usuario(self, usuario: Usuario) -> Set[str]:
        permisos = set()
        servicio_jerarquia = ServicioJerarquiaRoles(self.repositorio_roles)
        
        for rol_nombre in usuario.roles:
            rol = await self.repositorio_roles.obtener_por_nombre(rol_nombre)
            if rol:
                permisos_rol = await servicio_jerarquia.obtener_permisos_heredados(rol)
                permisos.update(permisos_rol)
        
        return permisos