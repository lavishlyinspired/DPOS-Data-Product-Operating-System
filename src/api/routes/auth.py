"""
DPOS Authentication Routes
JWT token generation and user authentication endpoints.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, Annotated
from datetime import timedelta

from src.core.security import (
    Token,
    TokenData,
    User,
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_user,
    generate_api_key
)
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class UserCreate(BaseModel):
    """User registration request."""
    username: str
    email: EmailStr
    password: str
    roles: list[str] = ["user"]


class UserLogin(BaseModel):
    """User login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class APIKeyResponse(BaseModel):
    """API key response."""
    api_key: str
    message: str


# In-memory user store for demo (replace with database in production)
_demo_users = {
    "admin": {
        "id": "user_admin",
        "username": "admin",
        "email": "admin@dpos.local",
        "hashed_password": get_password_hash("admin123"),
        "roles": ["admin", "user"],
        "is_active": True
    },
    "user": {
        "id": "user_default",
        "username": "user",
        "email": "user@dpos.local",
        "hashed_password": get_password_hash("user123"),
        "roles": ["user"],
        "is_active": True
    }
}


def get_user(username: str) -> Optional[dict]:
    """Get user by username (demo implementation)."""
    return _demo_users.get(username)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """
    OAuth2 compatible token login.
    Get an access token using username and password.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(
            f"Failed login attempt for user: {form_data.username}",
            extra={"username": form_data.username}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user["id"],
            "username": user["username"],
            "email": user["email"],
            "roles": user["roles"],
            "scopes": ["read", "write"] if "admin" in user["roles"] else ["read"]
        },
        expires_delta=access_token_expires
    )

    logger.info(
        f"User logged in: {user['username']}",
        extra={"user_id": user["id"], "username": user["username"]}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "roles": user["roles"]
        }
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login with username and password (JSON body).
    Alternative to OAuth2 form-based login.
    """
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        logger.warning(
            f"Failed login attempt for user: {credentials.username}",
            extra={"username": credentials.username}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": user["id"],
            "username": user["username"],
            "email": user["email"],
            "roles": user["roles"],
            "scopes": ["read", "write"] if "admin" in user["roles"] else ["read"]
        },
        expires_delta=access_token_expires
    )

    logger.info(
        f"User logged in: {user['username']}",
        extra={"user_id": user["id"], "username": user["username"]}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "roles": user["roles"]
        }
    )


@router.get("/me")
async def get_current_user_info(
    current_user: Annotated[TokenData, Depends(get_current_user)]
):
    """Get current authenticated user information."""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
        "scopes": current_user.scopes
    }


@router.post("/refresh")
async def refresh_token(
    current_user: Annotated[TokenData, Depends(get_current_user)]
):
    """Refresh the access token."""
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
        data={
            "sub": current_user.user_id,
            "username": current_user.username,
            "email": current_user.email,
            "roles": current_user.roles,
            "scopes": current_user.scopes
        },
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60
    }


@router.post("/api-key", response_model=APIKeyResponse)
async def generate_new_api_key(
    current_user: Annotated[TokenData, Depends(get_current_user)]
):
    """
    Generate a new API key for service-to-service authentication.
    Only admins can generate API keys.
    """
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can generate API keys"
        )

    new_key = generate_api_key()

    logger.info(
        f"API key generated by user: {current_user.username}",
        extra={"user_id": current_user.user_id}
    )

    return APIKeyResponse(
        api_key=new_key,
        message="Store this API key securely. It will not be shown again."
    )


@router.post("/register", response_model=dict)
async def register_user(user_data: UserCreate):
    """
    Register a new user (demo endpoint).
    In production, this should be protected or disabled.
    """
    if user_data.username in _demo_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Create new user
    new_user = {
        "id": f"user_{user_data.username}",
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": get_password_hash(user_data.password),
        "roles": ["user"],  # New users only get 'user' role
        "is_active": True
    }

    _demo_users[user_data.username] = new_user

    logger.info(
        f"New user registered: {user_data.username}",
        extra={"username": user_data.username, "email": user_data.email}
    )

    return {
        "message": "User registered successfully",
        "user_id": new_user["id"],
        "username": new_user["username"]
    }
