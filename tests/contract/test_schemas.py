"""
Contract tests — validate that API responses conform to expected schemas.

These tests act as a "contract" between the API producer and consumers:
if a schema changes in a breaking way, these tests catch it immediately.
"""

import pytest
from jsonschema import ValidationError, validate

# ── JSON Schema definitions (consumer-side contract) ─────────────────────────

BOOK_SCHEMA = {
    "type": "object",
    "required": ["id", "title", "author", "isbn", "price", "in_stock", "created_at"],
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "title": {"type": "string", "minLength": 1},
        "author": {"type": "string", "minLength": 1},
        "isbn": {"type": "string", "pattern": r"^\d{10}(\d{3})?$"},
        "price": {"type": "number", "exclusiveMinimum": 0},
        "genre": {"type": ["string", "null"]},
        "published_year": {"type": ["integer", "null"]},
        "in_stock": {"type": "boolean"},
        "owner_id": {"type": ["integer", "null"]},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": ["string", "null"], "format": "date-time"},
    },
    "additionalProperties": False,
}

BOOK_LIST_SCHEMA = {
    "type": "object",
    "required": ["total", "page", "page_size", "items"],
    "properties": {
        "total": {"type": "integer", "minimum": 0},
        "page": {"type": "integer", "minimum": 1},
        "page_size": {"type": "integer", "minimum": 1},
        "items": {"type": "array", "items": BOOK_SCHEMA},
    },
    "additionalProperties": False,
}

USER_SCHEMA = {
    "type": "object",
    "required": ["id", "username", "email", "is_active", "created_at"],
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "username": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "is_active": {"type": "boolean"},
        "created_at": {"type": "string", "format": "date-time"},
    },
    "additionalProperties": False,
}

TOKEN_SCHEMA = {
    "type": "object",
    "required": ["access_token", "token_type"],
    "properties": {
        "access_token": {"type": "string", "minLength": 1},
        "token_type": {"type": "string", "enum": ["bearer"]},
    },
    "additionalProperties": False,
}

HEALTH_SCHEMA = {
    "type": "object",
    "required": ["status", "version", "database"],
    "properties": {
        "status": {"type": "string", "enum": ["ok", "degraded", "error"]},
        "version": {"type": "string"},
        "database": {"type": "string", "enum": ["ok", "error"]},
    },
    "additionalProperties": False,
}

ERROR_SCHEMA = {
    "type": "object",
    "required": ["detail"],
    "properties": {
        "detail": {"type": ["string", "array"]},
    },
}


# ── Contract test helpers ─────────────────────────────────────────────────────


def assert_conforms(data: dict, schema: dict) -> None:
    """Assert that `data` validates against `schema`, with a clear failure message."""
    try:
        validate(instance=data, schema=schema)
    except ValidationError as exc:
        pytest.fail(f"Schema contract violation: {exc.message}\nPath: {list(exc.path)}")


# ── Health endpoint contract ──────────────────────────────────────────────────


class TestHealthContract:
    def test_health_response_schema(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert_conforms(response.json(), HEALTH_SCHEMA)

    def test_health_status_is_ok(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_has_version(self, client):
        data = client.get("/health").json()
        assert data["version"] != ""


# ── Auth endpoint contracts ───────────────────────────────────────────────────


class TestAuthContract:
    def test_register_response_schema(self, client):
        payload = {
            "username": "contractuser",
            "email": "contract@test.com",
            "password": "securepass",
        }
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 201
        assert_conforms(response.json(), USER_SCHEMA)

    def test_register_does_not_expose_password(self, client):
        payload = {"username": "nopassword", "email": "nopass@test.com", "password": "securepass"}
        data = client.post("/auth/register", json=payload).json()
        assert "password" not in data
        assert "hashed_password" not in data

    def test_token_response_schema(self, client, test_user):
        response = client.post(
            "/auth/token",
            data={"username": "testuser", "password": "password123"},
        )
        assert response.status_code == 200
        assert_conforms(response.json(), TOKEN_SCHEMA)

    def test_token_type_is_bearer(self, client, test_user):
        data = client.post(
            "/auth/token",
            data={"username": "testuser", "password": "password123"},
        ).json()
        assert data["token_type"] == "bearer"

    def test_me_response_schema(self, client, auth_headers):
        response = client.get("/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert_conforms(response.json(), USER_SCHEMA)

    def test_unauthorized_error_schema(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401
        assert_conforms(response.json(), ERROR_SCHEMA)


# ── Book endpoint contracts ───────────────────────────────────────────────────


class TestBookContract:
    def test_list_books_schema(self, client, sample_books):
        response = client.get("/books")
        assert response.status_code == 200
        assert_conforms(response.json(), BOOK_LIST_SCHEMA)

    def test_get_book_schema(self, client, sample_book):
        response = client.get(f"/books/{sample_book.id}")
        assert response.status_code == 200
        assert_conforms(response.json(), BOOK_SCHEMA)

    def test_create_book_schema(self, client, auth_headers):
        payload = {
            "title": "Contract Test Book",
            "author": "Test Author",
            "isbn": "9781234567890",
            "price": 29.99,
            "genre": "Testing",
            "published_year": 2024,
            "in_stock": True,
        }
        response = client.post("/books", json=payload, headers=auth_headers)
        assert response.status_code == 201
        assert_conforms(response.json(), BOOK_SCHEMA)

    def test_not_found_error_schema(self, client):
        response = client.get("/books/999999")
        assert response.status_code == 404
        assert_conforms(response.json(), ERROR_SCHEMA)

    def test_validation_error_schema(self, client, auth_headers):
        """Pydantic validation errors should return 422 with a structured body."""
        response = client.post("/books", json={"title": ""}, headers=auth_headers)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)

    def test_isbn_field_is_digits_only(self, client, sample_book):
        """ISBN in response must contain only digits (no hyphens)."""
        data = client.get(f"/books/{sample_book.id}").json()
        assert data["isbn"].isdigit()
