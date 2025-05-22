from fastapi import APIRouter, Depends, HTTPException, status
from app.interfaces.api.v1.esquemas import (
    LoginRequest, TokenResponse, RefreshTokenRequest, NewAccessTokenResponse
)
from app.aplicacion.casos_uso.autenticacion import LoginUseCase, RefreshTokenUseCase
from app.infraestructura.persistencia.unit_of_work import SqlAlchemyUnitOfWork, AbstractUnitOfWork
from app.aplicacion.servicios import AuthService
# SQLUserRepository is not directly used here but by AuthService
from app.shared.config.config import settings
from app.dominio.excepciones import (
    UserNotFoundError, InvalidCredentialsError, UserInactiveError, InvalidTokenError, DomainError
)

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])

# Dependencies
from typing import AsyncGenerator

async def get_uow() -> AsyncGenerator[AbstractUnitOfWork, None]: # Depend on abstraction
    async with SqlAlchemyUnitOfWork() as uow: # SqlAlchemyUnitOfWork implements async context manager
        yield uow

def get_auth_service(uow: AbstractUnitOfWork = Depends(get_uow)) -> AuthService:
    # uow.users should be an instance of SQLUserRepository, as initialized in SqlAlchemyUnitOfWork
    return AuthService(user_repository=uow.users) 

def get_login_use_case(auth_service: AuthService = Depends(get_auth_service)) -> LoginUseCase:
    return LoginUseCase(auth_service=auth_service)

def get_refresh_token_use_case(auth_service: AuthService = Depends(get_auth_service)) -> RefreshTokenUseCase:
    return RefreshTokenUseCase(auth_service=auth_service)

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest, 
    use_case: LoginUseCase = Depends(get_login_use_case)
):
    try:
        # TokenPairDTO from use case is compatible with TokenResponse schema
        token_pair_dto = await use_case.execute(login_data)
        return TokenResponse(
            access_token=token_pair_dto.access_token,
            refresh_token=token_pair_dto.refresh_token
            # token_type is defaulted in TokenResponse
        )
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except UserNotFoundError as e: # Should ideally be caught by InvalidCredentialsError for security
        # For better security, avoid confirming whether the user exists or if the password was wrong.
        # The AuthService.login method already raises UserNotFoundError or InvalidCredentialsError.
        # Here, we map both to a generic 401 to avoid leaking info.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    except UserInactiveError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) # Or 403 Forbidden
    except DomainError as e: # Catch other specific domain errors
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # General exception handler (e.g., for 500 errors) should be FastAPI middleware.

@router.post("/refresh", response_model=NewAccessTokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    use_case: RefreshTokenUseCase = Depends(get_refresh_token_use_case)
):
    try:
        new_access_token = await use_case.execute(refresh_data)
        return NewAccessTokenResponse(access_token=new_access_token)
    except InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except UserNotFoundError as e: # User associated with token not found
        # For better security, avoid confirming specific reasons for token failure.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")
    except UserInactiveError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) # Or 403
    except DomainError as e: # Catch other specific domain errors
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    # General exception handler (e.g., for 500 errors) should be FastAPI middleware.