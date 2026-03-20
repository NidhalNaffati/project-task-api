# project-task-api — Deep Codebase Understanding

## What This Project Is

A **REST API** for managing **Projects** and **Tasks** with a **many-to-many relationship**, built with:

| Layer | Technology |
|---|---|
| Web Framework | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 |
| Database (prod) | PostgreSQL 16 |
| Database (tests) | SQLite in-memory |
| Validation | Pydantic v2 |
| Configuration | pydantic-settings |
| Containerization | Docker + Docker Compose |
| Testing | pytest + FastAPI TestClient |

---

## Project Structure

```
project-task-api/
├── app/
│   ├── main.py                    # FastAPI app entry point, lifespan, global exception handler
│   ├── core/
│   │   └── config.py              # Settings via pydantic-settings (DATABASE_URL, etc.)
│   ├── db/
│   │   └── session.py             # SQLAlchemy engine, session factory, get_db() dependency
│   ├── models/
│   │   └── models.py              # ORM models: Project, Task, project_task association table
│   ├── schemas/
│   │   └── schemas.py             # Pydantic schemas: Create/Update/Read variants for each entity
│   ├── services/
│   │   ├── project_service.py     # All project business logic + relationship management
│   │   └── task_service.py        # All task business logic + tag filtering
│   └── api/
│       └── v1/
│           ├── router.py          # Aggregates all sub-routers under /api/v1
│           └── endpoints/
│               ├── projects.py    # Project route handlers (thin layer — calls service)
│               └── tasks.py       # Task route handlers (thin layer — calls service)
├── tests/
│   ├── conftest.py                # Pytest fixtures: SQLite DB + TestClient per test
│   ├── test_projects.py           # Project CRUD + task assignment tests
│   └── test_tasks.py              # Task CRUD + tag filter tests
├── scripts/
│   └── seed.py                    # Seeds 6 tasks + 3 projects into the running DB
├── Dockerfile                     # python:3.12-slim, installs deps, runs uvicorn
├── docker-compose.yml             # postgres:16-alpine + app service with health check
├── requirements.txt               # Pinned dependencies
└── .env.example                   # Template for DATABASE_URL override
```

---

## Data Model

### Entities

**[Project](file:///home/ryuke/Downloads/project-task-api/app/models/models.py#48-58)** ([projects](file:///home/ryuke/Downloads/project-task-api/app/api/v1/endpoints/projects.py#11-14) table)
| Column | Type | Constraint |
|---|---|---|
| [id](file:///home/ryuke/Downloads/project-task-api/app/services/project_service.py#12-20) | Integer | PK, auto-increment |
| `name` | String(255) | NOT NULL |
| [budget](file:///home/ryuke/Downloads/project-task-api/tests/test_projects.py#51-54) | Float | NOT NULL |
| `description` | Text | nullable |
| `hours_used` | Float | NOT NULL, default 0.0 |

**[Task](file:///home/ryuke/Downloads/project-task-api/app/models/models.py#60-69)** ([tasks](file:///home/ryuke/Downloads/project-task-api/app/services/project_service.py#78-81) table)
| Column | Type | Constraint |
|---|---|---|
| [id](file:///home/ryuke/Downloads/project-task-api/app/services/project_service.py#12-20) | Integer | PK, auto-increment |
| [title](file:///home/ryuke/Downloads/project-task-api/tests/test_tasks.py#45-48) | String(255) | NOT NULL |
| `description` | Text | nullable |
| [tags](file:///home/ryuke/Downloads/project-task-api/app/schemas/schemas.py#31-40) | [ArrayOfString](file:///home/ryuke/Downloads/project-task-api/app/models/models.py#10-37) | NOT NULL, default `[]` |

**[project_task](file:///home/ryuke/Downloads/project-task-api/app/api/v1/endpoints/projects.py#38-41)** (association table — many-to-many)
| Column | Type |
|---|---|
| `project_id` | FK → projects.id (CASCADE DELETE) |
| `task_id` | FK → tasks.id (CASCADE DELETE) |

### Smart Cross-DB [ArrayOfString](file:///home/ryuke/Downloads/project-task-api/app/models/models.py#10-37) Type
A custom `TypeDecorator` that behaves differently per dialect:
- **PostgreSQL**: uses native `ARRAY(String)` → enables `= ANY(tags)` indexed queries
- **SQLite**: serialises/deserialises the list as a JSON string → works in tests without Postgres

---

## Pydantic Schemas

Each entity has a full family of schemas following Pydantic v2 conventions:

```
TaskCreate / ProjectCreate   →  Input for POST (all required fields)
TaskUpdate / ProjectUpdate   →  Input for PATCH (all fields Optional)
TaskRead / ProjectRead       →  Output (includes id, from_attributes=True)
TaskReadWithProjects         →  TaskRead + embedded list[ProjectRead]
ProjectReadWithTasks         →  ProjectRead + embedded list[TaskRead]
```

### Validation rules enforced by Pydantic:
- [budget](file:///home/ryuke/Downloads/project-task-api/tests/test_projects.py#51-54): must be `> 0` (`gt=0`)
- `hours_used`: must be `>= 0` (`ge=0`)
- [title](file:///home/ryuke/Downloads/project-task-api/tests/test_tasks.py#45-48) / `name`: `min_length=1`, `max_length=255`
- [tags](file:///home/ryuke/Downloads/project-task-api/app/schemas/schemas.py#31-40): each tag must be non-empty after `.strip()`; all tags are lowercased + stripped on ingress
- Forward reference resolution: `TaskReadWithProjects.model_rebuild()` called after both schema classes are defined (since they reference each other)

---

## Service Layer (Business Logic)

### [project_service.py](file:///home/ryuke/Downloads/project-task-api/app/services/project_service.py)
| Function | Description |
|---|---|
| [get_all(db)](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py#9-11) | Returns all projects |
| [get_by_id(db, id)](file:///home/ryuke/Downloads/project-task-api/app/services/project_service.py#12-20) | Returns project or raises 404 |
| [create(db, payload)](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py#23-29) | `model_dump()` → ORM object → commit |
| [update(db, id, payload)](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py#31-38) | `exclude_unset=True` → only update sent fields |
| [delete(db, id)](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py#40-44) | Deletes project (cascade removes [project_task](file:///home/ryuke/Downloads/project-task-api/app/api/v1/endpoints/projects.py#38-41) rows) |
| [assign_task(db, pid, tid)](file:///home/ryuke/Downloads/project-task-api/app/api/v1/endpoints/projects.py#43-51) | Validates both exist; checks for duplicate → 409; appends to `project.tasks` |
| [remove_task(db, pid, tid)](file:///home/ryuke/Downloads/project-task-api/app/services/project_service.py#64-76) | Checks task is in project before removing |
| [get_tasks(db, pid)](file:///home/ryuke/Downloads/project-task-api/app/services/project_service.py#78-81) | Returns `project.tasks` list |

### [task_service.py](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py)
| Function | Description |
|---|---|
| [get_all(db)](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py#9-11) | Returns all tasks |
| [get_by_id(db, id)](file:///home/ryuke/Downloads/project-task-api/app/services/project_service.py#12-20) | Returns task or raises 404 |
| [create(db, payload)](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py#23-29) | Standard create pattern |
| [update(db, id, payload)](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py#31-38) | Partial update using `exclude_unset=True` |
| [delete(db, id)](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py#40-44) | Deletes task (cascade removes [project_task](file:///home/ryuke/Downloads/project-task-api/app/api/v1/endpoints/projects.py#38-41) rows) |
| [get_by_tag(db, tag)](file:///home/ryuke/Downloads/project-task-api/app/services/task_service.py#46-62) | **PostgreSQL**: `normalized == any_(Task.tags)` · **SQLite**: Python-side filter |

---

## API Endpoints

All routes are prefixed with `/api/v1` (set in [main.py](file:///home/ryuke/Downloads/project-task-api/app/main.py) via `settings.API_V1_STR`).

### Projects (`/api/v1/projects/`)

| Method | Path | Response Schema | Status |
|---|---|---|---|
| GET | `/projects/` | `list[ProjectRead]` | 200 |
| POST | `/projects/` | [ProjectRead](file:///home/ryuke/Downloads/project-task-api/app/schemas/schemas.py#74-78) | 201 |
| GET | `/projects/{id}` | [ProjectReadWithTasks](file:///home/ryuke/Downloads/project-task-api/app/schemas/schemas.py#80-84) | 200 |
| PATCH | `/projects/{id}` | [ProjectRead](file:///home/ryuke/Downloads/project-task-api/app/schemas/schemas.py#74-78) | 200 |
| DELETE | `/projects/{id}` | — | 204 |
| GET | `/projects/{id}/tasks` | `list[TaskRead]` | 200 |
| POST | `/projects/{id}/tasks/{task_id}` | [ProjectReadWithTasks](file:///home/ryuke/Downloads/project-task-api/app/schemas/schemas.py#80-84) | 200 |
| DELETE | `/projects/{id}/tasks/{task_id}` | [ProjectReadWithTasks](file:///home/ryuke/Downloads/project-task-api/app/schemas/schemas.py#80-84) | 200 |

### Tasks (`/api/v1/tasks/`)

| Method | Path | Notes |
|---|---|---|
| GET | `/tasks/` | Optional `?tag=<string>` query param for filtering |
| POST | `/tasks/` | Creates task |
| GET | `/tasks/{id}` | Returns [TaskReadWithProjects](file:///home/ryuke/Downloads/project-task-api/app/schemas/schemas.py#48-52) (includes nested projects) |
| PATCH | `/tasks/{id}` | Partial update |
| DELETE | `/tasks/{id}` | 204 No Content |

### Health

| GET | `/` | Returns `{"status": "ok", "message": "..."}` |

---

## Request / Response Flow

```
HTTP Request
    ↓
FastAPI Router (projects.py / tasks.py)
    → Dependency injection: get_db() provides SQLAlchemy Session
    → Pydantic validates & parses request body
    ↓
Service Layer (project_service.py / task_service.py)
    → Contains all business logic
    → Raises HTTPException on error (404, 409, etc.)
    ↓
SQLAlchemy ORM
    → Queries / mutations against PostgreSQL (or SQLite in tests)
    ↓
FastAPI serialises ORM object → Pydantic response_model → JSON
```

A global `IntegrityError` handler in [main.py](file:///home/ryuke/Downloads/project-task-api/app/main.py) catches any unexpected DB constraint violations and returns `409 Conflict`.

---

## Application Startup

[main.py](file:///home/ryuke/Downloads/project-task-api/app/main.py) uses a FastAPI **lifespan** context manager:
```python
@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)   # Creates tables if not exist
    yield
```
> In production this would be replaced by **Alembic** migrations.

---

## Configuration

[app/core/config.py](file:///home/ryuke/Downloads/project-task-api/app/core/config.py) uses `pydantic-settings`:
```python
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/projectdb"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Project & Task API"
    class Config:
        env_file = ".env"
```
The `DATABASE_URL` can be overridden via environment variable or `.env` file — this is how tests swap in SQLite.

---

## Testing Strategy

Tests live in `tests/` and are isolated per function via pytest fixtures:

### [conftest.py](file:///home/ryuke/Downloads/project-task-api/tests/conftest.py)
- **Before import**: sets `DATABASE_URL=sqlite:///./test.db` via `os.environ` to prevent Postgres connections
- **[db](file:///home/ryuke/Downloads/project-task-api/tests/conftest.py#23-32) fixture** (function scope): creates all tables → yields session → drops all tables (clean state per test)
- **[client](file:///home/ryuke/Downloads/project-task-api/tests/conftest.py#34-46) fixture**: overrides FastAPI's [get_db](file:///home/ryuke/Downloads/project-task-api/app/db/session.py#14-20) dependency to inject the test SQLite session; uses `TestClient`

### Test Coverage

**[test_projects.py](file:///home/ryuke/Downloads/project-task-api/tests/test_projects.py)**
- CRUD: create, list, get by ID, 404 on missing, update, delete
- Validation: invalid budget (< 0) → 422
- Task assignment: assign task, list tasks, duplicate assignment → 409, remove task, task in multiple projects

**[test_tasks.py](file:///home/ryuke/Downloads/project-task-api/tests/test_tasks.py)**
- CRUD: create, list, get by ID, 404 on missing, update, delete
- Validation: missing title → 422, empty tag → 422
- Tag filtering: filter by tag, case-insensitive filtering, no match returns `[]`, task appears in its project

---

## Docker Setup

### [Dockerfile](file:///home/ryuke/Downloads/project-task-api/Dockerfile)
```
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt . → pip install
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Deps are installed before copying app code for better layer caching.

### [docker-compose.yml](file:///home/ryuke/Downloads/project-task-api/docker-compose.yml)
- **[db](file:///home/ryuke/Downloads/project-task-api/tests/conftest.py#23-32)** service: `postgres:16-alpine`, persisted volume, `pg_isready` health check (retries: 10, interval: 5s)
- **[app](file:///home/ryuke/Downloads/project-task-api/tests/test_tasks.py#78-84)** service: built from local Dockerfile, `depends_on: db: condition: service_healthy` — guarantees DB is ready before API starts

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Router → Service → Model** layering | Routers are thin (HTTP only); services hold all logic; testable in isolation |
| **PATCH over PUT** | Clients send only changed fields; `exclude_unset=True` prevents accidental nulling |
| **Services raise `HTTPException`** | Keeps error handling co-located with business rules; routers stay clean |
| **[ArrayOfString](file:///home/ryuke/Downloads/project-task-api/app/models/models.py#10-37) TypeDecorator** | Single codebase for both Postgres (native ARRAY) and SQLite (JSON text) |
| **Tags lowercased + stripped on ingress** | Normalisation happens at schema boundary, not in service code |
| **[project_task](file:///home/ryuke/Downloads/project-task-api/app/api/v1/endpoints/projects.py#38-41) CASCADE DELETEs** | Deleting a project/task automatically cleans up the join table |
| **`Base.metadata.create_all()` on startup** | Simple for a single-developer assignment; Alembic noted as the production path |
| **No auth, no pagination** | Explicitly out of scope per the assignment brief |
| **SQLite for tests** | No Postgres needed in CI; the `ARRAY` workaround handles the one incompatibility |
