"""User schemas."""

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user fields."""

    email: str
    full_name: str | None = None


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str


class UserUpdate(BaseModel):
    """Schema for user update (partial)."""

    full_name: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """User response (no sensitive data)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    role: UserRole


class UserInDB(UserResponse):
    """User with hashed_password (internal)."""

    hashed_password: str
