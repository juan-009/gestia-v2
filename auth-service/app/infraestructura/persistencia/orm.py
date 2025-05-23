from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Table, DateTime, Text
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.sql import func # For server-side default timestamps
from datetime import datetime

# Assuming settings are correctly imported from your project structure
# This might need adjustment based on how your PYTHONPATH is configured when running Alembic or the app.
# For Alembic, env.py will handle adding 'app' to sys.path.
try:
    from auth_service.app.shared.config.config import settings
except ImportError:
    # This fallback might be useful if running scripts that don't have the full app context,
    # but for Alembic and the main app, the above should work.
    # A more robust solution for standalone script execution might involve setting PYTHONPATH explicitly.
    print("Warning: Could not import settings. Using a default DATABASE_URL for ORM setup. This might not be suitable for production.")
    class MockSettings:
        DATABASE_URL = "postgresql://user:pass@host/db" # Placeholder
        DEBUG = False
    settings = MockSettings()


Base = declarative_base()

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Association table for User and Role (Many-to-Many)
user_role_association = Table(
    'user_role_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True)
)

# Association table for Role and Permission (Many-to-Many)
role_permission_association = Table(
    'role_permission_association', Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete="CASCADE"), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete="CASCADE"), primary_key=True)
)

class UserTable(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False) # Specify length for String
    hashed_password = Column(String(255), nullable=False) # Specify length
    is_active = Column(Boolean, default=True)
    
    # Using server_default for database-side timestamp generation
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    roles = relationship("RoleTable", secondary=user_role_association, back_populates="users")

class RoleTable(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False) # Specify length
    description = Column(Text, nullable=True) # Text for potentially longer descriptions

    users = relationship("UserTable", secondary=user_role_association, back_populates="roles")
    permissions = relationship("PermissionTable", secondary=role_permission_association, back_populates="roles")

class PermissionTable(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False) # Specify length
    description = Column(Text, nullable=True)

    roles = relationship("RoleTable", secondary=role_permission_association, back_populates="permissions")

def init_db():
    """
    Initializes the database by creating all tables defined by Base.metadata.
    This function is suitable for initial setup in development or for tests.
    For production environments, Alembic migrations should be used.
    """
    # In a real application, you might want to check if tables already exist
    # or handle this with more sophisticated logic, but for a simple init, this is fine.
    print(f"Initializing database at {settings.DATABASE_URL}...")
    Base.metadata.create_all(bind=engine)
    print("Database initialization complete (tables created if they didn't exist).")

if __name__ == '__main__':
    # This allows running `python -m auth_service.app.infraestructura.persistencia.orm`
    # to initialize the DB, but be careful with this in production.
    print("Running ORM script directly. This will attempt to initialize the database.")
    # A .env file should be present in the root for settings to load correctly.
    # Ensure your DATABASE_URL is correctly configured.
    init_db()
