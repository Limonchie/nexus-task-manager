"""
Роуты аутентификации: регистрация, логин, refresh, logout, me.
Токены в HTTPOnly cookies; опционально Bearer в заголовке.
Auth routes; JWT in HTTPOnly cookies or Authorization: Bearer.
"""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
settings = get_settings()

# Cookie names and options
ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"
COOKIE_OPTIONS = {
    "httponly": True,
    "secure": settings.environment == "prod",
    "samesite": "lax",
    "path": "/",
}
ACCESS_MAX_AGE = settings.access_token_expire_minutes * 60
REFRESH_MAX_AGE = settings.refresh_token_expire_days * 24 * 3600


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=ACCESS_MAX_AGE,
        **COOKIE_OPTIONS,
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        max_age=REFRESH_MAX_AGE,
        **COOKIE_OPTIONS,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path="/")


def _get_token_from_cookie_or_bearer(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
) -> str | None:
    """Get access token from cookie or Authorization Bearer."""
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if token:
        return token
    if credentials:
        return credentials.credentials
    return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: str | None = Depends(_get_token_from_cookie_or_bearer),
) -> "User":
    """Dependency: current user from JWT (cookie or Bearer)."""
    from app.models.user import User

    if not token:
        raise UnauthorizedError("Not authenticated")
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token")
    repo = UserRepository(db)
    user = await repo.get_by_id(int(user_id))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit(f"{get_settings().auth_rate_limit_per_minute}/minute")
async def register(
    request: Request,
    data: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user. Returns user and sets auth cookies."""
    repo = UserRepository(db)
    existing = await repo.get_by_email(data.email)
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await repo.create(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
    )
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh)
    return user


@router.post("/login", response_model=UserResponse)
@limiter.limit(f"{get_settings().auth_rate_limit_per_minute}/minute")
async def login(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Login with email/password. Sets HTTPOnly cookies with tokens."""
    repo = UserRepository(db)
    user = await repo.get_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("User is disabled")
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh)
    return user


@router.post("/refresh", response_model=dict)
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token from cookie. Rotation: new refresh issued."""
    token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not token:
        raise UnauthorizedError("Refresh token required")
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid refresh token")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token")
    repo = UserRepository(db)
    user = await repo.get_by_id(int(user_id))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    _set_auth_cookies(response, access, refresh)
    return {"message": "Tokens refreshed"}


@router.post("/logout")
async def logout(response: Response):
    """Clear auth cookies."""
    _clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: "User" = Depends(get_current_user)):
    """Return current user. Requires valid access token."""
    from app.models.user import User
    return current_user
