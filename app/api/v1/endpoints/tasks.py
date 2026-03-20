from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.schemas import TaskCreate, TaskUpdate, TaskRead, TaskReadWithProjects
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/", response_model=list[TaskRead], summary="List all tasks")
def list_tasks(
    tag: str | None = Query(None, description="Filter tasks by tag"),
    db: Session = Depends(get_db),
):
    if tag:
        return task_service.get_by_tag(db, tag)
    return task_service.get_all(db)


@router.post("/", response_model=TaskRead, status_code=status.HTTP_201_CREATED, summary="Create a task")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    return task_service.create(db, payload)


@router.get("/{task_id}", response_model=TaskReadWithProjects, summary="Get a task by ID")
def get_task(task_id: int, db: Session = Depends(get_db)):
    return task_service.get_by_id(db, task_id)


@router.patch("/{task_id}", response_model=TaskRead, summary="Partially update a task")
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    return task_service.update(db, task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task_service.delete(db, task_id)
