from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

# Assuming these paths are correct relative to the project structure
# when the application/tests run.
try:
    from auth_service.app.infraestructura.persistencia.orm import SessionLocal
    from auth_service.app.infraestructura.persistencia.repositorios import (
        SQLUserRepository, 
        SQLRoleRepository,    # Assuming stub exists
        SQLPermissionRepository # Assuming stub exists
    )
except ImportError as e:
    print(f"Error importing modules for UnitOfWork: {e}")
    # Fallback for simpler environments or if run outside full app context
    # This is mostly for development convenience.
    # In a real app, ensure PYTHONPATH or project structure allows direct imports.
    from .orm import SessionLocal
    from .repositorios import SQLUserRepository, SQLRoleRepository, SQLPermissionRepository

# Placeholder for Abstract Repositories if we define them later
# from .repositories import AbstractUserRepository 

class AbstractUnitOfWork(ABC):
    users: SQLUserRepository # Or AbstractUserRepository
    roles: SQLRoleRepository # Or AbstractRoleRepository
    permissions: SQLPermissionRepository # Or AbstractPermissionRepository

    @abstractmethod
    def __enter__(self):
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, traceback):
        raise NotImplementedError

    @abstractmethod
    async def commit(self): # Making these async for future compatibility
        raise NotImplementedError

    @abstractmethod
    async def rollback(self): # Making these async for future compatibility
        raise NotImplementedError

class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self):
        self.session = self.session_factory()
        self.users = SQLUserRepository(self.session)
        self.roles = SQLRoleRepository(self.session) 
        self.permissions = SQLPermissionRepository(self.session)
        return self

    async def __aenter__(self): # Async context manager entry
        self.session = self.session_factory()
        self.users = SQLUserRepository(self.session)
        self.roles = SQLRoleRepository(self.session)
        self.permissions = SQLPermissionRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, traceback): # Async context manager exit
        if self.session: # Ensure session was created
            if exc_type:
                await self.rollback()
            else:
                await self.commit()
            self.session.close()

    # __exit__ for synchronous context management, if needed elsewhere,
    # but FastAPI dependencies often work well with async context managers.
    def __exit__(self, exc_type, exc_val, traceback):
        if self.session: # Ensure session was created
            if exc_type:
                # For sync __exit__, call sync rollback.
                self.session.rollback() 
            else:
                self.session.commit() # SQLAlchemy's commit is synchronous
            self.session.close()

    async def commit(self):
        if self.session:
            self.session.commit() # SQLAlchemy's commit is synchronous

    async def rollback(self):
        if self.session:
            self.session.rollback() # SQLAlchemy's rollback is synchronous
