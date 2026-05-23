"""Test basic health and root endpoints."""


def test_health_check(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_root(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "2.0.0"
    assert "Resume Analysis" in data["features"]
