# Project & Task API

A REST API to manage **Projects** and **Tasks** with a many-to-many relationship, built with FastAPI, PostgreSQL, and Docker.

---

## Quick Start

```bash
git clone <your-repo-url>
cd project-task-api
docker compose up --build
```

The API will be available at **http://localhost:8000**  
Interactive docs (Swagger UI): **http://localhost:8000/docs**  
Alternative docs (ReDoc): **http://localhost:8000/redoc**

### Seed sample data

```bash
docker compose exec app python scripts/seed.py
```

---

## API Endpoints

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/projects/` | List all projects |
| `POST` | `/api/v1/projects/` | Create a project |
| `GET` | `/api/v1/projects/{id}` | Get a project (includes its tasks) |
| `PATCH` | `/api/v1/projects/{id}` | Partially update a project |
| `DELETE` | `/api/v1/projects/{id}` | Delete a project |
| `GET` | `/api/v1/projects/{id}/tasks` | **Get all tasks belonging to a project** |
| `POST` | `/api/v1/projects/{id}/tasks/{task_id}` | Assign a task to a project |
| `DELETE` | `/api/v1/projects/{id}/tasks/{task_id}` | Remove a task from a project |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/tasks/` | List all tasks |
| `GET` | `/api/v1/tasks/?tag=backend` | **Filter tasks by tag** |
| `POST` | `/api/v1/tasks/` | Create a task |
| `GET` | `/api/v1/tasks/{id}` | Get a task (includes its projects) |
| `PATCH` | `/api/v1/tasks/{id}` | Partially update a task |
| `DELETE` | `/api/v1/tasks/{id}` | Delete a task |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |

---

## Example Requests

**Create a project**
```bash
curl -X POST http://localhost:8000/api/v1/projects/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Website Redesign", "budget": 50000, "hours_used": 0}'
```

**Create a task**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Design schema", "tags": ["backend", "database"]}'
```

**Assign task 1 to project 1**
```bash
curl -X POST http://localhost:8000/api/v1/projects/1/tasks/1
```

**Get all tasks for project 1**
```bash
curl http://localhost:8000/api/v1/projects/1/tasks
```

**Filter tasks by tag**
```bash
curl "http://localhost:8000/api/v1/tasks/?tag=backend"
```

---

## Running Tests

Tests use **SQLite in-memory** so no running database is required.

```bash
# Install dependencies locally
pip install -r requirements.txt

# Run tests
pytest -v
```

---

## Architecture & Key Decisions

### Project structure

```
app/
├── api/v1/endpoints/   # Route handlers (thin layer — delegate to services)
├── core/               # App configuration (pydantic-settings)
├── db/                 # SQLAlchemy engine, session, Base
├── models/             # ORM models
├── schemas/            # Pydantic request/response schemas
└── services/           # Business logic (CRUD operations)
```

### Layered architecture

The codebase follows a clean **router → service → model** separation:

- **Routers** handle HTTP concerns only (status codes, dependency injection).
- **Services** contain all business logic and raise `HTTPException` when invariants are violated (e.g. duplicate assignment, not found).
- **Models** are pure SQLAlchemy declarations with no business logic.

This makes the code testable in isolation and easy to extend.

### Many-to-many relationship

Tasks and Projects share a many-to-many relationship via an explicit `project_task` association table with `CASCADE` deletes. A task can belong to multiple projects simultaneously, and a project can contain multiple tasks. The relationship is managed through the `/projects/{id}/tasks/{task_id}` sub-resource endpoints, keeping the task resource itself free of project-specific concerns.

### Tag filtering

Tags are stored as a native **PostgreSQL `ARRAY(String)`** column on the Task model. Filtering uses SQLAlchemy's `any_()` construct, which translates to a native `= ANY(tags)` SQL expression — efficient and index-friendly without requiring a separate tags table for this scale.

> **Trade-off:** A normalised tags table would be better for large-scale tag analytics (counts, autocomplete). For this scope, the array column keeps the schema simple and queries fast.

### PATCH over PUT

All update endpoints use `PATCH` (partial update) rather than `PUT` (full replacement). This is more ergonomic for clients — they only need to send the fields they want to change — and avoids accidentally nulling out fields the client didn't intend to modify.

### Input validation

Pydantic schemas enforce constraints at the API boundary:
- `budget` must be `> 0`
- `hours_used` must be `>= 0`
- Tags are trimmed and lowercased on ingress, and empty string tags are rejected
- String fields have `min_length` and `max_length` bounds

### Docker & health checks

The `docker-compose.yml` uses a `healthcheck` on the `db` service with `pg_isready`, and the `app` service declares `depends_on: db: condition: service_healthy`. This ensures the API container only starts after PostgreSQL is ready to accept connections, preventing connection errors on cold starts.

---

## Assumptions & Trade-offs

| Decision | Rationale |
|----------|-----------|
| `Base.metadata.create_all()` on startup | Sufficient for an assignment; in production this would be replaced by Alembic migrations for controlled schema versioning |
| SQLite for tests | Avoids spinning up a real Postgres instance in CI; the one caveat is that `ARRAY` is Postgres-specific, so the tag filter test uses SQLite-compatible behaviour via the service layer |
| No authentication | Out of scope per the assignment brief |
| No pagination | Acceptable for the dataset sizes implied by the assignment |
| `PATCH` instead of `PUT` | More REST-idiomatic for partial updates |
