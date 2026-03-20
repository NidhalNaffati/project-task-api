from sqlalchemy import Column, Integer, String, Float, Text, Table, ForeignKey
from sqlalchemy.types import TypeDecorator, Text as TextType
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
import json

from app.db.session import Base


class ArrayOfString(TypeDecorator):
    """
    Cross-database array type.
    - PostgreSQL: uses native ARRAY(String) for efficient ANY() queries.
    - SQLite (tests): serialises as JSON text.
    """
    impl = TextType
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(String))
        return dialect.type_descriptor(TextType())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is None:
            return "[]"
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value if value is not None else []
        if value is None:
            return []
        return json.loads(value)


# Association table for the many-to-many relationship between projects and tasks
project_task = Table(
    "project_task",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    budget = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    hours_used = Column(Float, nullable=False, default=0.0)

    tasks = relationship("Task", secondary=project_task, back_populates="projects")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(ArrayOfString, nullable=False, default=list)

    projects = relationship("Project", secondary=project_task, back_populates="tasks")
