"""
Seed script — populates the database with sample Projects and Tasks.
Run with:  docker compose exec app python scripts/seed.py
Or locally: python scripts/seed.py (with DATABASE_URL set)
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db.session import SessionLocal, engine, Base
from app.models.models import Project, Task

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # ── Tasks ────────────────────────────────────────────────────────────────
    tasks = [
        Task(title="Design database schema", description="Draw ER diagram and decide on indexes", tags=["backend", "database"]),
        Task(title="Implement REST API", description="Build CRUD endpoints with FastAPI", tags=["backend", "api"]),
        Task(title="Write unit tests", description="Cover all service functions with pytest", tags=["backend", "qa"]),
        Task(title="Build landing page", description="Create responsive landing page", tags=["frontend", "ui"]),
        Task(title="Set up CI/CD pipeline", description="Configure GitHub Actions for build and deploy", tags=["devops", "ci-cd"]),
        Task(title="Deploy to GKE", description="Containerise and deploy using Terraform on GCP", tags=["devops", "cloud", "gcp"]),
    ]
    db.add_all(tasks)
    db.flush()  # get IDs before commit

    # ── Projects ─────────────────────────────────────────────────────────────
    projects = [
        Project(
            name="Website Redesign",
            budget=50000.0,
            description="Redesign the company public website",
            hours_used=120.5,
            tasks=[tasks[0], tasks[1], tasks[3]],
        ),
        Project(
            name="Internal DevOps Tooling",
            budget=30000.0,
            description="Automate CI/CD and infrastructure provisioning",
            hours_used=80.0,
            tasks=[tasks[4], tasks[5]],
        ),
        Project(
            name="API Platform",
            budget=75000.0,
            description="Build a centralised API gateway and management layer",
            hours_used=200.0,
            tasks=[tasks[0], tasks[1], tasks[2]],
        ),
    ]
    db.add_all(projects)
    db.commit()

    print(f"✅ Seeded {len(tasks)} tasks and {len(projects)} projects successfully.")

except Exception as e:
    db.rollback()
    print(f"❌ Seed failed: {e}")
    raise
finally:
    db.close()
