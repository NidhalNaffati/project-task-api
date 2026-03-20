from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.schemas import ProjectCreate, ProjectUpdate, ProjectRead, ProjectReadWithTasks, TaskRead
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("/", response_model=list[ProjectRead], summary="List all projects")
def list_projects(db: Session = Depends(get_db)):
    return project_service.get_all(db)


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED, summary="Create a project")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    return project_service.create(db, payload)


@router.get("/{project_id}", response_model=ProjectReadWithTasks, summary="Get a project by ID")
def get_project(project_id: int, db: Session = Depends(get_db)):
    return project_service.get_by_id(db, project_id)


@router.patch("/{project_id}", response_model=ProjectRead, summary="Partially update a project")
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    return project_service.update(db, project_id, payload)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a project")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project_service.delete(db, project_id)


# ── Task assignment sub-resource ─────────────────────────────────────────────

@router.get("/{project_id}/tasks", response_model=list[TaskRead], summary="Get all tasks for a project")
def get_project_tasks(project_id: int, db: Session = Depends(get_db)):
    return project_service.get_tasks(db, project_id)


@router.post(
    "/{project_id}/tasks/{task_id}",
    response_model=ProjectReadWithTasks,
    status_code=status.HTTP_200_OK,
    summary="Assign a task to a project",
)
def assign_task(project_id: int, task_id: int, db: Session = Depends(get_db)):
    return project_service.assign_task(db, project_id, task_id)


@router.delete(
    "/{project_id}/tasks/{task_id}",
    response_model=ProjectReadWithTasks,
    summary="Remove a task from a project",
)
def remove_task(project_id: int, task_id: int, db: Session = Depends(get_db)):
    return project_service.remove_task(db, project_id, task_id)
