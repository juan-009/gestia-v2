from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add app directory to sys.path to import settings and Base
# This assumes alembic.ini's script_location = migrations, and this env.py is in 'migrations/'
# So, '..' goes to project root, then 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))


try:
    from shared.config.config import settings # Import your app's settings
    from infraestructura.persistencia.orm import Base # Import your Base
except ImportError as e:
    print(f"Error importing settings or Base for Alembic: {e}")
    print("Ensure that 'app' directory is in sys.path and contains shared/config/config.py and infraestructura/persistencia/orm.py")
    print(f"Current sys.path: {sys.path}")
    print(f"Current working directory: {os.getcwd()}")
    # Attempting a relative import path that might work if alembic is run from project root.
    # This is less ideal than ensuring sys.path is correct.
    try:
        from app.shared.config.config import settings
        from app.infraestructura.persistencia.orm import Base
    except ImportError:
         # If this also fails, Alembic won't be able to find the models or DB URL.
        print("Secondary import attempt also failed. Alembic setup is likely incorrect.")
        raise e


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set DATABASE_URL in sqlalchemy.url from your application settings
# This allows alembic.ini to have a placeholder like sqlalchemy.url = %(DB_URL)s
# and then alembic can pick it up from here.
# If your alembic.ini already has the direct URL or you set it via environment variable
# that SQLAlchemy can pick up, this explicit setting might not be strictly necessary
# but it makes the source of the URL very clear.
if settings.DATABASE_URL:
    config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)
else:
    print("Error: settings.DATABASE_URL is not set. Alembic cannot determine the database URL.")
    # Optionally, exit or raise an error if DATABASE_URL is crucial and not found
    # For now, we'll let it proceed, but migrations will likely fail.


# Interpret the config file for Python logging.
# This line needs to be configured if you want to use Python logging with Alembic.
if config.config_file_name is not None: # Check if config_file_name is set
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # Ensure the URL is taken from our settings for online mode as well
        url=settings.DATABASE_URL 
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
