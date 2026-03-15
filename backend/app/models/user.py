"""User model."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.task import Task, TaskComment


class UserRole(str, enum.Enum):
    """User role enum."""

    USER = "user"
    ADMIN = "admin"


class User(Base, TimestampMixin):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="owner",
        foreign_keys="Task.owner_id",
    )
    comments: Mapped[list["TaskComment"]] = relationship(
        "TaskComment",
        back_populates="author",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
