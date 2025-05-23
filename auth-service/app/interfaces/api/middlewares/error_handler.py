from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException # To handle FastAPI's own
from auth_service.app.dominio.excepciones import (
    DomainError, AuthError, UserNotFoundError, InvalidCredentialsError, 
    InvalidTokenError, UserInactiveError, PermissionDeniedError, RoleError
)
import logging

async def global_exception_handler_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except InvalidCredentialsError as e:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(e) or "Invalid credentials."})
    except InvalidTokenError as e:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(e) or "Invalid or expired token."})
    except UserInactiveError as e: # Specific user state issue
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(e) or "User account is inactive."})
    except PermissionDeniedError as e: # Specific permission issue
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(e) or "Permission denied."})
    except UserNotFoundError as e: # General case for user not found, not during login
        # This is a sensitive error. Depending on context, you might want to return 401 or a more generic 404.
        # For example, if a user tries to access a sub-resource of a user that doesn't exist.
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(e) or "User or requested resource not found."})
    # Catch more specific AuthErrors before generic AuthError
    except AuthError as e: # Catch-all for other auth errors
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(e) or "Authentication error."})
    except RoleError as e: # Catch-all for role errors
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e) or "Role related error."})
    except DomainError as e: # Catch-all for other domain errors
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e) or "Bad request due to domain rule violation."})
    except StarletteHTTPException as e: # To handle FastAPI's own HTTPExceptions
        # This ensures that exceptions raised by FastAPI itself (e.g. validation errors if not handled elsewhere)
        # are also returned in a consistent JSON format.
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        # It's good practice to log the actual error for debugging.
        logging.error(f"Unhandled exception for request {request.url.path}: {e}", exc_info=True)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "An internal server error occurred."})
