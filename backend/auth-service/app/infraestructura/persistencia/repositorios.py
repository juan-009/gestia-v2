import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dominio.modelos import Usuario, Rol, Permiso, SessionActiva
from app.dominio.excepciones import (
    UserNotFoundError,
    RoleNotFoundError,
    DuplicateEmailError,
    DatabaseError
)
from app.infraestructura.persistencia.orm import Base
from app.shared.config.constants import DB_MAX_PAGINATION_LIMIT

logger = logging.getLogger(__name__)

class BaseRepository:
    """Clase base para repositorios con operaciones CRUD comunes"""
    
    def __init__(self, session: AsyncSession, model: type[Base]):
        self.session = session
        self.model = model
    
    async def get_by_id(self, id: UUID) -> Optional[Base]:
        try:
            result = await self.session.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error obteniendo entidad por ID: %s", str(e))
            raise DatabaseError("GET_BY_ID_ERROR") from e
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = DB_MAX_PAGINATION_LIMIT
    ) -> List[Base]:
        try:
            result = await self.session.execute(
                select(self.model)
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Error obteniendo todas las entidades: %s", str(e))
            raise DatabaseError("GET_ALL_ERROR") from e
    
    async def create(self, entity_data: Dict[str, Any]) -> Base:
        try:
            entity = self.model(**entity_data)
            self.session.add(entity)
            await self.session.flush()
            await self.session.refresh(entity)
            return entity
        except Exception as e:
            await self.session.rollback()
            logger.error("Error creando entidad: %s", str(e))
            raise DatabaseError("CREATE_ERROR") from e
    
    async def update(self, id: UUID, update_data: Dict[str, Any]) -> Optional[Base]:
        try:
            await self.session.execute(
                update(self.model)
                .where(self.model.id == id)
                .values(**update_data)
            )
            return await self.get_by_id(id)
        except Exception as e:
            await self.session.rollback()
            logger.error("Error actualizando entidad: %s", str(e))
            raise DatabaseError("UPDATE_ERROR") from e
    
    async def delete(self, id: UUID) -> bool:
        try:
            await self.session.execute(
                delete(self.model).where(self.model.id == id)
            )
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error("Error eliminando entidad: %s", str(e))
            raise DatabaseError("DELETE_ERROR") from e

class UserRepository(BaseRepository):
    """Repositorio para operaciones específicas de Usuario"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Usuario)
        self.include_relations = [selectinload(Usuario.roles)]
    
    async def get_by_email(self, email: str) -> Optional[Usuario]:
        try:
            result = await self.session.execute(
                select(Usuario)
                .where(Usuario.email == email)
                .options(*self.include_relations)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error obteniendo usuario por email: %s", str(e))
            raise DatabaseError("GET_BY_EMAIL_ERROR") from e
    
    async def create_user(self, user_data: Dict[str, Any]) -> Usuario:
        try:
            if await self.get_by_email(user_data["email"]):
                raise DuplicateEmailError(user_data["email"])
            
            return await self.create(user_data)
        except DuplicateEmailError:
            raise
        except Exception as e:
            raise DatabaseError("USER_CREATION_ERROR") from e
    
    async def update_password(self, user_id: UUID, new_hash: str) -> Usuario:
        try:
            return await self.update(user_id, {"password_hash": new_hash})
        except Exception as e:
            raise DatabaseError("PASSWORD_UPDATE_ERROR") from e
    
    async def mark_mfa_enabled(self, user_id: UUID, enabled: bool = True) -> Usuario:
        try:
            return await self.update(user_id, {"mfa_enabled": enabled})
        except Exception as e:
            raise DatabaseError("MFA_UPDATE_ERROR") from e
    
    async def get_active_sessions(self, user_id: UUID) -> List[SessionActiva]:
        try:
            result = await self.session.execute(
                select(SessionActiva)
                .where(SessionActiva.user_id == user_id)
                .order_by(SessionActiva.last_activity.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Error obteniendo sesiones activas: %s", str(e))
            raise DatabaseError("GET_SESSIONS_ERROR") from e

class RoleRepository(BaseRepository):
    """Repositorio para operaciones específicas de Roles y Permisos"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Rol)
        self.include_relations = [
            selectinload(Rol.permissions),
            selectinload(Rol.parent),
            selectinload(Rol.children)
        ]
    
    async def get_by_name(self, name: str) -> Optional[Rol]:
        try:
            result = await self.session.execute(
                select(Rol)
                .where(Rol.name == name)
                .options(*self.include_relations)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error obteniendo rol por nombre: %s", str(e))
            raise DatabaseError("GET_BY_NAME_ERROR") from e
    
    async def assign_role(self, user_id: UUID, role_id: UUID) -> Usuario:
        try:
            user = await self.session.get(Usuario, user_id, options=[selectinload(Usuario.roles)])
            role = await self.get_by_id(role_id)
            
            if not user:
                raise UserNotFoundError(user_id)
            if not role:
                raise RoleNotFoundError(role_id)
            
            user.roles.append(role)
            await self.session.flush()
            return user
        except (UserNotFoundError, RoleNotFoundError):
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error("Error asignando rol: %s", str(e))
            raise DatabaseError("ROLE_ASSIGN_ERROR") from e
    
    async def add_permission(self, role_id: UUID, permission_id: UUID) -> Rol:
        try:
            role = await self.session.get(Rol, role_id, options=[selectinload(Rol.permissions)])
            permission = await self.session.get(Permiso, permission_id)
            
            if not role:
                raise RoleNotFoundError(role_id)
            if not permission:
                raise RoleNotFoundError(permission_id)
            
            role.permissions.append(permission)
            await self.session.flush()
            return role
        except Exception as e:
            await self.session.rollback()
            logger.error("Error agregando permiso: %s", str(e))
            raise DatabaseError("ADD_PERMISSION_ERROR") from e
    
    async def get_role_permissions(self, role_id: UUID) -> List[Permiso]:
        try:
            role = await self.session.get(Rol, role_id, options=[selectinload(Rol.permissions)])
            if not role:
                raise RoleNotFoundError(role_id)
            
            return role.permissions
        except RoleNotFoundError:
            raise
        except Exception as e:
            logger.error("Error obteniendo permisos del rol: %s", str(e))
            raise DatabaseError("GET_PERMISSIONS_ERROR") from e
    
    async def get_role_hierarchy(self, role_id: UUID) -> Dict[str, Any]:
        try:
            role = await self.session.get(Rol, role_id, options=[
                selectinload(Rol.parent),
                selectinload(Rol.children)
            ])
            if not role:
                raise RoleNotFoundError(role_id)
            
            return {
                "role": role,
                "parent": role.parent,
                "children": role.children
            }
        except RoleNotFoundError:
            raise
        except Exception as e:
            logger.error("Error obteniendo jerarquía de roles: %s", str(e))
            raise DatabaseError("HIERARCHY_ERROR") from e

class PermissionRepository(BaseRepository):
    """Repositorio para operaciones específicas de Permisos"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Permiso)
    
    async def get_by_name(self, name: str) -> Optional[Permiso]:
        try:
            result = await self.session.execute(
                select(Permiso).where(Permiso.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error obteniendo permiso por nombre: %s", str(e))
            raise DatabaseError("GET_PERMISSION_ERROR") from e

class SessionRepository(BaseRepository):
    """Repositorio para gestión de sesiones activas"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, SessionActiva)
    
    async def revoke_session(self, session_id: UUID) -> bool:
        try:
            await self.session.execute(
                delete(SessionActiva).where(SessionActiva.id == session_id)
            )
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error("Error revocando sesión: %s", str(e))
            raise DatabaseError("SESSION_REVOKE_ERROR") from e
    
    async def revoke_all_sessions(self, user_id: UUID) -> int:
        try:
            result = await self.session.execute(
                delete(SessionActiva).where(SessionActiva.user_id == user_id)
            )
            return result.rowcount
        except Exception as e:
            await self.session.rollback()
            logger.error("Error revocando todas las sesiones: %s", str(e))
            raise DatabaseError("REVOKE_ALL_SESSIONS_ERROR") from e