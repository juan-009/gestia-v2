import uuid
from datetime import datetime
from typing import Any, Optional
import logging


from sqlalchemy import URL, Column, text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.infraestructura.persistencia.repositorios import UserRepository

from app.shared.config.config import settings
from app.shared.config.constants import DB_POOL_SIZE, DB_MAX_OVERFLOW

# Configuración del logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Base(AsyncAttrs, DeclarativeBase):
    """
    Clase base para todos los modelos ORM.
    Utiliza PostgreSQL UUID como tipo de clave primaria.
    """
    
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()")
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("NOW()")
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"

    @classmethod
    def get_field_names(cls) -> list[str]:
        return [column.name for column in cls.__table__.columns]

class DatabaseManager:
    """Gestión centralizada de conexiones y sesiones de base de datos"""
    
    def __init__(self) -> None:
        self._engine = None
        self._async_session_factory = None

    def initialize(self) -> None:
        """Inicializa el motor y la fábrica de sesiones"""
        db_url = URL.create(
            drivername="postgresql+asyncpg",
            username=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD.get_secret_value(),
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB
        )
        
        self._engine = create_async_engine(
            db_url,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=settings.DEBUG
        )
        
        self._async_session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )

    async def dispose(self) -> None:
        """Cierra todas las conexiones del pool"""
        if self._engine:
            await self._engine.dispose()

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if not self._async_session_factory:
            raise RuntimeError("DatabaseManager no inicializado")
        return self._async_session_factory

    async def get_session(self) -> AsyncSession:
        """Obtiene una nueva sesión asincrónica"""
        return self.session_factory()

    async def health_check(self) -> bool:
        """Verifica la conectividad con la base de datos"""
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database health check failed: %s", str(e))
            return False

class UnitOfWork:
    """Implementación del patrón Unit of Work para gestión transaccional"""
    
    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self.session_factory()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self) -> None:
        """Confirma la transacción actual"""
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        """Revierte la transacción actual"""
        if self.session:
            await self.session.rollback()

    @property
    def repositories(self) -> dict[str, Any]:
        """Devuelve los repositorios inyectados en la UoW"""
        # Implementar según repositorios específicos
        return {"user_repo": UserRepository(self.session)}

    

# Inicialización de la instancia de base de datos
db_manager = DatabaseManager()

async def initialize_database():
    """Función de inicialización para el startup del servicio"""
    db_manager.initialize()
    logger.info("Database manager inicializado")
    
    # Ejecutar migraciones si es necesario
    if settings.ENVIRONMENT == "dev":
        await run_migrations()

async def run_migrations():
    """Ejecuta migraciones de Alembic programáticamente"""
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("migrations/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(db_manager._engine.url))
    
    try:
        async with db_manager._engine.begin() as conn:
            await conn.run_sync(command.upgrade, alembic_cfg, "head")
        logger.info("Migraciones de base de datos aplicadas con éxito")
    except Exception as e:
        logger.error("Error aplicando migraciones: %s", str(e))
        raise