from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ── Task schemas ────────────────────────────────────────────────────────────

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, examples=["Design database schema"])
    description: Optional[str] = Field(None, examples=["Draw the ER diagram and decide on indexes"])
    tags: list[str] = Field(default_factory=list, examples=[["backend", "database"]])

    @field_validator("tags")
    @classmethod
    def tags_must_be_non_empty_strings(cls, v: list[str]) -> list[str]:
        for tag in v:
            if not tag.strip():
                raise ValueError("Tags must not be empty strings")
        return [t.strip().lower() for t in v]


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[list[str]] = None

    @field_validator("tags")
    @classmethod
    def tags_must_be_non_empty_strings(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        for tag in v:
            if not tag.strip():
                raise ValueError("Tags must not be empty strings")
        return [t.strip().lower() for t in v]


class TaskRead(TaskBase):
    id: int

    model_config = {"from_attributes": True}


class TaskReadWithProjects(TaskRead):
    projects: list[ProjectRead] = []

    model_config = {"from_attributes": True}


# ── Project schemas ──────────────────────────────────────────────────────────

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Website Redesign"])
    budget: float = Field(..., gt=0, examples=[50000.0])
    description: Optional[str] = Field(None, examples=["Redesign the company public website"])
    hours_used: float = Field(default=0.0, ge=0, examples=[120.5])


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    budget: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    hours_used: Optional[float] = Field(None, ge=0)


class ProjectRead(ProjectBase):
    id: int

    model_config = {"from_attributes": True}


class ProjectReadWithTasks(ProjectRead):
    tasks: list[TaskRead] = []

    model_config = {"from_attributes": True}


# resolve forward references
TaskReadWithProjects.model_rebuild()
