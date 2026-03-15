"""
Точка входа FastAPI-приложения.
Application entrypoint. Creates DB tables on startup, mounts API and health check.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException, app_exception_handler
from app.core.logging import configure_logging, get_logger
from app.db.base_class import Base
from app.db.session import engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте: логирование, создание таблиц. При остановке — закрытие движка.
    # On startup: logging + create tables. On shutdown: dispose engine.
    configure_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("application_started")
    yield
    await engine.dispose()
    logger.info("application_shutdown")


def create_application() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Task list API with auth and WebSocket",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # SlowAPI: лимиты на auth-роутах задаются в auth.py, здесь только app.state и handler
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(api_router)

    app.add_exception_handler(AppException, app_exception_handler)

    return app


app = create_application()


@app.get("/health")
async def health():
    """Проверка живости сервиса (Docker, балансировщик). Liveness probe."""
    return {"status": "ok"}
