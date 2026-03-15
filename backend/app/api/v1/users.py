"""Users API: get current user profile, update (and admin list)."""

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession
from app.api.v1.auth import get_current_user
from app.core.exceptions import ForbiddenError
from app.models.user import UserRole
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


def require_admin(user: CurrentUser) -> None:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin only")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Get current user profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update current user profile."""
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.is_active is not None and current_user.role == UserRole.ADMIN:
        current_user.is_active = data.is_active
    elif data.is_active is not None:
        raise ForbiddenError("Cannot change own active status")
    await db.flush()
    await db.refresh(current_user)
    return current_user
