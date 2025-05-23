from app.dominio.modelos import Usuario # Assuming Usuario has id, email, hashed_password, is_active, roles
from app.dominio.value_objects import Email # This is pydantic.EmailStr
from app.dominio.excepciones import UserNotFoundError, InvalidCredentialsError, UserInactiveError, InvalidTokenError
from app.infraestructura.persistencia.repositorios import SQLUserRepository 
from app.infraestructura.seguridad import hasher as PwdHasher # Alias to avoid conflict
from app.infraestructura.seguridad import jwt_manager
from app.shared.config.config import settings
from app.aplicacion.dto import TokenPairDTO # UserDTO might not be directly used here but good for context
from typing import Dict, Any

class AuthService:
    def __init__(self, user_repository: SQLUserRepository):
        self.user_repository = user_repository
        # Hasher and JWT manager are used as module-level singletons for now
        # settings.PASSWORD_PEPPER will be accessed directly

    async def login(self, email: Email, password: str) -> TokenPairDTO:
        # Using existing repository method which returns a domain Usuario object
        # The _map_user_orm_to_domain includes hashed_password and roles
        user_domain: Usuario | None = self.user_repository.get_by_email(email)

        if not user_domain:
            raise UserNotFoundError(f"User with email {email} not found.")

        if not user_domain.is_active:
            raise UserInactiveError(f"User {email} is inactive.")

        # user_domain.hashed_password should be available from the repository's mapping
        if not PwdHasher.verify_password(password, user_domain.hashed_password, settings.PASSWORD_PEPPER):
            raise InvalidCredentialsError("Invalid password.")

        # user_domain.roles should also be available
        user_roles = user_domain.roles if user_domain.roles else []

        additional_claims: Dict[str, Any] = {"roles": user_roles}

        access_token = jwt_manager.create_access_token(
            subject=str(user_domain.id), 
            additional_claims=additional_claims
        )
        refresh_token = jwt_manager.create_refresh_token(
            subject=str(user_domain.id)
        )

        return TokenPairDTO(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token_str: str) -> str:
        try:
            claims = jwt_manager.validate_token(refresh_token_str)
        except InvalidTokenError as e:
            # Log the specific error e if needed, then re-raise or raise a new one
            raise InvalidTokenError(f"Refresh token validation failed: {str(e)}")

        if not claims.sub: # Ensure subject is present
            raise InvalidTokenError("Refresh token subject (sub) is missing.")

        user_id_str = claims.sub
        try:
            user_id = int(user_id_str)
        except ValueError:
            raise InvalidTokenError("Refresh token subject (sub) must be an integer user ID.")

        # Using existing repository method which returns a domain Usuario object
        user_domain: Usuario | None = self.user_repository.get_by_id(user_id)

        if not user_domain:
            raise UserNotFoundError(f"User with ID {user_id} not found.")

        if not user_domain.is_active:
            raise UserInactiveError(f"User {user_id} is inactive.")

        user_roles = user_domain.roles if user_domain.roles else []
        additional_claims: Dict[str, Any] = {"roles": user_roles}

        new_access_token = jwt_manager.create_access_token(
            subject=str(user_domain.id),
            additional_claims=additional_claims
        )

        return new_access_token