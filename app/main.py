from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import engine, Base


import time
from sqlalchemy.exc import OperationalError

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cloud Run's Cloud SQL proxy sidecar can take a second to start. 
    # We retry the DB connection a few times before giving up.
    retries = 5
    for attempt in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database connection successful.")
            break
        except OperationalError as e:
            if attempt < retries - 1:
                print(f"Database not ready, retrying in 2 seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(2)
            else:
                print("Failed to connect to the database after multiple attempts.")
                raise e
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
