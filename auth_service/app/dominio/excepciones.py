class DomainError(Exception):
    """Base class for domain-specific errors."""
    pass

class AuthError(DomainError):
    """Base class for authentication related errors."""
    pass

class InvalidCredentialsError(AuthError):
    pass

class UserNotFoundError(AuthError):
    pass

class UserInactiveError(AuthError):
    pass

class UserAlreadyExistsError(AuthError):
    pass

class PermissionDeniedError(AuthError):
    pass

class RoleError(DomainError):
    """Base class for role related errors."""
    pass

class RoleNotFoundError(RoleError):
    pass

class RoleAlreadyExistsError(RoleError):
    pass

class InvalidTokenError(AuthError):
    pass
