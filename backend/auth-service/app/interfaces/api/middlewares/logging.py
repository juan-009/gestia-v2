import logging
import uuid
import time
from contextvars import ContextVar
from typing import Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from opentelemetry import trace
from pydantic import BaseModel
import json_log_formatter
from app.shared.config import settings
from app.shared.utils.logger import logger

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

class StructuredLogger(logging.Logger):
    def __init__(self, name: str, level: str = "INFO"):
        super().__init__(name)
        self.setLevel(level)
        self.addFilter(ContextFilter())
        self.formatter = json_log_formatter.JSONFormatter()

    def log_activity(self, level: str, message: str, context: Dict[str, Any]):
        span = trace.get_current_span()
        record = {
            "message": message,
            "context": context,
            "severity": level,
            "span_id": span.get_span_context().span_id if span else "",
            "trace_id": trace.format_trace_id(span.get_span_context().trace_id) if span else "",
            "request_id": request_id_ctx.get(""),
            "service": "auth-service"
        }
        self.log(getattr(logging, level), "", extra=record)

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get("")
        record.user_id = getattr(record, 'user_id', None)
        return True

class LoggingMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = StructuredLogger("api", settings.LOG_LEVEL)
        self.excluded_paths = ["/health", "/metrics", "/favicon.ico"]

    async def __call__(self, request: Request, call_next) -> Response:
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        request_id = self._generate_request_id(request)
        request_id_ctx.set(request_id)
        start_time = time.monotonic()

        try:
            response = await self._log_request(request, request_id)
            response = response or await call_next(request)
        except Exception as exc:
            response = await self._handle_exception(exc, request_id)
        finally:
            await self._log_response(request, response, start_time, request_id)

        return response

    async def _log_request(self, request: Request, request_id: str):
        context = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client": {
                "ip": request.client.host,
                "user_agent": request.headers.get("user-agent")
            }
        }
        self.logger.log_activity("INFO", "Request received", context)
        request.state.request_id = request_id

    async def _log_response(self, request: Request, response: Response, start_time: float, request_id: str):
        duration = round((time.monotonic() - start_time) * 1000, 2)
        context = {
            "status_code": response.status_code,
            "duration_ms": duration,
            "response_size": int(response.headers.get("content-length", 0)),
            "cache_status": response.headers.get("x-cache-status", "miss")
        }
        self.logger.log_activity("INFO", "Request completed", context)
        response.headers["X-Request-ID"] = request_id

    async def _handle_exception(self, exc: Exception, request_id: str) -> Response:
        span = trace.get_current_span()
        span.record_exception(exc) if span else None
        
        context = {
            "exception_type": exc.__class__.__name__,
            "exception_message": str(exc),
            "severity": "ERROR"
        }
        self.logger.log_activity("ERROR", "Request failed", context)
        
        return JSONResponse(
            content={"detail": "Internal server error"},
            status_code=500,
            headers={"X-Request-ID": request_id}
        )

    def _generate_request_id(self, request: Request) -> str:
        return request.headers.get("X-Request-ID") or str(uuid.uuid4())

class APILogger:
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = StructuredLogger("auth-api", settings.LOG_LEVEL)
        return cls._instance

logger = APILogger()