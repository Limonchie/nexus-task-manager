"""Tasks API: CRUD, filter, sort, pagination, comments."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, DbSession
from app.core.exceptions import NotFoundError
from app.models.task import TaskPriority, TaskStatus
from app.repositories.task import TaskRepository
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
    TaskCommentCreate,
    TaskCommentResponse,
)
from app.tasks.export import export_tasks_csv

router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    current_user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
):
    """List tasks for current user with server-side filter and pagination."""
    offset = (page - 1) * size
    repo = TaskRepository(db)
    tasks, total = await repo.list_for_user(
        current_user.id,
        status=status,
        priority=priority,
        offset=offset,
        limit=size,
    )
    pages = (total + size - 1) // size if size else 0
    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Create a new task."""
    repo = TaskRepository(db)
    task = await repo.create(
        owner_id=current_user.id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
    )
    return TaskResponse.model_validate(task)


@router.post("/export/csv")
async def trigger_export_csv(
    current_user: CurrentUser,
):
    """Trigger async export of tasks to CSV. Returns task id for status polling."""
    job = export_tasks_csv.delay(current_user.id)
    return {"task_id": job.id, "status": "queued"}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Get task by id (own tasks only)."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id, owner_id=current_user.id)
    if not task:
        raise NotFoundError("Task not found")
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update task (owner only)."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id, owner_id=current_user.id)
    if not task:
        raise NotFoundError("Task not found")
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        await repo.update(task, **update_data)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Delete task (owner only)."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id, owner_id=current_user.id)
    if not task:
        raise NotFoundError("Task not found")
    await repo.delete(task)


@router.get("/{task_id}/comments", response_model=list[TaskCommentResponse])
async def list_comments(
    task_id: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """List comments for a task (own task only)."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id, owner_id=current_user.id)
    if not task:
        raise NotFoundError("Task not found")
    comments = await repo.get_comments(task_id)
    return [TaskCommentResponse.model_validate(c) for c in comments]


@router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=201)
async def add_comment(
    task_id: int,
    data: TaskCommentCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Add comment to task (own task only)."""
    repo = TaskRepository(db)
    task = await repo.get_by_id(task_id, owner_id=current_user.id)
    if not task:
        raise NotFoundError("Task not found")
    comment = await repo.add_comment(task_id, current_user.id, data.content)
    return TaskCommentResponse.model_validate(comment)
