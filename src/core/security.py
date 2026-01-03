"""
DPOS Security Module
JWT Authentication, API Key validation, and security utilities.
"""
from datetime import datetime, timedelta, UTC
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import secrets

from src.core.config import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class Token(BaseModel):
    """JWT Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: list[str] = []
    scopes: list[str] = []


class User(BaseModel):
    """User model for authentication."""
    id: str
    username: str
    email: Optional[str] = None
    roles: list[str] = []
    is_active: bool = True
    is_superuser: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenData(
            user_id=user_id,
            username=payload.get("username"),
            email=payload.get("email"),
            roles=payload.get("roles", []),
            scopes=payload.get("scopes", [])
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    api_key: Annotated[Optional[str], Security(api_key_header)]
) -> Optional[TokenData]:
    """
    Get current user from JWT token or API key (optional - returns None if not authenticated).
    Use this for endpoints that work with or without auth.
    """
    # Try JWT token first
    if credentials and credentials.credentials:
        try:
            return decode_token(credentials.credentials)
        except HTTPException:
            pass

    # Try API key
    if api_key and settings.api_key and secrets.compare_digest(api_key, settings.api_key):
        return TokenData(
            user_id="api_key_user",
            username="api_service",
            roles=["service"],
            scopes=["read", "write"]
        )

    return None


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    api_key: Annotated[Optional[str], Security(api_key_header)]
) -> TokenData:
    """
    Get current user from JWT token or API key (required).
    Use this for protected endpoints.
    """
    user = await get_current_user_optional(credentials, api_key)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: Annotated[TokenData, Depends(get_current_user)]
) -> TokenData:
    """Get current active user."""
    # In production, check if user is active in database
    return current_user


def require_roles(*required_roles: str):
    """
    Dependency factory that requires specific roles.

    Usage:
        @app.get("/admin", dependencies=[Depends(require_roles("admin"))])
    """
    async def role_checker(
        current_user: Annotated[TokenData, Depends(get_current_user)]
    ) -> TokenData:
        for role in required_roles:
            if role in current_user.roles:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required roles: {required_roles}"
        )

    return role_checker


def require_scopes(*required_scopes: str):
    """
    Dependency factory that requires specific scopes.

    Usage:
        @app.get("/data", dependencies=[Depends(require_scopes("read:data"))])
    """
    async def scope_checker(
        current_user: Annotated[TokenData, Depends(get_current_user)]
    ) -> TokenData:
        for scope in required_scopes:
            if scope not in current_user.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scope: {scope}"
                )
        return current_user

    return scope_checker


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception."""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )
