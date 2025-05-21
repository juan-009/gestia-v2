import logging
from logging.config import fileConfig
import os
import sys
from typing import AsyncGenerator

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

# Añadir el path del proyecto al sistema
sys.path.append(os.getcwd())

from app.shared.config.config import settings
from app.infraestructura.persistencia.orm import Base
from app.dominio.modelos import *  # Importar todos los modelos para autogenerate

logger = logging.getLogger(__name__)

# Configurar el contexto de Alembic
config = context.config
fileConfig(config.config_file_name) if config.config_file_name else None

target_metadata = Base.metadata

def get_database_url() -> str:
    """Obtiene la URL de la base de datos desde la configuración"""
    return str(settings.POSTGRES_DSN)

def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo offline (solo para generar SQL)"""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        version_table_schema=settings.POSTGRES_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> AsyncGenerator[None, None]:
    """Ejecuta migraciones en modo online usando conexión asíncrona"""
    connectable = create_async_engine(
        get_database_url(),
        poolclass=pool.NullPool,
        future=True,
        echo=settings.DEBUG,
    )

    async with connectable.connect() as connection:
        await connection.execution_options(
            schema_translate_map={None: settings.POSTGRES_SCHEMA}
        )
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def do_run_migrations(connection: Connection) -> None:
    """Función wrapper para ejecutar migraciones en contexto síncrono"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        version_table_schema=settings.POSTGRES_SCHEMA,
        include_object=include_object,
        process_revision_directives=process_revision_directives,
        user_module_prefix="sa.",
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def include_object(object, name, type_, reflected, compare_to):
    """Filtro para excluir objetos específicos de las migraciones"""
    if type_ == "table" and name in ["spatial_ref_sys", "alembic_version"]:
        return False
    return True

def process_revision_directives(context, revision, directives):
    """Personaliza la generación de migraciones"""
    if config.cmd_opts.autogenerate:
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            logger.info("No se detectaron cambios en los modelos")

if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())