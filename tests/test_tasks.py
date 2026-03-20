import pytest


def create_task(client, title="Task", tags=None):
    return client.post("/api/v1/tasks/", json={"title": title, "tags": tags or []})


class TestTaskCRUD:
    def test_create_task(self, client):
        res = create_task(client, title="Write tests", tags=["backend", "qa"])
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Write tests"
        assert "backend" in data["tags"]

    def test_list_tasks(self, client):
        create_task(client, title="T1")
        create_task(client, title="T2")
        res = client.get("/api/v1/tasks/")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_get_task_by_id(self, client):
        task_id = create_task(client).json()["id"]
        res = client.get(f"/api/v1/tasks/{task_id}")
        assert res.status_code == 200
        assert res.json()["id"] == task_id

    def test_get_task_not_found(self, client):
        res = client.get("/api/v1/tasks/9999")
        assert res.status_code == 404

    def test_update_task(self, client):
        task_id = create_task(client, title="Old").json()["id"]
        res = client.patch(f"/api/v1/tasks/{task_id}", json={"title": "New", "tags": ["devops"]})
        assert res.status_code == 200
        assert res.json()["title"] == "New"
        assert res.json()["tags"] == ["devops"]

    def test_delete_task(self, client):
        task_id = create_task(client).json()["id"]
        assert client.delete(f"/api/v1/tasks/{task_id}").status_code == 204
        assert client.get(f"/api/v1/tasks/{task_id}").status_code == 404

    def test_create_task_missing_title(self, client):
        res = client.post("/api/v1/tasks/", json={"tags": ["x"]})
        assert res.status_code == 422

    def test_create_task_empty_tag(self, client):
        res = create_task(client, tags=["", "valid"])
        assert res.status_code == 422


class TestTaskFilterByTag:
    def test_filter_by_tag(self, client):
        create_task(client, title="T1", tags=["backend", "api"])
        create_task(client, title="T2", tags=["frontend"])
        create_task(client, title="T3", tags=["backend"])

        res = client.get("/api/v1/tasks/?tag=backend")
        assert res.status_code == 200
        results = res.json()
        assert len(results) == 2
        assert all("backend" in t["tags"] for t in results)

    def test_filter_by_tag_case_insensitive(self, client):
        create_task(client, title="T1", tags=["Backend"])
        res = client.get("/api/v1/tasks/?tag=backend")
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_filter_by_nonexistent_tag(self, client):
        create_task(client, title="T1", tags=["api"])
        res = client.get("/api/v1/tasks/?tag=devops")
        assert res.status_code == 200
        assert res.json() == []

    def test_task_appears_in_its_projects(self, client):
        task_id = create_task(client, title="Shared").json()["id"]
        p = client.post("/api/v1/projects/", json={"name": "P", "budget": 1000, "hours_used": 0}).json()
        client.post(f"/api/v1/projects/{p['id']}/tasks/{task_id}")
        res = client.get(f"/api/v1/tasks/{task_id}")
        assert any(proj["id"] == p["id"] for proj in res.json()["projects"])
