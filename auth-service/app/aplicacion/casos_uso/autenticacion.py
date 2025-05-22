from auth_service.app.aplicacion.servicios import AuthService
# Using API schemas as request DTOs for these use cases
from auth_service.app.interfaces.api.v1.esquemas import LoginRequest, RefreshTokenRequest 
from auth_service.app.aplicacion.dto import TokenPairDTO

class LoginUseCase:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    async def execute(self, login_request_data: LoginRequest) -> TokenPairDTO:
        # The AuthService.login method already handles exceptions appropriately
        return await self.auth_service.login(
            email=login_request_data.email, 
            password=login_request_data.password
        )

class RefreshTokenUseCase:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    async def execute(self, refresh_token_request_data: RefreshTokenRequest) -> str:
        # The AuthService.refresh_access_token method already handles exceptions
        # It returns a new access token string, not a TokenPairDTO.
        # The return type of this method should be str to match the service method.
        return await self.auth_service.refresh_access_token(
            refresh_token_str=refresh_token_request_data.refresh_token
        )
