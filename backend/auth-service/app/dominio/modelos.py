from datetime import datetime
from typing import List, Optional, Set
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.shared.config.constants import (
    SecurityConstants,
    RBACConstants,
    MFAConstants
)

class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy"""
    
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

# Tabla de asociación para relación muchos-a-muchos entre Usuario y Rol
user_role_association = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', PG_UUID(as_uuid=True), ForeignKey('users.id')),
    Column('role_id', PG_UUID(as_uuid=True), ForeignKey('roles.id'))
)

# Tabla de asociación para relación muchos-a-muchos entre Rol y Permiso
role_permission_association = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', PG_UUID(as_uuid=True), ForeignKey('roles.id')),
    Column('permission_id', PG_UUID(as_uuid=True), ForeignKey('permissions.id'))
)

class Usuario(Base):
    """Entidad principal de usuario con autenticación"""
    
    __tablename__ = "users"
    
    # Campos principales
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    mfa_secret: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True
    )
    recovery_codes: Mapped[Optional[List[str]]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Relaciones
    roles: Mapped[Set['Rol']] = relationship(
        secondary=user_role_association,
        back_populates="users"
    )
    
    # Métodos del dominio
    def verify_password(self, password: str) -> bool:
        from app.infraestructura.seguridad.hasher import verify_password
        return verify_password(password, self.password_hash)
    
    def has_permission(self, permission: str) -> bool:
        for role in self.roles:
            if role.has_permission(permission):
                return True
        return False
    
    def enable_mfa(self, secret: str, recovery_codes: List[str]):
        self.mfa_enabled = True
        self.mfa_secret = secret
        self.recovery_codes = recovery_codes
    
    class Meta:
        indexes = [
            Index('ix_users_email', 'email', unique=True)
        ]

class Rol(Base):
    """Entidad para gestión de roles con herencia jerárquica"""
    
    __tablename__ = "roles"
    
    # Campos principales
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    
    # Relaciones
    users: Mapped[Set[Usuario]] = relationship(
        secondary=user_role_association,
        back_populates="roles"
    )
    permissions: Mapped[Set['Permiso']] = relationship(
        secondary=role_permission_association,
        back_populates="roles"
    )
    parent: Mapped[Optional['Rol']] = relationship(
        'Rol',
        remote_side=[id],
        back_populates="children"
    )
    children: Mapped[List['Rol']] = relationship(
        'Rol',
        back_populates="parent"
    )
    
    # Métodos del dominio
    def has_permission(self, permission: str) -> bool:
        if RBACConstants.WILDCARD_PERMISSION in self.permissions:
            return True
        
        required_scope, required_action = permission.split(
            RBACConstants.PERMISSION_SCOPE_DELIMITER,
            1
        )
        
        for perm in self.permissions:
            perm_scope, perm_action = perm.name.split(
                RBACConstants.PERMISSION_SCOPE_DELIMITER,
                1
            )
            
            if perm_scope == required_scope:
                if perm_action == RBACConstants.WILDCARD_PERMISSION:
                    return True
                if perm_action == required_action:
                    return True
        
        return False

class Permiso(Base):
    """Entidad para permisos granulares RBAC"""
    
    __tablename__ = "permissions"
    
    # Campos principales
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Relaciones
    roles: Mapped[Set[Rol]] = relationship(
        secondary=role_permission_association,
        back_populates="permissions"
    )
    
    # Validación
    def __init__(self, name: str, **kwargs):
        self.validate_permission_name(name)
        super().__init__(name=name, **kwargs)
    
    @staticmethod
    def validate_permission_name(name: str):
        parts = name.split(RBACConstants.PERMISSION_SCOPE_DELIMITER)
        if len(parts) != 2:
            raise ValueError(
                f"Formato de permiso inválido. Usar: "
                f"'scope{RBACConstants.PERMISSION_SCOPE_DELIMITER}action'"
            )
        
        valid_scopes = list(RBACConstants.CORE_PERMISSIONS.keys())
        if parts[0] != RBACConstants.WILDCARD_PERMISSION and parts[0] not in valid_scopes:
            raise ValueError(f"Scope inválido. Válidos: {valid_scopes}")

class SessionActiva(Base):
    """Entidad para gestión de sesiones activas"""
    
    __tablename__ = "active_sessions"
    
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey('users.id'),
        index=True
    )
    device_info: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    
    # Relación
    user: Mapped[Usuario] = relationship("Usuario", backref="sessions")