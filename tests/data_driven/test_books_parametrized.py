"""
Data-driven tests for the Bookstore API.

Uses pytest.mark.parametrize and external JSON datasets to run the same
test logic across many input variations without duplicating test code.
"""

import json
from pathlib import Path

import pytest

DATASETS_DIR = Path(__file__).parent / "datasets"


def load_dataset(filename: str) -> list[dict]:
    with open(DATASETS_DIR / filename) as f:
        return json.load(f)


# ── Helpers ───────────────────────────────────────────────────────────────────


def idfn(val):
    """Use the 'id' field from dataset entries as the test ID."""
    if isinstance(val, dict) and "id" in val:
        return val["id"]
    return str(val)


# ── Valid book creation ───────────────────────────────────────────────────────

VALID_BOOKS = load_dataset("valid_books.json")


@pytest.mark.parametrize("book_data", VALID_BOOKS, ids=idfn)
def test_create_valid_book(client, auth_headers, book_data):
    """Each valid book dataset entry should create successfully."""
    payload = {k: v for k, v in book_data.items() if k != "id"}
    response = client.post("/books", json=payload, headers=auth_headers)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["title"] == book_data["title"]
    assert data["author"] == book_data["author"]
    assert data["isbn"] == book_data["isbn"]
    assert data["price"] == book_data["price"]


@pytest.mark.parametrize("book_data", VALID_BOOKS, ids=idfn)
def test_created_book_is_retrievable(client, auth_headers, book_data):
    """Books created via POST should be retrievable via GET."""
    payload = {k: v for k, v in book_data.items() if k != "id"}
    create_response = client.post("/books", json=payload, headers=auth_headers)
    assert create_response.status_code == 201
    book_id = create_response.json()["id"]

    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == book_id


# ── Invalid book creation ─────────────────────────────────────────────────────

INVALID_BOOKS = load_dataset("invalid_books.json")


@pytest.mark.parametrize("case", INVALID_BOOKS, ids=idfn)
def test_create_invalid_book_rejected(client, auth_headers, case):
    """Each invalid book dataset entry should be rejected with the expected status."""
    response = client.post("/books", json=case["payload"], headers=auth_headers)
    assert response.status_code == case["expected_status"], (
        f"[{case['id']}] {case['description']}: "
        f"expected {case['expected_status']}, got {response.status_code}"
    )


@pytest.mark.parametrize("case", INVALID_BOOKS, ids=idfn)
def test_invalid_book_error_mentions_field(client, auth_headers, case):
    """Validation errors should reference the offending field."""
    response = client.post("/books", json=case["payload"], headers=auth_headers)
    if response.status_code == 422:
        errors = response.json()["detail"]
        field_names = [
            loc for error in errors for loc in error.get("loc", []) if isinstance(loc, str)
        ]
        assert case["expected_error_field"] in field_names, (
            f"[{case['id']}] Expected field '{case['expected_error_field']}' "
            f"in error locations, got: {field_names}"
        )


# ── User registration ─────────────────────────────────────────────────────────

USERS = load_dataset("users.json")


@pytest.mark.parametrize("user_data", USERS, ids=idfn)
def test_user_registration(client, user_data):
    """Test user registration with various valid and invalid inputs."""
    payload = {k: v for k, v in user_data.items() if k not in ("id", "expected_status")}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == user_data["expected_status"], (
        f"[{user_data['id']}] Expected {user_data['expected_status']}, "
        f"got {response.status_code}: {response.text}"
    )


# ── Price boundary tests ──────────────────────────────────────────────────────

PRICE_CASES = [
    pytest.param(0.01, 201, id="minimum_valid_price"),
    pytest.param(1.00, 201, id="one_dollar"),
    pytest.param(999.99, 201, id="high_price"),
    pytest.param(9999.99, 201, id="very_high_price"),
    pytest.param(0.00, 422, id="zero_price"),
    pytest.param(-0.01, 422, id="just_below_zero"),
    pytest.param(-100.0, 422, id="negative_price"),
]


@pytest.mark.parametrize("price,expected_status", PRICE_CASES)
def test_book_price_boundaries(client, auth_headers, price, expected_status):
    """Verify price validation boundaries."""
    payload = {
        "title": f"Price Test Book {price}",
        "author": "Test Author",
        "isbn": f"978{abs(int(price * 100)):010d}"[:13].ljust(13, "0"),
        "price": price,
    }
    response = client.post("/books", json=payload, headers=auth_headers)
    assert response.status_code == expected_status


# ── Pagination boundary tests ─────────────────────────────────────────────────

PAGINATION_CASES = [
    pytest.param(1, 1, 200, id="first_page_min_size"),
    pytest.param(1, 10, 200, id="first_page_default_size"),
    pytest.param(1, 100, 200, id="first_page_max_size"),
    pytest.param(2, 5, 200, id="second_page"),
    pytest.param(0, 10, 422, id="page_zero_invalid"),
    pytest.param(1, 0, 422, id="page_size_zero_invalid"),
    pytest.param(1, 101, 422, id="page_size_over_max"),
]


@pytest.mark.parametrize("page,page_size,expected_status", PAGINATION_CASES)
def test_pagination_boundaries(client, page, page_size, expected_status):
    """Verify pagination parameter validation."""
    response = client.get(f"/books?page={page}&page_size={page_size}")
    assert response.status_code == expected_status


# ── Genre filter tests ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "genre,expected_count",
    [
        pytest.param("Programming", 3, id="programming_books"),
        pytest.param("Science Fiction", 2, id="scifi_books"),
        pytest.param("NonExistentGenre", 0, id="no_match"),
        pytest.param("programming", 3, id="case_insensitive"),  # ilike search
    ],
)
def test_filter_by_genre(client, sample_books, genre, expected_count):
    """Genre filter should be case-insensitive and return correct counts."""
    response = client.get(f"/books?genre={genre}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == expected_count, (
        f"Genre '{genre}': expected {expected_count} books, got {data['total']}"
    )
