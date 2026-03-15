"""Task and TaskComment schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    """Base task fields."""

    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskCreate(TaskBase):
    """Schema for creating a task."""

    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task (partial)."""

    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None


class TaskResponse(TaskBase):
    """Task response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Paginated task list."""

    items: list[TaskResponse]
    total: int
    page: int
    size: int
    pages: int


class TaskCommentBase(BaseModel):
    """Base comment fields."""

    content: str


class TaskCommentCreate(TaskCommentBase):
    """Schema for creating a comment."""

    pass


class TaskCommentResponse(TaskCommentBase):
    """Comment response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    created_at: datetime
