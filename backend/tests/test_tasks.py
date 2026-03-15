"""Tests for tasks API: CRUD, list, filter, pagination, comments, export."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_tasks_requires_auth(client: AsyncClient):
    """GET /tasks without auth returns 401."""
    r = await client.get("/api/v1/tasks")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_list_tasks_empty(auth_client: AsyncClient):
    """GET /tasks for user with no tasks returns empty list."""
    r = await auth_client.get("/api/v1/tasks")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["pages"] == 0


@pytest.mark.asyncio
async def test_create_task(auth_client: AsyncClient):
    """POST /tasks creates task and returns 201."""
    r = await auth_client.post(
        "/api/v1/tasks",
        json={"title": "My first task", "description": "Do something"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "My first task"
    assert data["description"] == "Do something"
    assert data["status"] == "todo"
    assert "id" in data
    assert "owner_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_task_by_id(auth_client: AsyncClient):
    """GET /tasks/:id returns task owned by current user."""
    create_r = await auth_client.post(
        "/api/v1/tasks",
        json={"title": "Get me", "description": "Test"},
    )
    assert create_r.status_code == 201
    task_id = create_r.json()["id"]
    r = await auth_client.get(f"/api/v1/tasks/{task_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Get me"


@pytest.mark.asyncio
async def test_get_task_not_found(auth_client: AsyncClient):
    """GET /tasks/99999 returns 404."""
    r = await auth_client.get("/api/v1/tasks/99999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_task(auth_client: AsyncClient):
    """PATCH /tasks/:id updates task."""
    create_r = await auth_client.post(
        "/api/v1/tasks",
        json={"title": "Original", "description": "Desc"},
    )
    task_id = create_r.json()["id"]
    r = await auth_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated title", "status": "in_progress"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Updated title"
    assert r.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_delete_task(auth_client: AsyncClient):
    """DELETE /tasks/:id removes task."""
    create_r = await auth_client.post(
        "/api/v1/tasks",
        json={"title": "To delete"},
    )
    task_id = create_r.json()["id"]
    r = await auth_client.delete(f"/api/v1/tasks/{task_id}")
    assert r.status_code == 204
    get_r = await auth_client.get(f"/api/v1/tasks/{task_id}")
    assert get_r.status_code == 404


@pytest.mark.asyncio
async def test_list_tasks_with_filter(auth_client: AsyncClient):
    """GET /tasks?status=done returns only done tasks."""
    await auth_client.post("/api/v1/tasks", json={"title": "T1", "status": "todo"})
    await auth_client.post("/api/v1/tasks", json={"title": "T2", "status": "done"})
    await auth_client.post("/api/v1/tasks", json={"title": "T3", "status": "done"})
    r = await auth_client.get("/api/v1/tasks", params={"status": "done"})
    assert r.status_code == 200
    assert r.json()["total"] == 2
    assert all(t["status"] == "done" for t in r.json()["items"])


@pytest.mark.asyncio
async def test_list_tasks_pagination(auth_client: AsyncClient):
    """GET /tasks?page=1&size=2 returns first page."""
    for i in range(3):
        await auth_client.post("/api/v1/tasks", json={"title": f"Task {i}"})
    r = await auth_client.get("/api/v1/tasks", params={"page": 1, "size": 2})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2
    assert r.json()["total"] == 3
    assert r.json()["page"] == 1
    assert r.json()["size"] == 2
    assert r.json()["pages"] == 2


@pytest.mark.asyncio
async def test_add_comment(auth_client: AsyncClient):
    """POST /tasks/:id/comments adds comment."""
    create_r = await auth_client.post(
        "/api/v1/tasks",
        json={"title": "Task with comment"},
    )
    task_id = create_r.json()["id"]
    r = await auth_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "First comment"},
    )
    assert r.status_code == 201
    assert r.json()["content"] == "First comment"
    assert r.json()["task_id"] == task_id
    assert "id" in r.json()
    assert "author_id" in r.json()


@pytest.mark.asyncio
async def test_list_comments(auth_client: AsyncClient):
    """GET /tasks/:id/comments returns comments for task."""
    create_r = await auth_client.post(
        "/api/v1/tasks",
        json={"title": "Task"},
    )
    task_id = create_r.json()["id"]
    await auth_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Comment A"},
    )
    await auth_client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "Comment B"},
    )
    r = await auth_client.get(f"/api/v1/tasks/{task_id}/comments")
    assert r.status_code == 200
    comments = r.json()
    assert len(comments) == 2
    contents = [c["content"] for c in comments]
    assert "Comment A" in contents and "Comment B" in contents


@pytest.mark.asyncio
async def test_get_task_other_user_returns_404(
    auth_client: AsyncClient,
    auth_headers: dict,
):
    """User A creates task; User B (Bearer only, no cookies) cannot get it — 404."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    headers = {k: v for k, v in auth_headers.items() if k == "Authorization"}
    create_r = await auth_client.post(
        "/api/v1/tasks",
        json={"title": "User A task"},
    )
    assert create_r.status_code == 201
    task_id = create_r.json()["id"]
    # Отдельный клиент без куков: только Bearer (User B). So we don't send User A's cookies.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client_b:
        r = await client_b.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_export_csv_queues_job(auth_client: AsyncClient):
    """POST /tasks/export/csv returns task_id and status queued (Celery mocked)."""
    with patch("app.api.v1.tasks.export_tasks_csv") as mock_export:
        mock_export.delay.return_value.id = "celery-task-123"
        r = await auth_client.post("/api/v1/tasks/export/csv")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "queued"
    assert data["task_id"] == "celery-task-123"
