from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import Project, Task
from app.schemas.schemas import ProjectCreate, ProjectUpdate


def get_all(db: Session) -> list[Project]:
    return db.query(Project).all()


def get_by_id(db: Session, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found",
        )
    return project


def create(db: Session, payload: ProjectCreate) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update(db: Session, project_id: int, payload: ProjectUpdate) -> Project:
    project = get_by_id(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete(db: Session, project_id: int) -> None:
    project = get_by_id(db, project_id)
    db.delete(project)
    db.commit()


def assign_task(db: Session, project_id: int, task_id: int) -> Project:
    project = get_by_id(db, project_id)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )
    if task in project.tasks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task {task_id} is already assigned to project {project_id}",
        )
    project.tasks.append(task)
    db.commit()
    db.refresh(project)
    return project


def remove_task(db: Session, project_id: int, task_id: int) -> Project:
    project = get_by_id(db, project_id)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task or task not in project.tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} is not assigned to project {project_id}",
        )
    project.tasks.remove(task)
    db.commit()
    db.refresh(project)
    return project


def get_tasks(db: Session, project_id: int) -> list[Task]:
    project = get_by_id(db, project_id)
    return project.tasks
