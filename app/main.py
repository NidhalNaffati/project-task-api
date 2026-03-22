from contextlib import asynccontextmanager
import os

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


def _detect_version() -> str:
    """Determine the application version string.

    Priority:
    1) APP_VERSION or VERSION env vars (manual override)
    2) VERSION file at repo root (optional)
    3) GIT_SHA or IMAGE_TAG (CI/CD release identifier)
    4) fallback: "1.0.0"
    """
    env_version = os.getenv("APP_VERSION") or os.getenv("VERSION")
    if env_version:
        return env_version.strip()

    try:
        # When running inside the container, WORKDIR is /app.
        version_path = os.path.join(os.getcwd(), "VERSION")
        with open(version_path, "r", encoding="utf-8") as f:
            file_version = f.read().strip()
            if file_version:
                return file_version
    except OSError:
        pass

    sha = os.getenv("GIT_SHA") or os.getenv("IMAGE_TAG")
    if sha:
        return sha.strip()[:12]

    return "1.0.0"


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    version=_detect_version(),
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

    # Prefer an injected release identifier from CI/CD (commit SHA / image tag).
    # - In GitHub Actions we can pass IMAGE_TAG=${{ github.sha }} to Cloud Run.
    # - `deploy-app.sh` can propagate it to the container as IMAGE_TAG.
    release = os.getenv("GIT_SHA") or os.getenv("IMAGE_TAG")
    return {
        "status": "ok",
        "message": "Project & Task API is running",
        "version": app.version,
        "release": release,
    }


@app.get("/version", tags=["Health"], summary="Return running app version and release identifier")
def version():
    release = os.getenv("GIT_SHA") or os.getenv("IMAGE_TAG")
    return {"version": app.version, "release": release}


@app.get("/build", tags=["Health"], summary="Return build metadata useful for CI/CD")
def build_info():
    # Common CI providers set one or more of these.
    return {
        "version": app.version,
        "release": os.getenv("GIT_SHA") or os.getenv("IMAGE_TAG"),
        "image": os.getenv("IMAGE_URI"),
        "service": os.getenv("K_SERVICE"),
        "revision": os.getenv("K_REVISION"),
        "configuration": os.getenv("K_CONFIGURATION"),
    }
