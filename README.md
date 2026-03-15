# Nexus Task Manager

Веб-приложение для учёта задач с авторизацией, комментариями и экспортом.  
Task list app with auth, comments, and CSV export.

---

# English

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Project structure](#project-structure)
- [Installation and launch](#installation-and-launch)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Development](#development)
- [Testing](#testing)
- [Docker and deployment](#docker-and-deployment)
- [CI/CD](#cicd)
- [Security](#security)

---

## Overview

An application for personal or team tasks: backend on FastAPI, front on React.  
Backend: async Python (FastAPI), JWT in HttpOnly cookies, WebSocket, Celery for background tasks. Frontend: React, TypeScript, Vite.

**What it does:**

- User registration and authentication with JWT (access + refresh tokens in HTTPOnly cookies)
- Full CRUD for tasks with filtering by status/priority and server-side pagination
- Comments on tasks
- Real-time task updates via WebSocket
- Asynchronous export of tasks to CSV (Celery)
- Role-based access (Admin / User); each user manages only their own tasks

---

## Architecture

High-level architecture:

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                      CLIENT (Browser)                    │
                    └─────────────────────────────┬─────────────────────────┘
                                                    │
                    ┌───────────────────────────────▼───────────────────────────┐
                    │  Frontend (React 18 + TypeScript + Vite)                    │
                    │  - TanStack Query (server state)                            │
                    │  - Zustand (client state)                                   │
                    │  - React Router v6                                          │
                    └───────────────────────────────┬───────────────────────────┘
                                                    │ HTTP / WebSocket
                    ┌───────────────────────────────▼───────────────────────────┐
                    │  Nginx (reverse proxy, WebSocket upgrade)                   │
                    └───────────────────────────────┬───────────────────────────┘
                                                    │
                    ┌───────────────────────────────▼───────────────────────────┐
                    │  Backend (FastAPI)                                          │
                    │  - REST API v1 (auth, users, tasks)                         │
                    │  - WebSocket /api/v1/ws/tasks                               │
                    │  - Rate limiting (SlowAPI) on auth endpoints                │
                    └───┬─────────────────────┬─────────────────────┬─────────────┘
                        │                     │                     │
            ┌───────────▼──────────┐ ┌───────▼──────┐ ┌────────────▼────────────┐
            │  PostgreSQL (prod)   │ │    Redis     │ │  Celery Worker         │
            │  SQLite (dev)        │ │  - Sessions  │ │  - export_tasks_csv    │
            │  SQLAlchemy 2.0     │ │  - Broker    │ │  - future jobs         │
            └─────────────────────┘ └──────────────┘ └─────────────────────────┘
```

**Data flow:**

- **Authentication:** User logs in → backend checks credentials → issues access + refresh JWT → cookies set (HTTPOnly, SameSite=Lax). Each API request sends cookies; optional Bearer token is also supported.
- **Tasks:** Frontend uses TanStack Query to fetch tasks from `/api/v1/tasks` with query params (page, size, status, priority). Mutations (create/update/delete) invalidate cache and refetch.
- **Real-time:** Optional WebSocket connection to `/api/v1/ws/tasks` for broadcast notifications (e.g. task created/updated by another tab or future integrations).
- **Export:** Frontend calls POST `/api/v1/tasks/export/csv` → backend enqueues Celery task → returns `task_id`; client can poll for result or download when ready.

---

## Features

| Feature | Description |
|--------|-------------|
| **Registration** | Email + password + optional full name. Password hashed with bcrypt. |
| **Login** | Email/password; returns user object and sets access + refresh tokens in HTTPOnly cookies. |
| **Refresh token** | POST `/api/v1/auth/refresh` with refresh token in cookie; new access + refresh issued (rotation). |
| **Logout** | Clears auth cookies. |
| **Rate limiting** | Login and register endpoints limited (e.g. 5 req/min) to prevent brute force. |
| **Tasks CRUD** | Create, read, update, delete tasks. Only the owner can modify their tasks. |
| **Filtering** | List tasks by `status` (todo, in_progress, done, cancelled) and `priority` (low, medium, high, urgent). |
| **Pagination** | Server-side: `page`, `size` (default 20, max 100). |
| **Comments** | Add and list comments per task; stored in `task_comments` table. |
| **WebSocket** | Connect to `/api/v1/ws/tasks` to receive broadcast messages (e.g. task updates). |
| **Export CSV** | POST to `/api/v1/tasks/export/csv` enqueues a Celery job; returns `task_id` for status polling. |
| **Roles** | `user` (default) and `admin`; admin can manage user active flag (future: admin-only routes). |

---

## Technology stack

| Layer | Technology | Notes |
|-------|------------|--------|
| **Backend** | FastAPI | Async endpoints, OpenAPI (Swagger) at `/docs`. |
| **ORM** | SQLAlchemy 2.0 | Async engine/session; Repository pattern over models. |
| **Database** | PostgreSQL (prod) / SQLite (dev) | Via `DATABASE_URL`. |
| **Auth** | JWT (python-jose), bcrypt (passlib) | Access + refresh; tokens in HTTPOnly cookies. |
| **Cache / Queue** | Redis | Celery broker and result backend; optional cache. |
| **Background jobs** | Celery | e.g. `export_tasks_csv`. |
| **Rate limiting** | SlowAPI | Per-IP limits on auth routes. |
| **Logging** | structlog | Structured logs; optional JSON output. |
| **Frontend** | React 18, TypeScript | Strict TS, no `any`. |
| **Build** | Vite | Fast HMR and production build. |
| **Server state** | TanStack Query | Fetch, cache, mutations for API. |
| **Client state** | Zustand | Auth state (with persist). |
| **Routing** | React Router v6 | Protected routes for authenticated users. |
| **Styling** | Tailwind CSS | Utility-first; ready for Shadcn/ui. |
| **DevOps** | Docker, Docker Compose | Backend, frontend, DB, Redis, Celery. |
| **CI** | GitHub Actions | Lint and test on push/PR. |

---

## Project structure

```
nexus-task-manager/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py              # Shared dependencies (get_db, CurrentUser, pagination)
│   │   │   └── v1/
│   │   │       ├── __init__.py      # Router aggregation (auth, users, tasks, websocket)
│   │   │       ├── auth.py          # Register, login, refresh, logout, get current user
│   │   │       ├── users.py         # GET/PATCH /users/me
│   │   │       ├── tasks.py         # Tasks CRUD, comments, export/csv
│   │   │       └── websocket.py     # WebSocket /ws/tasks
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic Settings from env
│   │   │   ├── security.py         # Password hashing, JWT create/decode
│   │   │   ├── exceptions.py       # AppException, handlers
│   │   │   └── logging.py          # structlog setup
│   │   ├── db/
│   │   │   ├── base_class.py        # SQLAlchemy Base, TimestampMixin
│   │   │   └── session.py          # Async engine, session factory, get_db
│   │   ├── models/
│   │   │   ├── user.py             # User (id, email, hashed_password, role, ...)
│   │   │   └── task.py             # Task, TaskComment
│   │   ├── repositories/
│   │   │   ├── user.py             # UserRepository (get_by_id, get_by_email, create)
│   │   │   └── task.py             # TaskRepository (CRUD, list_for_user, comments)
│   │   ├── schemas/
│   │   │   ├── user.py             # UserCreate, UserUpdate, UserResponse
│   │   │   ├── task.py             # TaskCreate, TaskUpdate, TaskResponse, TaskListResponse, comments
│   │   │   └── auth.py             # LoginRequest, TokenPayload, etc.
│   │   ├── tasks/
│   │   │   ├── celery_app.py       # Celery instance
│   │   │   └── export.py           # export_tasks_csv task
│   │   └── main.py                # FastAPI app, CORS, lifespan, health
│   ├── tests/
│   │   ├── conftest.py            # Pytest fixtures, test DB, async client
│   │   └── test_health.py         # Health check test
│   ├── alembic/                   # Migrations (optional; tables created on startup in dev)
│   ├── pyproject.toml
│   ├── .env.example
│   ├── Dockerfile
│   └── run.py                     # uvicorn entry for local run
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts          # api.get/post/patch/delete, types (User, Task, TaskListResponse)
│   │   ├── features/
│   │   │   ├── auth/              # LoginPage, RegisterPage
│   │   │   ├── dashboard/          # DashboardLayout (header, logout, Outlet)
│   │   │   └── tasks/              # TaskListPage (list, create, update status, delete, filters)
│   │   ├── stores/
│   │   │   └── authStore.ts       # Zustand store: user, logout, fetchMe, isAuthenticated
│   │   ├── App.tsx                # Routes, ProtectedRoute
│   │   ├── main.tsx               # QueryClient, BrowserRouter, root render
│   │   └── index.css              # Tailwind imports
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts            # Proxy /api, /ws to backend
│   ├── tailwind.config.js
│   ├── Dockerfile                 # Multi-stage: npm build → nginx serve
│   └── nginx.conf                 # SPA fallback, proxy to backend
├── infra/
│   └── docker-compose.yml        # backend, frontend, db (PostgreSQL), redis, celery
├── .github/
│   └── workflows/
│       └── ci.yml                # Backend: ruff, pytest; Frontend: npm run build
├── .gitignore
└── README.md
```

---

## Installation and launch

### Prerequisites

- **Python 3.11+** (backend)
- **Node.js 20+** and npm (frontend)
- **Docker and Docker Compose** (optional, for full stack)
- **Redis** (optional; required for Celery; backend runs without it if you don’t use export)

### Option 1: Backend only (local)

```bash
cd nexus-task-manager/backend
cp .env.example .env
# Edit .env: set SECRET_KEY (min 32 characters). Optionally set DATABASE_URL, REDIS_URL.
pip install -e .
uvicorn app.main:app --reload --port 8000
```

- API base: **http://localhost:8000**
- OpenAPI docs: **http://localhost:8000/docs**
- Health: **http://localhost:8000/health**

Without Redis, the export CSV endpoint will fail when enqueueing; the rest of the API works.

### Option 2: Frontend only (local, with backend running)

```bash
cd nexus-task-manager/frontend
npm install
npm run dev
```

- App: **http://localhost:5173**
- Vite proxies `/api` and `/ws` to `http://localhost:8000` (see `vite.config.ts`). Start the backend as in Option 1.

### Option 3: Full stack with Docker Compose

```bash
cd nexus-task-manager/infra
docker compose up -d
```

- Frontend: **http://localhost:5173**
- Backend: **http://localhost:8000**
- PostgreSQL and Redis are started by Compose. Set `SECRET_KEY` via env or `.env` in `infra/` if needed.

---

## Configuration

All backend configuration is via environment variables (see `backend/.env.example`).

| Variable | Required | Default | Description |
|----------|----------|--------|-------------|
| `SECRET_KEY` | Yes | — | Secret for JWT signing (min 32 characters). |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./nexus.db` | Async SQLAlchemy URL (e.g. `postgresql+asyncpg://user:pass@host:5432/db`). |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection for Celery broker/backend. |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/1` | Celery broker URL. |
| `CORS_ORIGINS` | No | `http://localhost:5173,http://localhost:3000` | Comma-separated origins for CORS. |
| `ENVIRONMENT` | No | `dev` | `dev` \| `staging` \| `prod` (affects cookie `secure`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token TTL. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token TTL. |
| `AUTH_RATE_LIMIT_PER_MINUTE` | No | `5` | Max requests per minute for login/register. |
| `LOG_LEVEL` | No | `INFO` | Logging level. |
| `LOG_JSON` | No | `false` | If true, logs are emitted as JSON (e.g. for production). |

---

## API reference

Base URL: `/api/v1`.

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register; body: `{ "email", "password", "full_name"? }`. Sets cookies. |
| POST | `/auth/login` | Login; form: `username` (email), `password`. Sets cookies. |
| POST | `/auth/refresh` | Refresh tokens; uses refresh token from cookie. Rotation. |
| POST | `/auth/logout` | Clear auth cookies. |
| GET | `/auth/me` | Current user (requires valid access token in cookie or Bearer). |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/me` | Current user profile. |
| PATCH | `/users/me` | Update profile; body: `{ "full_name"? }`. |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tasks` | List tasks; query: `page`, `size`, `status`, `priority`. |
| POST | `/tasks` | Create task; body: `{ "title", "description"? }`. |
| GET | `/tasks/{id}` | Get task by id (owner only). |
| PATCH | `/tasks/{id}` | Update task (owner only). |
| DELETE | `/tasks/{id}` | Delete task (owner only). |
| POST | `/tasks/export/csv` | Enqueue CSV export; returns `{ "task_id", "status": "queued" }`. |
| GET | `/tasks/{id}/comments` | List comments. |
| POST | `/tasks/{id}/comments` | Add comment; body: `{ "content" }`. |

### WebSocket

- **URL:** `ws://<host>/api/v1/ws/tasks` (or via same origin as frontend).  
- Accepts connections; can broadcast task update events. Client can send `{"type":"ping"}` and receive `{"type":"pong"}`.

### Health

- **GET** `/health` — returns `{"status":"ok"}` (no auth). Used by Docker/load balancer.

---

## Development

- **Backend:** after changing code, uvicorn with `--reload` restarts automatically. Use `ruff` for linting and `mypy` for type checking if configured.
- **Frontend:** Vite HMR; run `npm run dev`. Use ESLint and TypeScript strict mode.
- **Database:** For schema changes, use Alembic migrations (`alembic revision`, `alembic upgrade head`). In dev, the app creates tables on startup if they don’t exist.
- **OpenAPI:** Generate client types from `http://localhost:8000/openapi.json` (e.g. openapi-typescript-codegen) to keep frontend types in sync with the API.

---

## Testing

- **Backend:** From `backend/`: run `pytest`. Tests use a test DB (see `tests/conftest.py`); set `SECRET_KEY` and `DATABASE_URL` in env or in conftest. Target coverage >80%.
- **Frontend:** Use Vitest and React Testing Library for unit tests; add Playwright for E2E.  
- **CI:** GitHub Actions runs backend lint (e.g. ruff) and tests, and frontend `npm run build`.

---

## Docker and deployment

- **Images:** Backend and frontend have Dockerfiles; frontend is multi-stage (build with Node, serve with nginx).
- **Compose:** `infra/docker-compose.yml` defines services: backend, frontend, db (PostgreSQL), redis, celery. Backend and celery use the same codebase; celery runs `celery -A app.tasks.celery_app worker`.
- **Production:** Use a strong `SECRET_KEY`, `ENVIRONMENT=prod`, and a real PostgreSQL URL. Ensure Redis is available for Celery. Configure Nginx or a load balancer in front; enable HTTPS and set `secure` cookies.

---

## CI/CD

- **Workflow:** `.github/workflows/ci.yml` runs on push/PR to `main` and `develop`.
- **Backend job:** install deps, run ruff, run pytest (with coverage; may be configured to fail below 80%).
- **Frontend job:** `npm ci`, `npm run build`.
- No deployment step in the template; add a job to deploy to your server or PaaS when needed.

---

## Security

- Passwords hashed with **bcrypt** (configurable rounds).
- **JWT** access and refresh tokens; stored in **HTTPOnly** cookies to reduce XSS risk.
- **Refresh token rotation** on each refresh.
- **CORS** restricted to configured origins.
- **Rate limiting** on login and register.
- **Input validation** via Pydantic on all request bodies and query params.
- **SQL injection** mitigated by using SQLAlchemy ORM (parameterized queries).  
- Do not commit `.env` or secrets; use env vars or a secrets manager in production.


---

# Русский

## Содержание

- [Обзор](#обзор)
- [Архитектура](#архитектура-1)
- [Функциональность](#функциональность)
- [Технологический стек](#технологический-стек)
- [Структура проекта](#структура-проекта)
- [Установка и запуск](#установка-и-запуск)
- [Конфигурация](#конфигурация-1)
- [Справочник API](#справочник-api)
- [Разработка](#разработка)
- [Тестирование](#тестирование)
- [Docker и развёртывание](#docker-и-развёртывание)
- [CI/CD](#cicd-1)
- [Безопасность](#безопасность)

---

## Обзор

Nexus Task Manager — полнофункциональное веб-приложение для управления личными или командными задачами. Проект демонстрирует современные подходы к backend и frontend: асинхронный Python (FastAPI), аутентификация JWT с HTTPOnly-куками, обновления в реальном времени по WebSocket, фоновые задачи (Celery) и реактивный React-интерфейс на TypeScript.

**Основные возможности:**

- Регистрация и аутентификация пользователей по JWT (access- и refresh-токены в HTTPOnly-куках)
- Полный CRUD по задачам с фильтрацией по статусу/приоритету и серверной пагинацией
- Комментарии к задачам
- Обновления по задачам в реальном времени через WebSocket
- Асинхронный экспорт задач в CSV (Celery)
- Роли (Admin / User); каждый пользователь управляет только своими задачами

---

## Архитектура

Общая схема:

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                   КЛИЕНТ (браузер)                        │
                    └─────────────────────────────┬─────────────────────────┘
                                                    │
                    ┌───────────────────────────────▼───────────────────────────┐
                    │  Frontend (React 18 + TypeScript + Vite)                    │
                    │  - TanStack Query (серверное состояние)                    │
                    │  - Zustand (клиентское состояние)                           │
                    │  - React Router v6                                          │
                    └───────────────────────────────┬───────────────────────────┘
                                                    │ HTTP / WebSocket
                    ┌───────────────────────────────▼───────────────────────────┐
                    │  Nginx (обратный прокси, апгрейд WebSocket)               │
                    └───────────────────────────────┬───────────────────────────┘
                                                    │
                    ┌───────────────────────────────▼───────────────────────────┐
                    │  Backend (FastAPI)                                          │
                    │  - REST API v1 (auth, users, tasks)                         │
                    │  - WebSocket /api/v1/ws/tasks                               │
                    │  - Ограничение частоты запросов (SlowAPI) на auth           │
                    └───┬─────────────────────┬─────────────────────┬─────────────┘
                        │                     │                     │
            ┌───────────▼──────────┐ ┌───────▼──────┐ ┌────────────▼────────────┐
            │  PostgreSQL (prod)   │ │    Redis     │ │  Celery Worker          │
            │  SQLite (dev)       │ │  - сессии    │ │  - export_tasks_csv     │
            │  SQLAlchemy 2.0     │ │  - брокер    │ │  - прочие задачи        │
            └─────────────────────┘ └──────────────┘ └─────────────────────────┘
```

**Поток данных:**

- **Аутентификация:** пользователь логинится → backend проверяет учётные данные → выдаёт access- и refresh-JWT → выставляет куки (HTTPOnly, SameSite=Lax). Каждый запрос к API отправляет куки; дополнительно поддерживается заголовок Bearer.
- **Задачи:** фронтенд через TanStack Query запрашивает задачи с `/api/v1/tasks` с параметрами (page, size, status, priority). Мутации (создание/обновление/удаление) инвалидируют кэш и перезапрашивают данные.
- **Real-time:** при необходимости клиент подключается по WebSocket к `/api/v1/ws/tasks` для получения рассылок (например, обновления задач из другой вкладки или будущих интеграций).
- **Экспорт:** фронтенд вызывает POST `/api/v1/tasks/export/csv` → backend ставит задачу в очередь Celery → возвращает `task_id`; клиент может опрашивать статус или скачать файл по готовности.

---

## Функциональность

| Функция | Описание |
|--------|----------|
| **Регистрация** | Email, пароль и по желанию имя. Пароль хешируется bcrypt. |
| **Вход** | Email/пароль; возвращается объект пользователя и выставляются access- и refresh-токены в HTTPOnly-куках. |
| **Обновление токена** | POST `/api/v1/auth/refresh` с refresh-токеном в куке; выдаётся новая пара токенов (ротация). |
| **Выход** | Очистка auth-куков. |
| **Ограничение частоты** | Эндпоинты входа и регистрации ограничены (например, 5 запросов/мин) для защиты от перебора. |
| **CRUD задач** | Создание, чтение, обновление и удаление задач. Изменять может только владелец. |
| **Фильтрация** | Список задач по `status` (todo, in_progress, done, cancelled) и `priority` (low, medium, high, urgent). |
| **Пагинация** | Серверная: параметры `page`, `size` (по умолчанию 20, макс. 100). |
| **Комментарии** | Добавление и просмотр комментариев к задаче; хранятся в таблице `task_comments`. |
| **WebSocket** | Подключение к `/api/v1/ws/tasks` для получения рассылок (например, обновления задач). |
| **Экспорт CSV** | POST на `/api/v1/tasks/export/csv` ставит задачу Celery в очередь; возвращается `task_id` для опроса статуса. |
| **Роли** | `user` (по умолчанию) и `admin`; админ может управлять флагом активности пользователя (в перспективе — маршруты только для админа). |

---

## Технологический стек

| Слой | Технология | Примечание |
|------|------------|------------|
| **Backend** | FastAPI | Асинхронные эндпоинты, OpenAPI (Swagger) на `/docs`. |
| **ORM** | SQLAlchemy 2.0 | Асинхронный движок и сессии; паттерн Repository поверх моделей. |
| **БД** | PostgreSQL (prod) / SQLite (dev) | Через `DATABASE_URL`. |
| **Аутентификация** | JWT (python-jose), bcrypt (passlib) | Access и refresh; токены в HTTPOnly-куках. |
| **Кэш / Очередь** | Redis | Брокер и backend результатов Celery; при необходимости кэш. |
| **Фоновые задачи** | Celery | Например, `export_tasks_csv`. |
| **Ограничение частоты** | SlowAPI | Лимиты по IP на маршрутах auth. |
| **Логирование** | structlog | Структурированные логи; при необходимости вывод в JSON. |
| **Frontend** | React 18, TypeScript | Строгий TS, без `any`. |
| **Сборка** | Vite | Быстрый HMR и production-сборка. |
| **Серверное состояние** | TanStack Query | Запросы, кэш и мутации к API. |
| **Клиентское состояние** | Zustand | Состояние авторизации (с persist). |
| **Роутинг** | React Router v6 | Защищённые маршруты для авторизованных пользователей. |
| **Стили** | Tailwind CSS | Утилитарный подход; готовность к Shadcn/ui. |
| **DevOps** | Docker, Docker Compose | Backend, frontend, БД, Redis, Celery. |
| **CI** | GitHub Actions | Линт и тесты при push/PR. |

---

## Структура проекта

```
nexus-task-manager/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py              # Общие зависимости (get_db, CurrentUser, пагинация)
│   │   │   └── v1/
│   │   │       ├── __init__.py       # Агрегация роутеров (auth, users, tasks, websocket)
│   │   │       ├── auth.py           # Регистрация, вход, refresh, выход, текущий пользователь
│   │   │       ├── users.py          # GET/PATCH /users/me
│   │   │       ├── tasks.py          # CRUD задач, комментарии, export/csv
│   │   │       └── websocket.py      # WebSocket /ws/tasks
│   │   ├── core/
│   │   │   ├── config.py             # Pydantic Settings из env
│   │   │   ├── security.py          # Хеширование паролей, создание/декодирование JWT
│   │   │   ├── exceptions.py        # AppException, обработчики
│   │   │   └── logging.py           # Настройка structlog
│   │   ├── db/
│   │   │   ├── base_class.py         # SQLAlchemy Base, TimestampMixin
│   │   │   └── session.py           # Асинхронный движок, фабрика сессий, get_db
│   │   ├── models/
│   │   │   ├── user.py              # User (id, email, hashed_password, role, ...)
│   │   │   └── task.py              # Task, TaskComment
│   │   ├── repositories/
│   │   │   ├── user.py              # UserRepository (get_by_id, get_by_email, create)
│   │   │   └── task.py              # TaskRepository (CRUD, list_for_user, комментарии)
│   │   ├── schemas/
│   │   │   ├── user.py              # UserCreate, UserUpdate, UserResponse
│   │   │   ├── task.py              # TaskCreate, TaskUpdate, TaskResponse, TaskListResponse, комментарии
│   │   │   └── auth.py              # LoginRequest, TokenPayload и др.
│   │   ├── tasks/
│   │   │   ├── celery_app.py        # Экземпляр Celery
│   │   │   └── export.py            # Задача export_tasks_csv
│   │   └── main.py                  # FastAPI-приложение, CORS, lifespan, health
│   ├── tests/
│   │   ├── conftest.py              # Фикстуры pytest, тестовая БД, async-клиент
│   │   └── test_health.py          # Тест health check
│   ├── alembic/                     # Миграции (опционально; в dev таблицы создаются при старте)
│   ├── pyproject.toml
│   ├── .env.example
│   ├── Dockerfile
│   └── run.py                       # Точка входа uvicorn для локального запуска
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts            # api.get/post/patch/delete, типы (User, Task, TaskListResponse)
│   │   ├── features/
│   │   │   ├── auth/                # LoginPage, RegisterPage
│   │   │   ├── dashboard/           # DashboardLayout (шапка, выход, Outlet)
│   │   │   └── tasks/               # TaskListPage (список, создание, смена статуса, удаление, фильтры)
│   │   ├── stores/
│   │   │   └── authStore.ts         # Zustand: user, logout, fetchMe, isAuthenticated
│   │   ├── App.tsx                  # Маршруты, ProtectedRoute
│   │   ├── main.tsx                 # QueryClient, BrowserRouter, рендер корня
│   │   └── index.css                # Подключение Tailwind
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts               # Прокси /api, /ws на backend
│   ├── tailwind.config.js
│   ├── Dockerfile                   # Многоэтапная сборка: npm build → раздача через nginx
│   └── nginx.conf                   # SPA fallback, прокси на backend
├── infra/
│   └── docker-compose.yml           # backend, frontend, db (PostgreSQL), redis, celery
├── .github/
│   └── workflows/
│       └── ci.yml                   # Backend: ruff, pytest; Frontend: npm run build
├── .gitignore
└── README.md
```

---

## Установка и запуск

### Требования

- **Python 3.11+** (backend)
- **Node.js 20+** и npm (frontend)
- **Docker и Docker Compose** (опционально, для полного стека)
- **Redis** (опционально; нужен для Celery; backend работает без него, если не использовать экспорт)

### Вариант 1: Только backend (локально)

```bash
cd nexus-task-manager/backend
cp .env.example .env
# Отредактировать .env: указать SECRET_KEY (минимум 32 символа). По желанию DATABASE_URL, REDIS_URL.
pip install -e .
uvicorn app.main:app --reload --port 8000
```

- Базовый URL API: **http://localhost:8000**
- Документация OpenAPI: **http://localhost:8000/docs**
- Проверка здоровья: **http://localhost:8000/health**

Без Redis эндпоинт экспорта в CSV будет падать при постановке задачи в очередь; остальной API работает.

### Вариант 2: Только frontend (локально при запущенном backend)

```bash
cd nexus-task-manager/frontend
npm install
npm run dev
```

- Приложение: **http://localhost:5173**
- Vite проксирует `/api` и `/ws` на `http://localhost:8000` (см. `vite.config.ts`). Backend должен быть запущен, как в варианте 1.

### Вариант 3: Полный стек через Docker Compose

```bash
cd nexus-task-manager/infra
docker compose up -d
```

- Frontend: **http://localhost:5173**
- Backend: **http://localhost:8000**
- PostgreSQL и Redis поднимаются Compose. При необходимости задайте `SECRET_KEY` через env или `.env` в каталоге `infra/`.

---

## Конфигурация

Вся конфигурация backend задаётся переменными окружения (см. `backend/.env.example`).

| Переменная | Обязательна | По умолчанию | Описание |
|------------|-------------|--------------|-----------|
| `SECRET_KEY` | Да | — | Секрет для подписи JWT (мин. 32 символа). |
| `DATABASE_URL` | Нет | `sqlite+aiosqlite:///./nexus.db` | URL асинхронного SQLAlchemy (напр. `postgresql+asyncpg://user:pass@host:5432/db`). |
| `REDIS_URL` | Нет | `redis://localhost:6379/0` | Подключение к Redis для брокера/backend Celery. |
| `CELERY_BROKER_URL` | Нет | `redis://localhost:6379/1` | URL брокера Celery. |
| `CORS_ORIGINS` | Нет | `http://localhost:5173,http://localhost:3000` | Разрешённые источники для CORS (через запятую). |
| `ENVIRONMENT` | Нет | `dev` | `dev` \| `staging` \| `prod` (влияет на флаг `secure` у куков). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Нет | `30` | Время жизни access-токена. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Нет | `7` | Время жизни refresh-токена. |
| `AUTH_RATE_LIMIT_PER_MINUTE` | Нет | `5` | Макс. запросов в минуту на вход/регистрацию. |
| `LOG_LEVEL` | Нет | `INFO` | Уровень логирования. |
| `LOG_JSON` | Нет | `false` | Если true — логи в формате JSON (например, для продакшена). |

---

## Справочник API

Базовый URL: `/api/v1`.

### Аутентификация

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/auth/register` | Регистрация; тело: `{ "email", "password", "full_name"? }`. Устанавливает куки. |
| POST | `/auth/login` | Вход; форма: `username` (email), `password`. Устанавливает куки. |
| POST | `/auth/refresh` | Обновление токенов; используется refresh-токен из куки. Ротация. |
| POST | `/auth/logout` | Очистка auth-куков. |
| GET | `/auth/me` | Текущий пользователь (нужен валидный access-токен в куке или Bearer). |

### Пользователи

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/users/me` | Профиль текущего пользователя. |
| PATCH | `/users/me` | Обновление профиля; тело: `{ "full_name"? }`. |

### Задачи

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/tasks` | Список задач; query: `page`, `size`, `status`, `priority`. |
| POST | `/tasks` | Создание задачи; тело: `{ "title", "description"? }`. |
| GET | `/tasks/{id}` | Получение задачи по id (только владелец). |
| PATCH | `/tasks/{id}` | Обновление задачи (только владелец). |
| DELETE | `/tasks/{id}` | Удаление задачи (только владелец). |
| POST | `/tasks/export/csv` | Постановка экспорта в CSV в очередь; ответ: `{ "task_id", "status": "queued" }`. |
| GET | `/tasks/{id}/comments` | Список комментариев. |
| POST | `/tasks/{id}/comments` | Добавление комментария; тело: `{ "content" }`. |

### WebSocket

- **URL:** `ws://<хост>/api/v1/ws/tasks` (или через тот же origin, что и frontend).  
- Принимает подключения; может рассылать события обновления задач. Клиент может отправить `{"type":"ping"}` и получить `{"type":"pong"}`.

### Health

- **GET** `/health` — возвращает `{"status":"ok"}` (без авторизации). Используется для проверки в Docker/балансировщике.

---

## Разработка

- **Backend:** при изменении кода uvicorn с `--reload` перезапускается автоматически. Для линтинга — ruff, для проверки типов — mypy (если настроены).
- **Frontend:** HMR через Vite; запуск — `npm run dev`. Рекомендуется ESLint и строгий режим TypeScript.
- **БД:** Для изменения схемы используйте миграции Alembic (`alembic revision`, `alembic upgrade head`). В dev приложение при старте создаёт таблицы, если их нет.
- **OpenAPI:** Генерация типов клиента из `http://localhost:8000/openapi.json` (например, openapi-typescript-codegen) для синхронизации типов фронтенда с API.

---

## Тестирование

- **Backend:** Из каталога `backend/` выполнить `pytest`. Тесты используют тестовую БД (см. `tests/conftest.py`); в env или в conftest задаются `SECRET_KEY` и `DATABASE_URL`. Цель — покрытие >80%.
- **Frontend:** Unit-тесты — Vitest и React Testing Library; E2E — Playwright.  
- **CI:** В GitHub Actions запускаются линт backend (ruff) и тесты, а также сборка frontend (`npm run build`).

---

## Docker и развёртывание

- **Образы:** У backend и frontend есть Dockerfile; frontend — многоэтапная сборка (сборка на Node, раздача через nginx).
- **Compose:** В `infra/docker-compose.yml` описаны сервисы: backend, frontend, db (PostgreSQL), redis, celery. Backend и celery используют один и тот же код; celery запускается как `celery -A app.tasks.celery_app worker`.
- **Продакшен:** Задать надёжный `SECRET_KEY`, `ENVIRONMENT=prod` и реальный URL PostgreSQL. Обеспечить доступность Redis для Celery. Настроить Nginx или балансировщик перед приложением; включить HTTPS и флаг `secure` для куков.

---

## CI/CD

- **Workflow:** В `.github/workflows/ci.yml` задан запуск при push/PR в `main` и `develop`.
- **Backend:** установка зависимостей, ruff, pytest (с покрытием; при необходимости — падение при покрытии ниже 80%).
- **Frontend:** `npm ci`, `npm run build`.
- Шаг деплоя в шаблоне не добавлен; при необходимости добавьте задачу деплоя на свой сервер или PaaS.

---

## Безопасность

- Пароли хешируются **bcrypt** (количество раундов настраивается).
- **JWT** access- и refresh-токены; хранение в **HTTPOnly**-куках для снижения риска XSS.
- **Ротация refresh-токена** при каждом обновлении.
- **CORS** ограничен настроенными источниками.
- **Ограничение частоты запросов** на вход и регистрацию.
- **Валидация входных данных** через Pydantic для тел и query-параметров.
- **SQL-инъекции** снижаются за счёт использования ORM SQLAlchemy (параметризованные запросы).  
- Не коммитить `.env` и секреты; в продакшене использовать переменные окружения или менеджер секретов.

---
