import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response
from pydantic import BaseModel
from app.shared.utils.logger import logger
from app.infraestructura.mensajeria.adapters.kafka import AuditProducer
from app.dominio.excepciones import AuditError

class AuditLog(BaseModel):
    timestamp: datetime
    request_id: str
    user_id: Optional[str] = None
    client_ip: str
    http_method: str
    path: str
    status_code: int
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    integrity_hash: str

    def generate_hash(self, secret: str) -> str:
        data_str = json.dumps(self.dict(exclude={"integrity_hash"}), sort_keys=True)
        return hashlib.sha3_256(f"{secret}{data_str}".encode()).hexdigest()

class AuditMiddleware:
    def __init__(self, app):
        self.app = app
        self.producer = AuditProducer()
        self.sensitive_fields = {"password", "token", "secret"}
        self.required_audit_paths = {
            "/auth/login": "POST",
            "/users": ["POST", "PUT", "DELETE"],
            "/roles": ["POST", "PUT", "DELETE"]
        }

    async def __call__(self, request: Request, call_next) -> Response:
        if not self._requires_audit(request):
            return await call_next(request)

        audit_data = await self._capture_request_data(request)
        response = await call_next(request)
        await self._capture_response_data(response, audit_data)

        try:
            await self._process_audit_entry(audit_data)
        except Exception as e:
            logger.error(f"Audit processing failed: {str(e)}")
            raise AuditError("Failed to record audit trail")

        return response

    async def _capture_request_data(self, request: Request) -> Dict:
        request_id = request.headers.get("X-Request-ID", "unknown")
        user = getattr(request.state, "user", None)
        
        try:
            body = await request.json() if request.method in ["POST", "PUT", "PATCH"] else None
        except json.JSONDecodeError:
            body = None

        return {
            "timestamp": datetime.utcnow(),
            "request_id": request_id,
            "user_id": user.id if user else None,
            "client_ip": request.client.host,
            "http_method": request.method,
            "path": request.url.path,
            "request_data": self._sanitize_data(body) if body else None,
            "metadata": {
                "user_agent": request.headers.get("User-Agent"),
                "content_type": request.headers.get("Content-Type")
            }
        }

    async def _capture_response_data(self, response: Response, audit_data: Dict):
        audit_data.update({
            "status_code": response.status_code,
            "response_data": self._sanitize_data(self._get_response_body(response)),
        })

    async def _process_audit_entry(self, data: Dict):
        log_entry = AuditLog(**data)
        log_entry.integrity_hash = log_entry.generate_hash(self._get_hmac_secret())
        
        # Enviar a múltiples destinos
        await self._send_to_kafka(log_entry)
        self._write_local_log(log_entry)

    def _sanitize_data(self, data: Dict) -> Dict:
        return {
            key: self._redact_sensitive(key, value)
            for key, value in data.items()
        }

    def _redact_sensitive(self, key: str, value: Any) -> Any:
        if key.lower() in self.sensitive_fields:
            return "**REDACTED**"
        if isinstance(value, dict):
            return self._sanitize_data(value)
        return value

    def _requires_audit(self, request: Request) -> bool:
        path_config = self.required_audit_paths.get(request.url.path)
        if isinstance(path_config, list):
            return request.method in path_config
        return path_config == request.method or path_config is True

    async def _send_to_kafka(self, log_entry: AuditLog):
        await self.producer.send(
            topic="audit-logs",
            key=log_entry.user_id or "anonymous",
            value=log_entry.dict()
        )

    def _write_local_log(self, log_entry: AuditLog):
        logger.info(
            "Audit Event",
            extra={
                "type": "audit",
                "entry": log_entry.dict(),
                "integrity_check": log_entry.integrity_hash
            }
        )

    def _get_response_body(self, response: Response) -> Optional[Dict]:
        try:
            return json.loads(response.body.decode()) if response.body else None
        except json.JSONDecodeError:
            return None

    def _get_hmac_secret(self) -> str:
        # Implementar obtención de secret desde Vault
        return "secret-key-from-vault"  # Temporal, usar implementación real