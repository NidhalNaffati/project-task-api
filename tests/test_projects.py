import pytest


def create_project(client, name="Alpha", budget=10000.0, hours_used=0.0):
    return client.post("/api/v1/projects/", json={"name": name, "budget": budget, "hours_used": hours_used})


def create_task(client, title="Task 1", tags=None):
    return client.post("/api/v1/tasks/", json={"title": title, "tags": tags or []})


class TestProjectCRUD:
    def test_create_project(self, client):
        res = create_project(client)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Alpha"
        assert data["budget"] == 10000.0
        assert "id" in data

    def test_list_projects(self, client):
        create_project(client, name="P1")
        create_project(client, name="P2")
        res = client.get("/api/v1/projects/")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_get_project_by_id(self, client):
        project_id = create_project(client).json()["id"]
        res = client.get(f"/api/v1/projects/{project_id}")
        assert res.status_code == 200
        assert res.json()["id"] == project_id

    def test_get_project_not_found(self, client):
        res = client.get("/api/v1/projects/9999")
        assert res.status_code == 404

    def test_update_project(self, client):
        project_id = create_project(client).json()["id"]
        res = client.patch(f"/api/v1/projects/{project_id}", json={"name": "Updated", "hours_used": 42.0})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"
        assert res.json()["hours_used"] == 42.0

    def test_delete_project(self, client):
        project_id = create_project(client).json()["id"]
        res = client.delete(f"/api/v1/projects/{project_id}")
        assert res.status_code == 204
        assert client.get(f"/api/v1/projects/{project_id}").status_code == 404

    def test_create_project_invalid_budget(self, client):
        res = client.post("/api/v1/projects/", json={"name": "Bad", "budget": -100, "hours_used": 0})
        assert res.status_code == 422


class TestProjectTaskAssignment:
    def test_assign_and_list_tasks(self, client):
        project_id = create_project(client).json()["id"]
        task_id = create_task(client, title="T1").json()["id"]

        res = client.post(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        assert res.status_code == 200
        assert any(t["id"] == task_id for t in res.json()["tasks"])

        tasks = client.get(f"/api/v1/projects/{project_id}/tasks").json()
        assert len(tasks) == 1

    def test_assign_duplicate_task(self, client):
        project_id = create_project(client).json()["id"]
        task_id = create_task(client).json()["id"]
        client.post(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        res = client.post(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        assert res.status_code == 409

    def test_remove_task_from_project(self, client):
        project_id = create_project(client).json()["id"]
        task_id = create_task(client).json()["id"]
        client.post(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        res = client.delete(f"/api/v1/projects/{project_id}/tasks/{task_id}")
        assert res.status_code == 200
        assert res.json()["tasks"] == []

    def test_task_belongs_to_multiple_projects(self, client):
        p1 = create_project(client, name="P1").json()["id"]
        p2 = create_project(client, name="P2").json()["id"]
        task_id = create_task(client).json()["id"]
        client.post(f"/api/v1/projects/{p1}/tasks/{task_id}")
        client.post(f"/api/v1/projects/{p2}/tasks/{task_id}")
        assert len(client.get(f"/api/v1/projects/{p1}/tasks").json()) == 1
        assert len(client.get(f"/api/v1/projects/{p2}/tasks").json()) == 1
