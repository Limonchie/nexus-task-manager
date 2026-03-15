"""Task repository."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskComment, TaskPriority, TaskStatus


class TaskRepository:
    """Repository for Task and TaskComment models."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, task_id: int, owner_id: int | None = None) -> Task | None:
        """Get task by id, optionally filter by owner."""
        q = select(Task).where(Task.id == task_id)
        if owner_id is not None:
            q = q.where(Task.owner_id == owner_id)
        result = await self.session.execute(q)
        return result.scalars().one_or_none()

    async def list_for_user(
        self,
        owner_id: int,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Task], int]:
        """List tasks for user with filters and pagination. Returns (items, total)."""
        base_filter = select(Task).where(Task.owner_id == owner_id)
        if status is not None:
            base_filter = base_filter.where(Task.status == status)
        if priority is not None:
            base_filter = base_filter.where(Task.priority == priority)

        count_q = select(func.count()).select_from(base_filter.subquery())
        total_result = await self.session.execute(count_q)
        total = total_result.scalar() or 0

        q = base_filter.order_by(Task.updated_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(q)
        tasks = list(result.scalars().all())
        return tasks, total

    async def create(
        self,
        owner_id: int,
        title: str,
        description: str | None = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> Task:
        """Create a new task."""
        task = Task(
            owner_id=owner_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
        )
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def update(self, task: Task, **kwargs: object) -> Task:
        """Update task fields."""
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        """Delete task."""
        await self.session.delete(task)

    async def add_comment(self, task_id: int, author_id: int, content: str) -> TaskComment:
        """Add comment to task."""
        comment = TaskComment(task_id=task_id, author_id=author_id, content=content)
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment)
        return comment

    async def get_comments(self, task_id: int) -> list[TaskComment]:
        """Get comments for task."""
        result = await self.session.execute(
            select(TaskComment).where(TaskComment.task_id == task_id).order_by(TaskComment.created_at)
        )
        return list(result.scalars().all())
