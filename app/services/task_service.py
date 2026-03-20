from sqlalchemy.orm import Session
from sqlalchemy import any_, inspect
from fastapi import HTTPException, status

from app.models.models import Task
from app.schemas.schemas import TaskCreate, TaskUpdate


def get_all(db: Session) -> list[Task]:
    return db.query(Task).all()


def get_by_id(db: Session, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )
    return task


def create(db: Session, payload: TaskCreate) -> Task:
    task = Task(**payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update(db: Session, task_id: int, payload: TaskUpdate) -> Task:
    task = get_by_id(db, task_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete(db: Session, task_id: int) -> None:
    task = get_by_id(db, task_id)
    db.delete(task)
    db.commit()


def get_by_tag(db: Session, tag: str) -> list[Task]:
    """Return all tasks that contain the given tag (case-insensitive).

    - PostgreSQL: uses native `= ANY(tags)` for indexed array lookup.
    - SQLite (test env): falls back to an in-memory filter on the JSON-serialised column.
    """
    normalized = tag.strip().lower()
    dialect = db.bind.dialect.name  # type: ignore[union-attr]

    if dialect == "postgresql":
        return db.query(Task).filter(normalized == any_(Task.tags)).all()

    # SQLite fallback — load all tasks and filter in Python
    # Acceptable for tests; in production Postgres is always used.
    all_tasks = db.query(Task).all()
    return [t for t in all_tasks if normalized in (t.tags or [])]
