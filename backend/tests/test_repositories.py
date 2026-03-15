"""Unit tests for repositories: UserRepository, TaskRepository."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.task import Task, TaskComment, TaskPriority, TaskStatus
from app.models.user import User, UserRole
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


@pytest.mark.asyncio
async def test_user_repository_get_by_id(db_session: AsyncSession):
    """UserRepository.get_by_id returns user or None."""
    repo = UserRepository(db_session)
    assert await repo.get_by_id(999) is None

    user = User(
        email=_unique_email(),
        hashed_password=get_password_hash("x"),
        full_name="Repo User",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    found = await repo.get_by_id(user.id)
    assert found is not None
    assert found.id == user.id
    assert found.email == user.email


@pytest.mark.asyncio
async def test_user_repository_get_by_email(db_session: AsyncSession):
    """UserRepository.get_by_email returns user or None."""
    repo = UserRepository(db_session)
    assert await repo.get_by_email("nonexistent@x.com") is None

    email = _unique_email()
    user = User(
        email=email,
        hashed_password=get_password_hash("y"),
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    found = await repo.get_by_email(email)
    assert found is not None
    assert found.email == email


@pytest.mark.asyncio
async def test_user_repository_create(db_session: AsyncSession):
    """UserRepository.create persists user and returns it."""
    repo = UserRepository(db_session)
    user = await repo.create(
        email=_unique_email(),
        hashed_password=get_password_hash("z"),
        full_name="New One",
    )
    await db_session.commit()
    assert user.id is not None
    assert user.full_name == "New One"


@pytest.mark.asyncio
async def test_task_repository_create_and_get(db_session: AsyncSession):
    """TaskRepository.create and get_by_id work."""
    user = User(
        email=_unique_email(),
        hashed_password=get_password_hash("p"),
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    repo = TaskRepository(db_session)
    task = await repo.create(
        owner_id=user.id,
        title="Repo task",
        description="Desc",
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
    )
    await db_session.commit()
    assert task.id is not None
    assert task.title == "Repo task"

    found = await repo.get_by_id(task.id, owner_id=user.id)
    assert found is not None
    assert found.title == "Repo task"
    assert await repo.get_by_id(task.id, owner_id=user.id + 999) is None


@pytest.mark.asyncio
async def test_task_repository_list_for_user(db_session: AsyncSession):
    """TaskRepository.list_for_user returns paginated list and total."""
    user = User(
        email=_unique_email(),
        hashed_password=get_password_hash("p"),
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    repo = TaskRepository(db_session)
    tasks, total = await repo.list_for_user(user.id, offset=0, limit=10)
    assert tasks == []
    assert total == 0

    await repo.create(owner_id=user.id, title="A", status=TaskStatus.TODO)
    await repo.create(owner_id=user.id, title="B", status=TaskStatus.DONE)
    await db_session.commit()

    tasks, total = await repo.list_for_user(user.id, offset=0, limit=10)
    assert len(tasks) == 2
    assert total == 2

    tasks_filtered, total_filtered = await repo.list_for_user(
        user.id, status=TaskStatus.DONE, offset=0, limit=10
    )
    assert len(tasks_filtered) == 1
    assert tasks_filtered[0].status == TaskStatus.DONE
    assert total_filtered == 1


@pytest.mark.asyncio
async def test_task_repository_add_comment(db_session: AsyncSession):
    """TaskRepository.add_comment creates comment."""
    user = User(
        email=_unique_email(),
        hashed_password=get_password_hash("p"),
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    repo = TaskRepository(db_session)
    task = await repo.create(owner_id=user.id, title="T")
    await db_session.commit()

    comment = await repo.add_comment(task.id, user.id, "Hello")
    await db_session.commit()
    assert comment.id is not None
    assert comment.content == "Hello"
    assert comment.task_id == task.id
    assert comment.author_id == user.id

    comments = await repo.get_comments(task.id)
    assert len(comments) == 1
    assert comments[0].content == "Hello"
