"""
Integration tests for the /auth endpoints.

These tests exercise the full request/response cycle including
database writes, password hashing, and JWT issuance.
"""


class TestRegister:
    def test_register_success(self, client):
        payload = {"username": "newuser", "email": "new@example.com", "password": "strongpass1"}
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert data["is_active"] is True

    def test_register_duplicate_username(self, client, test_user):
        payload = {"username": "testuser", "email": "other@example.com", "password": "strongpass1"}
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_register_duplicate_email(self, client, test_user):
        payload = {"username": "uniqueuser", "email": "test@example.com", "password": "strongpass1"}
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_register_short_password(self, client):
        payload = {"username": "shortpass", "email": "short@example.com", "password": "abc"}
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        payload = {"username": "bademail", "email": "not-an-email", "password": "strongpass1"}
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_short_username(self, client):
        payload = {"username": "ab", "email": "ab@example.com", "password": "strongpass1"}
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client, test_user):
        response = client.post(
            "/auth/token",
            data={"username": "testuser", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        response = client.post(
            "/auth/token",
            data={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post(
            "/auth/token",
            data={"username": "ghost", "password": "password123"},
        )
        assert response.status_code == 401

    def test_login_returns_jwt_structure(self, client, test_user):
        """JWT should have three dot-separated base64 segments."""
        token = client.post(
            "/auth/token",
            data={"username": "testuser", "password": "password123"},
        ).json()["access_token"]
        parts = token.split(".")
        assert len(parts) == 3, "JWT must have header.payload.signature format"


class TestCurrentUser:
    def test_get_me_authenticated(self, client, auth_headers, test_user):
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

    def test_get_me_unauthenticated(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        response = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401

    def test_get_me_malformed_header(self, client):
        response = client.get("/auth/me", headers={"Authorization": "NotBearer token"})
        assert response.status_code == 401
