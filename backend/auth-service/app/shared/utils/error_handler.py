from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from typing import Any, Callable, Coroutine, Optional
from pydantic import BaseModel
import inspect
import uuid

from app.shared.utils.logger import logger
from app.dominio.excepciones import *
from app.infraestructura.config.settings import settings

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    correlation_id: Optional[str] = None
    details: Optional[dict] = None

class ErrorHandler:
    def __init__(self, app: FastAPI):
        self.app = app
        self._register_exceptions()
        self._add_middleware()

    class _ErrorContext:
        def __init__(self):
            self.correlation_id = None
            self.request = None

    def _register_exceptions(self):
        exceptions = [
            (RequestValidationError, 422),
            (AutenticacionFallida, 401),
            (PermisoDenegadoError, 403),
            (UsuarioBloqueadoError, 429),
            (TokenExpiradoError, 401),
            (TokenInvalidoError, 401),
            (RecursoNoEncontradoError, 404),
            (VersionTokenObsoletaError, 401),
            (LimiteRateExcedidoError, 429),
            (ConfiguracionError, 500)
        ]

        for exc, status_code in exceptions:
            self.app.add_exception_handler(exc, self._create_handler(status_code))

        self.app.add_exception_handler(Exception, self._generic_handler)

    def _create_handler(self, status_code: int) -> Callable:
        async def handler(request: Request, exc: Exception) -> JSONResponse:
            ctx = self._ErrorContext()
            ctx.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
            ctx.request = request

            error_code = self._get_error_code(exc)
            error_details = self._get_error_details(exc)
            message = self._get_user_message(exc)

            response = ErrorResponse(
                error_code=error_code,
                message=message,
                correlation_id=ctx.correlation_id,
                details=error_details if settings.DEBUG else None
            )

            self._log_error(ctx, exc, status_code)
            self._update_metrics(error_code, status_code)

            return JSONResponse(
                status_code=status_code,
                content=response.dict(),
                headers={"X-Correlation-ID": ctx.correlation_id}
            )
        return handler

    def _get_error_code(self, exc: Exception) -> str:
        if hasattr(exc, "error_code"):
            return exc.error_code  # type: ignore
        return exc.__class__.__name__

    def _get_error_details(self, exc: Exception) -> dict:
        details = {}
        if isinstance(exc, RequestValidationError):
            details["errors"] = exc.errors()
        elif hasattr(exc, "details"):
            details.update(exc.details)  # type: ignore
        return details

    def _get_user_message(self, exc: Exception) -> str:
        if hasattr(exc, "user_message"):
            return exc.user_message  # type: ignore
        return "Ocurrió un error inesperado en el servidor"

    def _log_error(self, ctx: _ErrorContext, exc: Exception, status_code: int):
        log_context = {
            "correlation_id": ctx.correlation_id,
            "status_code": status_code,
            "path": ctx.request.url.path if ctx.request else None,
            "method": ctx.request.method if ctx.request else None,
            "error_details": self._get_error_details(exc)
        }

        if 500 <= status_code < 600:
            logger.error(
                f"Server Error: {str(exc)}",
                exc_info=exc,
                extra={"context": log_context}
            )
        else:
            logger.warning(
                f"Client Error: {str(exc)}",
                extra={"context": log_context}
            )

    def _update_metrics(self, error_code: str, status_code: int):
        # Lógica para actualizar métricas Prometheus
        pass

    async def _generic_handler(self, request: Request, exc: Exception) -> JSONResponse:
        handler = self._create_handler(HTTP_500_INTERNAL_SERVER_ERROR)
        return await handler(request, exc)

    def _add_middleware(self):
        @self.app.middleware("http")
        async def add_correlation_id(request: Request, call_next):
            correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response

def setup_error_handler(app: FastAPI) -> None:
    ErrorHandler(app)

##############################################
# Ejemplo de uso en dominio/excepciones.py:
##############################################
"""
class PermisoDenegadoError(HTTPException):
    def __init__(self, permiso: str):
        super().__init__(
            status_code=403,
            detail={
                "error_code": "PERMISSION_DENIED",
                "user_message": "No tiene permisos para realizar esta acción",
                "details": {"required_permission": permiso}
            }
        )
"""