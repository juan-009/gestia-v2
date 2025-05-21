import logging
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
from logging.handlers import RotatingFileHandler
from starlette.requests import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

class JSONFormatter(logging.Formatter):
    """Formateador de logs en JSON estructurado con metadata contextual"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "service": "auth-service",
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', None),
            **getattr(record, 'context', {})
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)

class AuditFilter(logging.Filter):
    """Filtro para identificar eventos de auditoría"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        return hasattr(record, 'audit_event')

class CorrelationMiddleware:
    """Middleware para inyección de ID de correlación en logs"""
    
    def __init__(self, app: ASGIApp):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        request = Request(scope, receive)
        correlation_id = request.headers.get('X-Correlation-ID', None)
        
        logger = logging.getLogger('auth-service')
        logger = logger.bind(correlation_id=correlation_id)
        
        async def send_wrapper(response):
            if correlation_id:
                response.headers['X-Correlation-ID'] = correlation_id
            await send(response)
            
        await self.app(scope, receive, send_wrapper)

class StructuredLogger(logging.Logger):
    """Logger personalizado con métodos para auditoría y métricas"""
    
    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)
        self.addFilter(AuditFilter())
        
    def bind(self, **kwargs: Dict[str, Any]) -> 'StructuredLogger':
        return self
    
    def audit(
        self,
        event_type: str,
        user: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> None:
        log_data = {
            'audit_event': True,
            'event_type': event_type,
            'user': user,
            'client_ip': client_ip,
            **(metadata or {})
        }
        
        if request:
            log_data.update({
                'path': request.url.path,
                'method': request.method,
                'user_agent': request.headers.get('user-agent')
            })
            
        self.info(
            f"Audit Event: {event_type}",
            extra={'context': log_data}
        )

def configure_logging(log_dir: Path = Path("logs")) -> None:
    """Configuración centralizada del sistema de logging"""
    
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger('auth-service')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    # Formateador JSON
    json_formatter = JSONFormatter()
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    
    # Handler rotativo para archivo
    file_handler = RotatingFileHandler(
        filename=log_dir / 'auth-service.log',
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(json_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

# Configuración inicial al importar el módulo
configure_logging()

# Logger principal de la aplicación
logger: StructuredLogger = logging.getLogger('auth-service')  # type: ignore