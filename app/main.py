from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (Alembic handles migrations in production)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "A REST API to manage **Projects** and **Tasks** with a many-to-many relationship.\n\n"
        "- Full CRUD for both entities\n"
        "- Filter tasks by tag: `GET /api/v1/tasks?tag=backend`\n"
        "- Get all tasks of a project: `GET /api/v1/projects/{id}/tasks`\n"
        "- Assign / remove tasks to/from projects\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "Database integrity error. The record may already exist or violates a constraint."},
    )


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "Project & Task API is running"}
