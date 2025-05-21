from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
import re

from app.shared.config.constants import EventConstants
from app.dominio.excepciones import DomainException

@dataclass(frozen=True)
class DomainEvent:
    """Clase base para todos los eventos de dominio"""
    
    event_id: UUID = uuid4()
    timestamp: datetime = datetime.utcnow()
    version: str = EventConstants.EVENT_SCHEMA_VERSION
    event_type: str
    aggregate_id: UUID  # ID de la entidad raíz del agregado
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        self._validate_payload()
    
    def _validate_payload(self):
        """Validación base del payload del evento"""
        if not self.payload:
            raise DomainException("EventPayloadError", "Payload no puede estar vacío")
        
    def serialize(self) -> Dict[str, Any]:
        """Serializa el evento para publicación"""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "aggregate_id": str(self.aggregate_id),
            "payload": self.payload,
            "metadata": self.metadata or {}
        }

# ==================== EVENTOS DE AUTENTICACIÓN ====================
@dataclass(frozen=True)
class UserLoggedIn(DomainEvent):
    """Evento emitido cuando un usuario inicia sesión exitosamente"""
    
    def __post_init__(self):
        super().__post_init__()
        required_fields = ["user_id", "ip_address", "device_info"]
        self._validate_required_fields(required_fields)
        self._validate_ip_format()
    
    def _validate_ip_format(self):
        ip = self.payload.get("ip_address")
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip):
            raise DomainException("InvalidEventData", "Formato de IP inválido")

@dataclass(frozen=True)
class UserLoginFailed(DomainEvent):
    """Evento emitido en intentos fallidos de autenticación"""
    
    def __post_init__(self):
        super().__post_init__()
        required_fields = ["user_id", "ip_address", "failure_reason"]
        self._validate_required_fields(required_fields)

@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """Evento emitido al registrar un nuevo usuario"""
    
    def __post_init__(self):
        super().__post_init__()
        required_fields = ["user_id", "email", "registration_method"]
        self._validate_required_fields(required_fields)

# ==================== EVENTOS DE SEGURIDAD ====================
@dataclass(frozen=True)
class PasswordChanged(DomainEvent):
    """Evento emitido al cambiar una contraseña"""
    
    def __post_init__(self):
        super().__post_init__()
        required_fields = ["user_id", "changed_by"]
        self._validate_required_fields(required_fields)

@dataclass(frozen=True)
class MFASettingsChanged(DomainEvent):
    """Evento emitido al modificar configuración de MFA"""
    
    def __post_init__(self):
        super().__post_init__()
        required_fields = ["user_id", "mfa_type", "enabled"]
        self._validate_required_fields(required_fields)

# ==================== EVENTOS RBAC ====================
@dataclass(frozen=True)
class RoleAssigned(DomainEvent):
    """Evento emitido al asignar un rol a un usuario"""
    
    def __post_init__(self):
        super().__post_init__()
        required_fields = ["user_id", "role_id", "assigned_by"]
        self._validate_required_fields(required_fields)

@dataclass(frozen=True)
class PermissionUpdated(DomainEvent):
    """Evento emitido al actualizar permisos de un rol"""
    
    def __post_init__(self):
        super().__post_init__()
        required_fields = ["role_id", "permissions_added", "permissions_removed", "modified_by"]
        self._validate_required_fields(required_fields)

# ==================== EVENTOS DEL SISTEMA ====================
@dataclass(frozen=True)
class SecurityAlert(DomainEvent):
    """Evento emitido para alertas de seguridad críticas"""
    
    def __post_init__(self):
        super().__post_init__()
        required_fields = ["alert_type", "severity", "description"]
        self._validate_required_fields(required_fields)

# ==================== HELPERS ====================
def event_factory(event_type: str, aggregate_id: UUID, payload: Dict) -> DomainEvent:
    """Factory para creación de eventos basado en el tipo"""
    event_classes = {
        EventConstants.Types.USER_LOGIN_SUCCESS: UserLoggedIn,
        EventConstants.Types.USER_LOGIN_FAILED: UserLoginFailed,
        EventConstants.Types.ROLE_UPDATED: RoleAssigned,
        EventConstants.Types.PERMISSION_CHANGED: PermissionUpdated,
        "SecurityAlert": SecurityAlert
    }
    
    if event_type not in event_classes:
        raise DomainException("InvalidEventType", f"Tipo de evento no soportado: {event_type}")
    
    return event_classes[event_type](
        event_type=event_type,
        aggregate_id=aggregate_id,
        payload=payload
    )