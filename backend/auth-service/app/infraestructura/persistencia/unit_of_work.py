from typing import Any, AsyncIterator, Optional
from uuid import UUID
from contextlib import asynccontextmanager
import logging

from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.infraestructura.persistencia.orm import UnitOfWork as BaseUnitOfWork
from app.infraestructura.persistencia.repositorios import (
    UserRepository,
    RoleRepository,
    PermissionRepository,
    SessionRepository
)
from app.dominio.excepciones import DatabaseError

logger = logging.getLogger(__name__)

class UnitOfWork(BaseUnitOfWork):
    """Implementación avanzada del patrón Unit of Work con manejo transaccional"""
    
    def __init__(self, session_factory: AsyncSession):
        super().__init__(session_factory)
        self._transaction_depth = 0  # Para manejar transacciones anidadas

    async def __aenter__(self) -> "UnitOfWork":
        if self._transaction_depth == 0:
            self.session = self.session_factory()
            await self.session.begin()
            logger.debug("Nueva transacción iniciada")
        self._transaction_depth += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._transaction_depth -= 1
        if self._transaction_depth > 0:
            return
        
        try:
            if exc_type:
                await self.rollback()
                logger.debug("Transacción revertida debido a error")
            else:
                await self.commit()
                logger.debug("Transacción confirmada exitosamente")
        except SQLAlchemyError as e:
            logger.error("Error en gestión transaccional: %s", str(e))
            await self.rollback()
            raise DatabaseError("TRANSACTION_ERROR") from e
        finally:
            await self.session.close()
            logger.debug("Sesión de base de datos cerrada")

    @property
    def users(self) -> UserRepository:
        """Repositorio de usuarios con acceso transaccional"""
        return UserRepository(self.session)

    @property
    def roles(self) -> RoleRepository:
        """Repositorio de roles con acceso transaccional"""
        return RoleRepository(self.session)

    @property
    def permissions(self) -> PermissionRepository:
        """Repositorio de permisos con acceso transaccional"""
        return PermissionRepository(self.session)

    @property
    def sessions(self) -> SessionRepository:
        """Repositorio de sesiones activas con acceso transaccional"""
        return SessionRepository(self.session)

    async def commit(self) -> None:
        """Confirma la transacción actual con verificación de integridad"""
        try:
            if self.session.is_active:
                await self.session.commit()
                logger.debug("Commit realizado con éxito")
        except DBAPIError as e:
            logger.error("Error de integridad en commit: %s", str(e))
            await self.rollback()
            raise DatabaseError("INTEGRITY_ERROR") from e

    async def rollback(self) -> None:
        """Revierte la transacción actual con manejo seguro"""
        try:
            if self.session.is_active:
                await self.session.rollback()
                logger.debug("Rollback realizado con éxito")
        except SQLAlchemyError as e:
            logger.error("Error en rollback: %s", str(e))
            raise DatabaseError("ROLLBACK_ERROR") from e

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Context manager para transacciones anidadas"""
        async with self:
            try:
                yield
            except Exception as e:
                logger.debug("Error detectado en transacción anidada")
                raise e

    async def flush(self) -> None:
        """Sincroniza el estado de la sesión con la base de datos"""
        try:
            await self.session.flush()
            logger.debug("Flush realizado con éxito")
        except SQLAlchemyError as e:
            logger.error("Error en flush: %s", str(e))
            await self.rollback()
            raise DatabaseError("FLUSH_ERROR") from e

    async def refresh(self, entity: Any) -> None:
        """Actualiza una entidad desde la base de datos"""
        try:
            await self.session.refresh(entity)
            logger.debug("Entidad actualizada: %s", entity)
        except SQLAlchemyError as e:
            logger.error("Error refrescando entidad: %s", str(e))
            raise DatabaseError("REFRESH_ERROR") from e

    async def merge(self, entity: Any) -> Any:
        """Fusiona una entidad desconectada en la sesión actual"""
        try:
            merged_entity = await self.session.merge(entity)
            logger.debug("Entidad fusionada: %s", merged_entity)
            return merged_entity
        except SQLAlchemyError as e:
            logger.error("Error fusionando entidad: %s", str(e))
            raise DatabaseError("MERGE_ERROR") from e

    async def execute_query(self, query: str, params: dict = None) -> Any:
        """Ejecuta una consulta SQL cruda con parámetros"""
        try:
            result = await self.session.execute(text(query), params or {})
            logger.debug("Consulta ejecutada: %s", query)
            return result
        except SQLAlchemyError as e:
            logger.error("Error en consulta SQL: %s", str(e))
            raise DatabaseError("RAW_QUERY_ERROR") from e