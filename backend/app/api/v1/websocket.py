"""WebSocket endpoint for real-time task updates."""

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# In-memory connection manager (use Redis pub/sub in multi-instance setup)
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/tasks")
async def websocket_tasks(websocket: WebSocket):
    """WebSocket for real-time task updates. Client receives broadcast events."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Optional: client can send ping or subscribe to specific channels
            try:
                payload = json.loads(data)
                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning("websocket_error", error=str(e))
        manager.disconnect(websocket)


def get_manager() -> ConnectionManager:
    """Return the global connection manager (for use in services to broadcast)."""
    return manager
