"""Auth schemas."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request body."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Refresh token (optional body; can use cookie)."""

    refresh_token: str | None = None


class TokenPayload(BaseModel):
    """JWT payload (sub, exp, type)."""

    sub: str
    exp: int
    type: str
