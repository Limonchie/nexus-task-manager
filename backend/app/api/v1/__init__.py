"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import auth, users, tasks, websocket

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
