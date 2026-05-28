"""Test application tracking endpoints."""


def _auth_header(test_client):
    resp = test_client.post("/auth/signup", json={
        "email": "app@example.com",
        "password": "SecurePass123!",
        "name": "App User"
    })
    # If account already exists, login instead
    if resp.status_code == 409:
        resp = test_client.post("/auth/login", json={
            "email": "app@example.com",
            "password": "SecurePass123!",
        })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_create_and_list_applications(test_client):
    headers = _auth_header(test_client)
    resp = test_client.post("/applications/", json={
        "company": "Acme Corp",
        "role": "Python Engineer",
        "source": "LinkedIn",
        "status": "Saved"
    }, headers=headers)
    assert resp.status_code == 200

    resp = test_client.get("/applications/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["company"] == "Acme Corp"


def test_update_application_status(test_client):
    headers = _auth_header(test_client)
    resp = test_client.post("/applications/", json={
        "company": "Tech Ltd",
        "role": "Data Scientist"
    }, headers=headers)
    app_id = resp.json()["id"]

    resp = test_client.patch(f"/applications/{app_id}/status", json={"status": "Applied"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "Applied"


def test_delete_application(test_client):
    headers = _auth_header(test_client)
    resp = test_client.post("/applications/", json={
        "company": "Delete Me",
        "role": "DevOps"
    }, headers=headers)
    app_id = resp.json()["id"]

    resp = test_client.delete(f"/applications/{app_id}", headers=headers)
    assert resp.status_code == 200

    resp = test_client.get(f"/applications/{app_id}", headers=headers)
    assert resp.status_code == 404
