"""Test authentication flow."""

def test_signup(test_client):
    response = test_client.post("/auth/signup", json={
        "email": "test@example.com",
        "password": "SecurePass123!",
        "name": "Test User"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "test@example.com"


def test_login(test_client):
    # signup first
    test_client.post("/auth/signup", json={
        "email": "login@example.com",
        "password": "SecurePass123!",
        "name": "Login User"
    })
    response = test_client.post("/auth/login", json={
        "email": "login@example.com",
        "password": "SecurePass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_login_wrong_password(test_client):
    test_client.post("/auth/signup", json={
        "email": "wrong@example.com",
        "password": "SecurePass123!"
    })
    response = test_client.post("/auth/login", json={
        "email": "wrong@example.com",
        "password": "WrongPass!"
    })
    assert response.status_code == 401


def test_logout(test_client):
    resp = test_client.post("/auth/signup", json={
        "email": "logout@example.com",
        "password": "SecurePass123!"
    })
    token = resp.json()["access_token"]
    response = test_client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_login_token_invalidated_after_logout(test_client):
    resp = test_client.post("/auth/signup", json={
        "email": "revoke@example.com",
        "password": "SecurePass123!"
    })
    token = resp.json()["access_token"]

    # Logout invalidates token
    test_client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})

    # Token should no longer work
    response = test_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_refresh_cookie_flow_and_logout_revocation(test_client):
    signup = test_client.post("/auth/signup", json={
        "email": "refresh@example.com",
        "password": "SecurePass123!",
        "name": "Refresh User",
    })
    access_token = signup.json()["access_token"]

    refresh_response = test_client.post("/auth/refresh")
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()
    assert "access_token" in refreshed
    assert refreshed["access_token"]

    logout_response = test_client.post("/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert logout_response.status_code == 200

    revoked_refresh = test_client.post("/auth/refresh")
    assert revoked_refresh.status_code == 401
